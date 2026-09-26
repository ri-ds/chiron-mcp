"""End-to-end test of the Ask server against a live Chiron.

Sends real questions through /ask exactly as the page does, then checks every
artefact a user would see or click:

  * the figure the answer states matches ground truth computed independently, in raw
    SQL against the warehouse, not through Chiron or this server
  * the Query button's cohort, loaded into Chiron, makes Chiron's own count (the
    "Subject Count" the UI shows) equal the figure the answer states
  * a Report link opens, has at least one column, and reports the same subjects
  * refusals are refusals: no figures, no buttons
  * the answer carries no clutter the page would render twice

Run against the synthea-10k deployment:

    .venv/bin/python tests/ask_e2e.py            # all cases, 4 at a time
    .venv/bin/python tests/ask_e2e.py asthma     # cases whose id contains "asthma"

Needs the Ask server on :8900 (CHIRON_MCP_ALLOW_SAVE=1) and Chiron's API on :8000.
Exit code 0 means every case passed.
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

ASK = os.environ.get("ASK_URL", "http://localhost:8900")
API = os.environ.get("CHIRON_API", "http://localhost:8000")
DS = os.environ.get("TEST_DATASET", "synthea-10k")
SCHEMA = DS.replace("-", "_")
P = DS + "__"
WAREHOUSE = os.environ.get(
    "CHIRON_MCP_WAREHOUSE_URL", "postgresql://postgres:postgres@localhost:5432/chiron"
)


# --- ground truth, straight from Postgres ---------------------------------------

def sql(q: str) -> int:
    import psycopg2

    with psycopg2.connect(WAREHOUSE) as conn, conn.cursor() as cur:
        cur.execute(f"set search_path to {SCHEMA}")
        cur.execute(q)
        return int(cur.fetchone()[0])


def cond(where: str) -> str:
    """Subjects with a condition matching `where` on the description column."""
    return (
        f'select c._subject_id from condition c join "lkp_{P}condition__description" l '
        f"on l._collection_id = c._id where {where}"
    ).replace("DESC", f'l."{P}condition__description"')


def subj(concept: str, where: str) -> str:
    return (
        f'select s._subject_id from subject s join "lkp_{P}subject__{concept}" v '
        f'on v._collection_id = s._id where {where}'
    ).replace("VAL", f'v."{P}subject__{concept}"')


def count_of(*subqueries: str) -> int:
    """Distinct patients in the intersection of the subqueries.

    DISTINCT matters: a subquery returns one row per matching record, so a patient with
    three emergency encounters would otherwise be counted three times. (INTERSECT
    already dedupes, which is why only the single-subquery facts were affected.)
    """
    q = subqueries[0]
    for extra in subqueries[1:]:
        q = f"{q} intersect {extra}"
    return sql(f"select count(distinct _subject_id) from ({q}) x")


def truths() -> dict[str, dict[str, int]]:
    """Each fact with its fully variant-merged value and the naive exact-match one.

    The data carries case and spelling variants on purpose ("Asthma", "ASTHMA",
    "Asthm"). A correct answer merges them; the exact-only figure is kept so a miss
    is reported as a miss rather than as an unexplained number.
    """
    asthma = cond("lower(DESC) in ('asthma','asthm')")
    asthma_x = cond("DESC = 'Asthma'")
    htn = cond("lower(DESC) like 'essential hypertensi%'")
    htn_x = cond("DESC = 'Essential hypertension'")
    female = subj("gender", "upper(VAL) = 'F'")
    female_x = subj("gender", "VAL = 'F'")
    return {
        "total": {"right": sql("select count(*) from subject")},
        "asthma": {"right": count_of(asthma), "exact": count_of(asthma_x)},
        "female": {"right": count_of(female), "exact": count_of(female_x)},
        "female_asthma": {
            "right": count_of(asthma, female),
            "exact": count_of(asthma_x, female_x),
        },
        "htn": {"right": count_of(htn), "exact": count_of(htn_x)},
        "female_htn": {"right": count_of(htn, female), "exact": count_of(htn_x, female_x)},
        "income_100k": {"right": count_of(subj("income", "VAL > 100000"))},
        "asthma_income_50k": {
            "right": count_of(asthma, subj("income", "VAL > 50000")),
            "exact": count_of(asthma_x, subj("income", "VAL > 50000")),
        },
        "born_before_1950": {"right": count_of(subj("birthdate", "VAL < '1950-01-01'"))},
        "t2dm": {"right": count_of(cond("lower(DESC) like 'type 2 diabetes%'"))},
        "copd": {"right": count_of(cond("lower(DESC) like 'chronic obstructive%'"))},
        # the negation trap: exclude_selected on a multi-value field gives the "exact" one
        "no_htn": {
            "right": sql("select count(*) from subject") - count_of(htn),
            "exact": count_of(cond("lower(DESC) not like 'essential hypertensi%'")),
        },
        "income_30k_60k": {"right": count_of(subj("income", "VAL between 30000 and 60000"))},
        "deceased": {"right": count_of(subj("deathdate", "VAL is not null"))},
        "emergency": {"right": count_of(
            f'select e._subject_id from encounter e join "lkp_{P}encounter__encounterclass" l '
            f'on l._collection_id = e._id where lower(l."{P}encounter__encounterclass") = '
            "'emergency'")},
    }


# --- sessions ---------------------------------------------------------------------

def mint_session(username: str) -> str:
    """A real Django session for `username`, created the way Django's login does."""
    from chiron_mcp.bootstrap import ensure_django

    ensure_django()
    from django.contrib.auth import get_user_model
    from django.contrib.sessions.backends.db import SessionStore

    user = get_user_model().objects.get(username=username)
    s = SessionStore()
    s["_auth_user_id"] = str(user.pk)
    s["_auth_user_backend"] = "django.contrib.auth.backends.ModelBackend"
    s["_auth_user_hash"] = user.get_session_auth_hash()
    s.create()
    return s.session_key


# --- one question, driven like the page drives it -----------------------------------

@dataclass
class Case:
    id: str
    q: str
    kind: str                      # count | report | workspace | chart | table | refuse | list
    truth: str | None = None       # key into truths()
    user: str = "demouser"
    must_mention: list[str] = field(default_factory=list)
    dataset: str = DS
    also: list[str] = field(default_factory=list)   # further facts the answer must state


@dataclass
class Result:
    case: Case
    ok: bool = True
    notes: list[str] = field(default_factory=list)
    answer: str = ""
    steps: list[str] = field(default_factory=list)
    seconds: float = 0.0

    def fail(self, msg: str) -> None:
        self.ok = False
        self.notes.append("FAIL " + msg)

    def warn(self, msg: str) -> None:
        self.notes.append("warn " + msg)


def ask(q: str, cookie: str, dataset: str = DS) -> dict:
    url = f"{ASK}/ask?" + urllib.parse.urlencode({"q": q, "dataset": dataset})
    req = urllib.request.Request(url, headers={"Cookie": f"sessionid={cookie}"})
    events: dict = {"step": [], "thinking": []}
    event = None
    with urllib.request.urlopen(req, timeout=300) as resp:
        for raw in resp:
            line = raw.decode().rstrip("\n")
            if line.startswith("event: "):
                event = line[7:]
            elif line.startswith("data: ") and event:
                data = json.loads(line[6:])
                if event in ("step", "thinking"):
                    events[event].append(data)
                else:
                    events[event] = data
                if event == "done":
                    break
    return events


def post_json(url: str, body: dict, cookie: str) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Cookie": f"sessionid={cookie}",
            "Origin": ASK,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


def get_json(url: str, cookie: str) -> dict:
    req = urllib.request.Request(url, headers={"Cookie": f"sessionid={cookie}"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


def chiron_says(r, case, cookie, stated, truth, how) -> None:
    """Chiron's own count for the user's active query, i.e. the UI's Subject Count."""
    try:
        got = get_json(f"{API}/api/v2/{case.dataset}/query_tools/count/", cookie).get("count")
    except urllib.error.HTTPError as exc:
        r.fail(f"after {how}, Chiron's own count endpoint returns HTTP {exc.code}: "
               "the handed-over query is broken in the Chiron UI")
        return
    got = int(str(got).replace(",", "")) if got is not None else None
    want = stated if stated is not None else truth[case.truth]["right"]
    if got != want:
        r.fail(f"after {how}, Chiron shows {got} subjects, answer says {want}")
    else:
        r.notes.append(f"ok {how} -> Chiron shows {got}")


NUM = re.compile(r"(?<![\w.])\d{1,3}(?:,\d{3})+(?![\d.])|(?<![\w.,])\d+(?![\d.,]\d)")
CLUTTER = [
    "load as active", "click the", "open it here", "you can open", "from that page",
    "from there", "use the link", "link below", "button below",
]
REFUSAL = re.compile(
    r"(no access|not have access|doesn.t have access|don.t have access|cannot see|"
    r"can.t see|not permitted|refus|aggregate|no chironuser|not available|isn.t available)",
    re.I,
)


def numbers(text: str) -> set[int]:
    return {int(n.replace(",", "")) for n in NUM.findall(text)}


# A Chiron workspace is per user, so two cases that write one user's workspace must not
# interleave: the second would overwrite the first before it is checked.
_WORKSPACE = {}
_WS_GUARD = threading.Lock()


def workspace_lock(user: str) -> threading.Lock:
    with _WS_GUARD:
        return _WORKSPACE.setdefault(user, threading.Lock())


def run(case: Case, cookie: str, truth: dict) -> Result:
    try:
        if case.kind in ("count", "workspace"):
            with workspace_lock(case.user):
                return _run(case, cookie, truth)
        return _run(case, cookie, truth)
    except Exception as exc:  # noqa: BLE001
        r = Result(case)
        r.fail(f"harness error: {type(exc).__name__}: {exc}")
        return r


def _run(case: Case, cookie: str, truth: dict) -> Result:
    r = Result(case)
    t0 = time.time()
    try:
        ev = ask(case.q, cookie, case.dataset)
    except Exception as exc:  # noqa: BLE001
        r.fail(f"/ask raised {exc}")
        return r
    r.seconds = time.time() - t0
    r.steps = ev.get("step", [])
    answer = ev.get("answer") or ""
    r.answer = answer

    if "error" in ev:
        r.fail(f"error event: {str(ev['error'])[:160]}")
        return r
    if not answer.strip():
        r.fail("empty answer")
        return r

    if re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", answer) or "[redacted]" in answer:
        r.fail("answer mentions an email address")
    if re.search(r"/(Users|home|private|tmp)/", answer):
        r.fail("answer mentions a local file path")
    low = answer.lower()
    for phrase in CLUTTER:
        if phrase in low:
            r.fail(f"clutter in answer: {phrase!r}")
    if re.search(r"https?://\S+/(reports|query|results)\b", answer):
        r.warn("answer pastes a Chiron URL (the page strips it, but the prompt forbids it)")
    for word in case.must_mention:
        if word.lower() not in low:
            r.fail(f"answer never mentions {word!r}")

    found = numbers(answer)
    cohort = ev.get("cohort")
    link = ev.get("link")

    # --- refusals: nothing should leak
    if case.kind == "refuse":
        if not REFUSAL.search(answer):
            r.fail("expected a refusal, got an answer")
        if cohort:
            r.fail("refusal still offered a Query button")
        if link:
            r.fail("refusal still offered a link")
        return r

    # --- the stated figure
    stated = None
    if case.truth:
        t = truth[case.truth]
        if t["right"] in found:
            stated = t["right"]
        elif "exact" in t and t["exact"] in found:
            stated = t["exact"]
            r.fail(
                f"missed spelling variants: said {t['exact']}, the merged count is "
                f"{t['right']}"
            )
        else:
            near = sorted(found, key=lambda n: abs(n - t["right"]))[:3]
            r.fail(f"wrong figure: expected {t['right']}, answer has {near}")

    for key in case.also:
        if truth[key]["right"] not in found:
            r.fail(f"answer is missing {key} = {truth[key]['right']} (has {sorted(found)[:6]})")

    # --- the Query button must reproduce the stated figure inside Chiron
    if case.kind == "count" and case.truth:
        if not cohort:
            r.fail("no Query button offered for a cohort question")
        else:
            if stated is not None and cohort.get("subject_count") != stated:
                r.fail(f"Query button says {cohort.get('subject_count')}, answer says {stated}")
            try:
                loaded = post_json(f"{ASK}/load", cohort, cookie)
            except Exception as exc:  # noqa: BLE001
                r.fail(f"/load raised {exc}")
                loaded = {}
            if loaded.get("error"):
                r.fail(f"Query button fails: {loaded['error'][:140]}")
            elif loaded:
                chiron_says(r, case, cookie, stated, truth, "Query")

    if case.kind == "workspace":
        if not link or link.get("label") != "Query":
            r.fail(f"no Query link for a workspace hand-off (link: {link})")
        if cohort:
            r.fail("workspace hand-off also offered a second Query button")
        chiron_says(r, case, cookie, stated, truth, "workspace")

    # --- a report must open and agree
    if case.kind == "report":
        if not link or link.get("label") != "Report":
            r.fail(f"no Report link (link event: {link})")
        else:
            m = re.search(r"/reports/(\d+)", link["url"])
            if not m:
                r.fail(f"report link has no id: {link['url']}")
            else:
                prev = get_json(
                    f"{API}/api/v2/{case.dataset}/report_tools/{m.group(1)}/preview/"
                    "?page=1&records_per_page=5",
                    cookie,
                )
                fields = (prev.get("extended_table_def") or {}).get("fields") or []
                if prev.get("errors"):
                    r.fail(f"report {m.group(1)} has errors: {prev['errors']}")
                if not fields:
                    r.fail(f"report {m.group(1)} has no columns")
                subj_n = prev.get("subject_count")
                want = stated if stated is not None else (
                    truth[case.truth]["right"] if case.truth else None
                )
                if want is not None and subj_n != want:
                    r.fail(f"report {m.group(1)} shows {subj_n} subjects, answer says {want}")
                elif subj_n is not None:
                    r.notes.append(f"ok report {m.group(1)} -> {subj_n} subjects, "
                                   f"{len(fields)} column(s)")

    if case.kind == "chart":
        blocks = re.findall(r"```chart\s*([\s\S]*?)```", answer)
        if not blocks:
            r.fail("no chart block")
        else:
            try:
                spec = json.loads(blocks[0])
                pts = spec.get("data") or []
                if len(pts) < 3:
                    r.fail(f"chart has {len(pts)} points")
                if not all(isinstance(p.get("y"), (int, float)) for p in pts):
                    r.fail("chart has non-numeric values")
            except Exception as exc:  # noqa: BLE001
                r.fail(f"chart JSON invalid: {exc}")

    if case.kind == "table" and not re.search(r"^\s*\|.*\|\s*$", answer, re.M):
        r.fail("no markdown table")

    dupes = {s: r.steps.count(s) for s in set(r.steps) if r.steps.count(s) > 2}
    if dupes:
        r.warn(f"repeated tool calls {dupes}")
    return r


CASES = [
    # --- every starter question the page suggests; a suggestion must never fail
    Case("s_chart", "Which 5 conditions affect the most patients? Chart it", "chart"),
    Case("s_female_htn", "How many women have essential hypertension?", "count", "female_htn"),
    Case("s_asthma_income", "Asthma patients earning over $50,000", "count", "asthma_income_50k"),
    Case("s_born_1950", "How many patients were born before 1950?", "count", "born_before_1950"),
    Case("s_meds", "Top 10 medications by number of patients", "table"),
    Case("s_t2dm_report", "Save a type 2 diabetes cohort as a report", "report", "t2dm"),
    Case("s_copd_workspace", "Load a COPD cohort into my query", "workspace", "copd"),
    # --- figures, including the variant traps
    Case("total", "How many patients are in this dataset?", "plain", "total"),
    Case("asthma", "How many patients have asthma?", "count", "asthma"),
    Case("female", "How many female patients are there?", "count", "female"),
    Case("female_asthma", "How many female patients have asthma?", "count", "female_asthma"),
    Case("income", "How many patients earn more than $100,000 a year?", "count", "income_100k"),
    Case("filters", "What can I filter on?", "list", must_mention=["condition", "medication"]),
    # --- semantic traps: wrong-but-plausible answers, not errors
    Case("no_htn", "How many patients do not have hypertension?", "count", "no_htn"),
    Case("income_range", "How many patients earn between $30,000 and $60,000?", "count",
         "income_30k_60k"),
    Case("deceased", "How many patients have died?", "count", "deceased"),
    Case("emergency", "How many patients have had an emergency encounter?", "count", "emergency"),
    Case("compare", "How many patients have asthma, and how many have COPD?", "plain",
         "asthma", also=["copd"]),
    # --- identity and permissions
    Case("no_access", "How many patients are in dataset2_stored?", "refuse"),
    Case("agg_user", "How many subjects are there?", "refuse", user="agguser",
         dataset="dataset1_stored"),
    Case("admin_user", "How many patients have asthma?", "count", "asthma", user="admin"),
]


def main() -> int:
    only = sys.argv[1:] and sys.argv[1]
    cases = [c for c in CASES if not only or only in c.id]
    print(f"computing ground truth from {SCHEMA} ...")
    truth = truths()
    for k, v in truth.items():
        print(f"  {k:18} {v}")
    sessions = {u: mint_session(u) for u in {c.user for c in cases}}

    print(f"\nrunning {len(cases)} case(s) against {ASK} ...\n")
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda c: run(c, sessions[c.user], truth), cases))

    failed = 0
    for r in results:
        mark = "PASS" if r.ok else "FAIL"
        failed += not r.ok
        print(f"{mark}  {r.case.id:15} {r.seconds:5.0f}s  steps={len(r.steps):2}  "
              f"[{r.case.user}] {r.case.q}")
        for n in r.notes:
            print(f"        {n}")
        if not r.ok:
            print("        answer: " + r.answer.replace("\n", " ")[:260])
    print(f"\n{len(results) - failed}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

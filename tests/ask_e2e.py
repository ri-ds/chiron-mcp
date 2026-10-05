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
    .venv/bin/python tests/ask_e2e.py --suggestions   # every starter question in the pool
    .venv/bin/python tests/ask_e2e.py --suggestions results columns   # only those features

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
# For the few things done in-process (sessions, the shared-report fixture, cleanup).
os.environ.setdefault("CHIRON_MCP_USERNAME", "demouser")
os.environ.setdefault("CHIRON_MCP_ALLOW_SAVE", "1")

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
    races = ["white", "black", "other", "asian", "native"]
    grid = {
        (g, race): count_of(asthma, subj("gender", f"upper(VAL) = '{g}'"),
                            subj("race", f"lower(VAL) = '{race}'"))
        for g in ("F", "M") for race in races
    }
    def med(where: str) -> str:
        return (
            f'select m._subject_id from medication m join "lkp_{P}medication__description" l '
            f"on l._collection_id = m._id where {where}"
        ).replace("DESC", f'l."{P}medication__description"')

    albuterol = med("lower(DESC) like 'albuterol%'")
    return {
        "_grid": grid,
        # "now show their medications": right if scoped to the asthma cohort, and the
        # whole-dataset figure is what an answer that forgot "their" would give
        "asthma_albuterol": {"right": count_of(asthma, albuterol)},
        "asthma_lisinopril": {"right": count_of(asthma, med("lower(DESC) like 'lisinopril%'"))},
        "albuterol_all": {"right": count_of(albuterol)},
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
        # the top conditions, every variant merged, truncations ("Asthm") included
        "obesity": {"right": count_of(cond("lower(DESC) like 'body mass index 30%'"))},
        "mdd": {"right": count_of(cond("lower(DESC) like 'major depressive disorde%'"))},
        "copd": {"right": count_of(cond("lower(DESC) like 'chronic obstructive%'"))},
        # the negation trap: exclude_selected on a multi-value field gives the "exact" one
        "no_htn": {
            "right": sql("select count(*) from subject") - count_of(htn),
            "exact": count_of(cond("lower(DESC) not like 'essential hypertensi%'")),
        },
        "income_30k_60k": {"right": count_of(subj("income", "VAL between 30000 and 60000"))},
        "asthma_female_income_50k": {
            "right": count_of(asthma, female, subj("income", "VAL > 50000"))},
        "male": {"right": count_of(subj("gender", "upper(VAL) = 'M'"))},
        "asthma_male": {"right": count_of(asthma, subj("gender", "upper(VAL) = 'M'"))},
        "deceased": {"right": count_of(subj("deathdate", "VAL is not null"))},
        "emergency": {"right": count_of(
            f'select e._subject_id from encounter e join "lkp_{P}encounter__encounterclass" l '
            f'on l._collection_id = e._id where lower(l."{P}encounter__encounterclass") = '
            "'emergency'")},
    }


# --- sessions ---------------------------------------------------------------------

SESSIONS: dict[str, str] = {}


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
    cells: list[int] = field(default_factory=list)  # breakdown figures that must appear
    turns: list["Case"] = field(default_factory=list)  # follow-ups, same conversation
    pattern: str | None = None     # regex the answer must match (case-insensitive)
    absent: list[str] = field(default_factory=list)  # facts that must NOT be stated
    partial_rows: list[list[int]] = field(default_factory=list)  # one table row each


@dataclass
class Result:
    case: Case
    ok: bool = True
    notes: list[str] = field(default_factory=list)
    answer: str = ""
    steps: list[str] = field(default_factory=list)
    seconds: float = 0.0
    prefix: str = ""
    created: list[int] = field(default_factory=list)  # report ids to clean up

    def fail(self, msg: str) -> None:
        self.ok = False
        self.notes.append("FAIL " + self.prefix + msg)

    def warn(self, msg: str) -> None:
        self.notes.append("warn " + self.prefix + msg)

    def ok_note(self, msg: str) -> None:
        self.notes.append("ok " + self.prefix + msg)


# Every conversation a run starts, so its transcript can be deleted at the end.
STARTED: set[tuple[str, str]] = set()


def ask(q: str, cookie: str, dataset: str = DS, thread: str | None = None) -> dict:
    params = {"q": q, "dataset": dataset}
    if thread:
        params["thread"] = thread
    url = f"{ASK}/ask?" + urllib.parse.urlencode(params)
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
    if isinstance(events.get("thread"), str):
        STARTED.add((events["thread"], cookie))
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
        r.ok_note(f"{how} -> Chiron shows {got}")


NUM = re.compile(r"(?<![\w.])\d{1,3}(?:,\d{3})+(?![\d.])|(?<![\w.,])\d+(?![\d.,]\d)")
CLUTTER = [
    "load as active", "click the", "open it here", "you can open", "from that page",
    "from there", "use the link", "link below", "button below",
]
REFUSAL = re.compile(
    r"(no access|not have access|doesn.t have access|don.t have access|cannot see|"
    r"can.t see|not permitted|refus|aggregate|no chironuser|not available|isn.t available|"
    r"cannot access|can.t access|no permission|not authori)",
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
        # every kind whose checks load a cohort into the user's workspace
        if case.kind in ("count", "workspace", "breakdown", "results_flow"):
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
    if case.kind == "report_flow":
        report_flow(r, case, cookie, truth)
    elif case.kind == "hijack":
        hijack(r, case, cookie, truth)
    elif case.kind == "delete_refused":
        delete_refused(r, case, cookie)
    elif case.kind == "results_flow":
        results_flow(r, case, cookie, truth)
    elif case.kind == "report_columns":
        report_columns_flow(r, case, cookie, truth)
    else:
        thread = None
        for i, turn in enumerate([case] + case.turns):
            r.prefix = f"[turn {i + 1}] " if case.turns else ""
            try:
                ev = ask(turn.q, cookie, case.dataset, thread)
            except Exception as exc:  # noqa: BLE001
                r.fail(f"/ask raised {exc}")
                break
            if thread and ev.get("thread") != thread:
                r.fail("a follow-up started a new conversation instead of continuing")
            thread = ev.get("thread")
            check(r, turn, ev, cookie, truth, case.dataset)
            if not r.ok:
                break
    r.seconds = time.time() - t0
    return r


def check(r: Result, case: Case, ev: dict, cookie: str, truth: dict, dataset: str) -> None:
    """Every check on one answer; used for single questions and each follow-up."""
    case = Case(**{**case.__dict__, "dataset": dataset})
    r.steps += ev.get("step", [])
    answer = ev.get("answer") or ""
    r.answer = answer

    if "error" in ev:
        r.fail(f"error event: {str(ev['error'])[:160]}")
        return
    if not answer.strip():
        r.fail("empty answer")
        return

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
    if case.pattern and not re.search(case.pattern, answer, re.I | re.S):
        r.fail(f"answer does not match {case.pattern!r}")

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
        return

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
    for key in case.absent:
        if truth[key]["right"] in found:
            r.fail(f"answer states {key} = {truth[key]['right']}, which it should not")

    # --- the Query button must reproduce the stated figure inside Chiron
    if case.kind in ("count", "breakdown") and case.truth:
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
                r.created.append(int(m.group(1)))
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
                    r.ok_note(f"report {m.group(1)} -> {subj_n} subjects, "
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

    if case.kind in ("table", "breakdown") and not re.search(r"^\s*\|.*\|\s*$", answer, re.M):
        r.fail("no markdown table")
    missing = [n for n in case.cells if n not in found]
    if missing:
        r.fail(f"breakdown is missing {missing} (answer has {sorted(found)[:12]})")
    elif case.cells:
        r.ok_note(f"breakdown has all {len(case.cells)} expected figures")
    # A chart of one row of a two-way table, unlabelled, reads as the whole cohort.
    for body in re.findall(r"```chart\s*([\s\S]*?)```", answer):
        try:
            spec = json.loads(body)
        except ValueError:
            r.fail("chart JSON invalid")
            continue
        ys = [pt.get("y") for pt in spec.get("data") or []]
        if "series" not in spec and ys in case.partial_rows:
            r.fail(f"chart shows one row of the table ({ys}) as if it were the whole")
    # Aggregate-only accounts: a refusal, or aggregate figures masked the way Chiron's
    # analysis view masks them. Never a Query button, never a count from 1 to 5.
    if case.kind == "agg":
        if cohort or link:
            r.fail("an aggregate-only account was offered a button")
        small = [n for n in re.findall(r"(?<![<\w.,])([1-5])(?![\d.,]\d)", answer)]
        if small:
            r.fail(f"an aggregate-only answer shows unmasked small counts {small}")
        if not REFUSAL.search(answer) and not found:
            r.fail("neither a refusal nor a figure")
        return
    if case.kind == "masked":
        if "<5" not in answer.replace(" ", ""):
            r.fail("aggregate-only breakdown shows no masked (<5) counts")
        if cohort:
            r.fail("aggregate-only account was offered a Query button")

    mine = ev.get("step", [])  # this answer only; a conversation repeats tools per turn
    dupes = {s: mine.count(s) for s in set(mine) if mine.count(s) > 2}
    if dupes:
        r.warn(f"repeated tool calls {dupes}")


def report_flow(r: Result, case: Case, cookie: str, truth: dict) -> None:
    """Create, rename, refilter and delete one report in one conversation, checking
    Chiron's own API after every step rather than trusting the answer."""
    first, second = "E2E flow report", "E2E flow renamed"
    everyone, women = truth["asthma"]["right"], truth["female_asthma"]["right"]
    state = {"thread": None}

    def turn(label: str, q: str) -> dict:
        r.prefix = f"[{label}] "
        ev = ask(q, cookie, case.dataset, state["thread"])
        if state["thread"] and ev.get("thread") != state["thread"]:
            r.fail("started a new conversation instead of continuing")
        state["thread"] = ev.get("thread")
        r.steps += ev.get("step", [])
        r.answer = ev.get("answer") or ""
        if "error" in ev:
            r.fail(f"error event: {str(ev['error'])[:140]}")
        return ev

    def meta(rid: str) -> dict:
        return get_json(f"{API}/api/v2/{case.dataset}/reports/get_report/?report_id={rid}",
                        cookie)["oReport"]

    def subjects(rid: str) -> int | None:
        return get_json(f"{API}/api/v2/{case.dataset}/report_tools/{rid}/preview/"
                        "?page=1&records_per_page=5", cookie).get("subject_count")

    ev = turn("save", f"Save an asthma cohort as a report named '{first}'")
    m = re.search(r"/reports/(\d+)", (ev.get("link") or {}).get("url", ""))
    if not m:
        r.fail(f"no Report link (link: {ev.get('link')})")
        return
    rid = m.group(1)
    r.created.append(int(rid))
    got = meta(rid)["name"]
    if got != first:
        r.fail(f"report is named {got!r}, asked for {first!r}")
    n = subjects(rid)
    if n != everyone:
        r.fail(f"report {rid} has {n} subjects, expected {everyone}")
    else:
        r.ok_note(f"report {rid} saved, {n} subjects")

    ev = turn("rename", f"Rename that report to '{second}'")
    got = meta(rid)["name"]
    if got != second:
        r.fail(f"after rename Chiron shows {got!r}")
    else:
        r.ok_note(f"Chiron shows the new name {got!r}")
    if (ev.get("link") or {}).get("url", "").rstrip("/").split("/")[-1] != rid:
        r.fail(f"rename did not offer a Report button for report {rid}")

    turn("refilter", "Change that report to include only women")
    n = subjects(rid)
    if n != women:
        r.fail(f"after refiltering Chiron's report has {n} subjects, expected {women}")
    else:
        r.ok_note(f"Chiron's report now has {n} subjects")

    ev = turn("delete", "Delete that report")
    try:
        meta(rid)
        r.fail(f"report {rid} still exists after deletion")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            r.ok_note(f"report {rid} is gone (404)")
        else:
            r.fail(f"unexpected HTTP {exc.code} checking the deleted report")
    if ev.get("link"):
        r.fail("the deletion answer still offers a link to the deleted report")
    if ev.get("deleted") != int(rid):
        r.fail(f"the page was not told to retire buttons for report {rid} "
               f"(deleted event: {ev.get('deleted')})")


def hijack(r: Result, case: Case, cookie: str, truth: dict) -> None:
    """Another user presenting someone's conversation id must not get its context."""
    r.prefix = "[owner] "
    ev = ask("How many patients have asthma?", SESSIONS["demouser"], case.dataset)
    owned = ev.get("thread")
    r.prefix = "[intruder] "
    ev2 = ask("How many of them are women?", SESSIONS["admin"], case.dataset, owned)
    r.answer = ev2.get("answer") or ""
    if ev2.get("thread") == owned:
        r.fail("an intruder continued someone else's conversation")
    if truth["female_asthma"]["right"] in numbers(r.answer):
        r.fail("the intruder's answer used the owner's asthma cohort")
    else:
        r.ok_note("intruder got a fresh conversation with no prior cohort")


def _turn(r: Result, state: dict, case: Case, cookie: str, label: str, q: str) -> dict:
    """One question in a running conversation, recorded on the result."""
    r.prefix = f"[{label}] "
    ev = ask(q, cookie, case.dataset, state.get("thread"))
    if state.get("thread") and ev.get("thread") != state["thread"]:
        r.fail("started a new conversation instead of continuing")
    state["thread"] = ev.get("thread")
    r.steps += ev.get("step", [])
    r.answer = ev.get("answer") or ""
    if "error" in ev:
        r.fail(f"error event: {str(ev['error'])[:140]}")
    return ev


def results_flow(r: Result, case: Case, cookie: str, truth: dict) -> None:
    """Change the Results tab by asking, checking Chiron's own Results API each time."""
    state: dict = {}
    api = lambda path: get_json(f"{API}/api/v2/{case.dataset}/{path}", cookie)

    def columns():
        td = api("table_def/")["table_def"]
        by_id = {f["entry_id"]: f for f in td.get("fields") or []}
        cols = [(f["concept_id"].split("__", 1)[-1], f.get("aggregation_method") or "stack")
                for f in td.get("fields") or []]
        sort = [(by_id.get(x["entry_id"], {}).get("concept_id", "").split("__", 1)[-1],
                 x.get("direction")) for x in td.get("sort") or []]
        return cols, sort

    _turn(r, state, case, cookie, "load", "Load patients with asthma into my query")
    want = truth["asthma"]["right"]
    pv = api("query_tools/preview/?page=1&records_per_page=1")
    if pv.get("subject_count") != want:
        r.fail(f"Results has {pv.get('subject_count')} patients, expected {want}")

    ev = _turn(r, state, case, cookie, "add", "Add birthdate and city columns to my results")
    cols, _ = columns()
    names = [c for c, _ in cols]
    if not {"subject__birthdate", "subject__city"} <= set(names):
        r.fail(f"Results columns are {cols}")
    else:
        r.ok_note(f"Results columns {names}")
    if (ev.get("link") or {}).get("label") != "Results":
        r.fail(f"no Results button (link: {ev.get('link')})")
    pv = api("query_tools/preview/?page=1&records_per_page=1")
    if pv.get("subject_count") != want:
        r.fail(f"after adding columns Results has {pv.get('subject_count')} patients")
    elif (pv.get("record_count") or 0) < want * 0.9:
        r.fail(f"birthdate and city should give about one row per patient, got "
               f"{pv.get('record_count')} rows")
    else:
        r.ok_note(f"{pv.get('record_count')} rows for {pv.get('subject_count')} patients")

    _turn(r, state, case, cookie, "aggregate",
          "In my results, show the condition description column as a count instead of a list")
    cols, _ = columns()
    agg = dict(cols).get("condition__description")
    if agg not in ("count_all", "count_distinct"):
        r.fail(f"condition description is shown as {agg!r}")
    else:
        r.ok_note(f"condition description shown as {agg}")

    _turn(r, state, case, cookie, "sort", "Sort my results by birthdate, newest first")
    _, sort = columns()
    if not sort or sort[0] != ("subject__birthdate", -1):
        r.fail(f"sort is {sort}")
    else:
        r.ok_note("sorted by birthdate, newest first")

    _turn(r, state, case, cookie, "read", "What columns are in my results right now?")
    low = r.answer.lower()
    if not ("birthdate" in low and "city" in low):
        r.fail("the answer does not list the Results columns")

    want_cols, want_sort = columns()
    ev = _turn(r, state, case, cookie, "save", "Save my results as a report called 'E2E results copy'")
    m = re.search(r"/reports/(\d+)", (ev.get("link") or {}).get("url", ""))
    if not m:
        r.fail(f"no Report button (link: {ev.get('link')})")
        return
    r.created.append(int(m.group(1)))
    etd = get_json(f"{API}/api/v2/{case.dataset}/reports/get_report/?report_id={m.group(1)}",
                   cookie)["extended_table_def"]
    by_id = {f["entry_id"]: f for f in etd.get("fields") or []}
    got_cols = [(f["concept_id"].split("__", 1)[-1], f.get("aggregation_method") or "stack")
                for f in etd.get("fields") or []]
    got_sort = [(by_id.get(x["entry_id"], {}).get("concept_id", "").split("__", 1)[-1],
                 x.get("direction")) for x in etd.get("sort") or []]
    if sorted(got_cols) != sorted(want_cols) or got_sort != want_sort:
        r.fail(f"the report has {got_cols} sorted {got_sort}; Results had {want_cols} "
               f"sorted {want_sort}")
    else:
        r.ok_note("the saved report matches Results: columns, aggregations and sort")


def report_columns_flow(r: Result, case: Case, cookie: str, truth: dict) -> None:
    """Change how a report's columns are shown, checked in Chiron's report API."""
    state: dict = {}
    ev = _turn(r, state, case, cookie, "save",
               "Save patients with asthma as a report called 'E2E columns', with gender and "
               "medication description columns")
    m = re.search(r"/reports/(\d+)", (ev.get("link") or {}).get("url", ""))
    if not m:
        r.fail(f"no Report button (link: {ev.get('link')})")
        return
    rid = m.group(1)
    r.created.append(int(rid))

    def fields():
        d = get_json(f"{API}/api/v2/{case.dataset}/reports/get_report/?report_id={rid}", cookie)
        return {f["concept_id"].split("__", 1)[-1]: f for f in d["extended_table_def"]["fields"]}

    if "medication__description" not in fields():
        r.fail(f"the report's columns are {list(fields())}")
        return
    _turn(r, state, case, cookie, "has value",
          "In that report, show the medication column as whether they take albuterol, "
          "true or false")
    f = fields().get("medication__description") or {}
    values = (f.get("aggregation_settings") or {}).get("values") or []
    if f.get("aggregation_method") != "has_value" or not any("lbuterol" in v for v in values):
        r.fail(f"medication column is {f.get('aggregation_method')} {values}")
    else:
        r.ok_note(f"medication column: has value {values}")
    pv = get_json(f"{API}/api/v2/{case.dataset}/report_tools/{rid}/preview/"
                  "?page=1&records_per_page=3", cookie)
    if pv.get("errors") or pv.get("subject_count") != truth["asthma"]["right"]:
        r.fail(f"report preview: {pv.get('errors')} {pv.get('subject_count')} patients")
    else:
        r.ok_note(f"report runs: {pv.get('record_count')} rows, {pv.get('subject_count')} patients")


SHARED_REPORT = "Team asthma cohort (shared)"


def shared_report_id() -> int | None:
    """The public report admin owns; demouser can open it but must not change it.

    Made here when missing, so the case never depends on a report someone might tidy
    away in Chiron's own Reports page.
    """
    from chiron.models import UserCreatedContent

    row = UserCreatedContent.objects.filter(
        name=SHARED_REPORT, creator__user__username="admin").first()
    if row:
        return row.pk
    from chiron_mcp import server as S

    made = S.open_in_ui(
        DS, _asthma_cohort(), None, SHARED_REPORT,
        "report", "Shared by admin for the delete-refusal test",
        username="admin", allow_superuser=True,
    )
    if made.get("error") or not made.get("report_id"):
        return None
    UserCreatedContent.objects.filter(pk=made["report_id"]).update(public=True)
    return made["report_id"]


def _asthma_cohort() -> list:
    from chiron_mcp import server as S

    return S.chiron_edit_cohort(DS, [], {
        "type": "add_entry", "concept_id": f"{P}condition__description",
        "selected_categories": ["Asthma", "ASTHMA", "asthma", "Asthm"],
    })["cohort_def"]


def delete_refused(r: Result, case: Case, cookie: str) -> None:
    """Asking to delete a report someone else made must leave it in place."""
    rid = shared_report_id()
    if rid is None:
        r.fail(f"setup: no public report {SHARED_REPORT!r} owned by admin")
        return
    ev = ask(f"Delete the report called '{SHARED_REPORT}'", cookie, case.dataset)
    r.steps += ev.get("step", [])
    r.answer = ev.get("answer") or ""
    try:
        get_json(f"{API}/api/v2/{case.dataset}/reports/get_report/?report_id={rid}", cookie)
        r.ok_note(f"report {rid} still exists")
    except urllib.error.HTTPError as exc:
        r.fail(f"report {rid} was deleted by someone who did not create it (HTTP {exc.code})")
    if not re.search(r"(only (its|the) (creator|owner|person)|didn.t create|did not create|"
                     r"isn.t yours|not yours|created by|can.t delete|cannot delete|"
                     r"not (allowed|permitted|able))", r.answer, re.I):
        r.fail("answer does not say the report cannot be deleted by this user")
    if ev.get("link"):
        r.warn("refusal offered a link")


def cleanup(results: list[Result]) -> None:
    """Delete the reports this run created, so repeated runs leave Chiron tidy."""
    from chiron.models import UserCreatedContent

    ids = [i for r in results for i in r.created]
    if ids:
        n, _ = UserCreatedContent.objects.filter(
            pk__in=ids, creator__user__username__in=["demouser", "admin"]).delete()
        print(f"cleaned up {len(ids)} report(s) created by this run")
    # Transcripts hold tool results, i.e. patient rows: forget them now, not in 12 hours.
    forgotten = 0
    for tid, cookie in STARTED:
        try:
            forgotten += bool(post_json(f"{ASK}/forget", {"thread": tid}, cookie).get("forgotten"))
        except Exception:  # noqa: BLE001
            pass
    print(f"forgot {forgotten}/{len(STARTED)} conversation(s) and their transcripts")


CASES = [
    # --- every starter question the page suggests; a suggestion must never fail
    Case("s_chart", "Which 5 conditions affect the most patients? Chart it", "chart",
         also=["obesity", "htn", "mdd", "asthma", "t2dm"]),
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
    # --- follow-ups: one conversation, each turn builds on the last
    Case("followup", "How many patients have asthma?", "count", "asthma", turns=[
        Case("t2", "How many of them are women?", "count", "female_asthma"),
        Case("t3", "And of those, how many earn over $50,000?", "count",
             "asthma_female_income_50k"),
    ]),
    # the exact example from the request: "their" must mean the asthma cohort
    Case("followup_meds", "How many patients have asthma?", "count", "asthma", turns=[
        Case("t2", "Now show their medications", "plain",
             also=["asthma_albuterol", "asthma_lisinopril"], absent=["albuterol_all"]),
    ]),
    # a follow-up answered from context with no tool call must keep its Query button
    Case("rechart", "Break down asthma patients by gender", "breakdown", "asthma", turns=[
        Case("t2", "Chart that, and state the total", "count", "asthma",
             pattern=r"```chart"),
    ]),
    # --- breakdowns, checked cell by cell
    Case("breakdown_1d", "Break down asthma patients by gender", "breakdown", "asthma"),
    # one asthma patient has no recorded gender; the answer must say so or the table
    # visibly fails to add up (rows 840, total 841)
    Case("breakdown_2d", "Break down asthma patients by gender and race", "breakdown",
         "asthma", pattern=r"\b(1|one)\b[^.|]*(no|without|missing|unknown|unrecorded)"
                           r"[^.|]*gender"),
    Case("breakdown_whole", "How many patients are there of each gender?", "breakdown",
         also=["female", "male"]),
    Case("agg_breakdown", "Break down subjects by encounter type", "masked",
         user="agguser", dataset="dataset1_stored"),
    # --- report lifecycle, verified against Chiron's API after each step
    Case("report_flow", "", "report_flow"),
    Case("delete_refused", "", "delete_refused"),
    # --- the Results tab and report columns, checked in Chiron's own API
    Case("results_flow", "", "results_flow"),
    Case("report_columns", "", "report_columns"),
    # --- identity and permissions
    Case("hijack", "", "hijack"),
    Case("no_access", "How many patients are in dataset2_stored?", "refuse"),
    Case("agg_user", "How many subjects are there?", "agg", user="agguser",
         dataset="dataset1_stored"),
    Case("admin_user", "How many patients have asthma?", "count", "asthma", user="admin"),
]


def run_suggestions(features: list[str]) -> int:
    """Every starter question in the pool the page picks from must give a real answer.

    The pool is built from the dataset's own values, so a starter could name something
    the tools cannot answer. Checked for each: no error or refusal, a figure, table or
    chart, the button its feature promises (Report, Results, or the Query hand-off), a Query
    button that loads, and at most three sane follow-ups.
    """
    cookie = mint_session("demouser")
    SESSIONS["demouser"] = cookie
    pool = get_json(f"{ASK}/datasets?dataset={DS}", cookie).get("pool") or []
    if features:
        pool = [p for p in pool if p["feature"] in features]
    print(f"running {len(pool)} starter questions against {ASK} ...\n")

    def one(item):
        r = Result(Case(item["feature"], item["q"], "starter"))
        t0 = time.time()
        try:
            ev = ask(item["q"], cookie)
        except Exception as exc:  # noqa: BLE001
            r.fail(f"/ask raised {exc}")
            return r
        r.seconds = time.time() - t0
        answer = ev.get("answer") or ""
        r.answer, r.steps = answer, ev.get("step", [])
        link, cohort, followups = ev.get("link"), ev.get("cohort"), ev.get("followups") or []
        if "error" in ev:
            r.fail(f"error event: {str(ev['error'])[:140]}")
        if not answer.strip():
            r.fail("empty answer")
        elif REFUSAL.search(answer) and item["feature"] != "filters":
            r.fail("answered with a refusal")
        has_table = bool(re.search(r"^\s*\|.*\|\s*$", answer, re.M))
        if not (numbers(answer) or has_table or "```chart" in answer) and item["feature"] != "filters":
            r.fail("no figure, table or chart")
        low = answer.lower()
        for phrase in CLUTTER:
            if phrase in low:
                r.fail(f"clutter: {phrase!r}")
        if item["feature"] in ("report", "columns"):
            m = re.search(r"/reports/(\d+)", (link or {}).get("url", ""))
            if not m:
                r.fail(f"no Report button (link: {link})")
            else:
                r.created.append(int(m.group(1)))
        if item["feature"] == "query" and (not link or link.get("label") != "Query"):
            r.fail(f"no Query hand-off (link: {link})")
        if item["feature"] == "results" and (not link or link.get("label") != "Results"):
            r.fail(f"no Results button (link: {link})")
        if item["feature"] == "ranking" and "```chart" not in answer and not has_table \
                and "chart" in item["q"].lower():
            r.fail("asked for a chart, got none")
        if cohort:
            loaded = post_json(f"{ASK}/load", cohort, cookie)
            if loaded.get("error"):
                r.fail(f"Query button fails: {loaded['error'][:120]}")
        if len(followups) > 3 or any(len(f) > 90 for f in followups):
            r.fail(f"bad follow-ups {followups}")
        return r

    with ThreadPoolExecutor(max_workers=4) as pool_ex:
        results = list(pool_ex.map(one, pool))
    failed = [r for r in results if not r.ok]
    for r in results:
        mark = "PASS" if r.ok else "FAIL"
        print(f"{mark}  {r.case.id:12} {r.seconds:5.0f}s  {r.case.q}")
        for n in r.notes:
            print(f"        {n}")
        if not r.ok:
            print("        answer: " + r.answer.replace("\n", " ")[:220])
    cleanup(results)
    print(f"\n{len(results) - len(failed)}/{len(results)} starter questions passed")
    return 1 if failed else 0


def main() -> int:
    if "--suggestions" in sys.argv:
        return run_suggestions([a for a in sys.argv[1:] if a != "--suggestions"])
    only = sys.argv[1:] and sys.argv[1]
    cases = [c for c in CASES if not only or only in c.id]
    print(f"computing ground truth from {SCHEMA} ...")
    truth = truths()
    grid = truth.pop("_grid")
    for k, v in truth.items():
        print(f"  {k:24} {v}")
    print(f"  {'asthma gender x race':24} {grid}")
    sessions = {u: mint_session(u) for u in {c.user for c in cases} | {"admin", "demouser"}}
    SESSIONS.update(sessions)
    for c in cases:
        if c.id == "breakdown_1d":
            c.cells = [truth["female_asthma"]["right"], truth["asthma_male"]["right"]]
        if c.id == "breakdown_2d":
            c.cells = sorted({n for n in grid.values() if n})
            c.partial_rows = [[grid[(g, race)] for race in
                               ("white", "black", "other", "asian", "native")]
                              for g in ("F", "M")]

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
    cleanup(results)
    print(f"\n{len(results) - failed}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

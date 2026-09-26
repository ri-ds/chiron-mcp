"""A small web server that puts a chat box in front of the Chiron MCP tools.

Each question is answered by running Claude Code headless (`claude -p`) with this
project's MCP server loaded, so it uses the operator's existing Claude subscription
rather than an API key. Progress and the final answer stream back over SSE.

    .venv/bin/python -m chiron_mcp.webapp

Then open http://localhost:8900, or embed that URL in the Chiron UI (see
docs/chiron-ui-integration.md).

Standard library only, so it adds no dependencies to the MCP server itself.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from chiron_mcp.config import CONFIG

HERE = Path(__file__).resolve().parent
WEBUI = HERE / "webui"
PORT = int(os.environ.get("CHIRON_MCP_WEB_PORT", "8900"))

# Only the read-only analysis tools are offered by default. The hand-off tool is
# included so "open this in Chiron" works, but it is itself gated on
# CHIRON_MCP_ALLOW_SAVE inside the server.
TOOLS = [
    "chiron_datasets",
    "chiron_find_concepts",
    "chiron_describe_concept",
    "chiron_concept_values",
    "chiron_edit_cohort",
    "chiron_event_rule_options",
    "chiron_count_cohort",
    "chiron_run_table",
    "chiron_crosstab",
    "chiron_saved_reports",
    "chiron_run_saved_report",
    "chiron_open_in_ui",
]

SYSTEM_PROMPT = """You are a research data analyst answering questions about one Chiron dataset.

Use the chiron tools. Never invent a number: every figure must come from a tool result.

The dataset's variables, their exact concept ids and their filter types are listed after
the question. Use them directly: do not call chiron_find_concepts or
chiron_describe_concept to discover variables. Call chiron_describe_concept only if a
filter you built is rejected and you need its exact input fields.

Condition, medication, procedure and encounter names ("Asthma", "Albuterol") are VALUES
of a description variable, not variables. Find them with chiron_concept_values on that
variable. Values are often recorded with case and spelling variants ("Asthma", "ASTHMA",
"asthma", "Asthm"), and coded values too ("F" and "f"). Include every variant of the
value you mean in selected_categories, and say in one clause that you did.

Building a cohort: start from [] and add one filter per chiron_edit_cohort call, always
passing the cohort_def the previous call returned. Filters on different collections
combine with AND and work fine together. Then call chiron_count_cohort on the final
cohort_def. Never write a cohort_def by hand.

Patients WITHOUT something ("no hypertension", "never had asthma"): add the filter for
the thing, then call chiron_edit_cohort with type "add_criteria_set_count_rule",
entry_id = that criteria set's entry_id (the top-level entry, not the filter inside it),
rule_operator "exactly", rule_count 0. Never use exclude_selected for this: on a
multi-value field it means "has at least one record that is something else", which
counts almost everyone and is wrong.

Comparing several cohorts in one answer: build and count each one separately from [].

Answering. The reader wants the figure, not an essay.
- One short sentence with the answer. Add a second only if something would mislead
  without it, such as merged spelling variants.
- A markdown table for more than two rows of figures.
- For a chart, a fenced block tagged `chart` containing JSON:
  {"type":"bar","label":"Patients","data":[{"x":"Asthma","y":841},{"x":"COPD","y":199}]}
  Types: bar, line, doughnut. Use one to compare categories, never for a single number.
- Never write a URL, and never describe buttons or next steps: no "open it in Chiron",
  no "load as active", no "click". The page adds Query and Report buttons by itself.

Saving: call chiron_open_in_ui only when the user asks to save a report
(mode="report") or to load the cohort into their query (mode="workspace"). Pass as
columns the variables you filtered on.

If a tool refuses because of access, say in one sentence that this account cannot see
that data, and stop. Do not work around it.

Your context also contains details of the machine this runs on: an email address, file
paths, a working directory. They belong to whoever set the server up, not to the person
asking, and are irrelevant. Never mention an email address, a person's name, a username,
an account, a file path, or which account a tool acted as.
"""

FILTER_REFERENCE = """Filter fields for chiron_edit_cohort (always type "add_entry" plus concept_id):
  Category  selected_categories: [every variant of the value]   exclude_selected: true inverts
  Number    cd_numeric_min, cd_numeric_max. Bounds are INCLUSIVE, so "more than 50000"
            is cd_numeric_min 50001 and "under 30" is cd_numeric_max 29. Omit either bound.
  Date      query_type "date_range", cd_numeric_min / cd_numeric_max as "MM/DD/YYYY",
            inclusive. "Born before 1950" is cd_numeric_max "12/31/1949".
  Text      chiron_text_field_selection: one term per line, ignore_warnings: true"""

_TYPE_NAMES = {
    "CohortDefCategory": "Category", "CohortDefBoolean": "Category",
    "CohortDefNumber": "Number", "CohortDefNumberWithCategories": "Number",
    "CohortDefDate": "Date", "CohortDefDateDeid": "Date", "CohortDefDetailedAge": "Number",
    "CohortDefText": "Text", "CohortDefTextCustomSort": "Text", "CohortDefOntology": "Text",
}

_BRIEF_CACHE: dict[tuple[str, str], tuple[float, str, list[str]]] = {}
_BRIEF_TTL = 600.0


def dataset_brief(dataset_id: str, username: str, allow_superuser: bool) -> tuple[str, list[str]]:
    """The variables this identity may filter on, grouped by collection, plus their ids.

    Handed to the model up front so it does not spend five tool calls rediscovering the
    schema on every question; that search was most of the wait and most of the chips.
    Built as the requesting user, so it only lists what they are allowed to use.
    """
    import time

    key = (dataset_id, username)
    hit = _BRIEF_CACHE.get(key)
    if hit and time.time() - hit[0] < _BRIEF_TTL:
        return hit[1], hit[2]

    from chiron import models
    from chiron_mcp import identity

    ident = identity.resolve(dataset_id, username=username, allow_superuser=allow_superuser)
    cu = identity.checked_chironuser(ident)
    root = getattr(ident.dataset.root_collection, "permanent_id", None)
    by_coll: dict[str, list[str]] = {}
    ids: list[str] = []
    qs = models.Concept.objects.filter(
        collection__dataset=ident.dataset, published=True
    ).select_related("collection").order_by("collection__permanent_id", "permanent_id")
    for oConcept in qs:
        can_use, _ = oConcept.user_can_use_concept_in_cohort_def(cu)
        if not can_use:
            continue
        try:
            proc = oConcept.get_cohort_def_processor(cu)
            kind = _TYPE_NAMES.get(type(proc).__name__, "Other") if proc else "Other"
        except Exception:  # noqa: BLE001
            kind = "Other"
        coll = oConcept.collection.permanent_id
        by_coll.setdefault(coll, []).append(f"{oConcept.permanent_id} ({kind})")
        ids.append(oConcept.permanent_id)

    lines = [f"Dataset {dataset_id}. Variables you may use, by collection:"]
    for coll, items in by_coll.items():
        tag = "  [one row per patient]" if coll == root else ""
        lines.append(f"  {coll}{tag}: " + ", ".join(items))
    brief = "\n".join(lines) + "\n\n" + FILTER_REFERENCE
    _BRIEF_CACHE[key] = (time.time(), brief, ids)
    return brief, ids


def suggestions_for(concept_ids: list[str]) -> list[str]:
    """Starter questions that work on this dataset, checked by tests/ask_e2e.py.

    Each one exercises something different (a chart, a two-collection cohort, a numeric
    bound, a date bound, a report, a workspace hand-off) rather than five ways of asking
    for a count.
    """
    have = {c.split("__", 1)[-1] for c in concept_ids}
    synthea = {"condition__description", "subject__gender", "subject__income",
               "subject__birthdate", "medication__description"}
    if synthea <= have:
        return [
            "Which 5 conditions affect the most patients? Chart it",
            "How many women have essential hypertension?",
            "Asthma patients earning over $50,000",
            "How many patients were born before 1950?",
            "Top 10 medications by number of patients",
            "Save a type 2 diabetes cohort as a report",
            "Load a COPD cohort into my query",
        ]
    return [
        "How many subjects are in this dataset?",
        "What can I filter on?",
    ]


def request_identity(cookie_header: str | None) -> tuple[str, bool]:
    """Who this request acts as, and whether a superuser is acceptable.

    The person logged into Chiron, when their session cookie is valid: the chat must see
    exactly what they could see in Chiron, no more, and must save reports they can open.
    With no session (the page opened on its own, outside Chiron) it falls back to
    CHIRON_MCP_USERNAME, and that configured service identity may not be a superuser.
    """
    who = session_username(cookie_header)
    if who:
        return who, True
    return CONFIG.username, False


def _mcp_config(username: str, allow_superuser: bool) -> Path:
    """A per-request MCP config, so two people asking at once never swap identities."""
    import tempfile

    env = {
        "CHIRON_MCP_CHIRON_SRC": CONFIG.chiron_src,
        "CHIRON_MCP_USERNAME": username,
        "CHIRON_MCP_MAX_ACCESS_LEVEL": CONFIG.max_access_level,
        "CHIRON_MCP_UI_URL": CONFIG.ui_url,
    }
    if CONFIG.metadata_db:
        env["CHIRON_MCP_METADATA_DB"] = CONFIG.metadata_db
    if CONFIG.warehouse_url:
        env["CHIRON_MCP_WAREHOUSE_URL"] = CONFIG.warehouse_url
    if CONFIG.allow_save:
        env["CHIRON_MCP_ALLOW_SAVE"] = "1"
    if allow_superuser:
        env["CHIRON_MCP_ALLOW_SUPERUSER"] = "1"

    console = Path(sys.executable).parent / "chiron-mcp"
    cfg = {"mcpServers": {"chiron": {"command": str(console), "env": env}}}
    fd, path = tempfile.mkstemp(prefix="chiron-mcp-", suffix=".json")
    with os.fdopen(fd, "w") as fh:
        json.dump(cfg, fh)
    return Path(path)


class _CohortTracker:
    """Work out which cohort, if any, the answer is about.

    Only results that actually succeeded count. The earlier version recorded whatever
    cohort_def the model *passed* to a tool, including ones the tool rejected, so the
    Query button sometimes carried a malformed or hand-written cohort and failed.
    """

    _COUNTED = {"chiron_count_cohort", "chiron_run_table", "chiron_export_table",
                "chiron_crosstab", "chiron_open_in_ui"}

    def __init__(self):
        self._calls: dict[str, tuple[str, dict]] = {}
        self.cohort: dict | None = None
        self.last_edit: dict | None = None
        self.link: dict | None = None

    def tool_use(self, block: dict) -> None:
        self._calls[block.get("id", "")] = (
            block.get("name", "").replace("mcp__chiron__", ""),
            block.get("input") or {},
        )

    def tool_result(self, block: dict) -> None:
        name, args = self._calls.get(block.get("tool_use_id", ""), ("", {}))
        if not name or block.get("is_error"):
            return
        content = block.get("content")
        if isinstance(content, list):
            content = "".join(c.get("text", "") for c in content if isinstance(c, dict))
        try:
            data = json.loads(content or "")
        except (TypeError, ValueError):
            return
        if not isinstance(data, dict) or data.get("error"):
            return

        ds = args.get("dataset_id")
        if name == "chiron_edit_cohort":
            if data.get("successful") and data.get("cohort_def"):
                self.last_edit = {"dataset_id": ds, "cohort_def": data["cohort_def"],
                                  "columns": []}
            return
        if name not in self._COUNTED or not args.get("cohort_def"):
            return
        self.cohort = {
            "dataset_id": ds,
            "cohort_def": args["cohort_def"],
            "columns": [c for c in (args.get("columns") or []) if isinstance(c, dict)],
        }
        if name == "chiron_open_in_ui" and data.get("url"):
            self.link = {
                "label": "Report" if data.get("mode") == "report" else "Query",
                "url": data["url"],
                "mode": data.get("mode"),
            }

    def final(self) -> dict | None:
        return self.cohort or self.last_edit


def verify_cohort(state: dict, username: str, allow_superuser: bool) -> dict | None:
    """Re-check a cohort as the requesting user before offering a button for it.

    Runs the same validation /load will run and counts it, so every Query button that
    appears is one that works, and it can say how many subjects it will load. Returns
    None for whole-dataset cohorts (nothing to load) and anything that fails.
    """
    from chiron.query_engine import get_querytool
    from chiron_mcp import identity, server as S

    try:
        ident = identity.resolve(
            state["dataset_id"], username=username, allow_superuser=allow_superuser
        )
        identity.require_workspace(ident)
        identity.require_subject_level(ident)
        cohort = S._validated_cohort(ident, state.get("cohort_def") or [])
        if not cohort.cohort_def:
            return None
        n = get_querytool(identity.checked_chironuser(ident), cohort.cohort_def).get_cohort_count()
        return {**state, "cohort_def": cohort.cohort_def, "subject_count": int(n)}
    except Exception:  # noqa: BLE001
        return None


_NEUTRAL: str | None = None


def _neutral_dir() -> str:
    """An empty directory to run Claude in, so no project memory or CLAUDE.md loads."""
    global _NEUTRAL
    if not _NEUTRAL or not os.path.isdir(_NEUTRAL):
        import tempfile

        _NEUTRAL = tempfile.mkdtemp(prefix="chiron-ask-")
    return _NEUTRAL


_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PATH = re.compile(r"(?<![\w])(?:/Users|/home|/private|/tmp|/var/folders)/[^\s`'\")\]]*")


_URL = re.compile(r"\[([^\]]*)\]\((https?://[^)\s]+)\)|<?(https?://[^\s>)]+)>?")


def tidy(answer: str) -> str:
    """Remove links into Chiron from the prose; the page shows them as buttons.

    The model is told not to write URLs, but it sometimes does, and a pasted URL used to
    become a second Report button next to the real one.
    """
    base = CONFIG.ui_url.rstrip("/")

    def repl(m: re.Match) -> str:
        url = m.group(2) or m.group(3) or ""
        if base and url.startswith(base):
            return m.group(1) or ""
        return m.group(0)

    out = _URL.sub(repl, answer)
    # Answers about cohorts never need an email address or a local path, and the
    # headless session can see the operator's (see ask_stream), so neither leaves here.
    out = _EMAIL.sub("[redacted]", out)
    out = _PATH.sub("", out)
    out = re.sub(r"[ \t]*[:—-]?[ \t]*\n(?=\s*\n)", "\n", out)
    return re.sub(r"\n{3,}", "\n\n", out).strip()


def ask_stream(question: str, dataset: str | None, username: str, allow_superuser: bool):
    """Run Claude headless as `username` and yield (event, payload) tuples as it works.

    Events: step, link, cohort (verified, with its subject count), answer, error.
    """
    claude = shutil.which("claude") or os.path.expanduser("~/.local/bin/claude")
    if not Path(claude).exists():
        yield "error", "Claude Code CLI not found. Install it, or put `claude` on PATH."
        return

    prompt = question
    if dataset:
        try:
            brief, _ = dataset_brief(dataset, username, allow_superuser)
            prompt = f"Question: {question}\n\n{brief}"
        except Exception as exc:  # noqa: BLE001
            # No access to this dataset: let the model hit the same refusal and say so.
            prompt = f"[dataset: {dataset}]\n\n{question}\n\n(Access check: {exc})"

    cfg = _mcp_config(username, allow_superuser)
    # Isolate the headless session from the operator's own Claude Code setup. Without
    # this it inherits their git identity, project files, memory and every other MCP
    # server they have configured, and it will repeat any of it in an answer. The
    # account email is injected by Claude Code itself and cannot be switched off without
    # an API key (--bare), which is why tidy() also redacts on the way out.
    cmd = [
        claude, "-p", prompt,
        "--mcp-config", str(cfg),
        "--strict-mcp-config",
        "--setting-sources", "",
        "--allowed-tools", ",".join(f"mcp__chiron__{t}" for t in TOOLS),
        "--system-prompt", SYSTEM_PROMPT,
        "--output-format", "stream-json",
        "--verbose",
    ]
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL, text=True, bufsize=1, cwd=_neutral_dir(),
    )
    tracker = _CohortTracker()
    try:
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue

            kind = ev.get("type")
            if kind == "assistant":
                for block in ev.get("message", {}).get("content", []):
                    if block.get("type") == "tool_use":
                        raw = block.get("name", "")
                        # Only surface Chiron work; Claude's own housekeeping is noise.
                        if not raw.startswith("mcp__chiron__"):
                            continue
                        tracker.tool_use(block)
                        yield "step", raw.replace("mcp__chiron__chiron_", "")
            elif kind == "user":
                for block in ev.get("message", {}).get("content", []) or []:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        tracker.tool_result(block)
            elif kind == "result":
                if ev.get("is_error"):
                    yield "error", ev.get("result") or "Claude returned an error."
                    continue
                if tracker.link:
                    yield "link", tracker.link
                # A workspace hand-off has already loaded the query, and its link says
                # so; a second Query button for the same cohort would just repeat it.
                if not (tracker.link and tracker.link.get("mode") == "workspace"):
                    state = tracker.final()
                    verified = state and verify_cohort(state, username, allow_superuser)
                    if verified:
                        yield "cohort", verified
                yield "answer", tidy(ev.get("result", ""))
        proc.wait(timeout=10)
        if proc.returncode not in (0, None):
            err = (proc.stderr.read() or "").strip()
            if err:
                yield "error", err[:500]
    finally:
        if proc.poll() is None:
            proc.kill()
        try:
            cfg.unlink()
        except OSError:
            pass


def session_username(cookie_header: str | None) -> str | None:
    """The Django user behind a browser's Chiron session cookie, if any.

    Chiron and this server are reached on the same host (the UI proxies one and
    iframes the other), and cookies ignore the port, so the browser sends Chiron's
    `sessionid` here too.  Resolving it lets "use this as my query" land in the
    workspace of the person who clicked rather than in CHIRON_MCP_USERNAME's.
    """
    if not cookie_header:
        return None
    from http.cookies import SimpleCookie

    jar = SimpleCookie()
    try:
        jar.load(cookie_header)
    except Exception:  # noqa: BLE001
        return None
    if "sessionid" not in jar:
        return None
    try:
        from chiron_mcp import server as S  # noqa: F401  (boots Django)
        from django.contrib.auth import get_user_model
        from django.contrib.sessions.models import Session
        from django.utils import timezone

        sess = Session.objects.filter(
            session_key=jar["sessionid"].value, expire_date__gt=timezone.now()
        ).first()
        if not sess:
            return None
        uid = sess.get_decoded().get("_auth_user_id")
        user = get_user_model().objects.filter(pk=uid, is_active=True).first()
        return user.username if user else None
    except Exception:  # noqa: BLE001
        return None


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # keep the console quiet
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        url = urlparse(self.path)

        if url.path in ("/", "/index.html"):
            return self._file(WEBUI / "index.html", "text/html; charset=utf-8")
        if url.path == "/health":
            return self._json({"ok": True, "identity": CONFIG.username})
        if url.path == "/datasets":
            return self._datasets()
        if url.path == "/ask":
            return self._ask(parse_qs(url.query))

        self.send_error(404)

    def do_POST(self):
        url = urlparse(self.path)
        if url.path == "/load":
            return self._load()
        self.send_error(404)

    def _file(self, path: Path, ctype: str):
        if not path.exists():
            return self.send_error(404)
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        # The page is read from disk on every request, so never let a browser hold on
        # to an old copy: an edit here should show up on reload, not after a hard
        # refresh someone has to know to do.
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _datasets(self):
        """Who is asking, what they may use, and starter questions for ?dataset=."""
        who, allow_su = request_identity(self.headers.get("Cookie"))
        dataset = (parse_qs(urlparse(self.path).query).get("dataset") or [None])[0]
        out: dict = {"identity": who, "datasets": [], "suggestions": []}
        try:
            from chiron import models
            from chiron_mcp import identity

            for oDataset in models.Dataset.objects.all().order_by("unique_id"):
                try:
                    ident = identity.resolve(
                        oDataset.unique_id, username=who, allow_superuser=allow_su
                    )
                except identity.AccessError:
                    continue
                out["datasets"].append({
                    "id": oDataset.unique_id,
                    "name": oDataset.display_name or oDataset.unique_id,
                    "access_level": ident.access_level,
                })
            if dataset:
                match = next((d for d in out["datasets"] if d["id"] == dataset), None)
                out["access_level"] = match["access_level"] if match else None
                if match and match["access_level"] in ("phi", "deid"):
                    _, ids = dataset_brief(dataset, who, allow_su)
                    out["suggestions"] = suggestions_for(ids)
        except Exception as exc:  # noqa: BLE001
            out["error"] = str(exc)
        return self._json(out)

    def _origin_ok(self) -> bool:
        """Reject cross-site POSTs to /load.

        /load writes to the workspace of whoever the request's session cookie belongs
        to, so without this a page on another origin could make a visitor's browser
        clobber their Chiron query. Same-origin requests from the page itself send an
        Origin of this server; the UI embeds us in an iframe, which does not change it.
        """
        origin = self.headers.get("Origin")
        if not origin:
            return True  # curl, scripts, and same-origin form posts from this page
        allowed = {
            f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}",
            CONFIG.ui_url,
        }
        extra = os.environ.get("CHIRON_MCP_ALLOWED_ORIGINS", "")
        allowed |= {o.strip() for o in extra.split(",") if o.strip()}
        return origin in allowed

    def _load(self):
        """Replace the browser user's live Chiron query with a cohort from an answer.

        Body: {"dataset_id", "cohort_def", "columns"?}.  Writes to the workspace of the
        Chiron user behind the request's session cookie, falling back to
        CHIRON_MCP_USERNAME when there is none.  Same guards as chiron_open_in_ui:
        CHIRON_MCP_ALLOW_SAVE must be on, and an errored definition is refused.
        """
        if not self._origin_ok():
            return self._json({"error": "Refused: request came from an untrusted origin."})
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, TypeError):
            return self._json({"error": "Body must be JSON."})
        dataset_id = body.get("dataset_id")
        cohort_def = body.get("cohort_def")
        if not dataset_id or not isinstance(cohort_def, list) or not cohort_def:
            return self._json({"error": "dataset_id and a non-empty cohort_def are required."})

        from chiron_mcp import server as S

        who, allow_su = request_identity(self.headers.get("Cookie"))
        result = S.open_in_ui(
            dataset_id, cohort_def, body.get("columns") or [], mode="workspace",
            username=who, allow_superuser=allow_su,
        )
        result["browser_user"] = who
        return self._json(result)

    def _ask(self, params):
        question = (params.get("q") or [""])[0].strip()
        dataset = (params.get("dataset") or [None])[0]
        if not question:
            return self.send_error(400, "missing q")

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self._cors()
        self.end_headers()

        def send(event, data):
            chunk = f"event: {event}\ndata: {json.dumps(data)}\n\n"
            self.wfile.write(chunk.encode())
            self.wfile.flush()

        who, allow_su = request_identity(self.headers.get("Cookie"))
        try:
            for event, payload in ask_stream(question, dataset, who, allow_su):
                send(event, payload)
            send("done", "")
        except (BrokenPipeError, ConnectionResetError):
            pass  # the browser navigated away


def main() -> int:
    if not CONFIG.username:
        print("CHIRON_MCP_USERNAME is required.", file=sys.stderr)
        return 1
    WEBUI.mkdir(exist_ok=True)
    # Boot Django once, up front: several handlers use the ORM directly, and a request
    # with no session cookie would otherwise reach it before anything had set it up.
    from chiron_mcp.bootstrap import ensure_django

    ensure_django()
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Chiron Ask running at http://localhost:{PORT}")
    print("  identity : the user logged into Chiron; with no session, "
          f"{CONFIG.username} (ceiling {CONFIG.max_access_level})")
    print(f"  chiron ui: {CONFIG.ui_url}")
    print("  Ctrl-C to stop")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

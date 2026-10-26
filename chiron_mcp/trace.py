"""How one Ask answer was produced, step by step, so a wrong answer can be traced to
the step that made it wrong.

The Ask page shows a trace under an answer when the reader asks for it. Every step the
headless Claude run took is recorded against the clock:

- starting Claude Code and the Chiron tools;
- each model call, with the model's own summarised reasoning, what it said between
  tools and which tools it chose;
- each Chiron tool call, with its exact input and output, how long it took and what it
  found ("8,651 patients", "rejected: ...");
- API retries, rate limits and timeouts;
- what the server then did with the final text: which suggested follow-ups it kept,
  which charts it found, and whether the Query button's cohort matched the figure the
  answer leads with.

Checks then run over the whole record and point at the step where something the answer
depends on went wrong: a figure that appears in no tool result, a cohort the model
wrote by hand instead of building it with chiron_edit_cohort, a count rule Chiron does
not understand, a spelling variant left out of a filter, and so on.

A trace holds tool results, which can be patient-level data. It is stored next to the
conversation's transcript, readable only by the person who asked, and deleted with it
(see webapp._Threads). Tracing must never break an answer, so every hook here swallows
its own errors and records them in the trace instead.

Standard library only.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
import threading
import time
import uuid
from pathlib import Path

VERSION = 1

# What each Chiron tool call means to someone reading the timeline. The page uses the
# same words for the progress chips it shows while an answer is coming.
TOOL_LABELS = {
    "query": "Asking Chiron",
    "datasets": "Checking access", "find_concepts": "Finding variables",
    "describe_concept": "Reading a variable", "concept_values": "Looking up values",
    "edit_cohort": "Building filters", "event_rule_options": "Checking date rules",
    "count_cohort": "Counting patients", "run_table": "Pulling rows", "export_table": "Exporting",
    "crosstab": "Cross-tabulating", "breakdown": "Breaking down", "saved_reports": "Reading reports",
    "run_saved_report": "Running a report", "open_in_ui": "Saving to Chiron",
    "update_report": "Updating the report", "delete_report": "Deleting the report",
    "results": "Reading your results", "update_results": "Updating your results",
    "column_options": "Checking column options",
}

# Tools that run a cohort the model hands them. Their cohort_def should always be one
# Chiron produced (chiron_edit_cohort, a saved report, an earlier answer), never one the
# model typed out.
COHORT_TOOLS = {
    "chiron_count_cohort", "chiron_run_table", "chiron_export_table", "chiron_crosstab",
    "chiron_breakdown", "chiron_open_in_ui", "chiron_update_report", "chiron_update_results",
    "chiron_edit_cohort", "chiron_event_rule_options",
}

# The only count-rule types Chiron's query builder reads. Anything else ("at_least",
# "more than") falls through to its "exactly" branch without an error
# (where_builder.py), which silently changes the cohort.
RULE_TYPES = ("at least", "at most", "exactly")

# The fields Chiron reads for each cohort edit other than a filter (api/utils/
# cohort_def.py). Anything else is dropped without a word and the edit still reports
# success, so a guessed field name looks like it worked. A filter's own fields depend on
# its variable, so add_entry is judged separately.
EDIT_FIELDS = {
    "add_criteria_set": {"collection_id"},
    "add_criteria_set_count_rule": {"entry_id", "rule_operator", "rule_count"},
    "sort_cd_entries": {"entry_id", "child_ids"},
    "delete_entry": {"entry_id", "remove_empty_criteria_sets"},
    "delete_criteria_set": {"entry_id"},
    "set_criteria_set_alias": {"entry_id", "alias"},
    "change_to_boolean_or": {"entry_id"}, "change_to_boolean_and": {"entry_id"},
    "clear_all": set(),
}
# add_entry decides the criteria set itself (the first one for the variable's
# collection), so any field that tries to choose one is ignored.
_SET_FIELD = re.compile(r"set|parent|target|criteria|collection|group", re.I)

# Words that ask for patients WITHOUT something, which needs a count rule of exactly 0.
_NEGATION = re.compile(
    r"\b(but not|and not|without|never|not have|do not have|don't have|does not have|"
    r"doesn't have|no history of|free of|excluding)\b", re.I)

MAX_OUTPUT = 400_000      # characters of one tool result kept in the saved trace
MAX_PREVIEW = 6_000       # characters of it sent to the page while the answer streams
MAX_INPUT = 40_000        # characters of one tool input sent to the page
MAX_RAW_LINE = 40_000     # characters of one raw stream event kept for the debug view
MAX_RAW_TOTAL = 4_000_000

LIVE: dict[str, "Trace"] = {}      # answers still running, so their trace can be opened
_LIVE_GUARD = threading.Lock()


def _hash(cohort_def) -> str:
    return hashlib.sha1(
        json.dumps(cohort_def, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]


def _short(concept_id: str) -> str:
    """synthea-100k__condition__description -> condition description"""
    parts = str(concept_id or "").split("__")
    return " ".join(p.replace("_", " ") for p in parts[1:]) or str(concept_id)


def _plain_html(text: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", str(text or ""))
    text = re.sub(r"<[^>]+>", "", text)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def _number(v) -> str:
    return f"{v:,}" if isinstance(v, int) and not isinstance(v, bool) else str(v)


def _clip(text: str, n: int) -> str:
    text = str(text)
    return text if len(text) <= n else text[:n] + f"\n... ({len(text) - n:,} more characters)"


def _filter_text(f: dict) -> str:
    name = _short(f.get("concept_id"))
    cats = f.get("categories")
    if isinstance(cats, list) and cats:
        shown = ", ".join(f'"{c}"' for c in cats[:4]) + (f" +{len(cats) - 4} more" if len(cats) > 4 else "")
        return f"{name} {'NOT in' if f.get('exclude_selected') else 'in'} [{shown}]"
    lo, hi = f.get("min"), f.get("max")
    if lo is not None or hi is not None:
        kind = " (dates)" if f.get("query_type") == "date_range" else ""
        if lo is not None and hi is not None:
            return f"{name} from {lo} to {hi}{kind}"
        return f"{name} {'>=' if lo is not None else '<='} {lo if lo is not None else hi}{kind}"
    rest = {k: v for k, v in f.items() if k not in ("entry_id", "concept_id", "exclude_selected")}
    return f"{name} {json.dumps(rest)[:160]}"


def cohort_lines(cohort_def) -> list[str]:
    """A cohort definition as plain lines: one per criteria set, ANDed together."""
    lines = []
    for e in cohort_def or []:
        if not isinstance(e, dict):
            continue
        rule = e.get("subcol_count_restriction") or {"type": "at least", "value": 1}
        inner = [_filter_text(f) for f in e.get("list") or [] if isinstance(f, dict)]
        what = " AND ".join(inner) or "(no filters)"
        coll = e.get("collection_id") or "record"
        lines.append(f"{rule.get('type')} {rule.get('value')} {coll} record(s) where {what}")
    return lines


def _facts(name: str, args: dict, data) -> tuple[str, list[list[str]], str | None]:
    """(one-line outcome, [label, value] facts, Chiron's own description) of a result."""
    tool = name.replace("mcp__chiron__", "")
    if not isinstance(data, dict):
        text = str(data or "")
        return (text.splitlines()[0][:160] if text else "(no output)"), [], None
    if data.get("error"):
        return f"Rejected: {data['error']}", [["Error", str(data["error"])]], None
    facts: list[list[str]] = []
    describe = _plain_html(data["describe"]) if data.get("describe") else None
    summary = ""
    if tool == "chiron_count_cohort":
        n = data.get("subject_count")
        summary = f"{_number(n)} patients" + (" (whole dataset: no filters)" if data.get("is_whole_dataset") else "")
        facts.append(["Patients", _number(n)])
        if data.get("warnings"):
            facts.append(["Warnings", "; ".join(map(str, data["warnings"]))])
    elif tool == "chiron_query":
        n = data.get("count")
        summary = f"{_number(n)} patients" if n is not None else "Done"
        facts.append(["Patients", _number(n)])
        if data.get("what_was_counted"):
            facts.append(["Counted", str(data["what_was_counted"])[:400]])
        for m in data.get("matched") or []:
            facts.append([f"“{m.get('you asked')}”", f"{m.get('matched')} ({len(m.get('spellings') or [])} spellings)"])
        if data.get("group"):
            facts.append(["Group", str(data["group"])])
    elif tool == "chiron_edit_cohort":
        if data.get("successful"):
            summary = "Filter added" if (args.get("transformation") or {}).get("type") == "add_entry" \
                else f"{(args.get('transformation') or {}).get('type', 'edit')} applied"
            if data.get("validation_errors"):
                facts.append(["Validation errors", "; ".join(map(str, data["validation_errors"]))])
            if data.get("validation_warnings"):
                facts.append(["Validation warnings", "; ".join(map(str, data["validation_warnings"]))])
        else:
            errs = data.get("errors") or data.get("warnings") or ["no reason given"]
            summary = "Rejected: " + "; ".join(map(str, errs if isinstance(errs, list) else [errs]))
            facts.append(["Errors", "; ".join(map(str, errs if isinstance(errs, list) else [errs]))])
    elif tool == "chiron_concept_values":
        vals = data.get("values") or []
        summary = f"{len(vals)} values for {_short(data.get('concept_id') or args.get('concept_id'))}"
        top = ", ".join(f"{v.get('category')} ({_number(v.get('uniquePatientCount', v.get('count')))})"
                        for v in vals[:5] if isinstance(v, dict))
        if top:
            facts.append(["Most common", top])
    elif tool == "chiron_find_concepts":
        cs = data.get("concepts") or []
        summary = f"{data.get('count', len(cs))} variables found"
        facts.append(["Variables", ", ".join(str(c.get("concept_id")) for c in cs[:8] if isinstance(c, dict))])
    elif tool == "chiron_breakdown":
        rows = data.get("rows") or []
        by = [b.get("concept_id") for b in data.get("by") or [] if isinstance(b, dict)]
        summary = f"{len(rows)} groups by {' and '.join(_short(b) for b in by) or '?'}"
        totals = data.get("row_totals") or []
        if rows:
            facts.append(["Groups", ", ".join(f"{r} ({_number(t)})" for r, t in list(zip(rows, totals))[:8])])
        nv = data.get("no_value")
        if isinstance(nv, dict):
            nv = ", ".join(f"{_short(k) if '__' in str(k) else k}: {_number(v)}" for k, v in nv.items())
        if nv is not None:
            facts.append(["Patients with no value", _number(nv)])
        mv = data.get("merged_variants")
        if isinstance(mv, dict) and mv:
            facts.append(["Spellings merged", ", ".join(
                f"{k} ({len(v)} spellings)" if isinstance(v, list) else str(k) for k, v in list(mv.items())[:8])
                + (f", +{len(mv) - 8} more" if len(mv) > 8 else "")])
    elif tool in ("chiron_run_table", "chiron_run_saved_report", "chiron_results", "chiron_export_table"):
        rows = data.get("rows")
        n = data.get("row_count", data.get("total_rows", len(rows) if isinstance(rows, list) else None))
        summary = f"{_number(n)} rows" if n is not None else "Table read"
        if data.get("subject_count") is not None:
            facts.append(["Patients", _number(data["subject_count"])])
    elif tool in ("chiron_open_in_ui", "chiron_update_report", "chiron_update_results"):
        summary = f"Saved ({data.get('mode') or 'done'})"
        if data.get("changed"):
            facts.append(["Changed", ", ".join(map(str, data["changed"]))])
        if data.get("url"):
            facts.append(["Link", str(data["url"])])
    elif tool == "chiron_delete_report":
        summary = "Report deleted" if data.get("deleted") else "Not deleted"
    elif tool == "chiron_datasets":
        ds = data.get("datasets") or []
        ok = [d.get("dataset_id") for d in ds if isinstance(d, dict) and d.get("accessible")]
        summary = f"{len(ok)} of {len(ds)} datasets accessible"
    elif tool == "chiron_describe_concept":
        summary = f"{_short(data.get('concept_id') or args.get('concept_id'))}: " \
                  f"{(data.get('filter_input') or {}).get('processor', 'described')}"
    elif tool == "chiron_saved_reports":
        reps = data.get("reports") or []
        summary = f"{len(reps)} reports"
    if not summary:
        scalars = [(k, v) for k, v in data.items() if isinstance(v, (str, int, float, bool))][:4]
        summary = ", ".join(f"{k}: {str(v)[:40]}" for k, v in scalars) or "Done"
    for key in ("subject_count", "is_whole_dataset", "entry_id"):
        if key in data and not any(f[0].lower() == key.replace("_", " ") for f in facts) \
                and tool != "chiron_count_cohort":
            facts.append([key.replace("_", " ").capitalize(), _number(data[key])])
    return summary, facts, describe


# --- figures ----------------------------------------------------------------------------

_FIG = re.compile(r"(?<![\w.,])\d[\d,]*(?:\.\d+)?(?:\s?%)?")


def _figures(text: str) -> list[dict]:
    """Every number written in a piece of text, with commas read as thousands."""
    out = []
    for m in _FIG.finditer(text or ""):
        raw = m.group().rstrip(",")
        pct = raw.endswith("%")
        core = raw.rstrip("% ").rstrip(",")
        if "," in core and not re.fullmatch(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?", core):
            continue  # a list such as "1,2,3", not a number
        try:
            value = float(core.replace(",", ""))
        except ValueError:
            continue
        out.append({"text": raw, "value": value, "pct": pct, "decimal": "." in core})
    return out


def _numbers_in(text: str) -> set[str]:
    """Numbers in machine output (JSON), as normalised strings."""
    text = re.sub(r"(?<=\d),(?=\d{3}\b)", "", text or "")
    out = set()
    for m in re.finditer(r"(?<![\w.])\d+(?:\.\d+)?", text):
        s = m.group()
        out.add(_norm_num(float(s)))
    return out


def _norm_num(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:.6g}"


# --- charts -----------------------------------------------------------------------------

_CHART = re.compile(r"```chart\s*([\s\S]*?)```")


def chart_audit(text: str) -> list[dict]:
    """Each ```chart block in an answer, as the page will read it, with any problems."""
    out = []
    for body in _CHART.findall(text or ""):
        item: dict = {"source": body.strip()[:4000], "issues": []}
        try:
            spec = json.loads(body)
        except ValueError as exc:
            item.update(ok=False, issues=[f"Not valid JSON ({exc}), so the page drops the chart."])
            out.append(item)
            continue
        item.update(ok=True, spec=spec)
        if not isinstance(spec, dict):
            item["issues"].append("The chart is not a JSON object.")
        else:
            if spec.get("type", "bar") not in ("bar", "line", "doughnut"):
                item["issues"].append(f"Unknown chart type {spec.get('type')!r}; Chart.js may refuse it.")
            if isinstance(spec.get("series"), list) and isinstance(spec.get("x"), list):
                for s in spec["series"]:
                    ys = (s or {}).get("y") or []
                    if len(ys) != len(spec["x"]):
                        item["issues"].append(
                            f"Series {s.get('label')!r} has {len(ys)} values for {len(spec['x'])} bars.")
                    if any(not isinstance(y, (int, float)) for y in ys):
                        item["issues"].append(f"Series {s.get('label')!r} has values that are not numbers.")
                bars = len(spec["x"])
            else:
                data = spec.get("data") or []
                if not data:
                    item["issues"].append("The chart has no data.")
                if any(not isinstance((d or {}).get("y"), (int, float)) for d in data if isinstance(d, dict)):
                    item["issues"].append("Some bars have values that are not numbers.")
                bars = len(data)
            if bars == 1:
                item["issues"].append("A chart with a single bar: the prompt asks for no chart of one number.")
            if not spec.get("title"):
                item["issues"].append("No title, so the reader cannot tell what the bars are.")
        out.append(item)
    return out


# --- the trace --------------------------------------------------------------------------


class Trace:
    """The record of one answer. Fed the CLI's stream-json events as they arrive."""

    def __init__(self, *, question: str, dataset: str | None, user: str, thread: str,
                 followup: bool, prior: list[dict] | None = None, inherited: dict | None = None,
                 redact=None):
        prior = prior or []
        self.id = uuid.uuid4().hex
        self._t0 = time.monotonic()
        self._lock = threading.RLock()
        self._redact = redact or (lambda s: s)
        self._steps: dict[str, dict] = {}
        self._order: list[dict] = []
        self._dirty: list[str] = []
        self._model: dict | None = None
        self._tools: dict[str, dict] = {}
        self._idle_since: float | None = None
        self._post: dict | None = None
        self._raw_chars = 0
        self._n = 0
        self._calls = 0
        # Cohort definitions Chiron itself produced, in this conversation so far: every
        # cohort a tool is handed should be one of these.
        self._known = {h for p in prior for h in p.get("cohorts") or []}
        if inherited and inherited.get("cohort_def"):
            self._known.add(_hash(inherited["cohort_def"]))
        self._made: list[str] = []
        # Figures earlier answers in the conversation stated or counted: a follow-up may
        # rightly repeat them ("6.7% of the 5,885") without a tool call of its own.
        self._earlier = {n for p in prior for n in p.get("numbers") or []}
        # Claude Code reports cost summed over the whole resumed conversation; the last
        # traced answer's total is what to subtract to get this answer's share.
        self._prior_cost = prior[-1].get("cost") if prior else None
        self.data: dict = {
            "id": self.id, "version": VERSION, "started": time.time(),
            "question": question, "dataset": dataset, "user": user, "thread": thread,
            "followup": followup, "turn": len(prior) + 1 if followup else 1,
            "previous": [p.get("question") for p in prior],
            # A follow-up whose earlier answers were not all traced (asked before tracing
            # was on) cannot tell a carried-over cohort from a hand-written one.
            "prior_complete": not followup or bool(prior),
            "inherited": cohort_lines((inherited or {}).get("cohort_def")) if inherited else None,
            "model": None, "claude_version": None, "tools": [], "mcp_servers": [],
            "prompt": {}, "command": [], "post": {}, "result": None, "rate_limit": None,
            "answer": None, "error": None, "done": False, "ended": None,
            "stats": {}, "checks": [], "figures": [], "raw": [], "raw_skipped": {},
            "trace_errors": [],
        }
        self.step("request", label="Question received", t1=0.0, status="ok",
                  summary=("Follow-up " if followup else "New question ") + f"#{self.data['turn']}"
                  + (f" in this conversation ({len(prior)} earlier)" if followup else ""))
        with _LIVE_GUARD:
            LIVE[self.id] = self

    # -- bookkeeping ---------------------------------------------------------------------

    def now(self) -> float:
        return round((time.monotonic() - self._t0) * 1000, 1)

    def step(self, kind: str, *, label: str, t0: float | None = None, **fields) -> dict:
        with self._lock:
            self._n += 1
            s = {"id": f"s{self._n}", "kind": kind, "label": label,
                 "t0": self.now() if t0 is None else t0, "t1": None, "status": "running"}
            s.update(fields)
            self._steps[s["id"]] = s
            self._order.append(s)
            self._touch(s)
            return s

    def _end(self, s: dict, status: str = "ok", t1: float | None = None, **fields) -> None:
        s["t1"] = self.now() if t1 is None else t1
        if s.get("status") in (None, "running"):
            s["status"] = status
        s.update(fields)
        self._touch(s)

    def _touch(self, s: dict) -> None:
        if s["id"] not in self._dirty:
            self._dirty.append(s["id"])

    def _guard(self, fn, *args, **kwargs):
        with self._lock:
            try:
                return fn(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001  a trace must never break an answer
                self.data["trace_errors"].append(f"{fn.__name__}: {type(exc).__name__}: {exc}"[:400])
                return None

    # -- what the server tells it --------------------------------------------------------

    def launched(self, cmd: list[str], prompt: str, system_prompt: str, resume: bool) -> None:
        self._guard(self._launched, cmd, prompt, system_prompt, resume)

    def _launched(self, cmd, prompt, system_prompt, resume):
        shown, skip = [], False
        for i, part in enumerate(cmd):
            if skip:
                skip = False
                continue
            if part in ("-p", "--system-prompt"):
                shown += [part, "<below>"]
                skip = True
            elif i == 0 or "/" in part:
                shown.append(Path(part).name)
            else:
                shown.append(part)
        self.data["command"] = shown
        self.data["prompt"] = {"text": prompt, "system": system_prompt, "resume": resume}
        self._startup = self.step(
            "startup", label="Starting Claude Code and the Chiron tools",
            summary="Resuming the conversation's saved session" if resume else "New session")

    def restarted(self, thread: str) -> None:
        """The conversation had expired, so the question was asked as a new one."""
        def go():
            self.data.update(thread=thread, followup=False, followup_lost=True)
            s = self.step("note", label="Conversation expired", status="warn",
                          summary="The saved conversation was gone, so this was asked as a new one, "
                                  "without the earlier questions or their cohorts.")
            s["t1"] = s["t0"]
        self._guard(go)

    def note(self, label: str, summary: str, status: str = "info", **fields) -> None:
        def go():
            s = self.step("note", label=label, summary=summary, status=status, **fields)
            s["t1"] = s["t0"]
        self._guard(go)

    def error(self, message: str) -> None:
        def go():
            self.data["error"] = message
            if self._post and self._post["t1"] is None:
                self._end(self._post, "error", summary="Skipped: the run ended in an error")
            s = self.step("error", label="Error", summary=message, status="error")
            s["t1"] = s["t0"]
        self._guard(go)

    def raw(self, line: str, ev: dict | None = None) -> None:
        """Keep one line of the stream for the debug view (`ev` if already parsed)."""
        self._guard(self._raw, line, ev)

    def _raw(self, line: str, ev: dict | None):
        if ev is None:
            try:
                ev = json.loads(line)
            except ValueError:
                ev = {"unparsed": line}
        kind = ev.get("type")
        if kind == "stream_event":
            # Token-by-token deltas (only there when the CLI was asked for them) would
            # swamp the record; they are counted, not kept.
            sub = (ev.get("event") or {}).get("type", "?")
            if sub not in ("message_start", "message_delta", "message_stop"):
                self.data["raw_skipped"][sub] = self.data["raw_skipped"].get(sub, 0) + 1
                return
        if self._raw_chars > MAX_RAW_TOTAL:
            self.data["raw_skipped"]["over the size limit"] = \
                self.data["raw_skipped"].get("over the size limit", 0) + 1
            return
        text = line if len(line) <= MAX_RAW_LINE else None
        self._raw_chars += min(len(line), MAX_RAW_LINE)
        self.data["raw"].append({"t": self.now(), "type": kind, "subtype": ev.get("subtype"),
                                 "event": ev if text is not None else None,
                                 "clipped": None if text is not None else line[:MAX_RAW_LINE]})

    def feed(self, ev: dict) -> None:
        self._guard(self._feed, ev)

    def _feed(self, ev: dict) -> None:
        kind = ev.get("type")
        if kind == "system":
            sub = ev.get("subtype")
            if sub == "init":
                self._on_init(ev)
            elif sub == "api_retry":
                self._on_retry(ev)
            elif sub == "thinking_tokens" and self._model:
                self._model["thinking_tokens"] = ev.get("estimated_tokens")
                self._touch(self._model)
            elif sub == "status" and ev.get("status") == "requesting":
                self._open_model(requested=True)
        elif kind == "stream_event":
            e = ev.get("event") or {}
            if e.get("type") == "message_start":
                m = self._open_model()
                if m.get("ttft") is None:
                    m["ttft"] = ev.get("ttft_ms") or round(self.now() - m["t0"], 1)
        elif kind == "assistant":
            self._on_assistant(ev)
        elif kind == "user":
            self._on_user(ev)
        elif kind == "tool_progress":
            s = self._tools.get(ev.get("parent_tool_use_id") or "") or self._tools.get(ev.get("tool_use_id") or "")
            if s:
                s["still_running_s"] = ev.get("elapsed_time_seconds")
                self._touch(s)
        elif kind == "rate_limit_event":
            info = ev.get("rate_limit_info") or {}
            self.data["rate_limit"] = info
            if info.get("status") not in (None, "allowed", "allowed_warning"):
                s = self.step("retry", label="Rate limited", status="warn",
                              summary=f"Claude account limit: {info.get('status')}"
                                      f" ({info.get('rateLimitType', 'limit')})")
                s["t1"] = s["t0"]
        elif kind == "result":
            self._on_result(ev)

    def _on_init(self, ev: dict) -> None:
        servers = [{"name": s.get("name"), "status": s.get("status")} for s in ev.get("mcp_servers") or []]
        self.data.update(model=ev.get("model"), claude_version=ev.get("claude_code_version"),
                         tools=[t.replace("mcp__chiron__", "") for t in ev.get("tools") or []],
                         mcp_servers=servers, permission_mode=ev.get("permissionMode"))
        bad = [s for s in servers if s["status"] != "connected"]
        st = getattr(self, "_startup", None) or self.step("startup", label="Starting Claude Code and the Chiron tools")
        self._end(st, "error" if bad or not servers else "ok",
                  summary=f"{ev.get('model')} · Claude Code {ev.get('claude_code_version')} · "
                  + ("Chiron tools connected" if servers and not bad else
                     "Chiron tools NOT connected: " + ", ".join(f"{s['name']} {s['status']}" for s in bad)
                     if bad else "no MCP server"),
                  model=ev.get("model"))
        self._idle_since = self.now()

    def _on_retry(self, ev: dict) -> None:
        delay = ev.get("retry_delay_ms") or 0
        err = ev.get("error") or ev.get("error_status") or "API error"
        s = self.step("retry", label=f"API busy, retry {ev.get('attempt', '?')} of {ev.get('max_retries', '?')}",
                      status="warn", summary=f"{err}; waiting {delay / 1000:.1f} s", detail=ev)
        s["t1"] = round(s["t0"] + delay, 1)
        self._touch(s)

    def _open_model(self, requested: bool = False) -> dict:
        if self._model and self._model["t1"] is None:
            return self._model
        t0 = self._idle_since if (self._idle_since is not None and not requested) else None
        self._idle_since = None
        self._calls += 1
        self._model = self.step(
            "model", label=f"Model #{self._calls}", t0=t0, call=self._calls,
            thinking="", text=[], chose=[], usage=None, msg_id=None, thinking_tokens=None,
            ttft=None, stop_reason=None)
        return self._model

    def _close_model(self) -> None:
        m = self._model
        if not m or m["t1"] is not None:
            return
        tools = m["chose"]
        if tools:
            names = [TOOL_LABELS.get(t, t).lower() for t in tools]
            m["label"] = f"Model #{m['call']} → " + ", ".join(dict.fromkeys(names))
        elif m["text"]:
            m["label"] = f"Model #{m['call']} → writes the answer"
        bits = []
        if m.get("thinking"):
            bits.append("reasoned")
        elif m.get("thinking_tokens"):
            bits.append(f"thought ~{m['thinking_tokens']:,} tokens")
        if tools:
            bits.append(f"called {len(tools)} tool{'s' if len(tools) > 1 else ''}")
        if m["text"]:
            bits.append(f"wrote {sum(len(t) for t in m['text']):,} characters")
        m["summary"] = ", ".join(bits) or "no output"
        self._end(m, "ok", t1=m.get("t_last", self.now()))

    def _on_assistant(self, ev: dict) -> None:
        msg = ev.get("message") or {}
        mid = msg.get("id")
        last = self._model
        if last and last["t1"] is not None and mid and last["msg_id"] == mid:
            # More of a message whose first tool already answered (parallel tool calls
            # arrive one block at a time): it is still the same model call.
            last.update(t1=None, status="running")
            self._idle_since = None
            m = last
        else:
            m = self._open_model()
        if m["msg_id"] and mid and mid != m["msg_id"]:
            self._close_model()
            self._idle_since = m["t1"]
            m = self._open_model()
        m["msg_id"] = m["msg_id"] or mid
        if msg.get("usage"):
            m["usage"] = msg["usage"]
        if msg.get("stop_reason"):
            m["stop_reason"] = msg["stop_reason"]
        for block in msg.get("content") or []:
            btype = block.get("type")
            if btype == "thinking":
                if block.get("thinking"):
                    m["thinking"] += block["thinking"]
            elif btype == "redacted_thinking":
                m["thinking_redacted"] = True
            elif btype == "text":
                if block.get("text"):
                    m["text"].append(block["text"])
            elif btype == "tool_use":
                raw = block.get("name", "")
                tool = raw.replace("mcp__chiron__chiron_", "").replace("mcp__chiron__", "")
                m["chose"].append(tool)
                args = block.get("input") or {}
                ds = self.data.get("dataset")
                s = self.step(
                    "tool", label=TOOL_LABELS.get(tool, tool.replace("_", " ").capitalize()),
                    tool=raw, short=tool, call_id=block.get("id"), parent=m["id"],
                    input=args, chiron=raw.startswith("mcp__chiron__"),
                    cohort=cohort_lines(args.get("cohort_def")) if isinstance(args.get("cohort_def"), list) else None,
                    cohort_hash=_hash(args["cohort_def"]) if isinstance(args.get("cohort_def"), list) and args["cohort_def"] else None,
                    off_dataset=bool(ds and args.get("dataset_id") and args["dataset_id"] != ds),
                )
                self._tools[block.get("id", "")] = s
        m["t_last"] = self.now()
        self._touch(m)

    def _on_user(self, ev: dict) -> None:
        content = (ev.get("message") or {}).get("content")
        if not isinstance(content, list):
            return
        results = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_result"]
        if not results:
            return
        self._close_model()
        for block in results:
            s = self._tools.pop(block.get("tool_use_id", ""), None)
            if not s:
                continue
            body = block.get("content")
            if isinstance(body, list):
                body = "".join(c.get("text", "") for c in body if isinstance(c, dict))
            body = body if isinstance(body, str) else json.dumps(body)
            try:
                data = json.loads(body)
            except (TypeError, ValueError):
                data = None
            summary, facts, describe = _facts(s["tool"], s["input"], data if data is not None else body)
            failed = bool(block.get("is_error")) or (isinstance(data, dict) and (
                bool(data.get("error")) or data.get("successful") is False))
            if block.get("is_error") and data is None:
                summary = "Error: " + body.strip().splitlines()[0][:200] if body.strip() else "Error"
            for cd in _cohorts_in(data):
                h = _hash(cd)
                self._made.append(h)
            pretty = json.dumps(data, indent=2) if data is not None else body
            self._end(s, "error" if failed else "ok", summary=summary, facts=facts, describe=describe,
                      output=data if data is not None and len(body) <= MAX_OUTPUT else None,
                      output_text=None if data is not None and len(body) <= MAX_OUTPUT else _clip(body, MAX_OUTPUT),
                      output_preview=_clip(pretty, MAX_PREVIEW), output_size=len(body),
                      output_numbers=sorted(_numbers_in(body), key=lambda x: float(x))[:5000])
        if not self._tools:
            self._idle_since = self.now()

    def _on_result(self, ev: dict) -> None:
        self._close_model()
        for s in list(self._tools.values()):
            self._end(s, "error", summary="No result came back before the run ended")
        self._tools.clear()
        usage = ev.get("usage") or {}
        self.data["result"] = {
            "is_error": ev.get("is_error"), "subtype": ev.get("subtype"),
            "stop_reason": ev.get("stop_reason"), "terminal_reason": ev.get("terminal_reason"),
            "num_turns": ev.get("num_turns"), "duration_ms": ev.get("duration_ms"),
            "duration_api_ms": ev.get("duration_api_ms"),
            "total_cost_usd": ev.get("total_cost_usd"), "usage": usage,
            "model_usage": ev.get("modelUsage"), "permission_denials": ev.get("permission_denials") or [],
            "api_error_status": ev.get("api_error_status"), "session_id": ev.get("session_id"),
            "text": ev.get("result"),
        }
        self._post = self.step("post", label="Checking the answer before showing it",
                               summary="Follow-up suggestions, charts, Query button")

    def step_for_call(self, call_id: str | None) -> str | None:
        with self._lock:
            return next((s["id"] for s in self._order if call_id and s.get("call_id") == call_id), None)

    def post(self, key: str, value) -> None:
        def go():
            self.data["post"][key] = value
            if self._post:
                self._touch(self._post)
        self._guard(go)

    def answer(self, text: str) -> None:
        def go():
            self.data["answer"] = text
            if self._post and self._post["t1"] is None:
                p = self.data["post"]
                bits = []
                c = p.get("cohort") or {}
                if c.get("offered") is not None:
                    bits.append(f"Query button for {c['offered']:,} patients")
                elif c.get("reason"):
                    bits.append("no Query button")
                if p.get("followups"):
                    shown = sum(1 for f in p["followups"] if f.get("shown"))
                    bits.append(f"{shown} follow-up suggestion{'s' if shown != 1 else ''}")
                if p.get("charts"):
                    bits.append(f"{len(p['charts'])} chart{'s' if len(p['charts']) > 1 else ''}")
                self._end(self._post, "ok", summary=", ".join(bits) or "Nothing to add")
        self._guard(go)

    # -- the end ------------------------------------------------------------------------

    def finish(self, rc: int | None = None, stderr: str = "") -> None:
        def go():
            if self.data["done"]:
                return
            self._close_model()
            for s in self._order:
                if s["t1"] is None:
                    self._end(s, "error" if s["kind"] == "tool" else "ok",
                              summary=s.get("summary") or "Did not finish")
            self.data.update(done=True, ended=self.now(), rc=rc, stderr=_clip(stderr or "", 20_000))
            self.data["cohorts"] = sorted(set(self._made))
            self.data["numbers"] = _carried_numbers(self)
            self.data["stats"] = _stats(self)
            self.data["figures"] = _figure_sources(self)
            self.data["checks"] = _checks(self)
        self._guard(go)
        with _LIVE_GUARD:
            LIVE.pop(self.id, None)

    # -- what the page gets --------------------------------------------------------------

    def _clean(self, obj):
        if isinstance(obj, str):
            return self._redact(obj)
        if isinstance(obj, list):
            return [self._clean(x) for x in obj]
        if isinstance(obj, dict):
            return {k: self._clean(v) for k, v in obj.items()}
        return obj

    @staticmethod
    def _compact(s: dict) -> dict:
        out = {k: v for k, v in s.items() if k not in ("output", "output_text", "output_numbers")}
        if "input" in out:
            text = json.dumps(out["input"])
            if len(text) > MAX_INPUT:
                out["input"] = {"clipped": _clip(text, MAX_INPUT)}
        return out

    def drain(self) -> list[dict]:
        """Steps changed since the last call, small enough to stream to the page."""
        with self._lock:
            ids, self._dirty = self._dirty, []
            try:
                return [self._clean(self._compact(self._steps[i])) for i in ids]
            except Exception as exc:  # noqa: BLE001
                self.data["trace_errors"].append(f"drain: {exc}"[:400])
                return []

    def head(self) -> dict:
        keys = ("id", "question", "dataset", "followup", "turn", "previous", "thread", "inherited")
        with self._lock:
            return self._clean({k: self.data.get(k) for k in keys})

    def tail(self) -> dict:
        """What the page needs once the answer is done: checks, totals, decisions."""
        keys = ("id", "done", "ended", "model", "claude_version", "stats", "checks", "figures",
                "thread", "error")
        with self._lock:
            return self._clean({k: self.data.get(k) for k in keys})

    def snapshot(self) -> dict:
        with self._lock:
            out = copy.deepcopy(self.data)
            out["steps"] = copy.deepcopy(self._order)
            for s in out["steps"]:
                s.pop("output_numbers", None)
            return self._clean(out)

    def save(self, root: Path) -> Path | None:
        def go():
            d = Path(root) / _safe(self.data["thread"])
            d.mkdir(parents=True, exist_ok=True)
            for p in (Path(root), d):
                try:
                    p.chmod(0o700)
                except OSError:
                    pass
            path = d / f"{self.id}.json"
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.snapshot()))
            tmp.chmod(0o600)
            tmp.replace(path)
            return path
        return self._guard(go)


class _Off:
    """Stands in for a Trace when tracing is switched off: every hook does nothing."""

    id = None
    data: dict = {}

    def __getattr__(self, name):
        return lambda *a, **k: [] if name == "drain" else None


OFF = _Off()


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", str(name or "none"))[:80]


def _cohorts_in(data) -> list:
    """Every cohort definition a tool handed back, wherever it sits in the result."""
    found = []

    def walk(x, depth=0):
        if depth > 6:
            return
        if isinstance(x, dict):
            for k, v in x.items():
                if k in ("cohort_def", "unchanged_cohort_def") and isinstance(v, list) and v:
                    found.append(v)
                else:
                    walk(v, depth + 1)
        elif isinstance(x, list):
            for v in x[:200]:
                walk(v, depth + 1)

    walk(data)
    return found


# --- totals -----------------------------------------------------------------------------


def _union(spans: list[tuple[float, float]]) -> float:
    total, end = 0.0, None
    for a, b in sorted(spans):
        if end is None or a > end:
            total += b - a
            end = b
        elif b > end:
            total += b - end
            end = b
    return total


def _stats(tr: Trace) -> dict:
    steps = tr._order
    span = lambda kind: [(s["t0"], s["t1"]) for s in steps if s["kind"] == kind and s["t1"] is not None]
    res = tr.data.get("result") or {}
    usage = res.get("usage") or {}
    tools = [s for s in steps if s["kind"] == "tool"]
    return {
        "total_ms": tr.data.get("ended"),
        "startup_ms": round(_union(span("startup")), 1),
        "model_ms": round(_union(span("model")), 1),
        "chiron_ms": round(_union(span("tool")), 1),
        "post_ms": round(_union(span("post")), 1),
        "retry_ms": round(_union(span("retry")), 1),
        "model_calls": sum(1 for s in steps if s["kind"] == "model"),
        "tool_calls": len(tools),
        "tool_errors": sum(1 for s in tools if s["status"] == "error"),
        "input_tokens": (usage.get("input_tokens") or 0) + (usage.get("cache_read_input_tokens") or 0)
        + (usage.get("cache_creation_input_tokens") or 0),
        "cache_read_tokens": usage.get("cache_read_input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "thinking_tokens": (usage.get("output_tokens_details") or {}).get("thinking_tokens"),
        # Claude Code's cost is cumulative over a resumed conversation; this answer's
        # share is worked out by the server from the previous trace when it has one.
        "cost_usd_cumulative": res.get("total_cost_usd"),
        "cost_usd": _share(res.get("total_cost_usd"), tr.data.get("followup"), tr._prior_cost),
        "num_turns": res.get("num_turns"),
    }


def _share(total, followup: bool, before):
    """This answer's cost: all of it for a new conversation, else the growth since the
    previous traced answer. None when that cannot be known."""
    if total is None:
        return None
    if not followup:
        return round(total, 6)
    if before is None or before > total:
        return None
    return round(total - before, 6)


def _carried_numbers(tr: Trace) -> list[str]:
    """Numbers a later follow-up may repeat: this answer's own and its counts."""
    out = _numbers_in(tr.data.get("answer") or "")
    for s in tr._order:
        if s["kind"] == "tool" and s.get("short") in ("count_cohort", "breakdown", "crosstab"):
            out |= set(s.get("output_numbers") or [])
    return sorted(out, key=float)[:3000]


def _figure_sources(tr: Trace) -> list[dict]:
    """Where each number in the answer came from: which tool result, or none."""
    answer = tr.data.get("answer") or ""
    if not answer:
        return []
    asked = _numbers_in(tr.data.get("question") or "") | _numbers_in((tr.data.get("prompt") or {}).get("text") or "")
    # When a figure appears in several results, credit the tool most likely to have given
    # it, latest call first: "841" in a values lookup and in a patient count is the
    # count's, and a cohort's size in a count and in a breakdown of it is the count's.
    rank = {"count_cohort": 0, "breakdown": 1, "crosstab": 1, "run_table": 2,
            "run_saved_report": 2, "results": 2}
    tools = sorted((s for s in tr._order if s["kind"] == "tool" and s.get("status") == "ok"),
                   key=lambda s: (rank.get(s.get("short"), 3), -s["t0"]))
    out, seen = [], set()
    for f in _figures(answer):
        n = _norm_num(f["value"])
        # The same figure in the prose, a table and a chart ("4,034" and 4034) is one.
        # Numbers under 10 are mostly names ("Type 2", "top 5") and are not checked.
        if n in seen or (f["value"] < 10 and not (f["pct"] or f["decimal"])):
            continue
        seen.add(n)
        where = next((s for s in tools if n in set(s.get("output_numbers") or [])), None)
        if where:
            status, src = "tool", where
        elif n in asked:
            status, src = "question", None
        elif n in tr._earlier:
            status, src = "earlier", None
        elif f["pct"] or f["decimal"]:
            status, src = "derived", None
        else:
            status, src = "missing", None
        item = {"text": f["text"], "value": f["value"], "status": status,
                "step": src["id"] if src else None,
                "tool": src.get("short") if src else None,
                "label": src.get("label") if src else None}
        if status == "missing":
            item["near"] = _nearest(tools, f["value"])
        out.append(item)
    return out


def _nearest(tools: list[dict], value: float) -> dict | None:
    """The patient count Chiron returned that is closest to a figure it never returned:
    "392" in the answer next to a count of 403 is the model reporting the wrong number."""
    best = None
    for s in tools:
        if s.get("short") not in ("count_cohort", "breakdown", "crosstab"):
            continue
        for n in s.get("output_numbers") or []:
            v = float(n)
            if v < 10 or v == value:
                continue
            gap = abs(v - value) / max(v, value)
            if gap <= 0.25 and (best is None or gap < best[0]):
                best = (gap, v, s)
    if not best:
        return None
    return {"value": best[1], "step": best[2]["id"], "tool": best[2]["short"], "label": best[2]["label"]}


# --- checks -----------------------------------------------------------------------------


def _check(level: str, title: str, detail: str = "", step: str | None = None) -> dict:
    return {"level": level, "title": title, "detail": detail, "step": step}


def _norm_word(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def _checks(tr: Trace) -> list[dict]:
    d, steps = tr.data, tr._order
    out: list[dict] = []
    tools = [s for s in steps if s["kind"] == "tool"]
    res = d.get("result") or {}
    post = d.get("post") or {}

    # The run itself.
    if d.get("mcp_servers") and any(s.get("status") != "connected" for s in d["mcp_servers"]):
        st = next((s for s in steps if s["kind"] == "startup"), None)
        out.append(_check("fail", "Chiron's tools did not start",
                          "The model had no way to query the data, so any figure it gave is not from "
                          "Chiron.", st and st["id"]))
    if res.get("is_error") and not any(s["kind"] == "error" for s in steps):
        out.append(_check("fail", "Claude returned an error instead of an answer",
                          str(res.get("text") or res.get("api_error_status") or "")[:400]))
    for s in steps:
        if s["kind"] == "error":
            out.append(_check("fail", s["summary"], "", s["id"]))
    if res.get("stop_reason") == "max_tokens":
        out.append(_check("warn", "The answer was cut off", "The model hit its output limit mid-answer."))
    retries = [s for s in steps if s["kind"] == "retry"]
    if retries:
        out.append(_check("warn", f"Claude's API was busy: {len(retries)} retr{'y' if len(retries) == 1 else 'ies'}",
                          "Time spent waiting is not the model or Chiron.", retries[0]["id"]))
    for den in res.get("permission_denials") or []:
        out.append(_check("warn", f"The model tried a tool it may not use: {den.get('tool_name', den)}",
                          json.dumps(den)[:300]))
    if d.get("followup") and not d.get("prior_complete"):
        out.append(_check("info", "Earlier answers in this conversation were not traced",
                          "Checks that compare with earlier answers (hand-written cohorts) are less sure."))
    for s in steps:
        if s["kind"] == "note" and s.get("status") == "warn":
            out.append(_check("warn", s["label"], s.get("summary", ""), s["id"]))

    # Tool calls.
    if not tools and d.get("answer") and any(f["status"] == "missing" for f in d.get("figures") or []):
        out.append(_check("warn", "No Chiron tool was called, yet the answer gives figures",
                          "Every figure came from the model's memory of the conversation or was "
                          "made up." if d.get("followup") else "Every figure came from the model, "
                          "not from Chiron."))
    for s in tools:
        if not s.get("chiron"):
            out.append(_check("warn", f"Called a tool that is not Chiron's: {s['tool']}", "", s["id"]))
        if s["status"] == "error":
            later_ok = any(t["tool"] == s["tool"] and t["t0"] > s["t0"] and t["status"] == "ok" for t in tools)
            out.append(_check("info" if later_ok else "warn",
                              f"{s['short']} was rejected" + (" (a later call worked)" if later_ok else ""),
                              s.get("summary", ""), s["id"]))
        if s.get("off_dataset"):
            out.append(_check("warn", f"{s['short']} queried a different dataset: {s['input'].get('dataset_id')}",
                              f"The question was about {d.get('dataset')}.", s["id"]))
        if s["t1"] is not None and s["t1"] - s["t0"] > 30_000:
            out.append(_check("info", f"{s['short']} was slow: {(s['t1'] - s['t0']) / 1000:.1f} s",
                              "Chiron's database, not the model, took this long.", s["id"]))

    # Cohorts handed to tools.
    known, flagged = set(tr._known), {}
    events = sorted([(s["t0"], 0, s) for s in tools] + [(s["t1"], 1, s) for s in tools if s["t1"] is not None],
                    key=lambda x: (x[0], x[1]))
    for _, is_end, s in events:
        if is_end:
            for cd in _cohorts_in(s.get("output")):
                known.add(_hash(cd))
            continue
        if s["tool"].replace("mcp__chiron__", "") in COHORT_TOOLS and s.get("cohort_hash") \
                and s["cohort_hash"] not in known:
            if s["cohort_hash"] in flagged:
                flagged[s["cohort_hash"]].append(s["short"])
                continue
            flagged[s["cohort_hash"]] = [s["short"]]
            out.append(_check("warn" if d.get("prior_complete") else "info",
                              f"{s['short']} was handed a cohort no Chiron tool produced",
                              "The model wrote or altered this cohort_def by hand instead of passing the one "
                              "chiron_edit_cohort returned. The prompt forbids it, because a hand-written "
                              "definition can silently mean something else.", s["id"]))
            out[-1]["_hash"] = s["cohort_hash"]
    for c in out:
        uses = flagged.get(c.pop("_hash", None) or "", [])
        if len(uses) > 1:
            c["detail"] += f" Handed to {len(uses)} calls: {', '.join(uses)}."
    for s in tools:
        for e in (s.get("input") or {}).get("cohort_def") or []:
            rule = (e or {}).get("subcol_count_restriction") if isinstance(e, dict) else None
            if rule and rule.get("type") not in RULE_TYPES:
                out.append(_check("warn", f"Count rule {rule.get('type')!r} is not one Chiron reads",
                                  "Chiron only understands 'at least', 'at most' and 'exactly'; anything else "
                                  "is run as 'exactly', with no error.", s["id"]))
        t = (s.get("input") or {}).get("transformation") or {}
        if t.get("type") == "add_criteria_set_count_rule" and t.get("rule_operator") not in RULE_TYPES:
            out.append(_check("warn", f"Count rule {t.get('rule_operator')!r} is not one Chiron reads",
                              "Chiron only understands 'at least', 'at most' and 'exactly'; anything else is "
                              "run as 'exactly', with no error.", s["id"]))
        if t.get("exclude_selected") in (True, "true", "on", 1):
            out.append(_check("warn", f"exclude_selected used on {_short(t.get('concept_id'))}",
                              "On a field with many records per patient this means 'has at least one record "
                              "that is something else', which matches almost everyone. Patients WITHOUT "
                              "something need a count rule of exactly 0.", s["id"]))

    # Fields Chiron ignored.
    ignored: dict[str, tuple[set, list]] = {}
    for s in tools:
        t = (s.get("input") or {}).get("transformation") or {}
        kind = t.get("type")
        if s["short"] != "edit_cohort" or not kind:
            continue
        if kind == "add_entry":
            extra = {k for k in t if _SET_FIELD.search(k)}
            sets = {e.get("entry_id") for e in (s.get("input") or {}).get("cohort_def") or []
                    if isinstance(e, dict) and e.get("entry_type") == "criteria_set"}
            if t.get("entry_id") and t["entry_id"] in sets:
                out.append(_check("warn", "add_entry was given a criteria set's entry_id",
                                  "In add_entry, entry_id means 'replace this entry', so the whole criteria "
                                  "set was replaced by the new filter instead of the filter joining it.", s["id"]))
        elif kind in EDIT_FIELDS:
            extra = set(t) - EDIT_FIELDS[kind] - {"type", "ignore_warnings"}
        else:
            continue
        if extra:
            keys, steps_ = ignored.setdefault(kind, (set(), []))
            keys.update(extra)
            steps_.append(s["id"])
    for kind, (keys, steps_) in ignored.items():
        detail = (f"Chiron does not read {', '.join(sorted(keys))} in {kind}, so the edit reported "
                  f"success without doing what the model meant ({len(steps_)} call{'s' if len(steps_) > 1 else ''}).")
        if kind == "add_entry":
            detail += (" A new filter always joins the FIRST criteria set for its collection, so two "
                       "different records of one collection (has A, has no B) cannot be built with "
                       "add_entry alone; Chiron's query builder moves a filter into another criteria set "
                       "with sort_cd_entries.")
        out.append(_check("warn", f"Chiron ignored fields the model sent to {kind}", detail, steps_[0]))
    edits = [s for s in tools if s["short"] == "edit_cohort"]
    if len(edits) >= 6:
        out.append(_check("info", f"{len(edits)} filter edits in one answer",
                          "The model may have struggled to express this cohort; read its reasoning "
                          "between the edits.", edits[0]["id"]))

    # Spelling variants left out.
    values: dict[str, list[str]] = {}
    for s in tools:
        if s["short"] == "concept_values" and isinstance(s.get("output"), dict):
            cid = s["output"].get("concept_id") or s["input"].get("concept_id")
            values[cid] = [v.get("category") for v in s["output"].get("values") or [] if isinstance(v, dict)]
        t = (s.get("input") or {}).get("transformation") or {}
        sel = t.get("selected_categories")
        if s["short"] == "edit_cohort" and isinstance(sel, list) and t.get("concept_id") in values:
            have = {str(x) for x in sel}
            missed = set()
            for chosen in sel:
                n = _norm_word(chosen)
                for v in values[t["concept_id"]]:
                    nv = _norm_word(v)
                    if v not in have and (nv == n or (len(n) >= 5 and abs(len(nv) - len(n)) <= 2
                                                      and (nv.startswith(n) or n.startswith(nv)))):
                        missed.add(v)
            if missed:
                out.append(_check("warn", f"Possibly missed spelling variants on {_short(t['concept_id'])}",
                                  "The filter has " + ", ".join(f'"{x}"' for x in sel[:4])
                                  + " but the values lookup also showed " + ", ".join(f'"{x}"' for x in sorted(missed)[:6])
                                  + ". Patients recorded with those spellings are not counted.", s["id"]))

    # A question about patients WITHOUT something.
    if _NEGATION.search(d.get("question") or "") and tools:
        used = ("count_cohort", "breakdown", "crosstab", "run_table", "open_in_ui", "update_results")
        counted = [s for s in tools if s["short"] in used and s["status"] == "ok"
                   and (s.get("input") or {}).get("cohort_def")]
        last = counted[-1] if counted else None
        zero_rule = any(
            isinstance(e, dict) and (e.get("subcol_count_restriction") or {}).get("value") == 0
            and (e.get("subcol_count_restriction") or {}).get("type") in ("exactly", "at most")
            for e in ((last or {}).get("input") or {}).get("cohort_def") or [])
        if last and not zero_rule:
            out.append(_check("info", "The question asks for patients without something, but the last "
                              f"cohort used ({last['short']}) has no 'exactly 0' rule",
                              "Possibly fine (the wording may not mean exclusion), but this is how a "
                              "'but not' gets lost.", last["id"]))

    # Repeated calls.
    seen: dict[str, list[dict]] = {}
    for s in tools:
        seen.setdefault(s["tool"] + json.dumps(s.get("input"), sort_keys=True), []).append(s)
    for group in seen.values():
        if len(group) > 1:
            out.append(_check("info", f"{group[0]['short']} was called {len(group)} times with the same input",
                              "Wasted time, or the model did not trust the first result.", group[1]["id"]))

    # The answer's figures.
    figs = d.get("figures") or []
    missing = [f for f in figs if f["status"] == "missing"]
    derived = [f for f in figs if f["status"] == "derived"]
    if missing:
        near = [f for f in missing if f.get("near")]
        hint = " ".join(f"{f['text']} is close to {_number(int(f['near']['value']))}, which "
                        f"{f['near']['tool']} returned." for f in near[:3])
        out.append(_check("warn", "Figures in the answer that appear in no tool result: "
                          + ", ".join(f["text"] for f in missing[:8]),
                          "The model computed these itself (a sum, a difference) or made them up. The "
                          "prompt says every figure must come from a tool result." + (" " + hint if hint else ""),
                          near[0]["near"]["step"] if near else None))
    if derived:
        out.append(_check("info", "Percentages or decimals the model worked out: "
                          + ", ".join(f["text"] for f in derived[:8]),
                          "Not in any tool result; check the arithmetic against the counts."))
    sourced = [f for f in figs if f["status"] in ("tool", "earlier")]
    if sourced and not missing:
        out.append(_check("pass", f"Every figure in the answer traces back to a Chiron result ({len(sourced)})"))

    # What the server did with the answer.
    c = post.get("cohort") or {}
    if c.get("verified") is not None and c.get("figure") is not None and c.get("verified") != c.get("figure") \
            and c.get("offered") is None:
        out.append(_check("warn", f"The answer leads with {c['figure']:,}, but the cohort behind it has "
                          f"{c['verified']:,} patients",
                          "So no Query button was offered. Either the answer reports a figure from another "
                          "cohort, or the last cohort counted is not the one the answer describes.",
                          c.get("step")))
    if c.get("verify_error"):
        out.append(_check("info", "The answer's cohort could not be re-checked", c["verify_error"], c.get("step")))
    for ch in post.get("charts") or []:
        for issue in ch.get("issues") or []:
            out.append(_check("warn" if not ch.get("ok") else "info", "Chart: " + issue))
    dropped = [f for f in post.get("followups") or [] if not f.get("shown")]
    if dropped:
        out.append(_check("info", f"{len(dropped)} suggested follow-up{'s' if len(dropped) > 1 else ''} not shown",
                          "; ".join(f"\"{f['q']}\" ({f['why']})" for f in dropped[:4])))

    order = {"fail": 0, "warn": 1, "info": 2, "pass": 3}
    return sorted(out, key=lambda c: order.get(c["level"], 9))


# --- storage ----------------------------------------------------------------------------


def find(root: Path, trace_id: str, user: str | None) -> dict | None:
    """A trace by id, for the user who asked, from a running answer or from disk."""
    if not re.fullmatch(r"[0-9a-f]{32}", trace_id or "") or not user:
        return None
    with _LIVE_GUARD:
        live = LIVE.get(trace_id)
    if live is not None:
        return live.snapshot() if live.data.get("user") == user else None
    for path in Path(root).glob(f"*/{trace_id}.json"):
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            return None
        return data if data.get("user") == user else None
    return None


def prior(root: Path, thread: str, user: str) -> list[dict]:
    """The earlier traced answers in a conversation, oldest first, in brief."""
    out = []
    for path in (Path(root) / _safe(thread)).glob("*.json"):
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if data.get("user") != user:
            continue
        out.append({"question": data.get("question"), "cohorts": data.get("cohorts") or [],
                    "numbers": data.get("numbers") or [],
                    "started": data.get("started") or 0,
                    "cost": (data.get("stats") or {}).get("cost_usd_cumulative")})
    return sorted(out, key=lambda p: p["started"])


def delete_thread(root: Path, thread: str) -> None:
    shutil.rmtree(Path(root) / _safe(thread), ignore_errors=True)


def prune(root: Path, max_age_hours: float) -> None:
    """Traces outlive nothing: drop any left behind by a conversation that never closed."""
    cutoff = time.time() - max_age_hours * 3600
    for d in Path(root).glob("*"):
        try:
            if d.is_dir() and d.stat().st_mtime < cutoff:
                shutil.rmtree(d, ignore_errors=True)
        except OSError:
            pass

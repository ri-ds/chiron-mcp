"""The answer trace (chiron_mcp/trace.py) records runs faithfully and its checks fire.

Offline: feeds synthetic Claude Code stream-json events, so it needs no Chiron, no
database and no model.

    .venv/bin/python tests/ask_trace.py

Exit code 0 means every check held.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("CHIRON_MCP_USERNAME", "tester")

from chiron_mcp import trace as T  # noqa: E402
from chiron_mcp import webapp  # noqa: E402

fails: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    print(f"{'PASS' if cond else 'FAIL'}  {label}  {str(detail)[:140]}")
    if not cond:
        fails.append(label)


DS = "demo-ds"
COND = f"{DS}__condition__description"


def assistant(mid, *blocks):
    return {"type": "assistant", "message": {"id": mid, "content": list(blocks),
                                            "usage": {"input_tokens": 5, "cache_read_input_tokens": 100}}}


def tool_use(tid, name, args):
    return {"type": "tool_use", "id": tid, "name": f"mcp__chiron__chiron_{name}", "input": args}


def result(tid, data, is_error=False):
    return {"type": "user", "message": {"content": [{
        "type": "tool_result", "tool_use_id": tid, "is_error": is_error,
        "content": [{"type": "text", "text": json.dumps(data)}]}]}}


def cset(cats, rule=None):
    e = {"entry_type": "criteria_set", "entry_id": "E1", "collection_id": "condition",
         "list": [{"entry_id": "F1", "concept_id": COND, "categories": cats, "exclude_selected": False}]}
    if rule:
        e["subcol_count_restriction"] = rule
    return [e]


def run(tr, events):
    for ev in events:
        tr.feed(ev)
        tr.raw(json.dumps(ev))


def main() -> int:
    built = cset(["Asthma"])
    by_hand = cset(["Asthma", "ASTHMA"], rule={"type": "at_least", "value": 2})
    answer = ("**845** patients have asthma or so (about 12.5%).\n\n"
              "```chart\n{\"type\":\"bar\",\"data\":[{\"x\":\"Asthma\",\"y\":845}]}\n```\n\n"
              "Contact ops@example.org, see /Users/someone/secret.txt")
    tr = T.Trace(question="How many patients have asthma but not COPD?", dataset=DS, user="alice",
                 thread="thread-1", followup=False, redact=webapp._redact)
    tr.launched(["/opt/bin/claude", "-p", "Q", "--system-prompt", "SP", "--mcp-config", "/tmp/x.json"],
                "Question: How many patients have asthma?", "SP", False)
    run(tr, [
        {"type": "system", "subtype": "init", "model": "test-model", "claude_code_version": "9.9",
         "cwd": "/Users/operator/.cache", "tools": ["mcp__chiron__chiron_count_cohort"],
         "mcp_servers": [{"name": "chiron", "status": "connected"}]},
        {"type": "system", "subtype": "status", "status": "requesting"},
        assistant("m1", {"type": "thinking", "thinking": "Look up asthma values first."},
                  tool_use("t1", "concept_values", {"dataset_id": DS, "concept_id": COND})),
        result("t1", {"concept_id": COND, "values": [
            {"category": "Asthma", "count": 800, "uniquePatientCount": 800},
            {"category": "asthma", "count": 41, "uniquePatientCount": 41},
            {"category": "Asthm", "count": 4, "uniquePatientCount": 4}]}),
        {"type": "system", "subtype": "status", "status": "requesting"},
        assistant("m2", tool_use("t2", "edit_cohort", {
            "dataset_id": DS, "cohort_def": [], "transformation": {
                "type": "add_entry", "concept_id": COND, "selected_categories": ["Asthma"],
                "exclude_selected": True}})),
        result("t2", {"successful": True, "cohort_def": built, "describe": "Subject has<br>asthma"}),
        {"type": "system", "subtype": "status", "status": "requesting"},
        # Two tools in one message, the first answering before the second is sent.
        assistant("m3", {"type": "text", "text": "Counting now."},
                  tool_use("t3", "count_cohort", {"dataset_id": DS, "cohort_def": built})),
        result("t3", {"dataset_id": DS, "subject_count": 841, "is_whole_dataset": False}),
        assistant("m3", tool_use("t4", "count_cohort", {"dataset_id": "other-ds", "cohort_def": by_hand})),
        result("t4", {"error": "No published concept"}, is_error=False),
        {"type": "system", "subtype": "api_retry", "attempt": 1, "max_retries": 10,
         "retry_delay_ms": 500, "error": "overloaded"},
        {"type": "system", "subtype": "status", "status": "requesting"},
        assistant("m4", {"type": "text", "text": answer}),
        {"type": "result", "subtype": "success", "is_error": False, "result": answer,
         "usage": {"input_tokens": 10, "output_tokens": 50, "cache_read_input_tokens": 900},
         "total_cost_usd": 0.05, "num_turns": 4, "session_id": "s-1", "stop_reason": "end_turn"},
    ])
    tr.post("charts", T.chart_audit(answer))
    tr.post("followups", webapp.followup_audit(answer + '\n```followups\n["What is their average age?"]\n```'))
    tr.post("cohort", {"offered": None, "figure": 845, "verified": 841, "step": "s7"})
    tr.answer(answer)
    tr.finish(0, "")
    snap = tr.snapshot()
    steps = snap["steps"]
    kinds = [s["kind"] for s in steps]
    models = [s for s in steps if s["kind"] == "model"]
    tools = [s for s in steps if s["kind"] == "tool"]

    check("steps are in order: request, startup, model, tool ...", kinds[:4] == ["request", "startup", "model", "tool"], kinds)
    check("every step has ended", all(s["t1"] is not None for s in steps))
    check("one model step per message, even when a tool answers mid-message", len(models) == 4, len(models))
    check("the model's reasoning is kept", models[0]["thinking"] == "Look up asthma values first.")
    check("tool calls are recorded with inputs", [t["short"] for t in tools] == ["concept_values", "edit_cohort", "count_cohort", "count_cohort"])
    check("a count's outcome reads as patients", tools[2]["summary"] == "841 patients", tools[2]["summary"])
    check("a tool's error marks the step", tools[3]["status"] == "error", tools[3]["summary"])
    check("Chiron's description is plain text", tools[1]["describe"] == "Subject has\nasthma", tools[1]["describe"])
    check("a retry becomes a step", any(s["kind"] == "retry" for s in steps))
    check("stats add up", snap["stats"]["tool_calls"] == 4 and snap["stats"]["model_calls"] == 4, snap["stats"])
    check("a new conversation's cost is all its own", snap["stats"]["cost_usd"] == 0.05)

    titles = " | ".join(c["title"] for c in snap["checks"])
    has = lambda text: any(text in c["title"] for c in snap["checks"])  # noqa: E731
    check("check: hand-written cohort", has("was handed a cohort no Chiron tool produced"), titles)
    check("check: count rule Chiron does not read", has("Count rule 'at_least'"), titles)
    check("check: exclude_selected", has("exclude_selected used"), titles)
    check("check: missed spelling variants", has("Possibly missed spelling variants"), titles)
    check("check: other dataset", has("queried a different dataset"), titles)
    check("check: figure in no tool result", has("appear in no tool result: 845"), titles)
    near = next(f for f in snap["figures"] if f["text"] == "845").get("near") or {}
    check("a missing figure points at Chiron's nearest count", near.get("value") == 841, near)
    check("check: model-made percentage", has("Percentages or decimals the model worked out: 12.5%"), titles)
    check("check: answer leads with another figure than its cohort", has("The answer leads with 845"), titles)
    check("check: chart with a single bar and no title", has("Chart: A chart with a single bar"), titles)
    check("check: hidden follow-up suggestion", has("suggested follow-up not shown"), titles)
    check("check: negation without an exactly-0 rule", has("without something"), titles)
    check("check: API retries", has("Claude's API was busy"), titles)
    check("checks are worst first", [c["level"] for c in snap["checks"]] ==
          sorted((c["level"] for c in snap["checks"]), key=["fail", "warn", "info", "pass"].index))

    text = json.dumps(snap)
    check("no operator email in the trace", "ops@example.org" not in text)
    check("no local paths in the trace", "/Users/" not in text and "/opt/bin" not in text)
    check("the command hides the prompt", snap["command"][:3] == ["claude", "-p", "<below>"], snap["command"][:3])
    live = tr.drain()
    check("drained steps carry no full outputs", all("output" not in s and "output_numbers" not in s for s in live))

    # Storage: per user, per conversation, deleted with it.
    with tempfile.TemporaryDirectory() as root:
        path = tr.save(Path(root))
        check("saved with owner-only permissions", path and oct(path.stat().st_mode)[-3:] == "600")
        check("found by its owner", (T.find(Path(root), tr.id, "alice") or {}).get("id") == tr.id)
        check("hidden from anyone else", T.find(Path(root), tr.id, "mallory") is None)
        check("a malformed id finds nothing", T.find(Path(root), "../../etc/passwd", "alice") is None)
        before = T.prior(Path(root), "thread-1", "alice")
        check("a follow-up sees the earlier answer", len(before) == 1 and before[0]["cohorts"], before)

        follow = T.Trace(question="And how many are women?", dataset=DS, user="alice", thread="thread-1",
                         followup=True, prior=before, redact=webapp._redact)
        run(follow, [
            {"type": "system", "subtype": "init", "model": "test-model", "mcp_servers": [{"name": "chiron", "status": "connected"}]},
            assistant("f1", tool_use("u1", "count_cohort", {"dataset_id": DS, "cohort_def": built})),
            result("u1", {"dataset_id": DS, "subject_count": 432}),
            assistant("f2", {"type": "text", "text": "**432** of the 841 are women."}),
            {"type": "result", "is_error": False, "result": "**432** of the 841 are women.",
             "total_cost_usd": 0.08, "usage": {}},
        ])
        follow.answer("**432** of the 841 are women.")
        follow.finish(0, "")
        fs = follow.snapshot()
        check("a follow-up is numbered", fs["turn"] == 2 and fs["previous"] == ["How many patients have asthma but not COPD?"])
        check("a cohort from an earlier answer is not hand-written",
              not any("no Chiron tool produced" in c["title"] for c in fs["checks"]), [c["title"] for c in fs["checks"]])
        check("a figure from an earlier answer is credited to it",
              any(f["text"] == "841" and f["status"] in ("earlier", "tool") for f in fs["figures"]), fs["figures"])
        check("a follow-up's cost is its own share", abs((fs["stats"]["cost_usd"] or 0) - 0.03) < 1e-9, fs["stats"]["cost_usd"])

        T.delete_thread(Path(root), "thread-1")
        check("deleting the conversation deletes its traces", T.find(Path(root), tr.id, "alice") is None)

    # Edits whose fields Chiron silently ignores.
    ig = T.Trace(question="Asthma but never COPD?", dataset=DS, user="alice", thread="t2", followup=False)
    run(ig, [
        assistant("g1", tool_use("v1", "edit_cohort", {"dataset_id": DS, "cohort_def": built, "transformation": {
            "type": "add_criteria_set", "collection_id": "condition", "concept_id": COND}})),
        result("v1", {"successful": True, "cohort_def": built}),
        assistant("g2", tool_use("v2", "edit_cohort", {"dataset_id": DS, "cohort_def": built, "transformation": {
            "type": "add_entry", "concept_id": COND, "selected_categories": ["COPD"], "parent_id": "E1"}})),
        result("v2", {"successful": True, "cohort_def": built}),
        assistant("g3", tool_use("v3", "edit_cohort", {"dataset_id": DS, "cohort_def": built, "transformation": {
            "type": "add_entry", "concept_id": COND, "selected_categories": ["COPD"], "entry_id": "E1"}})),
        result("v3", {"successful": True, "cohort_def": built}),
    ])
    ig.finish()
    titles = [c["title"] for c in ig.snapshot()["checks"]]
    check("check: fields add_criteria_set ignores", "Chiron ignored fields the model sent to add_criteria_set" in titles, titles)
    check("check: add_entry cannot pick a criteria set", "Chiron ignored fields the model sent to add_entry" in titles, titles)
    check("check: add_entry given a criteria set's id", "add_entry was given a criteria set's entry_id" in titles, titles)

    # Tracing must never break an answer.
    bad = T.Trace(question="q", dataset=DS, user="alice", thread="t", followup=False)
    bad.feed({"type": "assistant", "message": {"content": [{"type": "tool_use", "input": None, "name": 5}]}})
    bad.feed("not an event")
    bad.finish()
    check("bad events are recorded, not raised", bool(bad.snapshot()["trace_errors"]))
    check("tracing switched off does nothing", T.OFF.drain() == [] and T.OFF.feed({}) is None)

    # The follow-up audit agrees with what the page shows.
    text = 'Answer\n```followups\n["How many are women?", "Average age?", "how many are women?", "a", "b", "c"]\n```'
    _, shown = webapp.split_followups(text)
    audit = webapp.followup_audit(text)
    check("split_followups shows the audit's kept suggestions", shown == [a["q"] for a in audit if a["shown"]], shown)
    check("the audit says why one was dropped",
          {a["q"]: a["why"] for a in audit}["Average age?"] == "asks for something the tools cannot do")

    print(f"\n{len(fails)} failed" if fails else "\nall passed")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())

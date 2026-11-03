"""The call log (chiron_mcp/calllog.py): one line in the server log per model call and
per Chiron call, plus the question's arrival and the answer's summary, with no question
text, arguments or results in any of them.

Offline: synthetic Claude Code stream-json events through the trace, no Chiron, no
database, no model.

    .venv/bin/python tests/call_log.py

Exit code 0 means every check held.
"""

import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("CHIRON_MCP_USERNAME", "tester")
LOG = os.path.join(tempfile.mkdtemp(), "calls.log")
os.environ["CHIRON_MCP_CALL_LOG"] = LOG

from chiron_mcp import calllog  # noqa: E402
from chiron_mcp import trace as T  # noqa: E402

fails: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    print(f"{'PASS' if cond else 'FAIL'}  {label}  {str(detail)[:200]}")
    if not cond:
        fails.append(label)


DS = "synthea-10k"
QUESTION = "How many patients started metformin within 90 days after a type 2 diabetes diagnosis?"
INIT = {"type": "system", "subtype": "init", "model": "us.anthropic.claude-haiku-5-5",
        "claude_code_version": "2.1.283", "mcp_servers": [{"name": "chiron", "status": "connected"}]}


def assistant(mid, *blocks, usage=None, stop=None):
    msg = {"id": mid, "content": list(blocks),
           "usage": usage or {"input_tokens": 4210, "cache_read_input_tokens": 3900,
                              "cache_creation_input_tokens": 0, "output_tokens": 88}}
    if stop:
        msg["stop_reason"] = stop
    return {"type": "assistant", "message": msg}


def tool_use(tid, args, name="mcp__chiron__chiron_query"):
    return {"type": "tool_use", "id": tid, "name": name, "input": args}


def result(tid, data, is_error=False):
    body = json.dumps(data) if not isinstance(data, str) else data
    return {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": tid,
                                                     "is_error": is_error,
                                                     "content": [{"type": "text", "text": body}]}]}}


def done(text, cost=0.00421):
    return {"type": "result", "is_error": False, "result": text, "total_cost_usd": cost, "num_turns": 2,
            "usage": {"input_tokens": 12600, "cache_read_input_tokens": 11700,
                      "cache_creation_input_tokens": 0, "output_tokens": 240}}


def lines() -> list[str]:
    with open(LOG, encoding="utf-8") as fh:
        return [ln.rstrip("\n") for ln in fh if ln.strip()]


def fields(ln: str) -> dict:
    """key=value pairs of one line (quoted values unquoted)."""
    out = {}
    for m in re.finditer(r'(\w+)=("(?:[^"\\]|\\.)*"|\S+)', ln):
        k, v = m.group(1), m.group(2)
        out[k] = json.loads(v) if v.startswith('"') else v
    return out


def kinds(ls: list[str]) -> list[str]:
    return [ln.split(" ")[2] for ln in ls]


def run(events, answer="179 patients started metformin.", question=QUESTION, followup=False, **kw):
    open(LOG, "w").close()
    calllog.reset()
    tr = T.Trace(question=question, dataset=DS, user="alice", thread="t-123", followup=followup, **kw)
    for ev in events:
        tr.feed(ev)
    if answer:
        tr.answer(answer)
    tr.finish(0, "")
    return tr, lines()


# --- the plain shape of a line --------------------------------------------------------
ln = calllog.line("model", answer="a1", user="alice", dataset=DS, call=1, nothing=None, flag=True,
                  tools=["query", "query"], text="two words", cost=0.00421, exact=2.0)
check("a line is a UTC timestamp, 'ask', the kind, then key=value pairs",
      re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z ask model answer=a1 user=alice dataset=synthea-10k call=1 ", ln),
      ln)
f = fields(ln)
check("None is left out, booleans are 1/0, lists join with commas",
      "nothing" not in f and f["flag"] == "1" and f["tools"] == "query,query", f)
check("text with a space is quoted, numbers are plain",
      f["text"] == "two words" and f["cost"] == "0.00421" and f["exact"] == "2", f)

# --- one answer: a query, then the text ----------------------------------------------
tr, ls = run([
    INIT,
    assistant("m1", tool_use("c1", {"dataset_id": DS, "where": [{"medication": "metformin"}]}), stop="tool_use"),
    result("c1", {"count": 179, "group": "g1", "what_was_counted": "metformin within 90 days"}),
    assistant("m2", {"type": "text", "text": "179 patients started metformin."},
              usage={"input_tokens": 8390, "cache_read_input_tokens": 7800, "cache_creation_input_tokens": 0,
                     "output_tokens": 152}, stop="end_turn"),
    done("179 patients started metformin."),
])
check("one answer writes request, model, chiron, model, answer, in that order",
      kinds(ls) == ["request", "model", "chiron", "model", "answer"], kinds(ls))
req = fields(ls[0])
check("the request line names the answer, the conversation, the user, the dataset and the turn",
      req.get("answer") == tr.id and req.get("thread") == "t-123" and req.get("user") == "alice"
      and req.get("dataset") == DS and req.get("turn") == "1" and req.get("followup") == "0", req)
m1 = fields(ls[1])
check("a model line carries the model, the tokens, the stop reason and the tools it chose",
      m1.get("call") == "1" and m1.get("model") == "us.anthropic.claude-haiku-5-5" and m1.get("in") == "4210"
      and m1.get("cache_read") == "3900" and m1.get("out") == "88" and m1.get("stop") == "tool_use"
      and m1.get("tools") == "query" and m1.get("ms", "x").isdigit(), m1)
c1 = fields(ls[2])
check("a chiron line carries the tool, its status, the count, the group, the result size and the call it came from",
      c1.get("tool") == "query" and c1.get("status") == "ok" and c1.get("count") == "179"
      and c1.get("group") == "g1" and c1.get("call") == "1" and c1.get("size", "x").isdigit()
      and c1.get("ms", "x").isdigit(), c1)
m2 = fields(ls[3])
check("the second model call is the one that wrote the answer",
      m2.get("call") == "2" and m2.get("stop") == "end_turn" and "tools" not in m2 and m2.get("out") == "152", m2)
a = fields(ls[4])
check("the answer line sums it up: status, calls, tokens, cost, time",
      a.get("status") == "ok" and a.get("model_calls") == "2" and a.get("chiron_calls") == "1"
      and a.get("chiron_errors") == "0" and a.get("in") == "12600" and a.get("cache_read") == "11700"
      and a.get("out") == "240" and a.get("cost_usd") == "0.00421" and a.get("cost_total") == "0.00421"
      and a.get("ms", "x").isdigit() and a.get("rc") == "0", a)
check("every line of the answer carries the same answer id, conversation, user and dataset",
      all(fields(x).get("answer") == tr.id and fields(x).get("thread") == "t-123"
          and fields(x).get("user") == "alice" and fields(x).get("dataset") == DS for x in ls), ls)
whole = "\n".join(ls)
check("no question text, no tool arguments, no results reach the log",
      "metformin" not in whole and "diabetes" not in whole and "what_was_counted" not in whole
      and "where" not in whole and "179 patients" not in whole, whole)

# --- a follow-up: the turn and the cost's share ----------------------------------------
tr, ls = run([INIT, assistant("m1", {"type": "text", "text": "89 of them."}, stop="end_turn"), done("89 of them.", cost=0.00921)],
             answer="89 of them.", followup=True, prior=[{"question": "q1", "cost": 0.00421, "cohorts": [], "numbers": []}])
a = fields(ls[-1])
check("a follow-up's answer line has its turn, followup=1 and the cost of this answer alone",
      a.get("turn") == "2" and a.get("followup") == "1" and a.get("cost_usd") == "0.005" and a.get("cost_total") == "0.00921", a)

# --- a tool that failed, and one whose result never came --------------------------------
tr, ls = run([
    INIT,
    assistant("m1", tool_use("c1", {"dataset_id": DS, "where": []}), stop="tool_use"),
    result("c1", {"error": "No variable matches 'xyzzy' in this dataset."}),
    assistant("m2", tool_use("c2", {"dataset_id": DS, "where": []}), stop="tool_use"),
    done("", cost=0.001),
], answer=None)
cs = [fields(x) for x in ls if x.split(" ")[2] == "chiron"]
check("a refused call is status=error with no message on the line",
      len(cs) == 2 and cs[0].get("status") == "error" and "xyzzy" not in "\n".join(ls) and "error=" not in ls[2], cs)
check("a call whose result never came back is status=error too",
      cs[1].get("status") == "error" and cs[1].get("call") == "2", cs[1])
a = fields(ls[-1])
check("no answer text means status=incomplete, with the error count",
      a.get("status") == "incomplete" and a.get("chiron_errors") == "2" and a.get("chiron_calls") == "2", a)

# --- a retry, and an error the server reported ------------------------------------------
tr, ls = run([
    INIT,
    {"type": "system", "subtype": "api_retry", "attempt": 1, "max_retries": 10, "retry_delay_ms": 2000,
     "error": "overloaded_error"},
    assistant("m1", {"type": "text", "text": "ok"}, stop="end_turn"),
    done("ok"),
], answer="ok")
r = next((fields(x) for x in ls if x.split(" ")[2] == "retry"), None)
check("an API retry is a line of its own, with the attempt and the wait",
      r is not None and r.get("attempt") == "1" and r.get("max") == "10" and r.get("delay_ms") == "2000"
      and r.get("error") == "overloaded_error", r)
check("the answer line counts the retries", fields(ls[-1]).get("retries") == "1", ls[-1])

open(LOG, "w").close()
calllog.reset()
tr = T.Trace(question=QUESTION, dataset=DS, user="alice", thread="t-9", followup=False)
tr.feed(INIT)
tr.error("Claude Code is not logged in.")
tr.finish(1, "not logged in")
a = fields(lines()[-1])
check("a failed run is status=error with its exit code", a.get("status") == "error" and a.get("rc") == "1", a)

# --- a model call reopened by a late parallel tool block keeps one line -----------------
tr, ls = run([
    INIT,
    assistant("m1", tool_use("c1", {"dataset_id": DS, "where": []}), stop="tool_use"),
    result("c1", {"count": 10}),
    assistant("m1", tool_use("c2", {"dataset_id": DS, "where": []}), stop="tool_use"),
    result("c2", {"count": 20}),
    assistant("m2", {"type": "text", "text": "done"}, stop="end_turn"),
    done("done"),
], answer="done")
ms_ = [fields(x) for x in ls if x.split(" ")[2] == "model"]
cs = [fields(x) for x in ls if x.split(" ")[2] == "chiron"]
check("two tool blocks of one message make one model line and two chiron lines on call 1",
      [m.get("call") for m in ms_] == ["1", "2"] and [c.get("call") for c in cs] == ["1", "1"]
      and [c.get("count") for c in cs] == ["10", "20"], (ms_, cs))

# --- rerouted and restarted conversations --------------------------------------------------
open(LOG, "w").close()
calllog.reset()
tr = T.Trace(question=QUESTION, dataset=DS, user="alice", thread="t-old", followup=True,
             prior=[{"question": "q1", "cost": 0.001, "cohorts": [], "numbers": []}])
tr.restarted("t-new")
tr.rerouted("t-newer", "us.anthropic.claude-opus-5-5", "us.anthropic.claude-haiku-5-5")
ls = lines()
check("a restarted conversation and a rerouted model each leave a line naming old and new",
      kinds(ls) == ["request", "restart", "reroute"] and fields(ls[1]).get("was") == "t-old"
      and fields(ls[1]).get("thread") == "t-new" and fields(ls[2]).get("was") == "t-new"
      and fields(ls[2]).get("thread") == "t-newer" and fields(ls[2]).get("refused") == "us.anthropic.claude-opus-5-5"
      and fields(ls[2]).get("model") == "us.anthropic.claude-haiku-5-5", ls)
tr.finish(0, "")

# --- switched off ---------------------------------------------------------------------------
os.environ["CHIRON_MCP_CALL_LOG"] = "off"
calllog.reset()
open(LOG, "w").close()
tr = T.Trace(question=QUESTION, dataset=DS, user="alice", thread="t-1", followup=False)
tr.feed(INIT)
tr.feed(assistant("m1", {"type": "text", "text": "ok"}, stop="end_turn"))
tr.feed(done("ok"))
tr.answer("ok")
tr.finish(0, "")
check("CHIRON_MCP_CALL_LOG=off writes nothing, and the trace is unharmed",
      lines() == [] and tr.data["done"] and not tr.data["trace_errors"] and tr.data["stats"]["model_calls"] == 1,
      (lines(), tr.data["trace_errors"]))
os.environ["CHIRON_MCP_CALL_LOG"] = LOG
calllog.reset()

print("\nALL PASS" if not fails else f"\nFAILED: {', '.join(fails)}")
sys.exit(1 if fails else 0)

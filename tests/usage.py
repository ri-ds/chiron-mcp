"""The usage ledger (chiron_mcp/usage.py): one durable row per answer, with no question
text, written when the trace finishes, summarised for the usage page, and filled from
call-log lines for answers given before the ledger existed.

Offline: synthetic Claude Code stream-json events through the trace, no Chiron, no
database, no model.

    .venv/bin/python tests/usage.py

Exit code 0 means every check held.
"""

import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("CHIRON_MCP_USERNAME", "tester")
TMP = tempfile.mkdtemp()
LOG = os.path.join(TMP, "calls.log")
DB = os.path.join(TMP, "usage.sqlite")
os.environ["CHIRON_MCP_CALL_LOG"] = LOG
os.environ["CHIRON_MCP_USAGE_DB"] = DB

from chiron_mcp import calllog, usage  # noqa: E402
from chiron_mcp import trace as T  # noqa: E402

fails: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    print(f"{'PASS' if cond else 'FAIL'}  {label}  {str(detail)[:200]}")
    if not cond:
        fails.append(label)


DS = "synthea-10k"
INIT = {"type": "system", "subtype": "init", "model": "us.anthropic.claude-haiku-5-5",
        "claude_code_version": "2.1.283", "mcp_servers": [{"name": "chiron", "status": "connected"}]}


def assistant(mid, *blocks, usage_=None, stop=None):
    msg = {"id": mid, "content": list(blocks),
           "usage": usage_ or {"input_tokens": 4210, "cache_read_input_tokens": 3900,
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


def done(text, cost=0.00421, is_error=False):
    return {"type": "result", "is_error": is_error, "result": text, "total_cost_usd": cost, "num_turns": 2,
            "usage": {"input_tokens": 12600, "cache_read_input_tokens": 11700,
                      "cache_creation_input_tokens": 0, "output_tokens": 240}}


ONE_ANSWER = [
    INIT,
    assistant("m1", tool_use("c1", {"dataset_id": DS, "where": [{"medication": "metformin"}]}), stop="tool_use"),
    result("c1", {"count": 179, "group": "g1", "what_was_counted": "metformin within 90 days"}),
    assistant("m2", {"type": "text", "text": "179 patients started metformin."},
              usage_={"input_tokens": 8390, "cache_read_input_tokens": 7800, "cache_creation_input_tokens": 0,
                      "output_tokens": 152}, stop="end_turn"),
    done("179 patients started metformin."),
]


def run(events, answer="179 patients started metformin.", user="alice", thread="t-123",
        followup=False, rc=0, **kw):
    tr = T.Trace(question="How many started metformin?", dataset=DS, user=user, thread=thread,
                 followup=followup, access_level=kw.pop("access_level", "deid"), **kw)
    for ev in events:
        tr.feed(ev)
    if answer:
        tr.answer(answer)
    tr.finish(rc, "")
    return tr


def rows(**where) -> list[dict]:
    s = usage.summary(**where)
    return s["recent"]


# --- one answer, one row ---------------------------------------------------------------
tr = run(ONE_ANSWER)
r = rows()
check("one answer writes one row", len(r) == 1 and r[0]["id"] == tr.id, [x["id"] for x in r])
row = r[0]
check("the row says who, where, at what level, and how it ended",
      row["user"] == "alice" and row["thread"] == "t-123" and row["dataset"] == DS
      and row["access_level"] == "deid" and row["status"] == "ok" and row["turn"] == 1
      and row["followup"] == 0 and row["rc"] == 0 and row["source"] == "live", row)
check("the model, the calls and the tokens are counted",
      row["model"] == "us.anthropic.claude-haiku-5-5" and row["model_calls"] == 2 and row["chiron_calls"] == 1
      and row["chiron_errors"] == 0 and row["retries"] == 0 and row["tokens_in"] == 12600
      and row["cache_read"] == 11700 and row["tokens_out"] == 240, row)
check("the cost and the times are there",
      abs(row["cost_usd"] - 0.00421) < 1e-9 and abs(row["cost_total"] - 0.00421) < 1e-9
      and isinstance(row["ms"], int) and row["ms"] >= 0 and row["model_ms"] >= 0 and row["chiron_ms"] >= 0, row)
check("started and ended are UTC timestamps, ended not before started",
      row["started"] and row["ended"] and row["started"].endswith("Z") and row["ended"] >= row["started"],
      (row["started"], row["ended"]))
check("no question text, argument or result is in the row",
      "metformin" not in json.dumps(row).lower() and "question" not in row, row)

# --- a failed run, a follow-up's cost share, another person ----------------------------
bad = run([INIT, assistant("m1", {"type": "text", "text": "x"}, stop="end_turn"),
           done("", cost=0.001, is_error=True)], answer="", user="alice", thread="t-124", rc=1)
fu = run(ONE_ANSWER[:-1] + [done("89 are women.", cost=0.00921)], answer="89 are women.", user="alice",
         thread="t-123", followup=True, prior=[{"question": "q1", "cost": 0.00421}])
bob = run(ONE_ANSWER, user="bob", thread="t-200", access_level="agg")
r = {x["id"]: x for x in rows()}
check("four rows now, one per answer", len(r) == 4, len(r))
check("a failed run is an error row with its exit code",
      r[bad.id]["status"] == "error" and r[bad.id]["rc"] == 1, r[bad.id])
check("a follow-up's cost is its share of the conversation's total",
      abs(r[fu.id]["cost_usd"] - 0.005) < 1e-9 and abs(r[fu.id]["cost_total"] - 0.00921) < 1e-9
      and r[fu.id]["followup"] == 1 and r[fu.id]["turn"] == 2, r[fu.id])
check("another person's row carries their own level", r[bob.id]["user"] == "bob" and r[bob.id]["access_level"] == "agg")

# --- the summary the page shows ---------------------------------------------------------
s = usage.summary()
t = s["totals"]
check("totals: answers, people, cost, errors",
      t["answers"] == 4 and t["people"] == 2 and abs(t["cost_usd"] - (0.00421 * 2 + 0.001 + 0.005)) < 1e-9
      and t["errors"] == 1, t)
pu = {x["user"]: x for x in s["per_user"]}
check("per person: alice three answers with one error, bob one",
      pu["alice"]["answers"] == 3 and pu["alice"]["errors"] == 1 and pu["bob"]["answers"] == 1
      and pu["bob"]["levels"] == "agg" and DS in (pu["alice"]["datasets"] or ""), pu)
check("per model and per dataset add up",
      sum(x["answers"] for x in s["per_model"]) == 4 and s["per_dataset"][0]["dataset"] == DS
      and s["per_dataset"][0]["answers"] == 4, (s["per_model"], s["per_dataset"]))
check("per day: everything today", len(s["per_day"]) == 1 and s["per_day"][0]["answers"] == 4
      and s["per_day"][0]["day"] == usage.iso(time.time())[:10], s["per_day"])
check("recent answers come newest first", [x["id"] for x in s["recent"]][0] == bob.id, [x["id"] for x in s["recent"]])
check("a person's own view holds only their rows",
      all(x["user"] == "bob" for x in usage.summary(user="bob")["recent"]) and usage.summary(user="bob")["totals"]["answers"] == 1)
since, until = usage.period("7d", now=time.time())
check("a period gives a since bound and no until", since and since.endswith("T00:00:00Z") and until is None, (since, until))
a, b = usage.period("2026-11-01..2026-11-03")
check("a date range includes its last day", a == "2026-11-01T00:00:00Z" and b == "2026-11-04T00:00:00Z", (a, b))
check("the future holds nothing", usage.summary(since="2999-01-01T00:00:00Z")["totals"]["answers"] == 0)

# --- backfill from the call log -----------------------------------------------------------
with open(LOG, encoding="utf-8") as fh:
    log_lines = [ln.rstrip("\n") for ln in fh]
DB2 = os.path.join(TMP, "usage2.sqlite")
os.environ["CHIRON_MCP_USAGE_DB"] = DB2
usage.reset()
out = usage.backfill(["chiron-ask-ask-1  | " + ln for ln in log_lines])  # with a docker log prefix
check("the backfill writes every answer the log has", out == {"answers": 4, "written": 4, "kept": 0}, out)
r2 = {x["id"]: x for x in rows()}
live = r
check("a backfilled row matches the live one in the fields that matter",
      all(r2[i][k] == live[i][k] for i in live for k in ("user", "thread", "dataset", "access_level", "status",
                                                        "model", "model_calls", "chiron_calls", "tokens_in",
                                                        "tokens_out", "ms", "rc", "turn", "followup"))
      and all(abs(r2[i]["cost_usd"] - live[i]["cost_usd"]) < 1e-9 for i in live), r2.get(tr.id))
check("a backfilled row is marked so, with the request line's time as its start",
      r2[tr.id]["source"] == "backfill" and r2[tr.id]["started"] == live[tr.id]["started"], r2[tr.id])
out = usage.backfill(log_lines)
check("running the backfill again keeps every row", out == {"answers": 4, "written": 0, "kept": 4}, out)
check("a line that is not an answer is ignored",
      usage.parse_line("garbage") is None and usage.parse_line("2026-11-03T15:40:14.010Z ask model answer=x call=1") is None)

# --- retention, and the off switch ---------------------------------------------------
os.environ["CHIRON_MCP_USAGE_RETENTION_DAYS"] = "1"
old = time.time() - 3 * 86400
t0 = time.time()
usage.record({"answer": "c-1", "thread": "th-1", "user": "alice", "dataset": DS, "status": "ok", "cost_usd": 0.1, "cost_total": 0.1}, started=t0 - 60, ended=t0 - 59)
usage.record({"answer": "c-2", "thread": "th-1", "user": "alice", "dataset": DS, "status": "ok", "cost_usd": 0.15, "cost_total": 0.25}, started=t0 - 30, ended=t0 - 29)
check("last_total gives the conversation's running cost after its latest answer",
      usage.last_total("th-1", "alice") == 0.25 and usage.last_total("th-1", "bob") is None and usage.last_total("th-x", "alice") is None,
      (usage.last_total("th-1", "alice"), usage.last_total("th-1", "bob")))
usage.record({"answer": "old-1", "user": "alice", "dataset": DS, "status": "ok"}, started=old, ended=old)
check("rows past the retention window are pruned", usage.prune() == 1 and "old-1" not in {x["id"] for x in rows()})
del os.environ["CHIRON_MCP_USAGE_RETENTION_DAYS"]
check("no retention set, nothing pruned", usage.prune() == 0)
os.environ["CHIRON_MCP_USAGE_DB"] = "off"
usage.reset()
check("switched off, nothing is written and the summary is empty",
      usage.record({"answer": "z"}) is False and usage.summary()["totals"] == {} and usage.path() is None)

print()
print("ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}")
sys.exit(1 if fails else 0)

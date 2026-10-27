"""The trace says in words what an answer rested on: the model calls, each Chiron call and
what it handed back, what a follow-up's query built on, whether patient rows left
Chiron, and where the answer's figures came from.

Offline: synthetic Claude Code stream-json events, no Chiron, no database, no model.

    .venv/bin/python tests/trace_calls.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("CHIRON_MCP_USERNAME", "tester")

from chiron_mcp import trace as T  # noqa: E402

fails: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    print(f"{'PASS' if cond else 'FAIL'}  {label}  {str(detail)[:160]}")
    if not cond:
        fails.append(label)


DS = "synthea-10k"
INIT = {"type": "system", "subtype": "init", "model": "us.anthropic.claude-haiku-5-5",
        "mcp_servers": [{"name": "chiron", "status": "connected"}]}


def assistant(mid, *blocks):
    return {"type": "assistant", "message": {"id": mid, "content": list(blocks), "usage": {"input_tokens": 5}}}


def tool_use(tid, args):
    return {"type": "tool_use", "id": tid, "name": "mcp__chiron__chiron_query", "input": args}


def result(tid, data):
    return {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": tid, "is_error": False,
                                                     "content": [{"type": "text", "text": json.dumps(data)}]}]}}


def done(text):
    return {"type": "result", "is_error": False, "result": text, "total_cost_usd": 0.01, "usage": {}}


def run(question, events, answer, **kw):
    tr = T.Trace(question=question, dataset=DS, user="alice", thread="t1", **kw)
    for ev in events:
        tr.feed(ev)
    tr.answer(answer)
    tr.finish(0, "")
    return tr.snapshot()


def titles(snap):
    return [c["title"] for c in snap["checks"]]


# 1. A first question: one count, nothing but a number leaves Chiron.
s1 = run("How many subjects are in this dataset?", [
    INIT,
    assistant("m1", tool_use("u1", {"dataset": DS})),
    result("u1", {"count": 10000, "group": "g1", "what_was_counted": "all patients"}),
    assistant("m2", {"type": "text", "text": "**10,000** patients."}),
    done("**10,000** patients."),
], "**10,000** patients.", followup=False)
c = s1["calls"]
check("the model and where it ran are named", c["model"].endswith("haiku-5-5") and c["via"] == "Bedrock", c)
check("two model calls, one Chiron call", c["model_calls"] == 2 and len(c["tools"]) == 1, c)
check("a count is reported as a count", c["tools"][0]["returned"] == "one count" and c["rows"] == 0, c["tools"][0])
check("the checks say no rows left Chiron", any(t.startswith("Only counts and aggregates") for t in titles(s1)), titles(s1))
check("every figure came from a tool", c["figures"]["tool"] == 1 and not c["figures"]["missing"], c["figures"])

# 2. A follow-up that starts from g1: the trace names the group, its count and what was added.
s2 = run("How many of them are women?", [
    INIT,
    assistant("m1", tool_use("u1", {"dataset": DS, "start_from": "g1", "where": [{"field": "gender", "is": "female"}]})),
    result("u1", {"count": 5007, "group": "g2", "what_was_counted": "women among all patients", "started_from": "all patients"}),
    assistant("m2", {"type": "text", "text": "**5,007** are women."}),
    done("**5,007** are women."),
], "**5,007** are women.", followup=True, groups={"g1": {"count": 10000, "what": "all patients"}})
step = next(s for s in s2["steps"] if s["kind"] == "tool")
check("the step says what it built on", step["builds_on"] == {"group": "g1", "count": 10000, "what": "all patients"}, step.get("builds_on"))
check("and what it added", step["adds"] == "field gender is female", step.get("adds"))
check("the started-from fact is shown", ["Started from", "all patients"] in step["facts"], step["facts"])
check("the checks carry the lineage", "Builds on g1 (10,000 patients, all patients)" in titles(s2), titles(s2))
check("the calls summary carries it too", s2["calls"]["tools"][0]["builds_on"]["group"] == "g1" and s2["calls"]["followup"])

# 3. A group made in the same answer is known to a later query of that answer.
s3 = run("Asthma, then the women among them", [
    INIT,
    assistant("m1", tool_use("u1", {"dataset": DS, "where": [{"condition": "Asthma"}]})),
    result("u1", {"count": 841, "group": "g1", "what_was_counted": "patients with asthma"}),
    assistant("m2", tool_use("u2", {"dataset": DS, "start_from": "g1", "where": [{"field": "gender", "is": "female"}]})),
    result("u2", {"count": 445, "group": "g2", "what_was_counted": "women with asthma"}),
    assistant("m3", {"type": "text", "text": "**445** of the 841 asthma patients are women."}),
    done("**445** of the 841 asthma patients are women."),
], "**445** of the 841 asthma patients are women.", followup=False)
second = [s for s in s3["steps"] if s["kind"] == "tool"][1]
check("a group from this answer is resolved", second["builds_on"]["count"] == 841 and second["builds_on"]["what"] == "patients with asthma", second["builds_on"])
check("both figures come from tools", s3["calls"]["figures"]["tool"] == 2, s3["calls"]["figures"])

# 4. A list: the rows that came back are counted, with their columns.
s4 = run("List 3 patients with COPD who died, with county and date", [
    INIT,
    assistant("m1", tool_use("u1", {"dataset": DS, "where": [{"condition": "COPD"}], "show": {"list": ["county", "deathdate"], "limit": 3}})),
    result("u1", {"count": 120, "group": "g1", "what_was_counted": "COPD patients who died",
                  "rows": {"header": ["county", "deathdate"], "records": [["Hamilton", "2019-01-02"], ["Butler", "2020-03-04"], ["Warren", "2021-05-06"]], "row_count": 3}}),
    assistant("m2", {"type": "text", "text": "Three of the **120**: Hamilton, Butler, Warren."}),
    done("Three of the **120**: Hamilton, Butler, Warren."),
], "Three of the **120**: Hamilton, Butler, Warren.", followup=False)
t = s4["calls"]["tools"][0]
check("rows are counted with their columns", t["returned"] == "3 patient rows, 2 columns" and t["columns"] == ["county", "deathdate"], t)
check("the checks say rows came back and why", any(x.startswith("3 patient rows came back") for x in titles(s4)), titles(s4))
check("no 'no rows' claim when rows came back", not any(x.startswith("Only counts") for x in titles(s4)))

# 5. A follow-up answered without any call: said so, with the carried-over cohort.
s5 = run("Chart that", [
    INIT,
    assistant("m1", {"type": "text", "text": "```chart\n{}\n```"}),
    done("```chart\n{}\n```"),
], "```chart\n{}\n```", followup=True, inherited={"cohort_def": [{"entry_type": "criteria_set", "entry_id": "E", "collection_id": "subject", "list": []}]})
check("no new query is said in words", "No new query: answered from the earlier results" in titles(s5), titles(s5))
check("the calls summary agrees", s5["calls"]["tools"] == [] and s5["calls"]["inherited"] is True)

# 6. The tail the page gets once the answer is done carries the summary.
tr = T.Trace(question="q", dataset=DS, user="alice", thread="t9", followup=False)
tr.feed(INIT)
tr.finish(0, "")
check("the page's tail includes the calls", isinstance(tr.tail().get("calls"), dict) and "tools" in tr.tail()["calls"], tr.tail().get("calls"))

print("\nALL PASS" if not fails else f"\nFAILED: {', '.join(fails)}")
sys.exit(1 if fails else 0)

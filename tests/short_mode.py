"""Ask's short mode (the default): chiron_query first, the groups note, the buttons.

Offline: needs no Chiron database and no model.

    .venv/bin/python tests/short_mode.py

Exit code 0 means every check held.
"""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("CHIRON_MCP_USERNAME", "tester")
os.environ.pop("CHIRON_MCP_ASK_TOOLS", None)
state = tempfile.mkdtemp()
os.environ["CHIRON_MCP_STATE_DIR"] = state

from chiron_mcp import webapp  # noqa: E402

fails: list[str] = []


def check(name: str, ok: bool, detail="") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:200])
    if not ok:
        fails.append(name)


check("short tool list is the default", webapp.TOOLS == webapp.TOOLS_SHORT, str(webapp.TOOLS))
check("chiron_query comes first", webapp.TOOLS[0] == "chiron_query")
check("no low-level cohort tools", not {"chiron_edit_cohort", "chiron_count_cohort"} & set(webapp.TOOLS))
p = webapp.SYSTEM_PROMPT
check("short instructions in use", p is webapp.SYSTEM_PROMPT_SHORT)
for rule in ('op ">"', '"at_least": 3', '"never": true', "start_from", 'show={"results"', '"report:latest"',
             "never answer from another dataset", "followups", "Never write a URL"):
    check(f"instructions say {rule!r}", rule in p)
check("no internal-format rules", "cohort_def by hand" not in p and "add_criteria_set_count_rule" not in p)

# the groups note
tid = "t-1"
path = webapp._groups_file(tid)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps({"g1": {"label": "marital status is widowed", "count": 21663},
                            "g2": {"label": "marital status is widowed; death date has a value", "count": 733}}))
note = webapp._groups_note(tid)
check("groups note lists every group with its count", "g1: marital status is widowed (21,663 patients)" in note
      and "(733 patients)" in note, note)
check("groups note names the latest", "the latest is g2" in note, note)
check("no groups, no note", webapp._groups_note("none") == "")
webapp.THREADS._delete_transcript(tid)
check("groups deleted with the conversation", not path.exists())

# buttons from chiron_query's results
tr = webapp._CohortTracker()
tr.tool_use({"id": "a", "name": "mcp__chiron__chiron_query", "input": {"dataset": "Synthea 100k"}})
tr.tool_result({"tool_use_id": "a", "content": json.dumps({
    "dataset_id": "synthea-100k", "count": 5885, "cohort_def": [{"entry_type": "criteria_set", "entry_id": "x"}],
    "report": {"url": "http://chiron/report/7", "report_id": 7}})})
check("the query's cohort is the answer's cohort", (tr.final() or {}).get("dataset_id") == "synthea-100k")
check("a saved report gets its button", (tr.link or {}).get("label") == "Report", str(tr.link))
tr = webapp._CohortTracker()
tr.tool_use({"id": "b", "name": "mcp__chiron__chiron_query", "input": {}})
tr.tool_result({"tool_use_id": "b", "content": json.dumps({
    "dataset_id": "synthea-100k", "count": 10, "cohort_def": [],
    "results": {"url": "http://chiron/results"}})})
check("Results gets its button", (tr.link or {}).get("label") == "Results", str(tr.link))
check("an empty cohort is not a Query button", tr.final() is None)

# the MCP server offers only the short list when told to
from chiron_mcp import server as S  # noqa: E402

everything = S.limit_tools("")
left = S.limit_tools(",".join(webapp.TOOLS))
check("the server can offer only the short list", left == sorted(webapp.TOOLS), str(left))
check("low-level tools are not offered", "chiron_edit_cohort" in everything and "chiron_edit_cohort" not in left)
cfg = webapp._mcp_config("tester", False, thread="t-2")
env = json.loads(cfg.read_text())["mcpServers"]["chiron"]["env"]
cfg.unlink()
check("Ask's config names the short list", env.get("CHIRON_MCP_TOOLS") == ",".join(webapp.TOOLS), env.get("CHIRON_MCP_TOOLS"))

print()
print("all passed" if not fails else f"{len(fails)} failed: {fails}")
sys.exit(1 if fails else 0)

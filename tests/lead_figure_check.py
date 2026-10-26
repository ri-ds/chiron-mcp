"""An answer whose lead figure came from no tool is held back and checked once (plan P7).

Offline: a fake `claude` on PATH prints a canned stream-json, so this needs no Chiron
database and no model. It runs the real ask_stream.

    .venv/bin/python tests/lead_figure_check.py

Exit code 0 means every check held.
"""

import json
import os
import stat
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
tmp = tempfile.mkdtemp()
os.environ.update(CHIRON_MCP_USERNAME="tester", CHIRON_MCP_STATE_DIR=os.path.join(tmp, "state"),
                  CHIRON_MCP_TRACE="0", PATH=os.path.join(tmp, "bin") + os.pathsep + os.environ.get("PATH", ""))

FAKE = r'''#!/usr/bin/env python3
import json, os, sys
log = os.environ["FAKE_LOG"]
with open(log, "a") as fh:
    fh.write(("resume" if "--resume" in sys.argv else "first") + "\n")
mode = os.environ["FAKE_MODE"]
first = "--resume" not in sys.argv
def out(ev): print(json.dumps(ev), flush=True)
out({"type": "system", "subtype": "init", "model": "fake", "claude_code_version": "0"})
tool = "mcp__chiron__chiron_datasets" if mode == "nocount" else "mcp__chiron__chiron_query"
count = 0 if mode == "zero" else 100
if first:
    out({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": tool, "input": {}}]}})
    out({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1",
        "content": json.dumps({"dataset_id": "ds", "count": count, "cohort_def": [], "datasets": [{}, {}]})}]}})
    text = {"invented": "**250** patients have asthma.", "right": "**100** patients have asthma.",
            "nocount": "You can query **2** datasets.", "words": "One hundred patients have asthma.",
            "zero": "No patients have asthma."}[mode]
else:
    text = "**100** patients have asthma (checked)."
out({"type": "result", "subtype": "success", "is_error": False, "result": text})
'''
os.makedirs(os.path.join(tmp, "bin"))
fake = os.path.join(tmp, "bin", "claude")
with open(fake, "w") as fh:
    fh.write(FAKE)
os.chmod(fake, os.stat(fake).st_mode | stat.S_IEXEC)

from chiron_mcp import webapp  # noqa: E402

fails: list[str] = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:200])
    if not ok:
        fails.append(name)


def run(mode: str):
    log = os.path.join(tmp, f"{mode}.log")
    os.environ.update(FAKE_LOG=log, FAKE_MODE=mode)
    events = list(webapp.ask_stream("How many patients have asthma?", None, "tester", False, None))
    answers = [p for e, p in events if e == "answer"]
    runs = open(log).read().split()
    return answers, runs


answers, runs = run("invented")
check("an invented lead figure is not shown", all("250" not in a for a in answers), str(answers))
check("the checked answer is shown instead", answers == ["**100** patients have asthma (checked)."], str(answers))
check("the model was asked once more", runs == ["first", "resume"], str(runs))

answers, runs = run("right")
check("a figure a tool returned is shown at once", answers == ["**100** patients have asthma."], str(answers))
check("no second run", runs == ["first"], str(runs))

answers, runs = run("nocount")
check("an answer that counted nothing is not checked", answers == ["You can query **2** datasets."] and runs == ["first"],
      f"{answers} {runs}")


answers, runs = run("words")
check("an answer with the figure in words is held back and asked for digits",
      answers == ["**100** patients have asthma (checked)."] and runs == ["first", "resume"], f"{answers} {runs}")
answers, runs = run("zero")
check("a count of 0 answered in words is shown as it is", answers == ["No patients have asthma."] and runs == ["first"],
      f"{answers} {runs}")

print()
print("all passed" if not fails else f"{len(fails)} failed: {fails}")
sys.exit(1 if fails else 0)

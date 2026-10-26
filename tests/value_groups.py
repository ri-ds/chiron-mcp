"""Spelling variants are merged; a value that merely starts like another is not.

Offline: no database, no model.

    .venv/bin/python tests/value_groups.py
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
tmp = tempfile.mkdtemp()
os.environ.update(CHIRON_MCP_USERNAME="tester", CHIRON_MCP_STATE_DIR=os.path.join(tmp, "state"), CHIRON_MCP_TRACE="0")

from chiron_mcp import server as S  # noqa: E402

fails: list[str] = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:200])
    if not ok:
        fails.append(name)


def groups(counts):
    out, _ = S._groups(counts, 10 ** 6)
    return {g["label"]: (sorted(g["values"]), g["approx"]) for g in out}


g = groups({"Asthma": 8623, "asthma": 10, "ASTHMA": 8, "Asthm": 11, "Osteoarthritis": 6383, "Osteoarthriti": 6})
check("case variants and a cut-off spelling fold into the name",
      g.get("Asthma") == (["ASTHMA", "Asthm", "Asthma", "asthma"], 8652), str(g.get("Asthma")))
check("a cut-off spelling of another name folds into that one", g.get("Osteoarthritis") == (["Osteoarthriti", "Osteoarthritis"], 6389),
      str(g.get("Osteoarthritis")))

prov = {f"prov-{i}": 8500 for i in range(1, 401)}
prov.update({"prov-14": 8555, "prov-147": 8559, "prov-40": 8339, "prov-400": 8368})
g = groups(prov)
check("an id that starts like ten others stays its own value", g.get("prov-14") == (["prov-14"], 8555), str(g.get("prov-14")))
check("an id as common as the one it starts stays its own value", g.get("prov-40") == (["prov-40"], 8339), str(g.get("prov-40")))
check("nothing else was folded", len(g) == 400, str(len(g)))

g = groups({"Essential hypertension": 21195, "ESSENTIAL HYPERTENSION": 22, "Essential hypertensio": 24,
            "Essential hypertension, benign": 300})
check("a cut-off spelling with one longer name within reach still folds",
      g.get("Essential hypertension") == (["ESSENTIAL HYPERTENSION", "Essential hypertensio", "Essential hypertension"], 21241),
      str(g.get("Essential hypertension")))

g = groups({"Asthma": 5, "Asthm": 1})
check("too few to tell a cut-off from a value: left apart", set(g) == {"Asthma", "Asthm"}, str(g))

print()
print("all passed" if not fails else f"{len(fails)} failed: {fails}")
sys.exit(1 if fails else 0)

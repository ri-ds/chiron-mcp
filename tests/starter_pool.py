"""The Ask page's starter questions come from the dataset's variables with either tool list.

Offline: no database, no model. The short tool list's brief carries no concept ids, which
once left the page with two generic starters; the pool must then take the ids from the
query catalogue instead.

    .venv/bin/python tests/starter_pool.py
"""

import os
import sys
import tempfile
from types import SimpleNamespace as NS

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
tmp = tempfile.mkdtemp()
os.environ.update(CHIRON_MCP_USERNAME="tester", CHIRON_MCP_STATE_DIR=os.path.join(tmp, "state"),
                  CHIRON_MCP_TRACE="0", CHIRON_MCP_ASK_TOOLS="short")

from chiron_mcp import identity  # noqa: E402
from chiron_mcp import webapp as W  # noqa: E402

fails: list[str] = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:200])
    if not ok:
        fails.append(name)


# Stand-ins: a Synthea-shaped dataset as the catalogue would list it, and the values a
# live lookup would return for its variables.
IDS = [f"ds__{c}" for c in (
    "subject__gender", "subject__race", "subject__ethnicity", "subject__birthdate",
    "subject__deathdate", "subject__income", "subject__married",
    "condition__description", "medication__description", "encounter__encounterclass",
    "procedure__description",
)]
TOP = {
    "ds__condition__description": ["Essential hypertension", "Asthma", "Chronic obstructive "
                                   "pulmonary disease", "Type 2 diabetes mellitus"],
    "ds__medication__description": ["Metformin 500 MG Oral Tablet", "Lisinopril 10 MG Oral Tablet"],
    "ds__encounter__encounterclass": ["ambulatory", "emergency", "inpatient"],
}

identity.resolve = lambda dataset_id, **kw: NS(dataset_id=dataset_id)  # type: ignore[assignment]
W._top = lambda ident, concept_id, n: TOP.get(concept_id, [])[:n]  # type: ignore[assignment]
W.dataset_brief = lambda d, u, s: ("plain words, no ids", [])  # the short list's brief
W.usable_concept_ids = lambda d, u, s: list(IDS)

pool = W.starter_pool("ds-short", "tester", False)
questions = [p["q"] for p in pool]
features = {p["feature"] for p in pool}
check("the short tool list still gets a full pool", len(pool) > 20, f"{len(pool)} starters")
check("starters name the dataset's own conditions",
      any("hypertension" in q.lower() for q in questions) and any("COPD" in q for q in questions))
check("starters cover the features the page picks from",
      {"count", "breakdown", "ranking", "medications", "visits", "report", "filters"} <= features,
      ", ".join(sorted(features)))
check("every starter is tagged with a known feature", all(f in W.FEATURES for f in features))

# Without ids the pool is the two generic starters: the state the page was in.
bare = W.suggestion_pool("ds-bare", "tester", False, [])
check("no ids means the two generic starters only", [p["q"] for p in bare] ==
      ["How many subjects are in this dataset?", "What can I filter on?"], str([p["q"] for p in bare]))

# The full tool list's brief carries the ids itself; the catalogue is not consulted.
W.dataset_brief = lambda d, u, s: ("full brief", list(IDS))
W.usable_concept_ids = lambda d, u, s: (_ for _ in ()).throw(AssertionError("catalogue consulted"))
full = W.starter_pool("ds-full", "tester", False)
check("the full brief's ids are used as they are", len(full) == len(pool), f"{len(full)} starters")

print("\nALL PASS" if not fails else f"\nFAILED: {', '.join(fails)}")
sys.exit(1 if fails else 0)

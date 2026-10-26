"""A lab's range is kept on disk by the cohort's meaning (chiron_mcp.query._statistics): the
same question from another conversation finds it, whatever entry ids Chiron handed out; a
new load of the dataset refreshes it; and two processes asking at once run the query once.

Needs Chiron's metadata (a user with access to synthea-100k, from the usual CHIRON_MCP_*
settings); the warehouse query itself is replaced by a stub. With chiron-benchmark's:

    CHIRON_BENCH_USER=bench-toolcheck PYTHONPATH=../chiron-benchmark .venv/bin/python -c \
      "from bench import config; config.setup(); import runpy; runpy.run_path('tests/range_cache.py', run_name='__main__')"

Exit code 0 means every check held.
"""

import copy
import json
import os
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("CHIRON_MCP_USERNAME", "tester")
os.environ["CHIRON_MCP_CACHE_DIR"] = tempfile.mkdtemp(prefix="chiron-mcp-range-test-")

from chiron_mcp.bootstrap import ensure_django  # noqa: E402

ensure_django()
from chiron_mcp import identity, query as Q  # noqa: E402

fails: list[str] = []


def check(name: str, ok: bool, detail="") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:200])
    if not ok:
        fails.append(name)


# --- the key -------------------------------------------------------------------------------
cd_a = [{"entry_id": "abc123", "type": "criteria_set", "collection_id": "observation", "list": [
    {"entry_id": "def456", "concept_id": "x__observation__description", "selected_categories": ["HbA1c"]}],
    "rule_operator": "at least", "rule_count": 2}]
cd_b = copy.deepcopy(cd_a)
cd_b[0]["entry_id"], cd_b[0]["list"][0]["entry_id"] = "zzz999", "yyy888"
cd_c = copy.deepcopy(cd_a)
cd_c[0]["list"][0]["selected_categories"] = ["Glucose"]
cd_d = copy.deepcopy(cd_a)
cd_d[0]["rule_count"] = 3
check("same filters with other entry ids: same key", Q._cohort_key(cd_a) == Q._cohort_key(cd_b))
check("another value: another key", Q._cohort_key(cd_a) != Q._cohort_key(cd_c))
check("another count rule: another key", Q._cohort_key(cd_a) != Q._cohort_key(cd_d))
check("the empty cohort has a key too", len(Q._cohort_key([])) == 16)

# --- the cache, with the warehouse query stubbed ----------------------------------------------
ident = identity.resolve("synthea-100k")
cu = identity.checked_chironuser(ident)
var = Q.resolve_field(ident, "observation value")
proc = var.concept.get_cohort_def_processor(cu)

# --- a cohort group that only repeats the range's lab is left out of the query ---------------
name = Q._var(ident, "observation", "description").concept
lab = Q.parse_condition(ident, {"lab": "Systolic Blood Pressure"})
check("a plain lab clause gives the prefilter", Q._lab_prefilter(lab) == (name, "Systolic Blood Pressure"))
check("a lab with a value filter does not",
      Q._lab_prefilter(Q.parse_condition(ident, {"lab": "Systolic Blood Pressure", "op": ">", "value": 0})) is None)
check("a lab with a count rule does not",
      Q._lab_prefilter(Q.parse_condition(ident, {"lab": "Systolic Blood Pressure", "count": {"op": ">=", "value": 3}})) is None)
both = Q.build(ident, [Q.parse_condition(ident, {"condition": "asthma"}), lab], [])
kept = Q._without_lab_set(both, name, "Systolic Blood Pressure")
check("the lab-only group is dropped, the asthma group stays", [g["collection_id"] for g in kept] == ["condition"])
ruled = Q.build(ident, [Q.parse_condition(ident, {"lab": "Systolic Blood Pressure", "count": {"op": ">=", "value": 3}})], [])
check("a group with a count rule stays", Q._without_lab_set(ruled, name, "Systolic Blood Pressure") == ruled)
valued = Q.build(ident, [Q.parse_condition(ident, {"lab": "Systolic Blood Pressure", "op": ">", "value": 0})], [])
check("a group with a value filter stays", Q._without_lab_set(valued, name, "Systolic Blood Pressure") == valued)
check("another lab's group stays", Q._without_lab_set(Q.build(ident, [Q.parse_condition(ident, {"lab": "HbA1c"})], []), name, "Systolic Blood Pressure") != [])
calls = []
STATS = {"stats": {"min": 1.0, "max": 2.0, "avg": 1.5, "count_non_null": 3, "unique_patients": 2},
         "count_missing_values": 0, "count_subjects_with_missing_values": 0, "histogram_data": []}


def stub(cu_, concept, proc_, cohort, prefilter=None, aggregate=True):
    calls.append(json.dumps(cohort.cohort_def, sort_keys=True))
    time.sleep(float(os.environ.get("STUB_SLEEP", "0")))
    return copy.deepcopy(STATS)


Q._aggregate_statistics = stub
# Built twice, as two conversations would: Chiron hands out other entry ids the second time.
scope_a = Q.build(ident, [Q.parse_condition(ident, {"lab": "HbA1c"})], [])
scope_b = Q.build(ident, [Q.parse_condition(ident, {"lab": "HbA1c"})], [])
check("Chiron gave the two builds different entry ids", json.dumps(scope_a) != json.dumps(scope_b))

out1 = Q._statistics(cu, var.concept, proc, copy.deepcopy(scope_a))
check("first ask runs the query", len(calls) == 1 and out1["stats"]["max"] == 2.0)
out2 = Q._statistics(cu, var.concept, proc, copy.deepcopy(scope_b))
check("the same cohort with other entry ids is read from disk", len(calls) == 1 and out2 == out1)
files = [p for p in os.listdir(os.path.join(os.environ["CHIRON_MCP_CACHE_DIR"], "values", "synthea-100k")) if p.startswith("range__")]
check("kept under the values cache, one file", [p for p in files if p.endswith(".json")].__len__() == 1, str(files))

real_stamp = Q._etl_stamp
Q._etl_stamp = lambda dataset_id: "another-load"
out3 = Q._statistics(cu, var.concept, proc, copy.deepcopy(scope_a))
check("a new load of the dataset runs the query again", len(calls) == 2)
Q._etl_stamp = real_stamp

other = Q.build(ident, [Q.parse_condition(ident, {"lab": "FEV1/FVC"})], [])
Q._statistics(cu, var.concept, proc, other)
check("another lab runs its own query", len(calls) == 3)

# Two at once: the second waits for the first's result instead of running the query too.
calls.clear()
os.environ["STUB_SLEEP"] = "1.5"
Q._etl_stamp = lambda dataset_id: "load-x"
results = []


def ask():
    results.append(Q._statistics(cu, var.concept, proc, copy.deepcopy(scope_a)))


t1 = threading.Thread(target=ask)
t2 = threading.Thread(target=ask)
t0 = time.time()
t1.start(); time.sleep(0.2); t2.start(); t1.join(); t2.join()
took = time.time() - t0
check("two concurrent asks: the query ran once", len(calls) == 1, f"{len(calls)} runs")
check("both got the result, the second after waiting, not after a second query", len(results) == 2 and took < 2.8, f"{took:.1f}s")
Q._etl_stamp = real_stamp

print()
print("all passed" if not fails else f"{len(fails)} failed: {fails}")
sys.exit(1 if fails else 0)

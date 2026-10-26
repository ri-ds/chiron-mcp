"""Chiron MCP refuses inputs Chiron would silently ignore, and fixes count-rule spellings.

Offline: tests the pure checks in chiron_mcp/server.py (check_transformation,
normalize_count_rule, normalize_cohort_rules), so it needs no Chiron database and no
model. The same checks run inside chiron_edit_cohort and every tool that takes a
cohort_def.

    .venv/bin/python tests/strict_tools.py

Exit code 0 means every check held.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("CHIRON_MCP_USERNAME", "tester")

from chiron_mcp import server as S  # noqa: E402
from chiron_mcp.identity import AccessError  # noqa: E402

fails: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:240])
    if not ok:
        fails.append(name)


def refused(t: dict) -> str | None:
    try:
        S.check_transformation(t)
    except AccessError as exc:
        return str(exc)
    return None


# Count rules: the spellings models used, read as Chiron's own.
for alias, canon in (("at_least", "at least"), (">=", "at least"), ("AT LEAST", "at least"),
                     ("min", "at least"), ("at_most", "at most"), ("<=", "at most"),
                     ("=", "exactly"), ("exact", "exactly"), ("at least", "at least")):
    got, note = S.normalize_count_rule(alias)
    check(f"count rule {alias!r} -> {canon!r}", got == canon and (note is None) == (alias == canon), str(note))
try:
    S.normalize_count_rule("roughly")
    check("unknown count rule refused", False)
except AccessError as exc:
    check("unknown count rule refused", "at least" in str(exc), str(exc))

t, notes = S.check_transformation({"type": "add_criteria_set_count_rule", "entry_id": "x",
                                   "rule_operator": "at_least", "rule_count": "3"})
check("count-rule transformation corrected", t["rule_operator"] == "at least" and t["rule_count"] == 3 and notes,
      str(notes))
check("negative rule_count refused", "negative" in (refused({"type": "add_criteria_set_count_rule", "entry_id": "x",
                                                              "rule_operator": "at least", "rule_count": -1}) or ""))

# A hand-written cohort_def with "at_least" is corrected before anything runs.
cd = [{"entry_type": "criteria_set", "entry_id": "a", "collection_id": "encounter", "list": [],
       "subcol_count_restriction": {"type": "at_least", "value": 3}}]
fixed, notes = S.normalize_cohort_rules(cd)
check("cohort_def count rule corrected", fixed[0]["subcol_count_restriction"]["type"] == "at least" and notes)
check("caller's cohort_def left unchanged", cd[0]["subcol_count_restriction"]["type"] == "at_least")
check("valid rules untouched", S.normalize_cohort_rules(fixed)[1] == [])

# Fields Chiron ignores are refused, with the way to do it instead.
for field in ("criteria_set_id", "parent_id", "set_id", "criteria_set", "target_entry_id", "parent_entry_id"):
    msg = refused({"type": "add_entry", "concept_id": "c", "selected_categories": ["x"], field: "abc"})
    check(f"add_entry with {field!r} refused, explains groups", bool(msg) and "sort_cd_entries" in msg, msg or "")
msg = refused({"type": "add_entry", "concept_id": "c", "min_count": 3})
check("min_count refused, explains count rules", bool(msg) and "add_criteria_set_count_rule" in msg, msg or "")
msg = refused({"type": "add_entry", "concept_id": "c", "min": 6.5})
check("'min' refused, names cd_numeric_min", bool(msg) and "cd_numeric_min" in msg, msg or "")
check("missing collection_id refused", "collection_id" in (refused({"type": "add_criteria_set"}) or ""))
check("missing concept_id refused", "concept_id" in (refused({"type": "add_entry", "selected_categories": ["x"]}) or ""))

# Filters Chiron does not have.
for qt in ("has_value", "is_not_missing", "not_null"):
    msg = refused({"type": "add_entry", "concept_id": "deathdate", "query_type": qt})
    check(f"query_type {qt!r} refused with the date-range way", bool(msg) and "date_range" in msg, msg or "")

# What models do right still passes untouched.
for t in ({"type": "add_entry", "concept_id": "c", "selected_categories": ["Asthma", "ASTHMA"]},
          {"type": "add_entry", "concept_id": "c", "cd_numeric_min": 6.5, "include_null_and_missing": False},
          {"type": "add_entry", "concept_id": "d", "query_type": "date_range", "cd_numeric_min": "01/01/1800"},
          {"type": "add_criteria_set", "collection_id": "observation"},
          {"type": "sort_cd_entries", "entry_id": "s", "child_ids": ["a", "b"]},
          {"type": "modify_event_rule", "entry_id": "s", "option_type": "date_range", "date_min": 2010},
          {"type": "clear_all"}):
    check(f"accepted: {t['type']} {sorted(set(t) - {'type'})}", refused(t) is None)

print()
print("all passed" if not fails else f"{len(fails)} failed: {fails}")
sys.exit(1 if fails else 0)

"""chiron_mcp.chiron_patches: the two run-time fixes land on a Chiron that lacks them and
leave one that has them alone.

Against the Chiron this checkout runs with (the vendored copy by default, which has both
fixes in its source), apply() must change nothing. Then, on stand-ins shaped like Chiron
6.5.4 before the fixes, each fix must be applied and must behave: a fresh dict per cohort
entry, and the relative-date rule reading a multivalue date through the lookup alias.

    .venv/bin/python tests/chiron_patches.py

Exit code 0 means every check held.
"""

from __future__ import annotations

import inspect
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("CHIRON_MCP_USERNAME", "tester")

from chiron_mcp.bootstrap import ensure_django  # noqa: E402

ensure_django()

from chiron.processors.abstract.cohort_def_processor import CohortDefProcessor  # noqa: E402
from chiron.query_engine.postgres.sql_alchemy_queries.longitudinal_combos import (  # noqa: E402
    LongitudinalCombo,
)
from chiron.query_engine.postgres.sql_alchemy_queries.sections.where_builder import (  # noqa: E402
    WhereStatementBuilder,
)
from chiron_mcp import chiron_patches  # noqa: E402

fails: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    print(f"{'PASS' if cond else 'FAIL'}  {label}  {detail[:160]}")
    if not cond:
        fails.append(label)


# --- a Chiron that has the fixes: nothing happens -------------------------------------

before = (CohortDefProcessor._generate_cd_entry_template,
          LongitudinalCombo.generate_sql_alchemy_clauses_for_event,
          WhereStatementBuilder.get_clauses_for_longitudinal_combo)
applied = chiron_patches.apply(verbose=False)
after = (CohortDefProcessor._generate_cd_entry_template,
         LongitudinalCombo.generate_sql_alchemy_clauses_for_event,
         WhereStatementBuilder.get_clauses_for_longitudinal_combo)
has_fixes = (hasattr(WhereStatementBuilder, "get_event_date_column")
             and inspect.signature(before[0]).parameters["additional_args"].default is None)
check("a fixed Chiron is left alone", (applied == []) == has_fixes and (before == after) == has_fixes,
      f"applied={applied} source_has_fixes={has_fixes}")

# --- stand-ins shaped like Chiron 6.5.4 before the fixes ------------------------------

import chiron.processors.abstract.cohort_def_processor as cdp_mod  # noqa: E402
import chiron.query_engine.postgres.sql_alchemy_queries.longitudinal_combos as lc_mod  # noqa: E402
import chiron.query_engine.postgres.sql_alchemy_queries.sections.where_builder as wb_mod  # noqa: E402


class OldProcessor:
    """The 6.5.4 method: the default argument is returned, so it is shared."""

    def __init__(self):
        self.concept = type("C", (), {"permanent_id": "cid"})()
        self.prefilter_value = None

    def _generate_cd_entry_template(self, additional_args={}):  # noqa: B006
        response = additional_args
        response["entry_id"] = "e"
        response["concept_id"] = self.concept.permanent_id
        return response


class OldCombo:
    def __init__(self, combo):
        self.combo = combo

    def generate_sql_alchemy_clauses_for_event(self, table0, table1):
        raise AssertionError("the old method reads the date off the collection table")


class OldWhereBuilder:
    def __init__(self):
        self.calls = []

    def get_clauses_for_longitudinal_combo(self, combo, subquery_type, subquery_id0,
                                           subquery_id1, table0=None, table1=None):
        # 6.5.4 calls the combo with no resolver
        return combo.generate_sql_alchemy_clauses_for_event(table0, table1)


saved = (cdp_mod.CohortDefProcessor, lc_mod.LongitudinalCombo, wb_mod.WhereStatementBuilder)
cdp_mod.CohortDefProcessor, lc_mod.LongitudinalCombo, wb_mod.WhereStatementBuilder = (
    OldProcessor, OldCombo, OldWhereBuilder)
try:
    applied = chiron_patches.apply(verbose=False)
    check("both fixes applied to an unfixed Chiron", len(applied) == 2, "; ".join(applied))

    p = OldProcessor()
    a, b = p._generate_cd_entry_template(), p._generate_cd_entry_template()
    check("a fresh cohort entry per filter",
          a is not b and a["concept_id"] == b["concept_id"] == "cid" and "entry_id" in a)
    given = {"terms": ["x"]}
    c = p._generate_cd_entry_template(given)
    check("the caller's arguments are copied, not kept", c is not given and c["terms"] == ["x"]
          and "entry_id" not in given)

    import sqlalchemy as sa

    md = sa.MetaData()
    t_cond = sa.Table("condition", md, sa.Column("_id", sa.Integer), sa.Column("_subject_id", sa.Integer))
    t_med = sa.Table("medication", md, sa.Column("_id", sa.Integer), sa.Column("_subject_id", sa.Integer))
    lk_cond = sa.Table("lkp_condition_start", md, sa.Column("_collection_id", sa.Integer),
                       sa.Column("condition__start", sa.Date))
    lk_med = sa.Table("lkp_medication_start", md, sa.Column("_collection_id", sa.Integer),
                      sa.Column("medication__start", sa.Date))

    class Concept:
        def __init__(self, pid, multivalue, table):
            self.permanent_id, self.multivalue, self.table = pid, multivalue, table

    class Coll:
        def __init__(self, date):
            self.event_date_field = self.event_end_date_field = date

    class AliasManager:
        def __init__(self):
            self.aliases = {}

        def get_concept_alias(self, subquery_type, subquery_id, oConcept):
            return self.aliases.setdefault((subquery_id, oConcept.permanent_id), oConcept.table.alias())

    class QueryInfo:
        @staticmethod
        def get_sql_alchemy_table_for_concept(oConcept):
            return oConcept.table

    med_start = Concept("medication__start", True, lk_med)
    cond_start = Concept("condition__start", True, lk_cond)
    combo = OldCombo([
        {"collection": Coll(med_start), "entry_id": "m",
         "event_rule": {"range_start_days_from_target": 0, "range_end_days_from_target": 90,
                        "reference_date": "start", "range_start_target": "start",
                        "range_end_target": "start"}},
        {"collection": Coll(cond_start), "entry_id": "c"},
    ])
    wb = OldWhereBuilder()
    wb.alias_manager, wb.query_info = AliasManager(), QueryInfo()

    # Both sides in subqueries: the dates come from the lookup aliases.
    clauses = wb.get_clauses_for_longitudinal_combo(combo, "sub", "s0", "s1", t_med, t_cond)
    sql = " AND ".join(str(c.compile(compile_kwargs={"literal_binds": True})) for c in clauses)
    check("two subqueries: dates read through the lookup aliases",
          "lkp_medication_start" in sql and "lkp_condition_start" in sql
          and "medication.medication__start" not in sql and ">= 0" in sql and "<= 90" in sql, sql)
    check("the resolver is not left on the combo", not hasattr(combo, chiron_patches._ATTR))

    # One side without a subquery of its own: a correlated lookup of that record's value.
    clauses = wb.get_clauses_for_longitudinal_combo(combo, "sub", None, "s1", t_med, t_cond)
    sql = " AND ".join(str(c.compile(compile_kwargs={"literal_binds": True})) for c in clauses)
    check("outer table: a correlated lookup of its date",
          "SELECT" in sql and "_collection_id = medication._id" in sql and "LIMIT 1" in sql, sql)

    # A single-value date is still read off the collection table.
    t_visit = sa.Table("visit", md, sa.Column("_id", sa.Integer), sa.Column("visit__date", sa.Date))
    single = Concept("visit__date", False, t_visit)
    combo2 = OldCombo([
        {"collection": Coll(single), "entry_id": "v",
         "event_rule": {"range_start_days_from_target": -30, "range_end_days_from_target": 0,
                        "reference_date": "start", "range_start_target": "start",
                        "range_end_target": "start"}},
        {"collection": Coll(single), "entry_id": "w"},
    ])
    clauses = wb.get_clauses_for_longitudinal_combo(combo2, "sub", "s0", "s1", t_visit, t_visit.alias("v2"))
    sql = " AND ".join(str(c.compile(compile_kwargs={"literal_binds": True})) for c in clauses)
    check("single-value dates come off the collection table",
          "visit.visit__date - v2.visit__date >= -30" in sql and "lkp_" not in sql, sql)

    # Applying again changes nothing more.
    check("idempotent", chiron_patches.apply(verbose=False) == [])
finally:
    cdp_mod.CohortDefProcessor, lc_mod.LongitudinalCombo, wb_mod.WhereStatementBuilder = saved

print(f"\n{'ALL PASS' if not fails else str(len(fails)) + ' FAILED: ' + ', '.join(fails)}")
sys.exit(1 if fails else 0)

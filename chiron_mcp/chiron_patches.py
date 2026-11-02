"""Two fixes the host's Chiron needs for Ask, applied in this process when it lacks them.

chiron-mcp runs against whichever Chiron it is pointed at (``CHIRON_MCP_CHIRON_SRC``), and
a deployment's own Chiron will not carry these fixes until they are merged upstream. So
right after Django starts (``chiron_mcp.bootstrap``) this module looks at the host's code
and, only where the fix is missing, replaces the method in memory. Nothing on disk is
written, and Chiron's own web app, which runs in its own process, is not affected: a
deployment that wants the relative-date rule fixed in its query builder too needs the
upstream change. The vendored copy under ``vendor/is4r-chiron`` has both fixes in its
source, so nothing is applied there.

1. ``CohortDefProcessor._generate_cd_entry_template`` (Chiron 6.5.4) has a mutable default
   argument, ``additional_args={}``, and returns it after writing into it, so every filter
   entry built without arguments in one process is the *same* dict: building a second
   filter silently rewrites the first (README, "A Chiron bug this project found").
   ``chiron_edit_cohort`` deep-copies around it already; the fix makes every caller safe.
   Detected by the default's type.

2. The relative-date rule between two event collections ("within 90 days after") read each
   event date straight off the collection table
   (``LongitudinalCombo.generate_sql_alchemy_clauses_for_event``), which is where a
   single-value concept lives. A dataset loaded with every concept multivalue, as the
   Synthea bundles are, keeps its dates in lookup tables, and the rule then failed with
   ``AttributeError: <date concept>``. The fix resolves a multivalue date through the
   subquery's lookup alias (joined like the filters' lookups) or, for a table with no
   subquery of its own, a correlated lookup of that record's value. Detected by whether
   the where builder has ``get_event_date_column``. The where builder's own method is
   wrapped, not replaced, so a host whose method body differs a little still gets the
   resolver.
"""

from __future__ import annotations

import inspect
import sys

_ATTR = "_chiron_mcp_column_for"  # the resolver the where builder lends a combo


def apply(verbose: bool = True) -> list[str]:
    """Apply whichever fixes the host Chiron lacks. Returns what was applied."""
    applied = []
    for fix in (_fix_entry_template, _fix_event_dates):
        try:
            name = fix()
        except ImportError:
            # A Chiron without this part (another query engine, an older layout): nothing
            # to fix, and nothing Ask could use there anyway.
            name = None
        if name:
            applied.append(name)
    if verbose:
        for name in applied:
            print(f"chiron-mcp: the host Chiron lacks a fix Ask needs; applied in this "
                  f"process only: {name}", file=sys.stderr)
    return applied


# --- 1. a fresh cohort entry per filter ---------------------------------------------


def _fix_entry_template() -> str | None:
    from chiron.processors.abstract.cohort_def_processor import CohortDefProcessor

    current = CohortDefProcessor._generate_cd_entry_template
    param = inspect.signature(current).parameters.get("additional_args")
    if param is None or not isinstance(param.default, dict):
        return None  # fixed in the source (additional_args=None), or shaped differently

    from chiron import helpers

    def _generate_cd_entry_template(self, additional_args=None):
        # A fresh dict every call (the original returned the default argument itself).
        response = dict(additional_args or {})
        response["entry_id"] = helpers.generate_entry_id()
        response["concept_id"] = self.concept.permanent_id
        if self.prefilter_value:
            response["prefilter_value"] = self.prefilter_value
        return response

    _generate_cd_entry_template.__doc__ = current.__doc__
    CohortDefProcessor._generate_cd_entry_template = _generate_cd_entry_template
    return "a fresh cohort entry per filter (CohortDefProcessor._generate_cd_entry_template)"


# --- 2. event dates kept in lookup tables --------------------------------------------


def _fix_event_dates() -> str | None:
    from chiron.query_engine.postgres.sql_alchemy_queries.longitudinal_combos import (
        LongitudinalCombo,
    )
    from chiron.query_engine.postgres.sql_alchemy_queries.sections.where_builder import (
        WhereStatementBuilder,
    )

    if hasattr(WhereStatementBuilder, "get_event_date_column"):
        return None  # fixed in the source

    combo_sig = inspect.signature(LongitudinalCombo.generate_sql_alchemy_clauses_for_event)
    if "column_for" not in combo_sig.parameters:
        LongitudinalCombo.generate_sql_alchemy_clauses_for_event = _clauses_for_event
    WhereStatementBuilder.get_event_date_column = get_event_date_column
    original = WhereStatementBuilder.get_clauses_for_longitudinal_combo

    def get_clauses_for_longitudinal_combo(self, combo, subquery_type, subquery_id0,
                                           subquery_id1, table0=None, table1=None):
        subquery_ids = (subquery_id0, subquery_id1)

        def column_for(index, table, oConcept):
            return self.get_event_date_column(oConcept, table, subquery_type, subquery_ids[index])

        # The host's method calls combo.generate_sql_alchemy_clauses_for_event(table0,
        # table1) with no resolver; lend the combo one for the duration of the call.
        setattr(combo, _ATTR, column_for)
        try:
            return original(self, combo, subquery_type, subquery_id0, subquery_id1,
                            table0, table1)
        finally:
            try:
                delattr(combo, _ATTR)
            except AttributeError:
                pass

    get_clauses_for_longitudinal_combo.__doc__ = original.__doc__
    WhereStatementBuilder.get_clauses_for_longitudinal_combo = get_clauses_for_longitudinal_combo
    return ("the relative-date rule with event dates kept in lookup tables "
            "(WhereStatementBuilder.get_event_date_column)")


def _clauses_for_event(self, table0, table1, column_for=None):
    """LongitudinalCombo.generate_sql_alchemy_clauses_for_event, with a column resolver.

    :param table0: the sqlalchemy table or alias for the first related collection
    :param table1: the sqlalchemy table or alias for the second related collection
    :param column_for: optional, column_for(index, table, oConcept) returning the column
      holding that event date concept for the table of combo index 0 or 1. The default
      reads it off the collection table, which is where a single-value concept lives; a
      multivalue date concept lives in a lookup table, and the where builder passes a
      resolver that joins it.
    """
    column_for = column_for or getattr(self, _ATTR, None)
    if column_for is None:

        def column_for(index, table, oConcept):
            return getattr(table.c, oConcept.permanent_id)

    clauses = []
    rule = self.combo[0]["event_rule"]
    range_start_days_from_target = rule["range_start_days_from_target"]
    range_end_days_from_target = rule["range_end_days_from_target"]
    reference_date = rule["reference_date"]
    range_start_target = rule["range_start_target"]
    range_end_target = rule["range_end_target"]
    collection0 = self.combo[0]["collection"]
    collection1 = self.combo[1]["collection"]
    date_concept0 = collection0.event_date_field
    if reference_date == "end":
        date_concept0 = collection0.event_end_date_field
    date_concept1_range_start = collection1.event_date_field
    date_concept1_range_end = collection1.event_date_field
    if range_start_target == "end":
        date_concept1_range_start = collection1.event_end_date_field
    if range_end_target == "end":
        date_concept1_range_end = collection1.event_end_date_field
    date_column0 = column_for(0, table0, date_concept0)
    date_column1_range_start = column_for(1, table1, date_concept1_range_start)
    date_column1_range_end = column_for(1, table1, date_concept1_range_end)
    clauses.append(date_column0 - date_column1_range_start >= range_start_days_from_target)
    clauses.append(date_column0 - date_column1_range_end <= range_end_days_from_target)
    return clauses


def get_event_date_column(self, oConcept, table, subquery_type, subquery_id):
    """The column holding an event date concept for `table` (a collection table or alias).

    A single-value concept is a column of the collection table. A multivalue concept
    lives in its lookup table: inside a subquery that is the lookup alias registered for
    the subquery, which the caller joins like the aliases of the filters (get_aliases
    "lookup"); for a table with no subquery of its own (the outer table of a one-sided
    combo), a correlated lookup of that record's value.
    """
    from sqlalchemy import select

    if not oConcept.multivalue:
        return getattr(table.c, oConcept.permanent_id)
    if subquery_id is not None:
        alias = self.alias_manager.get_concept_alias(subquery_type, subquery_id, oConcept)
        return getattr(alias.c, oConcept.permanent_id)
    lookup = self.query_info.get_sql_alchemy_table_for_concept(oConcept).alias()
    return (
        select(getattr(lookup.c, oConcept.permanent_id))
        .where(lookup.c._collection_id == table.c._id)
        .limit(1)
        .scalar_subquery()
    )

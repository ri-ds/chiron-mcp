"""Chiron MCP server.

Runs in-process against Chiron rather than over its REST API, because
`QueryToolsViewSet._get_cohort_def` (chiron/api/viewsets/query_tools.py:204-214)
discards any caller-supplied cohort_def and returns the caller's active server-side
snapshot instead.  An HTTP wrapper would therefore have to mutate a researcher's
live workspace on every turn -- and `CohortDefSnapshot.save` deletes their redo
stack (chiron/models/user_models.py:189-193).

The design is stateless by choice: every tool takes a cohort_def and returns one,
so the model holds the working query and Chiron holds none.  No tool in this server
writes a snapshot.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from chiron_mcp.bootstrap import ensure_django

ensure_django()

from mcp.server.mcpserver import MCPServer  # noqa: E402

from chiron_mcp import filters, identity  # noqa: E402
from chiron_mcp.config import CONFIG  # noqa: E402
from chiron_mcp.identity import AccessError  # noqa: E402

mcp = MCPServer("chiron")


# --- helpers -----------------------------------------------------------------


def _err(exc: Exception) -> dict:
    return {"error": str(exc)}


def _concept(ident, concept_id: str):
    from chiron import models

    oConcept = models.Concept.objects.filter(
        permanent_id=concept_id, collection__dataset=ident.dataset, published=True
    ).first()
    if not oConcept:
        raise AccessError(
            f"No published concept {concept_id!r} in dataset {ident.dataset_id!r}."
        )
    return oConcept


def _validated_cohort(ident, cohort_def: list):
    """Build a Cohort and refuse to proceed if it has errors.

    This guard is load-bearing: `clean_cohort_def` replaces an errored definition
    with an EMPTY list (chiron/query_definition/cohort_def_functions.py:72-75), and
    an empty cohort_def matches EVERY subject.  Running an errored definition would
    therefore silently return the whole dataset instead of failing.
    """
    from chiron import query_definition as qdef

    try:
        cohort = qdef.Cohort(identity.checked_chironuser(ident), cohort_def or [])
    except Exception as exc:  # noqa: BLE001
        raise AccessError(
            f"Malformed cohort_def ({type(exc).__name__}: {exc}). Build it with "
            "chiron_edit_cohort rather than by hand -- entries carry required keys such as "
            "entry_type, entry_id and collection_id."
        ) from exc
    if cohort.errors:
        raise AccessError(
            "Cohort definition has errors, refusing to run it (an errored definition is "
            "reduced to an empty one, which would match every subject in the dataset). "
            f"Errors: {cohort.errors}"
        )
    return cohort


def _table_def_from_columns(ident, cohort_def: list, columns: list[dict]) -> dict:
    """Turn a plain column list into a real table_def via Chiron's own transformations."""
    from chiron.api.utils import table_def as td_utils

    cu = identity.checked_chironuser(ident)
    table_def: dict = {}
    for col in columns:
        transformation = {
            "type": "add_entry",
            "concept_id": col["concept_id"],
            "aggregate": col.get("aggregate", False),
            "aggregation_method": col.get("aggregation_method"),
        }
        if col.get("alias"):
            transformation["alias"] = col["alias"]
        result = td_utils.transformation_function_lookup["add_entry"](
            cu, table_def, transformation
        )
        if not result.get("transformation_successful"):
            raise AccessError(
                f"Could not add column {col['concept_id']!r}: "
                f"{result.get('transformation_errors')}"
            )
        table_def = result["table_def"]
    return table_def


def _header_from(table) -> list[str]:
    """Build the header the way Chiron does, skipping errored fields.

    Mirrors chiron/api/utils/export.py:152-159.  Fields flagged has_errors are
    omitted from the header AND from the rows, so a naive header would be wider
    than the data.
    """
    names = []
    for entry in table.extended_table_def.get("fields", []):
        if not entry.get("has_errors", False):
            names.append(entry.get("alias") or entry["label"])
    return names


# --- orientation -------------------------------------------------------------


@mcp.tool()
def chiron_datasets(dataset_id: str | None = None) -> dict:
    """List the Chiron datasets this identity can actually use, or describe one.

    Datasets the bound identity has no ChironUser on are reported as refused rather
    than silently provisioned. Start here.
    """
    from chiron import models

    try:
        out = []
        for oDataset in models.Dataset.objects.all().order_by("unique_id"):
            if dataset_id and oDataset.unique_id != dataset_id:
                continue
            row: dict[str, Any] = {
                "dataset_id": oDataset.unique_id,
                "name": oDataset.display_name,
                "description": oDataset.description,
            }
            try:
                ident = identity.resolve(oDataset.unique_id)
            except AccessError as exc:
                row["accessible"] = False
                row["reason"] = str(exc)
                out.append(row)
                continue
            row.update(
                accessible=True,
                access_level=ident.access_level,
                raw_access_level=ident.chironuser.access_level,
                can_view_workspace=ident.can_view_workspace,
                can_view_subject_details=ident.can_view_subject_details,
                subject_level_data=ident.access_level in ("phi", "deid"),
            )
            out.append(row)
        if dataset_id and not out:
            return _err(AccessError(f"No dataset {dataset_id!r}."))
        return {"identity": CONFIG.username, "access_ceiling": CONFIG.max_access_level,
                "datasets": out}
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@mcp.tool()
def chiron_find_concepts(
    dataset_id: str,
    search: str | None = None,
    collection: str | None = None,
    limit: int = 50,
) -> dict:
    """Find concepts (queryable variables) in a dataset.

    `search` matches the concept's name and description. Only concepts this identity
    is permitted to use in a cohort definition are returned.
    """
    from django.db.models import Q

    from chiron import models

    try:
        ident = identity.resolve(dataset_id)
        identity.require_workspace(ident)
        cu = identity.checked_chironuser(ident)

        qs = models.Concept.objects.filter(
            collection__dataset=ident.dataset, published=True
        ).select_related("collection")
        if collection:
            qs = qs.filter(collection__permanent_id=collection)
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))

        out = []
        for oConcept in qs.order_by("collection__permanent_id", "name"):
            can_use, reason = oConcept.user_can_use_concept_in_cohort_def(cu)
            if not can_use:
                continue
            out.append(
                {
                    "concept_id": oConcept.permanent_id,
                    "name": oConcept.name,
                    "collection": oConcept.collection.permanent_id,
                    "description": oConcept.description,
                    "has_phi": oConcept.has_phi,
                    "multivalue": oConcept.multivalue,
                }
            )
            if len(out) >= limit:
                break
        return {
            "dataset_id": dataset_id,
            "count": len(out),
            "concepts": out,
            "note": (
                "multivalue concepts live in their own lookup table joined one-to-many, so a "
                "filter matches a subject if ANY of their values match."
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@mcp.tool()
def chiron_describe_concept(
    dataset_id: str,
    concept_id: str,
    cohort_def: list | None = None,
    prefilter_value: str | None = None,
    include_statistics: bool = True,
) -> dict:
    """Describe one concept, including THE EXACT FIELD NAMES needed to filter on it.

    Chiron publishes no machine-readable schema for filter inputs, so the `filter_input`
    block here is the authoritative answer to "what arguments does chiron_edit_cohort
    take for this concept?". Call this before building any filter.
    """
    try:
        ident = identity.resolve(dataset_id)
        identity.require_workspace(ident)
        cu = identity.checked_chironuser(ident)
        oConcept = _concept(ident, concept_id)

        can_use, reason = oConcept.user_can_use_concept_in_cohort_def(cu)
        processor = oConcept.get_cohort_def_processor(cu, prefilter_value)
        if processor is None:
            raise AccessError(
                f"No cohort_def processor available for {concept_id!r} as this identity: {reason}"
            )

        out: dict[str, Any] = {
            "concept_id": oConcept.permanent_id,
            "name": oConcept.name,
            "description": oConcept.description,
            "collection": oConcept.collection.permanent_id,
            "has_phi": oConcept.has_phi,
            "multivalue": oConcept.multivalue,
            "can_use_in_cohort_def": can_use,
            "reason": reason,
            "filter_input": filters.describe(processor),
        }

        if include_statistics:
            identity.require_subject_level(ident)
            try:
                out["statistics"] = processor.get_statistics(cohort_def or [])
            except Exception as exc:  # noqa: BLE001
                out["statistics_error"] = str(exc)
        return out
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@mcp.tool()
def chiron_concept_values(
    dataset_id: str,
    concept_id: str,
    cohort_def: list | None = None,
    limit: int = 100,
) -> dict:
    """List the distinct values of a concept with subject counts.

    The direct answer to "what can I filter this field on?".
    """
    from chiron.query_engine import get_stattool

    try:
        ident = identity.resolve(dataset_id)
        identity.require_workspace(ident)
        # StatTool performs NO permission check of its own -- verified by grep across
        # stattool.py and abstract_stattool.py -- so the gate has to happen here.
        identity.require_subject_level(ident)
        cu = identity.checked_chironuser(ident)
        oConcept = _concept(ident, concept_id)

        can_use, reason = oConcept.user_can_use_concept_in_cohort_def(cu)
        if not can_use:
            raise AccessError(f"Not permitted to use {concept_id!r}: {reason}")

        stats = get_stattool(chironuser=cu, cohort_def=cohort_def or [], concept=oConcept)
        values = stats.get_unique_values_with_counts(sort_by="count")
        if limit:
            values = values[:limit]
        return {"concept_id": concept_id, "values": values}
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


# --- cohort building ---------------------------------------------------------


@mcp.tool()
def chiron_edit_cohort(
    dataset_id: str,
    cohort_def: list,
    transformation: dict,
) -> dict:
    """Apply one transformation to a cohort definition and return the new one.

    Purely functional: nothing is saved, and the caller's Chiron workspace is untouched.
    Pass the cohort_def you are holding (use [] to start).

    `transformation` must carry a "type". Common types: add_entry, delete_entry,
    add_criteria_set, change_to_boolean_or, change_to_boolean_and, clear_all,
    create_event_rule, modify_event_rule, delete_event_rule.

    For "add_entry" also pass "concept_id" plus that concept's filter fields --
    get them from chiron_describe_concept's `filter_input`. Field names are HTML form
    names such as cd_numeric_min / selected_categories / chiron_text_field_selection,
    NOT cohort_def keys.
    """
    from chiron.api.utils import cohort_def as cd_utils
    from chiron.query_definition import cohort_def_functions as cdfuncs

    try:
        ident = identity.resolve(dataset_id)
        identity.require_workspace(ident)
        identity.require_subject_level(ident)
        cu = identity.checked_chironuser(ident)

        ttype = transformation.get("type")
        lookup = cd_utils.transformation_function_lookup
        if ttype not in lookup:
            raise AccessError(
                f"Unknown transformation type {ttype!r}. Available: {sorted(lookup)}"
            )

        result = lookup[ttype](cu, cohort_def or [], transformation)
        successful = result.get("transformation_successful", False)

        if not successful:
            # Deliberately do NOT return a `cohort_def` key on failure. Chiron hands back
            # the unchanged definition, and an unchanged (often empty) definition matches
            # EVERY subject -- so a caller that chained it would silently query the whole
            # dataset instead of seeing an error.
            out = {
                "successful": False,
                "unchanged_cohort_def": result.get("cohort_def", cohort_def or []),
                "errors": result.get("transformation_errors"),
                "warnings": result.get("transformation_warnings"),
            }
            out["hint"] = (
                "If this failed with 'Entry X not found' on a text or ontology filter, the "
                "term is absent from this dataset. Pass ignore_warnings=true in the "
                "transformation to accept it anyway. If it said 'Please select at least "
                "one value', you used the wrong field name -- call chiron_describe_concept "
                "and use the exact names in its filter_input block. DO NOT reuse "
                "unchanged_cohort_def as if the filter had applied."
            )
            return out

        out = {"successful": True, "cohort_def": result.get("cohort_def", cohort_def or [])}
        if result.get("entry_id"):
            out["entry_id"] = result["entry_id"]
        try:
            cd_info = cdfuncs.clean_cohort_def(out["cohort_def"], cu, include_metadata=True)
            out["describe"] = cdfuncs.describe_cohort_def(cd_info["extended_cohort_def"])
            out["validation_errors"] = cd_info["errors"]
            out["validation_warnings"] = cd_info["warnings"]
        except Exception as exc:  # noqa: BLE001
            out["describe_error"] = str(exc)
        return out
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@mcp.tool()
def chiron_event_rule_options(dataset_id: str, cohort_def: list, entry_id: str) -> dict:
    """List the event-rule (date/age restriction) options available for one criteria set.

    Event rules are how you say "diagnosed between 2015 and 2020" or "before age 5".
    Which options apply depends on the collection's date concepts, so ask here rather
    than guessing, then pass the option_id as `type` plus its fields to
    chiron_edit_cohort with transformation type create_event_rule.

    `entry_id` is the criteria-set entry_id returned by chiron_edit_cohort.
    """
    from chiron.query_definition.event_options import EventOptionCollection

    try:
        ident = identity.resolve(dataset_id)
        identity.require_workspace(ident)
        identity.require_subject_level(ident)
        cu = identity.checked_chironuser(ident)

        collection = EventOptionCollection(cu, cohort_def or [], entry_id)
        options = []
        for opt in collection.options:
            options.append(
                {
                    "option_id": opt.get_unique_name(),
                    "title": opt.get_option_title(),
                    "fields": list(getattr(opt, "fields", None) or []),
                }
            )
        return {
            "entry_id": entry_id,
            "options": options,
            "usage": (
                "Two steps. 1) create a blank rule: transformation={'type': "
                "'create_event_rule', 'entry_id': <entry_id>}. 2) set it: "
                "transformation={'type': 'modify_event_rule', 'entry_id': <entry_id>, "
                "'option_type': <option_id>, ...that option's fields}. Note the key is "
                "option_type, and date_min/date_max take YEARS for the date_range option."
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@mcp.tool()
def chiron_count_cohort(dataset_id: str, cohort_def: list) -> dict:
    """Count the distinct subjects matching a cohort definition.

    The cheapest way to check a cohort is the right size before pulling rows.
    Refuses to run a definition that has errors.
    """
    from chiron.query_engine import get_querytool

    try:
        ident = identity.resolve(dataset_id)
        identity.require_workspace(ident)
        identity.require_subject_level(ident)
        cu = identity.checked_chironuser(ident)
        cohort = _validated_cohort(ident, cohort_def)
        count = get_querytool(cu, cohort.cohort_def).get_cohort_count()
        return {
            "dataset_id": dataset_id,
            "subject_count": int(count),
            "warnings": cohort.warnings,
            "is_whole_dataset": not cohort.cohort_def,
        }
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


# --- running -----------------------------------------------------------------


@mcp.tool()
def chiron_run_table(
    dataset_id: str,
    cohort_def: list,
    columns: list[dict],
    page: int = 1,
    records_per_page: int = 10,
) -> dict:
    """Run a cohort and return one page of rows.

    `columns` is a list of {concept_id, aggregate?, aggregation_method?, alias?} --
    you never author table_def JSON. Use chiron_count_cohort first to check size.
    """
    from chiron import query_definition as qdef
    from chiron.api.utils.export import get_paginated_preview

    try:
        ident = identity.resolve(dataset_id)
        identity.require_workspace(ident)
        identity.require_subject_level(ident)
        cu = identity.checked_chironuser(ident)
        cohort = _validated_cohort(ident, cohort_def)

        table_def = _table_def_from_columns(ident, cohort.cohort_def, columns)
        response = get_paginated_preview(
            cohort.cohort_def,
            table_def,
            cu,
            {"page": page, "records_per_page": records_per_page, "output_type": "json"},
        )
        if response.get("preview_failed"):
            return {"error": "Preview failed.", "errors": response.get("errors")}

        table = qdef.Table(cu, cohort.cohort_def, table_def)
        return {
            "header": _header_from(table),
            "records": response.get("data"),
            "record_count": response.get("record_count"),
            "subject_count": response.get("subject_count"),
            "paginator": response.get("paginator"),
            "warnings": response.get("warnings"),
            "table_def": table_def,
        }
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@mcp.tool()
def chiron_export_table(
    dataset_id: str,
    cohort_def: list,
    columns: list[dict],
    acknowledged_record_count: int,
) -> dict:
    """Return the COMPLETE unpaginated result set for a cohort.

    Chiron applies no LIMIT anywhere in this path, so you must first call
    chiron_run_table (or chiron_count_cohort) and pass the record count you saw as
    `acknowledged_record_count`. Output is capped at CHIRON_MCP_MAX_EXPORT_ROWS and
    flagged `truncated` if the cap is hit.
    """
    from chiron.api.utils.export import generate_cohort_json

    try:
        ident = identity.resolve(dataset_id)
        identity.require_workspace(ident)
        identity.require_subject_level(ident)
        cu = identity.checked_chironuser(ident)
        cohort = _validated_cohort(ident, cohort_def)

        if acknowledged_record_count <= 0:
            raise AccessError(
                "Pass acknowledged_record_count from a prior chiron_run_table or "
                "chiron_count_cohort call. This export is otherwise unbounded."
            )

        table_def = _table_def_from_columns(ident, cohort.cohort_def, columns)
        result = generate_cohort_json(cohort.cohort_def, table_def, cu, "json")
        records = result.get("records") or []
        truncated = False
        if isinstance(records, list) and len(records) > CONFIG.max_export_rows:
            records = records[: CONFIG.max_export_rows]
            truncated = True
        return {
            "header": result.get("header"),
            "records": records,
            "row_count": len(records) if isinstance(records, list) else None,
            "truncated": truncated,
            "cap": CONFIG.max_export_rows,
        }
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@mcp.tool()
def chiron_crosstab(
    dataset_id: str,
    cohort_def: list,
    rows: list[str],
    cols: list[str],
) -> dict:
    """Cross-tabulate a cohort: subject counts broken down by row and column concepts.

    The aggregate-safe path -- this is the only analysis surface Chiron applies
    small-count masking to, so it is available to aggregate-level identities.
    """
    from chiron.api.utils import analysis_def as ad_utils
    from chiron.query_definition import Analysis
    from chiron.query_engine import get_querytool

    try:
        ident = identity.resolve(dataset_id)
        identity.require_workspace(ident)
        identity.require_analysis_view()
        cu = identity.checked_chironuser(ident)

        # run_analysis reads dataset.root_collection.event_id_field
        # (chiron/query_engine/abstract_querytool.py:155) and dereferences it without a
        # null check, so an unconfigured root collection would surface as AttributeError.
        root = ident.dataset.root_collection
        if root is None or root.event_id_field is None:
            raise AccessError(
                f"Dataset {dataset_id!r} cannot be cross-tabulated: its root collection "
                f"({getattr(root, 'permanent_id', 'unset')!r}) has no event_id_field "
                "configured in the data dictionary, which Chiron's analysis view requires. "
                "Use chiron_concept_values for single-variable counts instead."
            )

        cohort = _validated_cohort(ident, cohort_def)

        # Build through Chiron's own transformation so entries get the entry_id the
        # rest of the analysis pipeline requires (chiron/api/utils/analysis_def.py:26).
        analysis_def: dict = {}
        add = ad_utils.transformation_function_lookup["add_entry"]
        for role, concept_ids in (("rows", rows), ("cols", cols)):
            for concept_id in concept_ids:
                result = add(cu, analysis_def, {
                    "type": "add_entry", "concept_id": concept_id, "role": role,
                })
                if not result.get("transformation_successful"):
                    raise AccessError(
                        f"Could not add {concept_id!r} to {role}: "
                        f"{result.get('transformation_errors')}"
                    )
                analysis_def = result["analysis_def"]
        analysis = Analysis(cu, analysis_def)
        result = get_querytool(cu, cohort.cohort_def).run_analysis(analysis)
        return {
            "dataset_id": dataset_id,
            "analysis_def": analysis_def,
            "result": result,
            "note": (
                "For aggregate-level identities Chiron masks small counts by replacing any "
                "cell whose string value is 1-5 (CHIRON_AGG_SUBJECT_COUNT_MIN_LIMIT)."
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


# --- saved reports -----------------------------------------------------------


@mcp.tool()
def chiron_saved_reports(
    dataset_id: str, report_id: int | None = None, search: str | None = None
) -> dict:
    """List saved reports, or fetch one report's stored cohort_def and table_def.

    The best cold-start move: an existing report shows how colleagues express a
    question in this dataset, and can be branched from.
    """
    try:
        ident = identity.resolve(dataset_id)
        cu = identity.checked_chironuser(ident)
        qs = cu.get_viewable_reports()

        if report_id is not None:
            oReport = qs.filter(pk=report_id).first()
            if not oReport:
                raise AccessError(f"No viewable report {report_id} on {dataset_id!r}.")
            definition = oReport.get_def_value()
            return {
                "report_id": oReport.pk,
                "name": oReport.name,
                "description": oReport.description,
                "public": oReport.public,
                "cohort_def": definition.get("cohort_def"),
                "table_def": definition.get("table_def"),
            }

        out = []
        for oReport in qs.order_by("-id"):
            if search and search.lower() not in (oReport.name or "").lower():
                continue
            out.append(
                {
                    "report_id": oReport.pk,
                    "name": oReport.name,
                    "description": oReport.description,
                    "public": oReport.public,
                }
            )
        return {"dataset_id": dataset_id, "count": len(out), "reports": out}
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@mcp.tool()
def chiron_run_saved_report(
    dataset_id: str, report_id: int, page: int = 1, records_per_page: int = 10
) -> dict:
    """Run a saved report by id, using its own stored definitions."""
    from chiron import query_definition as qdef
    from chiron.api.utils.export import get_paginated_preview

    try:
        ident = identity.resolve(dataset_id)
        identity.require_workspace(ident)
        identity.require_subject_level(ident)
        cu = identity.checked_chironuser(ident)

        # Scope to reports this identity may actually view. Chiron's own
        # report_tools endpoints omit UserCreatedContentPermission and fetch by pk
        # alone (chiron/api_v2/viewsets/report_tools.py:28); that hole is not copied here.
        oReport = cu.get_viewable_reports().filter(pk=report_id).first()
        if not oReport:
            raise AccessError(f"No viewable report {report_id} on {dataset_id!r}.")

        definition = oReport.get_def_value()
        cohort_def = definition.get("cohort_def") or []
        table_def = definition.get("table_def") or {}
        cohort = _validated_cohort(ident, cohort_def)

        response = get_paginated_preview(
            cohort.cohort_def,
            table_def,
            cu,
            {"page": page, "records_per_page": records_per_page, "output_type": "json"},
        )
        if response.get("preview_failed"):
            return {"error": "Preview failed.", "errors": response.get("errors")}
        table = qdef.Table(cu, cohort.cohort_def, table_def)
        return {
            "report_id": oReport.pk,
            "name": oReport.name,
            "header": _header_from(table),
            "records": response.get("data"),
            "record_count": response.get("record_count"),
            "subject_count": response.get("subject_count"),
            "paginator": response.get("paginator"),
        }
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


# --- operations group --------------------------------------------------------


@mcp.tool()
def chiron_validate_dictionary(dataset_id: str) -> dict:
    """OPERATIONS. Run Chiron's own data-dictionary validator.

    This is the exact check chiron_run_etl gates on, so a non-empty result means the
    next ETL will refuse to run without --ignore-validation-errors.
    """
    from chiron.data_dictionary.validate import validate_data_dictionary

    try:
        identity.require_operator()
        ident = identity.resolve(dataset_id)
        errors = validate_data_dictionary(ident.dataset)
        return {
            "dataset_id": dataset_id,
            "errors": errors,
            "caveats": [
                "validate_collection_event_concepts is effectively dead code: it filters "
                "permanent_id__startswith='_', so its loop body is unreachable for normally "
                "named collections.",
                "No rule checks identifier length, though long permanent_ids become longer "
                "lkp_ table names.",
            ],
        }
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@mcp.tool()
def chiron_schema_diagram(dataset_id: str, include_related: bool = False) -> dict:
    """OPERATIONS. Render the dataset's shape as a Mermaid erDiagram."""
    from chiron.data_dictionary.visualize_schema import VisSchema

    try:
        identity.require_operator()
        ident = identity.resolve(dataset_id)
        vis = VisSchema(ident.dataset)
        for oCollection in ident.dataset.subcollections():
            vis.add_subcollection(oCollection.permanent_id, include_related=include_related)
        vis.add_all_missing_subrelationships()
        return {"dataset_id": dataset_id, "mermaid": vis.get_mermaid_diagram()}
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@mcp.tool()
def chiron_etl_history(dataset_id: str | None = None, limit: int = 20) -> dict:
    """OPERATIONS. The ETL audit trail, which has no HTTP API at all."""
    from chiron import models

    try:
        identity.require_operator()
        qs = models.EtlLog.objects.all()
        if dataset_id:
            ident = identity.resolve(dataset_id)
            # EtlLog.dataset is a SlugField (log_models.py:15), not a ForeignKey.
            qs = qs.filter(dataset=ident.dataset.unique_id)
        out = []
        for oLog in qs.order_by("-id")[:limit]:
            out.append(
                {
                    "log_id": oLog.pk,
                    "dataset": oLog.dataset,
                    "status": oLog.status,
                    "start_date": str(oLog.start_date) if oLog.start_date else None,
                    "end_date": str(oLog.end_date) if oLog.end_date else None,
                    "comment": oLog.comment,
                    "duration": str(oLog.get_duration()) if oLog.get_duration() else None,
                    "sources_loaded": oLog.count_sources_loaded(),
                }
            )
        return {
            "runs": out,
            "note": (
                "A run stuck at 'ETL started' with a null end_date never completed its "
                "bookkeeping, even if the data is queryable."
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@mcp.tool()
def chiron_explain_access(dataset_id: str, concept_id: str) -> dict:
    """OPERATIONS. Why can or cannot the bound identity use this concept?

    Returns Chiron's own (bool, reason) verdicts verbatim.
    """
    try:
        identity.require_operator()
        ident = identity.resolve(dataset_id)
        cu = identity.checked_chironuser(ident)
        oConcept = _concept(ident, concept_id)
        stats_ok, stats_reason = oConcept.user_can_view_concept_stats(cu)
        cd_ok, cd_reason = oConcept.user_can_use_concept_in_cohort_def(cu)
        td_ok, td_reason = oConcept.user_can_use_concept_in_table_def(cu)
        return {
            "concept_id": concept_id,
            "chironuser_id": cu.pk,
            "access_level": ident.access_level,
            "has_phi": oConcept.has_phi,
            "exclude_from_aggregated": oConcept.exclude_from_aggregated,
            "view_stats": {"allowed": stats_ok, "reason": stats_reason},
            "use_in_cohort_def": {"allowed": cd_ok, "reason": cd_reason},
            "use_in_table_def": {"allowed": td_ok, "reason": td_reason},
            "note": (
                "user_can_view_concept_stats ALLOWS agg users for non-PHI concepts; the agg "
                "block at the API is the DRF class SubjectLevelAccess, mirrored in "
                "chiron_mcp.identity.require_subject_level."
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


def main() -> None:
    CONFIG.validate()
    # Fail fast on a bad identity rather than at the first tool call.
    try:
        identity._django_user()
    except AccessError as exc:
        print(f"chiron-mcp: {exc}", file=sys.stderr)
        raise SystemExit(1)
    print(
        f"chiron-mcp: bound to {CONFIG.username!r}, ceiling={CONFIG.max_access_level}, "
        f"operator={CONFIG.operator}, save={CONFIG.allow_save}",
        file=sys.stderr,
    )
    mcp.run()


if __name__ == "__main__":
    main()

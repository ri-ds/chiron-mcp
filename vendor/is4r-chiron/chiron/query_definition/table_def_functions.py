from chiron import helpers
from chiron.models import CohortDefSnapshot, Concept, DefaultTableDefConcept, TableDefSnapshot
from chiron.query_definition.cohort_def_functions import (
    get_all_criteria_set_options_for_collection_id,
)


def set_active_table_def(request, table_def):
    oSnapshot = TableDefSnapshot(chironuser=request.chironuser)
    oSnapshot.set_table_def(table_def)
    oSnapshot.save()
    return oSnapshot


def get_active_table_def(request):
    table_def = TableDefSnapshot.get_active_table_def(request.chironuser)
    return table_def


def get_default_field_list(chironuser):
    """
    Fetch default concepts for a table and build a list of table_def entries efficiently.
    """
    # Query all defaults in one go
    defaults = DefaultTableDefConcept.objects.filter(dataset=chironuser.dataset).select_related(
        "concept"
    )

    # Build fields list directly without repeatedly calling add_table_def_entry
    fields = []
    for oDefault in defaults:
        oConcept = oDefault.concept
        display_processor = oConcept.get_display_processor(chironuser)
        td_entry = display_processor.generate_table_def_entry()
        fields.append(td_entry)

    return fields


def clean_active_table_def(chironuser, include_metadata=False):
    """
    Wrapper for clean_table_def()
    """
    cohort_def = CohortDefSnapshot.get_active_cohort_def(chironuser)
    table_def = TableDefSnapshot.get_active_table_def(chironuser)
    return clean_table_def(cohort_def, table_def, chironuser, include_metadata)


def clean_table_def(cohort_def, table_def, chironuser, include_metadata=False):
    """
    Cleans table_def and sort_def, merging results efficiently.
    """
    sort_def = table_def.get("sort", [])

    if include_metadata:
        td_validated = _clean_table_def(cohort_def, table_def, chironuser, include_metadata)
        sd_validated = _clean_sort_def(
            td_validated["table_def"], sort_def, chironuser, include_metadata
        )

        # Use shallow copies instead of deepcopy (fields are already validated)
        merged_table_def = {**td_validated["table_def"], "sort": sd_validated["sort_def"]}
        merged_extended_table_def = {
            **td_validated["extended_table_def"],
            "sort": sd_validated["extended_sort_def"],
        }

        return {
            "table_def": merged_table_def,
            "extended_table_def": merged_extended_table_def,
            "warnings": td_validated["warnings"] + sd_validated["warnings"],
            "errors": td_validated["errors"] + sd_validated["errors"],
        }

    # Non-metadata mode: single pass
    table_def = _clean_table_def(cohort_def, table_def, chironuser)
    table_def["sort"] = _clean_sort_def(table_def, sort_def, chironuser)


def _clean_table_def(cohort_def, table_def, chironuser, include_metadata=False):
    """
    Validate and clean table_def, removing broken links and adding metadata.
    Uses bulk DB query for Concept objects to minimize queries.
    """
    warnings, errors = [], []
    validated_fields, extended_fields = [], []

    # Ensure table_def is a dict and has fields
    if not isinstance(table_def, dict):
        table_def = {}
    if not table_def.get("fields"):
        table_def["fields"] = get_default_field_list(chironuser)

    fields = table_def.get("fields", [])
    concept_ids = {f.get("concept_id") for f in fields if f.get("concept_id")}

    # Bulk fetch concepts
    concepts = Concept.objects.filter(permanent_id__in=concept_ids)
    concept_lookup = {c.permanent_id: c for c in concepts}

    # Process each field
    for td_entry in fields:
        concept_id = td_entry.get("concept_id")
        oConcept = concept_lookup.get(concept_id)

        if oConcept:
            can_use, reason = oConcept.user_can_use_concept_in_table_def(chironuser, td_entry)
            has_errors = not can_use
            if has_errors:
                warnings.append(f"{oConcept.name}: {reason}")
            else:
                validated_fields.append(td_entry)

            extended_fields.append(
                _create_extended_table_def_entry(
                    td_entry, oConcept, cohort_def, chironuser, has_errors=has_errors
                )
            )
        else:
            # Concept not found
            warnings.append(f'The concept "{concept_id}" was not found in the database.')
            extended_fields.append(
                {
                    "entry_id": td_entry.get("entry_id"),
                    "concept_id": concept_id,
                    "categories": [],
                    "label": concept_id,
                    "has_errors": True,
                    "can_delete": True,
                    "can_sort": True,
                    "aggregate": td_entry.get("aggregate", False),
                }
            )

    # Build validated and extended table_def (shallow copy)
    validated_table_def = {**table_def, "fields": validated_fields}
    extended_table_def = {**validated_table_def, "fields": extended_fields}
    extended_table_def.setdefault("table_type", "subject")

    if include_metadata:
        return {
            "table_def": validated_table_def,
            "extended_table_def": extended_table_def,
            "warnings": warnings,
            "errors": errors,
        }
    return validated_table_def


def _create_extended_table_def_entry(td_entry, oConcept, cohort_def, chironuser, has_errors=False):
    # Build categories using list comprehension
    categories = [cat.name for cat in oConcept.get_category_hierarchy()]

    # Prepare display processor
    display_processor = oConcept.get_display_processor(chironuser)
    if display_processor:
        display_processor.set_td_entry(td_entry)

    # Cache collection object
    collection = oConcept.collection
    collection_info = {
        "collection_id": collection.permanent_id,
        "event_date_field": getattr(collection.event_date_field, "permanent_id", None),
        "event_end_date_field": getattr(collection.event_end_date_field, "permanent_id", None),
    }

    # Handle aggregation criteria set name lookup
    agg_criteria_set = td_entry.get("aggregation_criteria_set")
    aggregation_criteria_set_name = None
    if agg_criteria_set:
        criteria_set_name_lookup = get_all_criteria_set_options_for_collection_id(
            cohort_def, chironuser, collection.permanent_id
        )
        aggregation_criteria_set_name = criteria_set_name_lookup.get(
            agg_criteria_set, agg_criteria_set
        )

    # Determine label
    label = (
        display_processor.get_header_display_value(aggregation_criteria_set_name)
        if display_processor
        else oConcept.name
    )

    # Build response dictionary
    response = {
        "entry_id": td_entry["entry_id"],
        "concept_id": oConcept.permanent_id,
        "concept_name": oConcept.name,
        "collection": collection_info,
        "categories": categories,
        "label": label,
        "can_delete": True,
        "can_sort": has_errors,
        "has_errors": has_errors,
        "aggregate": td_entry.get("aggregate", False),
        "alias": td_entry.get("alias"),
        "categorize": td_entry.get("categorize", False),
    }

    # Add aggregation details if applicable
    if response["aggregate"]:
        response.update(
            {
                "aggregation_method": td_entry.get("aggregation_method", "count"),
                "aggregation_settings": td_entry.get("aggregation_settings", {}),
                "aggregation_criteria_set": agg_criteria_set,
                "aggregation_criteria_set_name": aggregation_criteria_set_name,
            }
        )

    return response


def get_table_def_concept_ids(table_def):
    """
    Returns a list of unique concept_ids associated with a table def.
    """
    return list({entry.get("concept_id") for entry in table_def.get("fields", [])})


def get_relevant_concepts_for_table_def(table_def):
    concept_ids = get_table_def_concept_ids(table_def)
    concepts = Concept.objects.filter(permanent_id__in=concept_ids)
    return concepts


def get_table_def_entry(table_def, entry_id):
    for entry in table_def["fields"]:
        if entry["entry_id"] == entry_id:
            return entry
    return None


def add_table_def_entry(table_def, td_entry, existing_entry_id=None, position="append"):
    fields = table_def.get("fields", [])

    if existing_entry_id:
        for i, item in enumerate(fields):
            if item.get("entry_id") == existing_entry_id:
                fields[i] = td_entry
                return table_def

    if position == "append":
        fields.append(td_entry)
    else:
        fields.insert(0, td_entry)

    table_def["fields"] = fields
    return table_def


def duplicate_table_def_entry(table_def, entry_id):
    # Shallow copy of table_def
    new_table_def = {**table_def}
    new_fields = []

    for entry in table_def.get("fields", []):
        new_fields.append(entry)
        if entry.get("entry_id") == entry_id:
            dup_entry = entry.copy()  # shallow copy is enough unless nested structures exist
            dup_entry["entry_id"] = helpers.generate_entry_id()
            new_fields.append(dup_entry)

    new_table_def["fields"] = new_fields
    return new_table_def


def delete_table_def_entry(table_def, entry_id):
    # Shallow copy for top-level keys
    new_table_def = dict(table_def)
    # Filter fields using list comprehension
    new_table_def["fields"] = [
        entry for entry in table_def.get("fields", []) if entry.get("entry_id") != entry_id
    ]
    return new_table_def


def resort_table_def(table_def, entry_ids):
    # Build a lookup dict for O(1) access
    field_lookup = {entry["entry_id"]: entry for entry in table_def.get("fields", [])}

    # Reorder fields based on entry_ids
    new_fields = [field_lookup[entry_id] for entry_id in entry_ids if entry_id in field_lookup]

    # Create a shallow copy of table_def and update fields
    new_table_def = {**table_def, "fields": new_fields}
    return new_table_def


def add_sort_def_entry(table_def, entry_id):
    """
    Add or update a Sort Def entry by Entry ID.
    If the entry exists at the top, reverse its direction.
    Otherwise, insert it at the top with default direction.
    Remove any other occurrences of the same entry_id.
    Return the first 3 entries.

    :param sort_def: Soft def to add an entry to
    :type sort_def: list
    :param entry_id: Entry ID to add to Sort Def
    :type entry_id: str
    :return: Resulting Sort Def
    :rtype: list
    """
    sort_def = table_def.get("sort", [])

    # If first entry matches, reverse direction
    if sort_def and sort_def[0].get("entry_id") == entry_id:
        sort_def[0]["direction"] *= -1
    else:
        sort_def.insert(0, {"entry_id": entry_id, "direction": 1})

    # Remove duplicates (except the first one)
    sort_def = [sort_def[0]] + [
        entry for entry in sort_def[1:] if entry.get("entry_id") != entry_id
    ]
    return sort_def[:3]


def get_default_sort_def(table_def):
    """
    Set to first field if there's any table_def
    """
    if len(table_def["fields"]) > 0:
        return [{"entry_id": table_def["fields"][0]["entry_id"], "direction": 1}]
    return []


def _clean_sort_def(table_def, sort_def, user, include_metadata=False):
    """
    Validate and clean sort_def, removing broken links and adding metadata.
    Uses bulk DB query for Concept objects to minimize queries.
    """
    warnings, errors = [], []
    validated_sort_def, extended_sort_def = [], []

    # Ensure sort_def is a list
    if not isinstance(sort_def, list):
        sort_def = []

    # Build lookup for entry_id → concept_id
    field_lookup = {f["entry_id"]: f.get("concept_id") for f in table_def.get("fields", [])}

    # Collect concept_ids for sort_def entries
    concept_ids = {
        field_lookup.get(entry.get("entry_id"))
        for entry in sort_def
        if field_lookup.get(entry.get("entry_id"))
    }

    # If no valid concept_ids, fallback to default sort
    if not concept_ids:
        validated_sort_def = get_default_sort_def(table_def)
        concept_ids = {
            field_lookup.get(entry.get("entry_id"))
            for entry in validated_sort_def
            if field_lookup.get(entry.get("entry_id"))
        }
    else:
        validated_sort_def = [
            entry for entry in sort_def if field_lookup.get(entry.get("entry_id"))
        ]

    # Bulk fetch concepts
    concepts = Concept.objects.filter(permanent_id__in=concept_ids)
    concept_lookup = {c.permanent_id: c for c in concepts}

    # Build extended sort_def
    for entry in validated_sort_def:
        concept_id = field_lookup.get(entry.get("entry_id"))
        if concept_id in concept_lookup:
            extended_sort_def.append(
                {
                    "entry_id": entry["entry_id"],
                    "direction": entry["direction"],
                    "label": concept_lookup[concept_id].name,
                }
            )

    if include_metadata:
        return {
            "sort_def": validated_sort_def,
            "extended_sort_def": extended_sort_def,
            "warnings": warnings,
            "errors": errors,
        }
    return validated_sort_def


def get_corresponding_table_def_entry(sort_def_entry, table_def):
    for idx, td_entry in enumerate(table_def.get("fields", [])):
        if td_entry["entry_id"] == sort_def_entry["entry_id"]:
            return idx, td_entry
    return -1, None


def get_collections_with_fields_requiring_event_dates(chironuser, table_def):
    # Collect all concept_ids from table_def fields
    concept_ids = {
        td_entry.get("concept_id")
        for td_entry in table_def.get("fields", [])
        if td_entry.get("concept_id")
    }

    if not concept_ids:
        return []

    # Bulk fetch all concepts
    concepts = Concept.objects.filter(permanent_id__in=concept_ids)
    concept_lookup = {c.permanent_id: c for c in concepts}

    # Determine which concepts require event dates
    requiring_event_dates = set()
    for td_entry in table_def.get("fields", []):
        concept_id = td_entry.get("concept_id")
        oConcept = concept_lookup.get(concept_id)
        if oConcept:
            display_processor = oConcept.get_display_processor(chironuser, td_entry)
            if display_processor.check_requires_event_dates():
                requiring_event_dates.add(concept_id)

    # Collect unique collection IDs for those concepts
    collection_ids = {
        concept_lookup[cid].collection.permanent_id
        for cid in requiring_event_dates
        if cid in concept_lookup
    }

    return list(collection_ids)

import copy
from django.core.exceptions import ObjectDoesNotExist

from chiron import models
from chiron import query_definition as qdef


def apply_transformation_add_entry(chironuser, input_table_def, transformation):
    """
    Add or edit an entry on the table definition.

    :type: "add_entry"
    :concept_id: (str) the permanent_id of the Concept to add
    :entry_id: (str, default=None) if editing existing entry, the entry_id
    :position: (default="append") append|prepend new entry, has no effect if editing existing
    :aggregate: (default=False) stack/aggregate records for field
    :aggregation_method: (default=None) if aggregate is True, the method to use for
      aggregation

    """
    existing_entry_id = transformation.get("entry_id", None)
    concept_id = transformation.get("concept_id")
    position = transformation.get("position", "append")
    oConcept = models.Concept.objects.get(permanent_id=concept_id)
    display_processor = oConcept.get_display_processor(chironuser)
    if display_processor.validate_form(transformation):
        td_entry = display_processor.generate_table_def_entry()
        output_table_def = qdef.add_table_def_entry(
            input_table_def, td_entry, existing_entry_id, position
        )
        return {
            "transformation_successful": True,
            "table_def": output_table_def,
        }
    return {
        "transformation_successful": False,
        "table_def": input_table_def,
        "transformation_errors": display_processor.errors,
    }


def apply_transformation_bulk_add_entries(chironuser, input_table_def, transformation):
    """
    Add multiple entries to table definition.

    :type: "bulk_add_entries"
    :concept_id_list: (list) the permanent_id of the Concept to add
    """
    # Get Concept ID list from parameter
    concept_id_list = transformation.get("concept_id_list")
    # Make copy of Table Definition to update with new entries
    output_table_def = copy.deepcopy(input_table_def)
    # Iterate through Concept ID list and add new entries to Table Definition
    for concept_id in concept_id_list:
        # Get Concept that needs to be added and its Display Processor
        concept_to_add = models.Concept.objects.get(permanent_id=concept_id)
        display_processor = concept_to_add.get_display_processor(chironuser)
        # Add Table Definition entry if transformation is valid, if not then return error
        if display_processor.validate_form(transformation):
            td_entry = display_processor.generate_table_def_entry()
            output_table_def = qdef.add_table_def_entry(output_table_def, td_entry)
        else:
            return {
                "transformation_successful": False,
                "table_def": input_table_def,
                "transformation_errors": display_processor.errors,
            }
    # Return new Table Definition
    return {
        "transformation_successful": True,
        "table_def": output_table_def,
    }


def apply_transformation_add_category(chironuser, input_table_def, transformation):
    """
    Add a new category on the table definition.

    :type: "add_category"
    :category_id: (str) the unique_id of the Category to add
    """
    # Get Category ID
    category_id = int(transformation.get("category_id"))
    # Check if Category exists, if not return error
    try:
        selected_category = models.Category.objects.get(id=category_id)
    except ObjectDoesNotExist:
        return {
            "transformation_successful": False,
            "table_def": input_table_def,
            "transformation_errors": ["No category found with id {}".format(category_id)],
        }
    # Get Concepts
    concept_queryset = models.Concept.objects.filter(category=selected_category)
    # Build table definition using Concepts
    output_table_def = input_table_def
    for item in concept_queryset:
        # Get display processor for Concept
        display_processor = item.get_display_processor(chironuser)
        # If display processor is not None, add entry to table def
        if display_processor:
            # Generate table def entry for using display processor
            # TODO: Figure out how to handle error here? Situation means multiple entries.
            td_entry = display_processor.generate_table_def_entry()
            # Add table def entry need to copy the entries so they are not persisted to the next
            # call
            output_table_def = qdef.add_table_def_entry(dict(output_table_def), dict(td_entry))
    # Return results
    return {
        "transformation_successful": True,
        "table_def": output_table_def,
    }


def apply_transformation_duplicate_entry(chironuser, input_table_def, transformation):
    """
    Duplicates an entry from the table def with the provided entry_id and adds it in the next
    position.

    :type: "duplicate_entry"
    :entry_id: The entry_id of the table def entry to duplicate
    """
    entry_id = transformation["entry_id"]
    output_table_def = qdef.duplicate_table_def_entry(input_table_def, entry_id)

    return {
        "transformation_successful": True,
        "table_def": output_table_def,
    }


def apply_transformation_delete_entry(chironuser, input_table_def, transformation):
    """
    Deletes an entry from the table def with the provided entry_id.

    :type: "delete_entry"
    :entry_id: The entry_id of the table def entry to remove
    """
    entry_id = transformation["entry_id"]
    output_table_def = qdef.delete_table_def_entry(input_table_def, entry_id)

    return {
        "transformation_successful": True,
        "table_def": output_table_def,
    }


def apply_transformation_resort_columns(chironuser, input_table_def, transformation):
    """
    Change the sort order of the table def entries (affects how columns in results table are
    sorted).
    This is also used to reset current table def by submitting a blank set of entry IDs.

    :type: "resort_columns"
    :entry_ids: The array of entry IDs sorted in the correct order.
    """
    # print(transformation)
    entry_ids = transformation.get("entry_ids", [])
    output_table_def = qdef.resort_table_def(input_table_def, entry_ids)

    return {
        "transformation_successful": True,
        "table_def": output_table_def,
    }


def apply_transformation_add_sort_entry(chironuser, input_table_def, transformation):
    """
    Select a column to sort by (affects how rows are sorted in the results table).
    To reverse sort, do two add_sort_entry transformations on the same column.

    :type: "add_sort_entry"
    :entry_id: The entry_id of the entry to sort by.
    """
    # Get Entry ID from Transformation
    entry_id = transformation["entry_id"]
    # Use Entry ID to add entry to Sort Def
    output_sort_def = qdef.add_sort_def_entry(input_table_def, entry_id)
    input_table_def["sort"] = output_sort_def
    # Return transformation results
    return {
        "transformation_successful": True,
        "table_def": input_table_def,
    }


def apply_transformation_clear_sort_entries(user, input_table_def, transformation):
    """Apply Transformation Clear Sort

    Clear sort definition.

    :type: "clear_sort_entries"
    """
    input_table_def["sort"] = []
    return {
        "transformation_successful": True,
        "table_def": input_table_def,
    }


transformation_function_lookup = {
    "add_entry": apply_transformation_add_entry,
    "bulk_add_entries": apply_transformation_bulk_add_entries,
    "duplicate_entry": apply_transformation_duplicate_entry,
    "delete_entry": apply_transformation_delete_entry,
    # "edit_entry": apply_transformation_edit_entry,
    "resort_columns": apply_transformation_resort_columns,
    "add_sort_entry": apply_transformation_add_sort_entry,
    "clear_sort_entries": apply_transformation_clear_sort_entries,
    "add_category": apply_transformation_add_category,
}

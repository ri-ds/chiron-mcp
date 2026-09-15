import copy

from django.db import transaction
from django.shortcuts import get_object_or_404

from chiron import models
from chiron import query_definition as qdef


def apply_transformation_add_entry(chironuser, input_cohort_def, transformation):
    """
    Add a new entry or edit an existing entry on the cohort definition.

    The options for the transformation definition will depend on the type of cohort def processor.
    However, these are the global options for all "add entry" transformations:

    :type: "add_entry"
    :concept_id: (str) the permanent_id of the Concept to add
    :entry_id: (optional) If editing an existing entry, provide the entry_id
    :prefilter_value: (optional) TODO: Define what this is.
    :validate_only: (default=False) Do not save results and return validation info
    :ignore_warnings: (default=False) Apply the transformation even if there are warnings
    """
    # Get parameters from transformation
    concept_id = transformation["concept_id"]
    existing_entry_id = transformation.get("entry_id", None)
    prefilter_value = transformation.get("prefilter_value", None)
    validate_only = transformation.get("validate_only", False)
    # Get concept and processor
    oConcept = get_object_or_404(models.Concept, permanent_id=concept_id)
    processor = oConcept.get_cohort_def_processor(chironuser, prefilter_value=prefilter_value)
    # Get existing Cohort Def entry if applicable
    cohort_def_entry = None
    if existing_entry_id:
        cohort_def_entry = qdef.lookup_cohort_def_entry(input_cohort_def, existing_entry_id)
    # Add Cohort Def entry if input passes validation and "validate only" parameter is false
    if processor.validate_form(transformation) and not validate_only:
        cd_entry = processor.generate_cohort_def_entry(
            input_cohort_def, existing_cd_entry=cohort_def_entry
        )
        if existing_entry_id:
            output_cohort_def = qdef.edit_concept_entry_in_cohort_def(
                input_cohort_def, existing_entry_id, cd_entry
            )
        else:
            output_cohort_def = qdef.append_concept_entry_to_cohort_def(
                chironuser, input_cohort_def, cd_entry
            )
        entry_id = cd_entry.get("entry_id")
        return {
            "transformation_successful": True,
            "cohort_def": output_cohort_def,
            "entry_id": entry_id,
        }
    form_errors = processor.form_errors
    form_warnings = processor.form_warnings
    return {
        "transformation_successful": False,
        "transformation_errors": form_errors,
        "transformation_warnings": form_warnings,
        "cohort_def": input_cohort_def,
    }


def apply_transformation_delete_entry(chironuser, input_cohort_def, transformation):
    """
    Delete an entry from the cohort definition.

    :type: "delete_entry"
    :entry_id: The entry_id of the cohort def entry to remove
    :remove_empty_criteria_sets: (optional, default=False) If this is the last entry in
      a criteria set, also delete the criteria set.

    """
    entry_id = transformation["entry_id"]
    output_cohort_def = qdef.delete_concept_entry_from_cohort_def(input_cohort_def, entry_id)

    # check for last entry removed and clear out the whole cohort def
    if transformation.get("remove_empty_criteria_sets"):
        new_output_cohort_def = []
        for criteria_set in output_cohort_def:
            if criteria_set.get("list", []):
                new_output_cohort_def.append(criteria_set)
        output_cohort_def = new_output_cohort_def

    return {
        "transformation_successful": True,
        "cohort_def": output_cohort_def,
    }


def apply_transformation_add_criteria_set(chironuser, input_cohort_def, transformation):
    """
    Add an empty criteria set to a cohort definition

    :type: "add_criteria_set"
    :collection_id: The permanent_id of the Collection to add
    """
    collection_id = transformation["collection_id"]
    oCollection = models.Collection.objects.get(
        dataset=chironuser.dataset, permanent_id=collection_id
    )
    output_cohort_def = qdef.append_criteria_set_to_cohort_def(input_cohort_def, oCollection)

    return {
        "transformation_successful": True,
        "cohort_def": output_cohort_def,
    }


def apply_transformation_set_criteria_set_alias(chironuser, input_cohort_def, transformation):
    """
    Set an alias for referring to this criteria set

    :type: "set_criteria_set_alias"
    :entry_id: the entry_id for this criteria set in the cohort def
    :alias: (str) the new alias, or None/empty string to remove alias
    """
    output_cohort_def = copy.deepcopy(input_cohort_def)
    entry_id = transformation.get("entry_id")
    alias = transformation.get("alias")
    cd_entry = qdef.lookup_cohort_def_entry(output_cohort_def, entry_id)
    if alias:
        cd_entry["alias"] = alias
    elif "alias" in cd_entry:
        del cd_entry["alias"]
    response = {
        "transformation_successful": True,
        "cohort_def": output_cohort_def,
    }
    return response


def apply_transformation_delete_criteria_set(chironuser, input_cohort_def, transformation):
    """
    Delete a criteria set (and all its members) from the cohort definition.

    :type: "delete_criteria_set"
    :entry_id: The entry_id of the criteria set to remove
    """
    entry_id = transformation["entry_id"]
    output_cohort_def = qdef.delete_criteria_set_from_cohort_def(input_cohort_def, entry_id)

    return {
        "transformation_successful": True,
        "cohort_def": output_cohort_def,
    }


def apply_transformation_create_event_rule(chironuser, input_cohort_def, transformation):
    """
    Creates a blank event rule for a criteria set "any date".

    :type: "create_event_rule"
    :entry_id: The entry_id of the criteria set
    """
    output_cohort_def = copy.deepcopy(input_cohort_def)
    entry_id = transformation.get("entry_id")
    cd_entry = qdef.lookup_cohort_def_entry(output_cohort_def, entry_id)
    cd_entry["event_rule"] = {
        "type": "no_restriction",
    }
    response = {
        "transformation_successful": True,
        "cohort_def": output_cohort_def,
    }
    return response


def apply_transformation_delete_event_rule(chironuser, input_cohort_def, transformation):
    """
    Delete an event rule from a criteria set.

    :type: "delete_event_rule"
    :entry_id: The entry_id of the criteria set the event rule is associated with
    """
    output_cohort_def = copy.deepcopy(input_cohort_def)
    entry_id = transformation.get("entry_id")
    cd_entry = qdef.lookup_cohort_def_entry(output_cohort_def, entry_id)
    # delete any references to this entry before deleting the entry
    output_cohort_def = qdef.delete_references_to_criteria_set_event(output_cohort_def, entry_id)
    del cd_entry["event_rule"]
    response = {
        "transformation_successful": True,
        "cohort_def": output_cohort_def,
    }
    return response


def apply_transformation_modify_event_rule(chironuser, input_cohort_def, transformation):
    """
    Edit an existing event rule.

    :type: "modify_event_rule"
    :entry_id: The entry_id of the criteria set the event rule is associated with
    :option_type: There are various forms that can be used to modify an event rule
    :[various]: Other data will depend on the form type.
    """
    output_cohort_def = copy.deepcopy(input_cohort_def)
    entry_id = transformation.get("entry_id")
    cd_entry = qdef.lookup_cohort_def_entry(output_cohort_def, entry_id)
    event_options = qdef.EventOptionCollection(chironuser, output_cohort_def, entry_id)
    event_option = event_options.get_event_option_by_type(transformation["option_type"])
    if event_option.validate_user_input(transformation):
        cd_entry["event_rule"] = event_option.create_event_rule()
        response = {
            "transformation_successful": True,
            "cohort_def": output_cohort_def,
        }
    else:
        response = {
            "transformation_successful": False,
            "transformation_errors": event_option.errors,
            "cohort_def": input_cohort_def,
        }
    return response


def apply_transformation_change_to_boolean_or(chironuser, input_cohort_def, transformation):
    """
    Groups two cohort def entries into an "or" group. Both entries must be in the same criteria
    set and adjacent.

    :type: "change_to_boolean_or"
    :entry_id:  Pass the entry_id of the first entry. The second entry will be autodetected.
    """
    entry_id = transformation.get("entry_id")
    output_cohort_def = qdef.change_to_boolean_or(input_cohort_def, entry_id)
    response = {
        "transformation_successful": True,
        "cohort_def": output_cohort_def,
    }
    return response


def apply_transformation_change_to_boolean_and(chironuser, input_cohort_def, transformation):
    """
    Separates two cd_entries already in an "or" group. The entries must be
      adjacent. If any remaining "or" groups after the split have only one cd_entry, the "or"
      group will be eliminated altogether.

    :type: "change_to_boolean_and"
    :entry_id: the entry_id of the first entry. The second entry will be autodetected.
    """
    entry_id = transformation.get("entry_id")
    output_cohort_def = qdef.change_to_boolean_and(input_cohort_def, entry_id)
    response = {
        "transformation_successful": True,
        "cohort_def": output_cohort_def,
    }
    return response


def apply_transformation_sort_cd_entries(chironuser, input_cohort_def, transformation):
    """
    Change how entries are sorted within a criteria set.

    :type: "sort_cd_entries"
    :entry_id: The entry ID of the criteria set to be sorted
    :child_ids: An array of entry_ids for all cd_entries in the criteria set, sorted in the
      new desired order.
    """
    entry_id = transformation.get("entry_id")
    child_ids = transformation.get("child_ids")
    output_cohort_def = qdef.change_concept_entry_sort_order(
        chironuser, input_cohort_def, entry_id, child_ids
    )
    response = {
        "transformation_successful": True,
        "cohort_def": output_cohort_def,
    }
    return response


def apply_transformation_clear_all(chironuser, input_cohort_def, transformation):
    response = {
        "transformation_successful": True,
        "cohort_def": [],
    }
    return response


def apply_transformation_add_criteria_set_count_rule(chironuser, input_cohort_def, transformation):
    """
    Add or edit the count rule for an existing criteria set.

    :type: "add_criteria_set_count_rule"
    :entry_id: The entry ID of the criteria set to be sorted
    :rule_operator: "at least", "at most", or "exactly"
    :rule_count: integer
    """
    # TODO: test that transformation definition is valid
    entry_id = transformation["entry_id"]
    cd_entry = qdef.lookup_cohort_def_entry(input_cohort_def, entry_id)
    cd_entry["subcol_count_restriction"] = {
        "type": transformation["rule_operator"],
        "value": int(transformation["rule_count"]),
    }
    # need criteria_set_entry_id, rule_operator, rule_count
    response = {
        "transformation_successful": True,
        "cohort_def": input_cohort_def,
    }
    return response


# TODO: Add Unit Test for this function
def update_cohort_autosave(combined_def, chiron_user):
    """Update Cohort Autosave

    Updates Cohort Auto-Save for current Chirton User.

    :param combined_def: New auto-saved Cohort Definition, Table Definition, and Sort Definition
    :type combined_def: str
    :param chiron_user: Chiron User
    :type chiron_user: class: chiron.models.ChironUser
    :return: User Created Content entry for Cohort Auto-Save
    :rtype: class: chiron.models.UserCreatedContent
    """
    with transaction.atomic():
        models.UserCreatedContent.objects.filter(creator=chiron_user, type="cohort_auto").delete()
        updated_cohort_autosave = models.UserCreatedContent(
            creator=chiron_user, type="cohort_auto", definition=combined_def, public=False
        )
        updated_cohort_autosave.save()
    return updated_cohort_autosave


transformation_function_lookup = {
    "add_entry": apply_transformation_add_entry,
    "delete_entry": apply_transformation_delete_entry,
    "add_criteria_set": apply_transformation_add_criteria_set,
    "delete_criteria_set": apply_transformation_delete_criteria_set,
    "change_to_boolean_or": apply_transformation_change_to_boolean_or,
    "change_to_boolean_and": apply_transformation_change_to_boolean_and,
    "sort_cd_entries": apply_transformation_sort_cd_entries,
    "clear_all": apply_transformation_clear_all,
    "add_criteria_set_count_rule": apply_transformation_add_criteria_set_count_rule,
    "set_criteria_set_alias": apply_transformation_set_criteria_set_alias,
    "create_event_rule": apply_transformation_create_event_rule,
    "modify_event_rule": apply_transformation_modify_event_rule,
    "delete_event_rule": apply_transformation_delete_event_rule,
    # ...
    # See chiron/views/views_ajax_cohort_def.py for examples of possible transformations
}

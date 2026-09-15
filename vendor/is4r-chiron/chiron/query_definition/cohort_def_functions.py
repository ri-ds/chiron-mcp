import random
import string
import copy
from collections import OrderedDict

from .. import models
from .event_options import EventOptionCollection


def set_active_cohort_def(request, cohort_def):
    oSnapshot = models.CohortDefSnapshot(chironuser=request.chironuser)
    oSnapshot.set_cohort_def(cohort_def)
    oSnapshot.save()
    return oSnapshot


def get_active_cohort_def(request):
    cohort_def = models.CohortDefSnapshot.get_active_cohort_def(request.chironuser)
    return cohort_def


def clean_active_cohort_def(chironuser, include_metadata=False):
    """
    Wrapper for clean_cohort_def()
    """
    cohort_def = models.CohortDefSnapshot.get_active_cohort_def(chironuser)
    return clean_cohort_def(cohort_def, chironuser, include_metadata)


def clean_cohort_def(cohort_def, chironuser, include_metadata=False):
    """
    Checks for JSON errors, broken links to Collection and Concept models, etc.
    Also checks for user permissions and applies appropriate restrictions.

    cohort_def: the cohort_def with appropriate modifications if there were problems with it
    extended_cohort_def: a cohort_def with additional descriptive fields added for displaying
    warnings: notifications about problems that don't break the query
    errors: notifications about problems that break the query

    - pass include_metadata=True to get back only the cohort_def
    """
    extended_cohort_def = []
    warnings = []
    errors = []
    if not isinstance(cohort_def, list):
        cohort_def = []

    for criteria_set in cohort_def:
        response = _create_extended_criteria_set(cohort_def, criteria_set, chironuser)
        if response["extended_criteria_set"].get("is_root_collection"):
            extended_cohort_def.insert(0, response["extended_criteria_set"])
        else:
            extended_cohort_def.append(response["extended_criteria_set"])
        warnings += response["warnings"]
        errors += response["errors"]

    criteria_set_name_counters = {}
    for criteria_set in extended_cohort_def:
        if criteria_set.get("is_root_collection"):
            continue
        collection_name = criteria_set.get("collection_name", criteria_set["collection_id"])
        if collection_name not in criteria_set_name_counters:
            criteria_set_name_counters[collection_name] = 0
        criteria_set_name_counters[collection_name] += 1
        if criteria_set.get("alias"):
            criteria_set["criteria_set_name"] = criteria_set["alias"]
        else:
            criteria_set["criteria_set_name"] = "{} {}".format(
                collection_name, criteria_set_name_counters[collection_name]
            )

    if errors:
        validated_cohort_def = []
    else:
        validated_cohort_def = cohort_def

    if include_metadata:
        return {
            "cohort_def": validated_cohort_def,
            "extended_cohort_def": extended_cohort_def,
            "warnings": warnings,
            "errors": errors,
        }
    return cohort_def


def _create_extended_criteria_set(cohort_def, criteria_set, chironuser):
    referenced_date_rules = get_entry_ids_referenced_by_relative_date_rule(cohort_def)
    warnings = []
    errors = []
    # set basic extended fields
    extended_criteria_set = {
        "entry_type": criteria_set["entry_type"],
        "entry_id": criteria_set["entry_id"],
        "collection_id": criteria_set["collection_id"],
        "alias": criteria_set.get("alias", ""),
    }
    if "event_rule" in criteria_set:
        if criteria_set["entry_id"] in referenced_date_rules:
            extended_criteria_set["referenced_by_other_event"] = True

    # set extended fields that depend on the existence of oCollection
    try:
        oCollection = models.Collection.objects.get(
            dataset=chironuser.dataset, permanent_id=criteria_set["collection_id"]
        )
        if oCollection.is_root_collection:
            extended_criteria_set["label"] = "{} Criteria".format(oCollection.name.title())
            extended_criteria_set["is_root_collection"] = True
        else:
            extended_criteria_set["label"] = _set_title_for_subcol_criteria_set(
                criteria_set, oCollection
            )

        # data to use for display purposes
        extended_criteria_set["collection_name"] = oCollection.name.title()
        extended_criteria_set["subcol_count_restriction"] = criteria_set.get(
            "subcol_count_restriction", {}
        )

        if (
            oCollection.check_event_permission_group(chironuser)
            and oCollection.check_event_user_access_level(chironuser) is not None
        ):
            extended_criteria_set["has_event_field"] = True
        else:
            extended_criteria_set["has_event_field"] = False
        if "event_rule" in criteria_set:
            event_options = EventOptionCollection(chironuser, cohort_def, criteria_set["entry_id"])
            option = event_options.get_active_option()
            event_rule_string = option.event_rule_to_string()
            extended_criteria_set["event_rule_label"] = event_rule_string
            # check that user is allowed to view this event rule
            if event_rule_string:
                if not oCollection.check_event_permission_group(chironuser):
                    extended_criteria_set["event_rule_error"] = True
                    extended_criteria_set["can_edit_event_rule"] = False
                    errors.append(
                        "You are not allowed to access events on the criteria set '{}'.".format(
                            oCollection.name
                        )
                    )
                event_user_access_level = oCollection.check_event_user_access_level(chironuser)
                if event_user_access_level is None:
                    extended_criteria_set["event_rule_error"] = True
                    extended_criteria_set["can_edit_event_rule"] = False
                    errors.append(
                        "The event rule on criteria set '{}' includes PHI.".format(
                            oCollection.name
                        )
                    )
                elif event_user_access_level == "deid" and not option.is_deidentified():
                    extended_criteria_set["event_rule_error"] = True
                    extended_criteria_set["can_edit_event_rule"] = True
                    errors.append(
                        "The event rule on criteria set '{}' includes PHI.".format(
                            oCollection.name
                        )
                    )

    except models.Collection.DoesNotExist:
        errors.append(
            'Couldn\'t find data definition for collection ID "{}"'.format(
                criteria_set["collection_id"]
            )
        )
        extended_criteria_set["label"] = 'collection ID "{}" not found'.format(
            criteria_set["collection_id"]
        )
        extended_criteria_set["has_errors"] = True
        extended_criteria_set["can_not_edit"] = True

    # add cd_entries
    extended_cd_entries = []
    for cd_entry in criteria_set["list"]:
        response = _get_extended_cd_entry(cd_entry, chironuser)
        extended_cd_entries.append(response["extended_cd_entry"])
        warnings += response["warnings"]
        errors += response["errors"]
    extended_criteria_set["entries"] = extended_cd_entries

    return {
        "extended_criteria_set": extended_criteria_set,
        "warnings": warnings,
        "errors": errors,
    }


def _get_extended_cd_entry(cd_entry, chironuser):
    if "concept_id" in cd_entry:
        return _cd_entry_to_extended_cd_entry(cd_entry, chironuser)
    elif cd_entry["entry_type"] == "or_group":
        warnings = []
        errors = []
        or_group = {
            "entry_type": "or_group",
            "entry_id": cd_entry["entry_id"],
            "entries": [],
        }
        for subentry in cd_entry["list"]:
            response = _cd_entry_to_extended_cd_entry(subentry, chironuser)
            or_group["entries"].append(response["extended_cd_entry"])
            warnings += response["warnings"]
            errors += response["errors"]
        return {
            "extended_cd_entry": or_group,
            "warnings": warnings,
            "errors": errors,
        }


def _cd_entry_to_extended_cd_entry(cd_entry, chironuser):
    warnings = []
    errors = []
    try:
        oConcept = models.Concept.objects.get(
            collection__dataset=chironuser.dataset, permanent_id=cd_entry["concept_id"]
        )
        processor = oConcept.get_cohort_def_processor(chironuser)
        if processor is None:
            # even if no permission on the processor, get it anyway just to generate labels
            forced_processor = oConcept.get_cohort_def_processor_without_user()
            if forced_processor is None:
                label = "there was an error"
                abbreviated_label = "there was an error"
            else:
                label = forced_processor.display_entry_as_html_full(cd_entry)
                abbreviated_label = forced_processor.display_entry_as_html_abbreviated(cd_entry)
        else:
            label = processor.display_entry_as_html_full(cd_entry)
            abbreviated_label = processor.display_entry_as_html_abbreviated(cd_entry)

        extended_cd_entry = {
            "entry_id": cd_entry["entry_id"],
            "concept_id": cd_entry["concept_id"],
            "prefilter_value": cd_entry.get("prefilter_value", None),
            "label": label,
            "abbreviated_label": abbreviated_label,
            "exclude_selected": (
                cd_entry["exclude_selected"] if "exclude_selected" in cd_entry else True
            ),
            "values": cd_entry.get("categories"),
        }
        can_use_concept, reason = oConcept.user_can_use_concept_in_cohort_def(chironuser, cd_entry)
        if not can_use_concept:
            extended_cd_entry["has_errors"] = True
            errors.append(f"{oConcept.name}: {reason}")
            if reason != "This cohort def entry is set up in a way that could expose PHI.":
                extended_cd_entry["can_not_edit"] = True
    except models.Concept.DoesNotExist:
        errors.append('Can\'t find concept "{}" in system'.format(cd_entry["concept_id"]))
        extended_cd_entry = {
            "entry_id": cd_entry["entry_id"],
            "concept_id": cd_entry["concept_id"],
            "prefilter_value": cd_entry.get("prefilter_value", None),
            "label": 'concept ID "{}" not found'.format(cd_entry["concept_id"]),
            "has_errors": True,
            "can_not_edit": True,
        }
    return {
        "extended_cd_entry": extended_cd_entry,
        "warnings": warnings,
        "errors": errors,
    }


def _set_title_for_subcol_criteria_set(criteria_set, oCollection):
    subcol_count_type = (
        criteria_set["subcol_count_restriction"]["type"]
        if "subcol_count_restriction" in criteria_set
        else "at least"
    )
    subcol_count_value = (
        criteria_set["subcol_count_restriction"]["value"]
        if "subcol_count_restriction" in criteria_set
        else 1
    )
    subcol_name = oCollection.name if subcol_count_value == 1 else oCollection.get_name_plural()
    oProjectCollection = oCollection.dataset.root_collection
    title = "{} has {} {} <strong>{}</strong> where:".format(
        oProjectCollection.name.capitalize(),
        subcol_count_type,
        subcol_count_value,
        subcol_name,
    )
    return title


def get_criteria_set_name(chironuser, cohort_def, entry_id):
    """
    This name will already be in the extended cohort def, but can use
    this to get it when looking at the standard cohort def.
    TODO: This code duplicates logic used when creating extended_criteria_set. It's needed for
      event option classes. Because those classes are used to make the extended_cohort_def, they
      can't reference the extended cohort def without creating a circular reference.
    """
    criteria_set_name_counters = {}
    for criteria_set in cohort_def:
        oCollection = models.Collection.objects.get(
            dataset=chironuser.dataset, permanent_id=criteria_set["collection_id"]
        )
        collection_name = oCollection.name.title()
        if collection_name not in criteria_set_name_counters:
            criteria_set_name_counters[collection_name] = 0
        criteria_set_name_counters[collection_name] += 1
        if criteria_set.get("alias"):
            criteria_set_name = criteria_set["alias"]
        else:
            criteria_set_name = "{} {}".format(
                collection_name, criteria_set_name_counters[collection_name]
            )
        if criteria_set["entry_id"] == entry_id:
            return criteria_set_name
    raise ValueError("No criteria set found for entry ID {}".format(entry_id))


def lookup_cohort_def_entry(cohort_def, entry_id):
    """Returns the entry matching provided entry_id or None.
    "Entry" could be anything with an entry id (criteria_set, or_group, cd_entry, etc.)
    """
    for entry in cohort_def:
        if "entry_id" in entry and entry["entry_id"] == entry_id:
            return entry
        if "list" in entry:
            child_entry = lookup_cohort_def_entry(entry["list"], entry_id)
            if child_entry:
                return child_entry
    return None


def get_all_event_criteria_sets(extended_cohort_def, exclude_entry_ids=[]):
    event_criteria_sets = []
    for criteria_set in extended_cohort_def:
        if "event_rule" in criteria_set and criteria_set["entry_id"] not in exclude_entry_ids:
            event_criteria_sets.append(copy.deepcopy(criteria_set))
        if "list" in criteria_set:
            event_criteria_sets += get_all_event_criteria_sets(criteria_set["list"])
    return event_criteria_sets


def get_criteria_sets_with_relative_date_rule(cohort_def):
    criteria_sets = []
    for criteria_set in cohort_def:
        if (
            "event_rule" in criteria_set
            and criteria_set["event_rule"]["type"] == "relative_to_other_event"
        ):
            criteria_sets.append(criteria_set)
    return criteria_sets


def get_entry_ids_referenced_by_relative_date_rule(cohort_def):
    """if a criteria set is involved in multiple relative date rules, its ID will be listed
    multiple times
    """
    entries = []
    for criteria_set in cohort_def:
        if (
            "event_rule" in criteria_set
            and criteria_set["event_rule"]["type"] == "relative_to_other_event"
        ):
            entries.append(criteria_set["event_rule"]["target_entry_id"])
    return entries


def get_entry_ids_associated_with_relative_date_rule(cohort_def):
    """if a criteria set is involved in multiple relative date rules, its ID will be listed
    multiple times
    """
    entries = []
    for criteria_set in cohort_def:
        if (
            "event_rule" in criteria_set
            and criteria_set["event_rule"]["type"] == "relative_to_other_event"
        ):
            entries.append(criteria_set["entry_id"])
            entries.append(criteria_set["event_rule"]["target_entry_id"])
    return entries


def check_criteria_set_has_custom_count_rule(criteria_set):
    standard_rule = {"type": "at least", "value": 1}
    if (
        "subcol_count_restriction" in criteria_set
        and criteria_set["subcol_count_restriction"] != standard_rule
    ):
        return True
    return False


def get_criteria_sets_with_custom_count_rule(cohort_def):
    criteria_sets = []
    for criteria_set in cohort_def:
        if check_criteria_set_has_custom_count_rule(criteria_set):
            criteria_sets.append(criteria_set)
    return criteria_sets


def delete_concept_entry_from_cohort_def(cohort_def, entry_id):
    for i, criteria_set in enumerate(cohort_def):
        if "list" in criteria_set:
            for j, concept_entry in enumerate(criteria_set["list"]):
                if concept_entry["entry_id"] == entry_id:
                    del criteria_set["list"][j]
    return cohort_def


def delete_criteria_set_from_cohort_def(cohort_def, entry_id):
    # find and delete any event references to this criteria set
    cohort_def = delete_references_to_criteria_set_event(cohort_def, entry_id)
    # delete criteria set
    for i, criteria_set in enumerate(cohort_def):
        if criteria_set["entry_id"] == entry_id:
            del cohort_def[i]
    return cohort_def


def delete_references_to_criteria_set_event(cohort_def, entry_id):
    for criteria_set in cohort_def:
        if entry_id == criteria_set["entry_id"]:
            continue
        if (
            "event_rule" in criteria_set
            and criteria_set["event_rule"]["type"] == "relative_to_other_event"
        ):
            if criteria_set["event_rule"]["target_entry_id"] == entry_id:
                # before deleting, event rule, must check this one also for references
                delete_references_to_criteria_set_event(cohort_def, criteria_set["entry_id"])
                # delete event rule
                del criteria_set["event_rule"]
    return cohort_def


def get_criteria_set_for_cohort_entry(cohort_def, entry_id):
    for criteria_set in cohort_def:
        if "list" in criteria_set:
            flat_list = _flatten_list(criteria_set)
            if entry_id in flat_list.keys():
                return criteria_set
    return None


def change_concept_entry_sort_order(chironuser, cohort_def, criteria_set_id, concept_entry_ids):
    criteria_set = lookup_cohort_def_entry(cohort_def, criteria_set_id)
    flat_list = _flatten_list(criteria_set)
    resorted_flat_list = []
    # determine if internal or external move
    moving_between_collections = False
    for entry_id in concept_entry_ids:
        if entry_id not in flat_list:
            moving_between_collections = True
            moved_entry_id = entry_id
    if moving_between_collections:
        # verify that entry is allowed in this destination, if not return cohort_def
        # with no change
        moved_entry = lookup_cohort_def_entry(cohort_def, moved_entry_id)
        oConcept = models.Concept.objects.get(
            collection__dataset=chironuser.dataset, permanent_id=moved_entry["concept_id"]
        )
        oCollection = models.Collection.objects.get(
            dataset=chironuser.dataset, permanent_id=criteria_set["collection_id"]
        )
        if oConcept.collection != oCollection and not oCollection.is_root_collection:
            # print("do not allow")
            return cohort_def
        # get the criteria_set for the source of move
        source_criteria_set = get_criteria_set_for_cohort_entry(cohort_def, moved_entry_id)
        # delete moved entry from source criteria set, add to flat_list of entries for
        # destination
        source_flat_list = _flatten_list(source_criteria_set)
        flat_list[moved_entry_id] = source_flat_list[moved_entry_id]
        cohort_def = delete_concept_entry_from_cohort_def(cohort_def, moved_entry_id)
    for entry_id in concept_entry_ids:
        if entry_id:
            resorted_flat_list.append(flat_list[entry_id])
            criteria_set["list"] = _stack_list(resorted_flat_list)
    return cohort_def


def get_relevant_fields_for_cohort_def(dataset, cohort_def, collection_id=None):
    """
    collection_type can be "external", "subcollection", or "any"
    if collection_id is provided, will match permanent_id of collection
    """
    fields = []
    for criteria_set in cohort_def:
        field_count = len(fields)
        oCollection = models.Collection.objects.get(
            dataset=dataset, permanent_id=criteria_set["collection_id"]
        )
        if collection_id and oCollection.permanent_id != collection_id:
            continue
        if "event_rule" in criteria_set:
            fields.append(oCollection.event_date_field.get_full_database_field_name())
            if oCollection.event_end_date_field:
                fields.append(oCollection.event_end_date_field.get_full_database_field_name())
        if check_criteria_set_has_custom_count_rule(criteria_set) and not criteria_set.get("list"):
            fields.append("{}._id".format(oCollection.name))
        for entry in criteria_set.get("list", []):
            if "entry_type" in entry and entry["entry_type"] == "or_group":
                for subentry in entry.get("list", []):
                    oConcept = models.Concept.objects.get(permanent_id=subentry["concept_id"])
                    fields.append(oConcept.get_full_database_field_name())
                    if oConcept.concept_for_prefilter:
                        fields.append(
                            oConcept.concept_for_prefilter.get_full_database_field_name()
                        )
            else:
                oConcept = models.Concept.objects.get(permanent_id=entry["concept_id"])
                fields.append(oConcept.get_full_database_field_name())
                if oConcept.concept_for_prefilter:
                    fields.append(oConcept.concept_for_prefilter.get_full_database_field_name())
        if len(fields) != field_count or field_count == 0:
            if not oCollection.is_root_collection:
                fields.append("{}._id".format(oCollection.name))
    return list(set(fields))


def _stack_list(flat_list):
    # takes a flattened list and turns it back into a stacked list
    new_list = []
    current_or_group = []
    current_or_group_id = None
    for i, record in enumerate(flat_list):
        if record["or_group_id"] is None:
            if current_or_group_id:
                new_list.append(
                    {
                        "entry_type": "or_group",
                        "entry_id": current_or_group_id,
                        "list": current_or_group,
                    }
                )
                current_or_group_id = None
                current_or_group = []
            new_list.append(record["entry"])
        elif record["or_group_id"] == current_or_group_id:
            current_or_group.append(record["entry"])
        else:  # or_group_id exists and is different from current_or_group_id
            if current_or_group_id:
                new_list.append(
                    {
                        "entry_type": "or_group",
                        "entry_id": current_or_group_id,
                        "list": current_or_group,
                    }
                )
                current_or_group_id = None
                current_or_group = []
            j = i + 1
            # k = i+2
            if j < len(flat_list) and record["or_group_id"] == flat_list[j]["or_group_id"]:
                current_or_group_id = record["or_group_id"]
                current_or_group = [record["entry"]]
            else:
                new_list.append(record["entry"])
    if current_or_group_id is not None:
        new_list.append(
            {"entry_type": "or_group", "entry_id": current_or_group_id, "list": current_or_group}
        )
    return new_list


def _flatten_list(criteria_set):
    flat_list = OrderedDict()
    for entry in criteria_set["list"]:
        if "entry_type" in entry and entry["entry_type"] == "or_group":
            for subentry in entry["list"]:
                flat_list[subentry["entry_id"]] = {
                    "or_group_id": entry["entry_id"],
                    "entry": subentry,
                }
        else:
            flat_list[entry["entry_id"]] = {
                "or_group_id": None,
                "entry": entry,
            }
    return flat_list


def change_to_boolean_and(cohort_def, entry_id):
    criteria_set = get_criteria_set_for_cohort_entry(cohort_def, entry_id)
    flat_list = _flatten_list(criteria_set)
    or_group_id = flat_list[entry_id]["or_group_id"]
    or_group_entry = lookup_cohort_def_entry(cohort_def, or_group_id)
    # print(or_group_entry)
    group1 = []
    group2 = []
    split_entry_reached = False
    for entry in or_group_entry["list"]:
        if not split_entry_reached:
            group1.append(entry["entry_id"])
        else:
            group2.append(entry["entry_id"])
        if entry["entry_id"] == entry_id:
            split_entry_reached = True
    # print(group1)
    # print(group2)
    if len(group1) < 2:
        for entry_id in group1:
            flat_list[entry_id]["or_group_id"] = None
    if len(group2) < 2:
        for entry_id in group2:
            flat_list[entry_id]["or_group_id"] = None
    else:
        new_or_group_id = "ttttttt"
        for entry_id in group2:
            flat_list[entry_id]["or_group_id"] = new_or_group_id

    different_format_flat_list = []
    for entry_id in flat_list:
        different_format_flat_list.append(flat_list[entry_id])

    criteria_set["list"] = _stack_list(different_format_flat_list)
    return cohort_def


def change_to_boolean_or(cohort_def, entry_id):
    criteria_set = get_criteria_set_for_cohort_entry(cohort_def, entry_id)
    flat_list = _flatten_list(criteria_set)
    entry_found = False
    key2 = None
    key1 = None
    for key in flat_list.keys():
        if entry_found:
            key2 = key
            break
        if key == entry_id:
            key1 = key
            entry_found = True
    # if neither in or group, create new or group
    if flat_list[key1]["or_group_id"] is None and flat_list[key2]["or_group_id"] is None:
        new_entry_id = "".join(
            random.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits)
            for _ in range(12)
        )
        flat_list[key1]["or_group_id"] = new_entry_id
        flat_list[key2]["or_group_id"] = new_entry_id
    # if one in or group, merge other into that group
    elif flat_list[key1]["or_group_id"] and flat_list[key2]["or_group_id"] is None:
        flat_list[key2]["or_group_id"] = flat_list[key1]["or_group_id"]
    elif flat_list[key2]["or_group_id"] and flat_list[key1]["or_group_id"] is None:
        flat_list[key1]["or_group_id"] = flat_list[key2]["or_group_id"]
    # if both in separate or groups, merge or groups together
    elif (
        flat_list[key1]["or_group_id"]
        and flat_list[key2]["or_group_id"]
        and flat_list[key1]["or_group_id"] != flat_list[key2]["or_group_id"]
    ):
        for key, record in flat_list.items():
            if record["or_group_id"] == flat_list[key2]["or_group_id"]:
                record["or_group_id"] = flat_list[key1]["or_group_id"]

    different_format_flat_list = []
    for entry_id in flat_list:
        different_format_flat_list.append(flat_list[entry_id])

    criteria_set["list"] = _stack_list(different_format_flat_list)
    return cohort_def


def find_first_criteria_set_with_collection_id(cohort_def, collection_id):
    for idx, criteria_set in enumerate(cohort_def):
        if (
            criteria_set["entry_type"] == "criteria_set"
            and criteria_set["collection_id"] == collection_id
        ):
            return idx
    return None


def get_all_criteria_set_ids_for_collection_id(cohort_def, collection_id):
    criteria_set_ids = []
    for criteria_set in cohort_def:
        if (
            criteria_set["entry_type"] == "criteria_set"
            and criteria_set["collection_id"] == collection_id
        ):
            criteria_set_ids.append(criteria_set["entry_id"])
    return criteria_set_ids


def get_all_criteria_set_options_for_collection_id(cohort_def, user, collection_id):
    extended_cohort_def = clean_cohort_def(cohort_def, user, include_metadata=True)[
        "extended_cohort_def"
    ]
    options = {}
    for criteria_set in extended_cohort_def:
        if (
            criteria_set["entry_type"] == "criteria_set"
            and criteria_set["collection_id"] == collection_id
        ):
            options[criteria_set["entry_id"]] = criteria_set.get("criteria_set_name")
    return options


def edit_concept_entry_in_cohort_def(cohort_def, entry_id, new_concept_entry):
    _find_and_edit_concept_entry(cohort_def, entry_id, new_concept_entry)
    return cohort_def


def _find_and_edit_concept_entry(cohort_def, entry_id, new_concept_entry):
    for i, criteria_set in enumerate(cohort_def):
        if "entry_id" in criteria_set and criteria_set["entry_id"] == entry_id:
            cohort_def[i] = new_concept_entry
            return True
        if "list" in criteria_set:
            child_obj = _find_and_edit_concept_entry(
                criteria_set["list"], entry_id, new_concept_entry
            )
            if child_obj:
                return True
    return False


def append_concept_entry_to_cohort_def(chironuser, cohort_def, concept_entry):
    oConcept = models.Concept.objects.get(
        collection__dataset=chironuser.dataset, permanent_id=concept_entry["concept_id"]
    )
    collection_name = oConcept.collection.permanent_id
    oCollection = models.Collection.objects.get(
        dataset=chironuser.dataset, permanent_id=collection_name
    )
    collection_idx = find_first_criteria_set_with_collection_id(cohort_def, collection_name)
    if collection_idx is not None:
        collection_entry = cohort_def[collection_idx]
    else:
        collection_entry = {
            "entry_type": "criteria_set",
            "entry_id": "".join(
                random.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits)
                for _ in range(12)
            ),
            "collection_id": collection_name,
            "list": [],
        }
        if oCollection.is_root_collection:
            cohort_def.insert(0, collection_entry)
        else:
            cohort_def.append(collection_entry)
    collection_entry["list"].append(concept_entry)
    return cohort_def


def append_criteria_set_to_cohort_def(cohort_def, oCollection):
    criteria_set = {
        "entry_type": "criteria_set",
        "entry_id": "".join(
            random.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits)
            for _ in range(12)
        ),
        "collection_id": oCollection.permanent_id,
        "list": [],
    }
    if oCollection.is_root_collection:
        cohort_def.insert(0, criteria_set)
    else:
        cohort_def.append(criteria_set)
    return cohort_def


def describe_cohort_def(extended_cohort_def):
    response = []
    for criteria_set in extended_cohort_def:
        event_name_str = ""
        if criteria_set.get("referenced_by_other_event", False):
            event_name_str = "({}) ".format(criteria_set.get("criteria_set_name"))
        line = criteria_set.get("label", "")
        # if no criteria rules, remove the word "where"
        if (
            not criteria_set.get("event_rule_label")
            or criteria_set["event_rule_label"] == "any date"
        ):
            if not criteria_set.get("entries", []):
                line = line.replace(" where:", "")

        response.append(event_name_str + line)
        if criteria_set.get("event_rule_label") and criteria_set["event_rule_label"] != "any date":
            response.append("- " + criteria_set["event_rule_label"])
        for cd_entry in criteria_set.get("entries", []):
            if cd_entry.get("entry_type") == "or_group":
                or_entries = []
                for or_entry in cd_entry["entries"]:
                    line = "({})".format(or_entry.get("label", ""))
                    or_entries.append(line)
                or_entries_str = " OR ".join(or_entries)
                response.append("- " + or_entries_str)
            else:
                response.append("- " + cd_entry.get("label", ""))
        response.append("")
    return "<br>".join(response)

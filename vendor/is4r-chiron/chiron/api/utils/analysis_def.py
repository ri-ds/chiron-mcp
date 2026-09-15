import copy
import random
import string

from chiron import query_definition as qdef


def apply_transformation_add_entry(chironuser, input_analysis_def, transformation):
    """
    Add or edit an entry on the analysis definition.

    :type: "add_entry"
    :concept_id: (str) the permanent_id of the Concept to add
    :def_component: (str, default="row") "rows" or "cols"
    :index: (int/None, default=None) index position to add to, if None then appends to end
    """
    concept_id = transformation.get("concept_id")
    role = transformation.get("role", "rows")
    index = transformation.get("index", None)
    if concept_id in qdef.get_analysis_def_concept_ids(input_analysis_def):
        return {
            "transformation_successful": False,
            "analysis_def": input_analysis_def,
            "transformation_errors": ["concepts can't be used multiple times"],
        }
    entry = {"entry_id": _generate_entry_id(), "concept_id": concept_id}
    if role not in input_analysis_def:
        input_analysis_def[role] = [entry]
    else:
        if index:
            input_analysis_def[role].insert(index, entry)
        else:
            input_analysis_def[role].append(entry)
    return {
        "transformation_successful": True,
        "analysis_def": input_analysis_def,
        "transformation_errors": [],
    }


def _generate_entry_id():
    return "".join(
        random.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits)
        for _ in range(12)
    )


def apply_transformation_move_entry(chironuser, input_analysis_def, transformation):
    """
    Move an entry from one role to another or change index position within the same role

    :type: "move_entry"
    :entry_id: The entry_id of the analysis def entry to remove
    :role: (str) "row" or "col"
    :index: (int/None, default=None) index position to add to, if None then appends to end
    """
    entry_id = transformation.get("entry_id")
    role = transformation.get("role")
    index = transformation.get("index")
    if entry_id is None or index is None or role is None:
        return {
            "transformation_successful": False,
            "analysis_def": input_analysis_def,
            "transformation_errors": ["Missing required args (entry_id, index, and role)"],
        }
    entry = copy.deepcopy(qdef.get_analysis_def_entry(input_analysis_def, entry_id))
    output_analysis_def = qdef.delete_analysis_def_entry(input_analysis_def, entry_id)
    output_analysis_def[role].insert(index, entry)
    # Return new Table Definition
    return {
        "transformation_successful": True,
        "analysis_def": output_analysis_def,
    }


def apply_transformation_swap_rows_and_cols(chironuser, input_analysis_def, transformation):
    """
    Switches rows and column roles.

    :type: "swap_rows_and_cols"
    """
    output_analysis_def = {
        "rows": input_analysis_def.get("cols", []),
        "cols": input_analysis_def.get("rows", []),
    }
    # Return results
    return {
        "transformation_successful": True,
        "analysis_def": output_analysis_def,
    }


def apply_transformation_clear_all(chironuser, input_analysis_def, transformation):
    """
    Creates empty analysis def

    :type: "clear_all"
    """
    output_analysis_def = {
        "rows": [],
        "cols": [],
    }
    # Return results
    return {
        "transformation_successful": True,
        "analysis_def": output_analysis_def,
    }


def apply_transformation_delete_entry(chironuser, input_analysis_def, transformation):
    """
    Deletes an entry from the analysis def with the provided entry_id.

    :type: "delete_entry"
    :entry_id: The entry_id of the table def entry to remove
    """
    entry_id = transformation["entry_id"]
    output_analysis_def = qdef.delete_analysis_def_entry(input_analysis_def, entry_id)

    return {
        "transformation_successful": True,
        "analysis_def": output_analysis_def,
    }


transformation_function_lookup = {
    "add_entry": apply_transformation_add_entry,
    "move_entry": apply_transformation_move_entry,
    "delete_entry": apply_transformation_delete_entry,
    "clear_all": apply_transformation_clear_all,
    # "edit_entry": apply_transformation_edit_entry,
    "swap_rows_and_cols": apply_transformation_swap_rows_and_cols,
}

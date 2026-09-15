import copy

from chiron.models import Concept, AnalysisDefSnapshot


def set_active_analysis_def(request, analysis_def):
    oSnapshot = AnalysisDefSnapshot(chironuser=request.chironuser)
    oSnapshot.set_analysis_def(analysis_def)
    oSnapshot.save()
    return oSnapshot


def get_active_analysis_def(request):
    analysis_def = AnalysisDefSnapshot.get_active_analysis_def(request.chironuser)
    return analysis_def


def clean_active_analysis_def(chironuser, include_metadata=False):
    """
    Wrapper for clean_analysis_def()
    """
    analysis_def = AnalysisDefSnapshot.get_active_analysis_def(chironuser)
    return clean_analysis_def(analysis_def, chironuser, include_metadata)


def clean_analysis_def(analysis_def, chironuser, include_metadata=False):
    """

    This function runs both and merges the results together
    """
    if include_metadata:
        new_analysis_def = analysis_def

        extended_analysis_def = {
            "rows": [],
            "cols": [],
        }

        for role in ["rows", "cols"]:
            for entry in analysis_def.get(role, []):
                out_row = copy.deepcopy(entry)
                oConcept = Concept.objects.filter(permanent_id=entry["concept_id"]).first()
                if oConcept:
                    out_row["label"] = oConcept.name
                    extended_analysis_def[role].append(out_row)
                else:
                    analysis_def[role].remove(entry)

        warnings = []
        errors = []
        return {
            "analysis_def": new_analysis_def,
            "extended_analysis_def": extended_analysis_def,
            "warnings": warnings,
            "errors": errors,
        }
    else:
        new_analysis_def = analysis_def
        return new_analysis_def


def get_analysis_def_concept_ids(analysis_def):
    """
    Returns a list of concept_ids associated with a table def.
    """
    concept_ids = []
    if "rows" in analysis_def:
        for entry in analysis_def["rows"]:
            concept_ids.append(entry["concept_id"])
    if "cols" in analysis_def:
        for entry in analysis_def["cols"]:
            concept_ids.append(entry["concept_id"])
    return list(set(concept_ids))


def get_relevant_concepts_for_analysis_def(table_def):
    concept_ids = get_analysis_def_concept_ids(table_def)
    concepts = []
    for concept_id in concept_ids:
        oConcept = Concept.objects.get(permanent_id=concept_id)
        concepts.append(oConcept)
    return concepts


# def add_analysis_def_entry(analysis_def, ):
#     if existing_entry_id:
#         index = next(
#             (
#                 i
#                 for i, item in enumerate(table_def["fields"])
#                 if item["entry_id"] == existing_entry_id
#             ),
#             None,
#         )
#         if index is not None:
#             table_def["fields"][index] = td_entry
#             return table_def
#     if position == "append":
#         table_def["fields"].append(td_entry)
#     else:
#         table_def["fields"].insert(0, td_entry)
#     return table_def


def get_analysis_def_entry(analysis_def, entry_id):
    for entry in analysis_def.get("rows", []):
        if entry["entry_id"] == entry_id:
            return entry
    for entry in analysis_def.get("cols", []):
        if entry["entry_id"] == entry_id:
            return entry
    return None


def delete_analysis_def_entry(analysis_def, entry_id):
    new_analysis_def = {
        "rows": [],
        "cols": [],
    }
    for entry in analysis_def.get("rows", []):
        if entry["entry_id"] != entry_id:
            new_analysis_def["rows"].append(entry)
    for entry in analysis_def.get("cols", []):
        if entry["entry_id"] != entry_id:
            new_analysis_def["cols"].append(entry)
    return new_analysis_def


# def resort_table_def(table_def, entry_ids):
#     new_fields = []
#     for entry_id in entry_ids:
#         for td_entry in table_def["fields"]:
#             if td_entry["entry_id"] == entry_id:
#                 new_fields.append(td_entry)
#     new_table_def = copy.deepcopy(table_def)
#     new_table_def["fields"] = new_fields
#     return new_table_def

import copy

from chiron.models import Concept
from chiron.query_definition import table_def_functions as tdfuncs
from chiron.query_definition import cohort_def_functions as cdfuncs


class Table:
    """
    Represents a table of subject data, like a report or a dataset in the results view.
    """

    def __init__(self, chironuser, cohort_def=None, table_def=None):
        if cohort_def is None:
            cohort_def = cdfuncs.clean_active_cohort_def(chironuser, include_metadata=False)
        if table_def is None:
            td_info = tdfuncs.clean_active_table_def(chironuser, include_metadata=True)
        else:
            td_info = tdfuncs.clean_table_def(
                cohort_def, table_def, chironuser, include_metadata=True
            )
        self.chironuser = chironuser
        self.table_def = td_info["table_def"]
        self.extended_table_def = td_info["extended_table_def"]
        self.errors = td_info["errors"]
        self.warnings = td_info["warnings"]
        self.internal_table_def = self.create_internal_table_def()

    def create_internal_table_def(self):
        """
        The internal table def has some additional objects stored with each field.
        It can't be converted to JSON
        """
        if self.table_def is None:
            return None
        internal_table_def = copy.deepcopy(self.extended_table_def)
        if "fields" not in internal_table_def:
            internal_table_def["fields"] = []
        for td_entry in internal_table_def["fields"]:
            oConcept = Concept.objects.filter(permanent_id=td_entry["concept_id"]).first()
            if oConcept:
                td_entry["concept"] = oConcept if oConcept else None
                display_processor = oConcept.get_display_processor(
                    self.chironuser, td_entry=td_entry
                )
                td_entry["processor"] = display_processor
            else:
                td_entry["concept"] = None
                td_entry["processor"] = None
        return internal_table_def

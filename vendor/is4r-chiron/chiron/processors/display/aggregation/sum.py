from ._base import AggregationMethod

from chiron import helpers


class Sum(AggregationMethod):
    """
    Calculate sum value of a set of numbers.
    """

    def __init__(self, id="sum", label="sum", group="aggregate"):
        super().__init__(id, label, group)

    def get_header_display_value(self, oConcept, td_entry):
        return "{} (sum)".format(oConcept.name)

    def get_display_value3(self, td_entry, value, default_value_method, output_type):
        return default_value_method(value, output_type)

    def calculate_agg_value(self, td_entry, value, display_processor_sort_value_func=None):
        concept_id = td_entry["concept_id"]
        if not value:
            return None
        value = self._merge_duplicates_for_different_subjects(concept_id, value)
        value = self._get_value_list_no_nulls(concept_id, value)
        if not value:
            return None
        return helpers.round_sig_3(sum(value), round_whole_number=False)

    def get_sort_key(self, value):
        val = value[self.column_index]
        response = []
        if val is None or len(val) == 0:
            response.append(self.display_processor_sort_value_func(None))
        else:
            if self.reverse:
                val = reversed(val)
            for entry in val:
                response.append(self.display_processor_sort_value_func(entry))
        return response

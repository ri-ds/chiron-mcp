from statistics import stdev

from ._base import AggregationMethod


class StdDev(AggregationMethod):
    """
    Calculate the standard deviation of a set of numbers
    """

    def __init__(self, id="std_dev", label="standard deviation", group="aggregate"):
        super().__init__(id, label, group)

    def get_header_display_value(self, oConcept, td_entry):
        return "{} (std dev)".format(oConcept.name)

    def get_display_value3(self, td_entry, value, default_value_method, output_type):
        return default_value_method(value, output_type)

    def calculate_agg_value(self, td_entry, value, display_processor_sort_value_func=None):
        concept_id = td_entry["concept_id"]
        if not value:
            return None
        value = self._merge_duplicates_for_different_subjects(concept_id, value)
        value = [x[concept_id] for x in value if x.get(concept_id) is not None]
        if len(value) < 2:
            return None
        return round(stdev(value), 2)

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

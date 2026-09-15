from ._base import AggregationMethod


class CountAll(AggregationMethod):
    """
    Count all non-null values, including duplicates.
    """

    def __init__(self, id="count_all", label="count all", group="aggregate"):
        super().__init__(id, label, group)

    def get_header_display_value(self, oConcept, td_entry):
        return "{} (count all)".format(oConcept.name)

    def get_display_value3(self, td_entry, value, default_value_method, output_type):
        if output_type == "html":
            return str(value)
        return value

    def calculate_agg_value(self, td_entry, value, display_processor_sort_value_func=None):
        if not value:
            return 0
        concept_id = td_entry["concept_id"]
        value = self._remove_records_with_null_values(concept_id, value)
        value = self._merge_duplicates_for_different_subjects(concept_id, value)
        return len(value)

from ._base import AggregationMethod


class CountDistinct(AggregationMethod):
    """
    Count distinct non-null values
    """

    def __init__(self, id="count_distinct", label="count distinct", group="aggregate"):
        super().__init__(id, label, group)

    def get_header_display_value(self, oConcept, td_entry):
        return "{} (count distinct)".format(oConcept.name)

    def get_display_value3(self, td_entry, value, default_value_method, output_type):
        if output_type == "html":
            return str(value)
        return value

    def calculate_agg_value(self, td_entry, value, display_processor_sort_value_func=None):
        concept_id = td_entry["concept_id"]
        value = self._get_value_list_no_nulls(concept_id, value)
        try:
            response = list(set(value))
        except TypeError:
            response = []
            for val in value:
                if val not in response:
                    response.append(val)
        return len(response)

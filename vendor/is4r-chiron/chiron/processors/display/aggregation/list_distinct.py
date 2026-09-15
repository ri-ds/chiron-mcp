from ._base import AggregationMethod
from chiron import chiron_settings


class ListDistinct(AggregationMethod):
    """
    List distinct values in same cell as semicolon-separated string.
    """

    def __init__(self, id="list_distinct", label="list distinct", group="list"):
        super().__init__(id, label, group)

    def get_header_display_value(self, oConcept, td_entry):
        return "{} (list distinct)".format(oConcept.name)

    def get_display_value3(self, td_entry, value, default_value_method, output_type):
        # value will be a list
        if not value:
            return ""
        if len(value) == 1:
            return default_value_method(value[0], output_type)
        out_values = []
        response = []
        for val in value:
            if val not in response:
                response.append(val)
        value = response

        for single_value in value:
            out_values.append(default_value_method(single_value, output_type))
        if output_type in ["html", "csv"]:
            return chiron_settings.CHIRON_AGG_DELIMITER.join([str(x) for x in out_values])
        return [x for x in out_values]

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
        if not response:
            return None
        if display_processor_sort_value_func:
            response = sorted(response, key=display_processor_sort_value_func)
        else:
            response = sorted(response)
        return response

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

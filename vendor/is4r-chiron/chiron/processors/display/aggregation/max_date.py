from ._base import AggregationMethod


class MaxDate(AggregationMethod):
    """
    Aggregate a date by getting maximum value only (i.e. the latest date)
    """

    def __init__(self, id="max_date", label="latest", group="aggregate"):
        super().__init__(id, label, group)

    def get_header_display_value(self, oConcept, td_entry):
        max_ordinal = td_entry.get("aggregation_settings", {}).get("max_date_ordinal_position", 1)
        if max_ordinal == 1:
            return "{} (latest)".format(oConcept.name)
        return "{} ({} latest)".format(oConcept.name, self._get_ordinal_string(max_ordinal))

    def get_display_value3(self, td_entry, value, default_value_method, output_type):
        return default_value_method(value, output_type)

    def get_inputs(self, chironuser, td_entry):
        options = [(1, "latest date (default)")]
        for n in range(2, 21):
            ord = self._get_ordinal_string(n)
            options.append((n, "{} latest date".format(ord)))
        inputs = [
            {
                "id": "max_date_ordinal_position",
                "label": "select specific ordinal position",
                "type": "select",
                "selected": td_entry.get("aggregation_settings", {}).get(
                    "max_date_ordinal_position", 1
                ),
                "options": options,
            }
        ]
        return inputs

    def set_custom_settings(self, input_data):
        pos = int(input_data.get("max_date_ordinal_position", "1"))
        return {
            "max_date_ordinal_position": pos,
        }

    def calculate_agg_value(self, td_entry, value, display_processor_sort_value_func=None):
        max_ordinal = td_entry.get("aggregation_settings", {}).get("max_date_ordinal_position", 1)
        if not value:
            return None
        concept_id = td_entry["concept_id"]
        value = self._merge_duplicates_for_different_subjects(concept_id, value)
        value = self._get_value_list_no_nulls(concept_id, value)
        if len(value) < max_ordinal:
            return None
        if display_processor_sort_value_func:
            value = sorted(value, key=display_processor_sort_value_func, reverse=True)
        else:
            value = sorted(value, reverse=True)
        return value[max_ordinal - 1]

    def get_sort_key(self, value):
        return self.display_processor_sort_value_func(value[self.column_index])

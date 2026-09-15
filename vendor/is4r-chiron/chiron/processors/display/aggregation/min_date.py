from ._base import AggregationMethod


class MinDate(AggregationMethod):
    """
    Aggregate a date by getting minimum value only (i.e. the earliest date)
    """

    def __init__(self, id="min_date", label="earliest", group="aggregate"):
        super().__init__(id, label, group)

    def get_header_display_value(self, oConcept, td_entry):
        min_ordinal = td_entry.get("aggregation_settings", {}).get("min_date_ordinal_position", 1)
        if min_ordinal == 1:
            return "{} (earliest)".format(oConcept.name)
        return "{} ({} earliest)".format(oConcept.name, self._get_ordinal_string(min_ordinal))

    def get_display_value3(self, td_entry, value, default_value_method, output_type):
        return default_value_method(value, output_type)

    def get_inputs(self, chironuser, td_entry):
        options = [(1, "earliest date (default)")]
        for n in range(2, 21):
            ord = self._get_ordinal_string(n)
            options.append((n, "{} earliest date".format(ord)))
        inputs = [
            {
                "id": "min_date_ordinal_position",
                "label": "select specific ordinal position",
                "type": "select",
                "selected": td_entry.get("aggregation_settings", {}).get(
                    "min_date_ordinal_position", 1
                ),
                "options": options,
            }
        ]
        return inputs

    def set_custom_settings(self, input_data):
        pos = int(input_data.get("min_date_ordinal_position", "1"))
        return {
            "min_date_ordinal_position": pos,
        }

    def calculate_agg_value(self, td_entry, value, display_processor_sort_value_func=None):
        max_ordinal = td_entry.get("aggregation_settings", {}).get("min_date_ordinal_position", 1)
        if not value:
            return None
        concept_id = td_entry["concept_id"]
        value = self._merge_duplicates_for_different_subjects(concept_id, value)
        value = self._get_value_list_no_nulls(concept_id, value)
        if len(value) < max_ordinal:
            return None
        if display_processor_sort_value_func:
            value = sorted(value, key=display_processor_sort_value_func)
        else:
            value = sorted(value)
        return value[max_ordinal - 1]

    def get_sort_key(self, value):
        return self.display_processor_sort_value_func(value[self.column_index])

from ._base import AggregationMethod


class Earliest(AggregationMethod):
    """
    Get the earliest value based on the event_date_field for the collection.
    """

    def __init__(self, id="earliest", label="earliest value", group="aggregate"):
        super().__init__(id, label, group)

    def get_header_display_value(self, oConcept, td_entry):
        position = td_entry.get("aggregation_settings", {}).get("earliest_ordinal_position", 1)
        if position == 1:
            return "{} (earliest)".format(oConcept.name)
        return "{} ({} earliest)".format(oConcept.name, self._get_ordinal_string(position))

    def check_requires_event_dates(self, td_entry):
        return True

    def get_display_value3(self, td_entry, value, default_value_method, output_type):
        return default_value_method(value, output_type)

    def get_inputs(self, chironuser, td_entry):
        options = [(1, "earliest value (default)")]
        for n in range(2, 21):
            ord = self._get_ordinal_string(n)
            options.append((n, "{} earliest value".format(ord)))
        inputs = [
            {
                "id": "earliest_ordinal_position",
                "label": "select specific ordinal position",
                "type": "select",
                "selected": td_entry.get("aggregation_settings", {}).get(
                    "earliest_ordinal_position", 1
                ),
                "options": options,
            }
        ]
        return inputs

    def set_custom_settings(self, input_data):
        position = int(input_data.get("earliest_ordinal_position", "1"))
        return {
            "earliest_ordinal_position": position,
        }

    def calculate_agg_value(self, td_entry, value, display_processor_sort_value_func=None):
        position = td_entry.get("aggregation_settings", {}).get("earliest_ordinal_position", 1)
        if not value:
            return None
        concept_id = td_entry["concept_id"]
        event_date_field = td_entry["collection"]["event_date_field"]
        value = self._merge_duplicates_for_different_subjects(concept_id, value)
        value = self._get_event_list(concept_id, event_date_field, value)
        if len(value) < position:
            return None
        value = sorted(value, key=lambda k: display_processor_sort_value_func(k[1]))
        value = sorted(value, key=lambda k: k[0])
        value = [x[1] for x in value]
        return value[position - 1]

    def get_sort_key(self, value):
        return self.display_processor_sort_value_func(value[self.column_index])

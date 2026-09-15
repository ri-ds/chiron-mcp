from ._base import AggregationMethod

import collections


class MostFrequent(AggregationMethod):
    """
    Can get for the most frequent value and how many times it occurred
    """

    def __init__(self, id="most_frequent", label="most frequent value", group="aggregate"):
        super().__init__(id, label, group)

    def get_header_display_value(self, oConcept, td_entry):
        position = td_entry.get("aggregation_settings", {}).get(
            "most_frequent_ordinal_position", 1
        )
        return_value = td_entry.get("aggregation_settings", {}).get(
            "most_frequent_return_value", "value"
        )
        if return_value == "value_and_count":
            return_value = "count/value"
        if position == 1:
            return "{} (most frequent {})".format(oConcept.name, return_value)
        return "{} ({} most frequent {})".format(
            oConcept.name, self._get_ordinal_string(position), return_value
        )

    def get_display_value3(self, td_entry, value, default_value_method, output_type):
        return_value = td_entry.get("aggregation_settings", {}).get(
            "most_frequent_return_value", "value"
        )
        if return_value == "value":
            return default_value_method(value, output_type)
        if return_value == "count":
            if output_type == "html":
                return str(value)
            return value  # should be integer
        if return_value == "value_and_count":
            return value
        return default_value_method(value, output_type)

    def get_inputs(self, chironuser, td_entry):
        options = [(1, "most frequent value (default)")]
        for n in range(2, 21):
            ord = self._get_ordinal_string(n)
            options.append((n, "{} most frequent value".format(ord)))
        inputs = [
            {
                "id": "most_frequent_ordinal_position",
                "label": "select specific ordinal position",
                "type": "select",
                "selected": td_entry.get("aggregation_settings", {}).get(
                    "most_frequent_ordinal_position", 1
                ),
                "options": options,
            },
            {
                "id": "most_frequent_return_value",
                "label": "return value",
                "type": "select",
                "selected": td_entry.get("aggregation_settings", {}).get(
                    "most_frequent_return_value", "value"
                ),
                "options": [
                    ("value", "Value"),
                    ("count", "Count (how many times does value occur)"),
                    ("value_and_count", "Count + Value"),
                ],
            },
        ]
        return inputs

    def set_custom_settings(self, input_data):
        position = int(input_data.get("most_frequent_ordinal_position", "1"))
        most_frequent_return_value = input_data.get("most_frequent_return_value", "value")
        return {
            "most_frequent_ordinal_position": position,
            "most_frequent_return_value": most_frequent_return_value,
        }

    def calculate_agg_value(self, td_entry, value, display_processor_sort_value_func=None):
        """ """
        concept_id = td_entry["concept_id"]
        position = td_entry.get("aggregation_settings", {}).get(
            "most_frequent_ordinal_position", 1
        )
        return_value = td_entry.get("aggregation_settings", {}).get(
            "most_frequent_return_value", "value"
        )
        if not value:
            return self._generate_null_response(return_value)
        concept_id = td_entry["concept_id"]
        value = self._merge_duplicates_for_different_subjects(concept_id, value)
        values = [x[concept_id] for x in value if concept_id in x]
        # sort first so that entries with the same frequency will be listed in order
        if display_processor_sort_value_func:
            values = sorted(values, key=display_processor_sort_value_func)
        else:
            values = sorted(values)
        counter = collections.Counter(values).most_common()
        if len(counter) < position:
            return self._generate_null_response(return_value)
        if return_value == "value":
            return counter[position - 1][0]
        if return_value == "count":
            return counter[position - 1][1]
        if return_value == "value_and_count":
            # return "({}) {}".format(counter[position - 1][1], counter[position - 1][0])
            return [counter[position - 1][0], counter[position - 1][1]]
        return None

    def _generate_null_response(self, return_value):
        if return_value == "count":
            return 0
        if return_value == "value_and_count":
            return ["", 0]
        return None

    def get_sort_key(self, value):
        return self.display_processor_sort_value_func(value[self.column_index])

import datetime

from ._base import AggregationMethod
from chiron import chiron_settings


class Min(AggregationMethod):
    """
    Aggregate by getting miniumum value only
    """

    def __init__(self, id="min", label="min value", group="aggregate"):
        super().__init__(id, label, group)

    def get_header_display_value(self, oConcept, td_entry):
        min_ordinal = td_entry.get("aggregation_settings", {}).get("min_ordinal_position", 1)
        if min_ordinal == 1:
            position = "min"
        else:
            position = self._get_ordinal_string(min_ordinal) + " lowest"
        labels = {
            "value": position,
            "count": "count {} occurrences".format(position),
            "earliest_date": "first date of {} value".format(position),
            "latest_date": "latest date of {} value".format(position),
            "all_dates": "all dates of {} value".format(position),
        }

        return_value = td_entry.get("aggregation_settings", {}).get("min_return_value", "value")
        return "{} ({})".format(oConcept.name, labels[return_value])

    def check_requires_event_dates(self, td_entry):
        return_value = td_entry.get("aggregation_settings", {}).get("min_return_value", "value")
        if return_value in ["earliest_date", "latest_date", "all_dates"]:
            return True
        return False

    def get_inputs(self, chironuser, td_entry):
        options = [(1, "min value (default)")]
        for n in range(2, 21):
            ord = self._get_ordinal_string(n)
            options.append((n, "{} lowest value".format(ord)))
        inputs = [
            {
                "id": "min_ordinal_position",
                "label": "select specific ordinal position",
                "type": "select",
                "selected": td_entry.get("aggregation_settings", {}).get(
                    "min_ordinal_position", 1
                ),
                "options": options,
            },
            {
                "id": "min_return_value",
                "label": "return value",
                "type": "select",
                "selected": td_entry.get("aggregation_settings", {}).get(
                    "min_return_value", "value"
                ),
                "options": [
                    ("value", "value"),
                    ("count", "Count (how many times does value occur)"),
                    ("earliest_date", "Date of first occurrence of value"),
                    ("latest_date", "Date of most recent occurrence of value"),
                    ("all_dates", "All dates where value occurred"),
                ],
            },
        ]
        return inputs

    def set_custom_settings(self, input_data):
        position = int(input_data.get("min_ordinal_position", "1"))
        min_return_value = input_data.get("min_return_value", "value")
        return {
            "min_ordinal_position": position,
            "min_return_value": min_return_value,
        }

    def get_display_value3(self, td_entry, value, default_value_method, output_type):
        if output_type == "python":
            return value
        return_value = td_entry.get("aggregation_settings", {}).get("min_return_value", "value")
        if return_value in ["all_dates"]:
            if output_type in ["html", "csv"]:
                return chiron_settings.CHIRON_AGG_DELIMITER.join(
                    [self._date_to_string(x) for x in value]
                )
            if len(value) == 1:
                return self._date_to_string(value[0])
            return [self._date_to_string(x) for x in value]
        if return_value in ["earliest_date", "latest_date"]:
            return self._date_to_string(value)
        if return_value == "value":
            return default_value_method(value, output_type)
        # return value == "count"
        if output_type == "html":
            return str(value)
        return value

    def calculate_agg_value(self, td_entry, value, display_processor_sort_value_func=None):
        min_ordinal = td_entry.get("aggregation_settings", {}).get("min_ordinal_position", 1)
        return_value = td_entry.get("aggregation_settings", {}).get("min_return_value", "value")
        concept_id = td_entry["concept_id"]
        value = self._merge_duplicates_for_different_subjects(concept_id, value)
        if return_value == "value":
            if not value:
                return None
            value = self._get_value_list_no_nulls(concept_id, value)
            if len(value) < min_ordinal:
                return None
            if display_processor_sort_value_func:
                value = sorted(value, key=display_processor_sort_value_func)
            else:
                value = sorted(value)
            return value[min_ordinal - 1]
        if return_value == "count":
            if not value:
                return 0
            value = self._get_value_list_no_nulls(concept_id, value)
            if len(value) < min_ordinal:
                return 0
            if display_processor_sort_value_func:
                value = sorted(value, key=display_processor_sort_value_func)
            else:
                value = sorted(value)
            min_value = value[min_ordinal - 1]
            return value.count(min_value)
        else:
            if not value:
                return None
            value1 = self._get_value_list_no_nulls(concept_id, value)
            if len(value1) < min_ordinal:
                return None
            if display_processor_sort_value_func:
                value1 = sorted(value1, key=display_processor_sort_value_func)
            else:
                value1 = sorted(value1)
            value1 = value1[min_ordinal - 1]
            event_date_field = td_entry["collection"]["event_date_field"]
            value2 = self._get_event_list(concept_id, event_date_field, value)
            value2 = [x[0] for x in value2 if x[1] == value1]
            value2.sort()
            if not value2:
                return None
            if return_value == "all_dates":
                return value2
            elif return_value == "earliest_date":
                return value2[0]
            elif return_value == "latest_date":
                return value2[-1]
        # the code should never reach this point
        return None

    def get_sort_key_function(
        self, display_processor_sort_value_func, column_index, reverse, aggregation_settings
    ):
        self.column_index = column_index
        self.display_processor_sort_value_func = display_processor_sort_value_func
        self.reverse = reverse
        self.aggregation_settings = aggregation_settings
        return_value = self.aggregation_settings.get("min_return_value", "value")
        if return_value in ["all_dates"]:
            return self.get_sort_key_date_list
        if return_value in ["earliest_date", "latest_date"]:
            return self.get_sort_key_date
        if return_value == "value":
            return self.get_sort_key_from_display_processor
        return self.get_sort_key

    def get_sort_key_from_display_processor(self, value):
        return self.display_processor_sort_value_func(value[self.column_index])

    def get_sort_key_date_list(self, value):
        val = value[self.column_index]
        response = []
        if val is None or len(val) == 0:
            response.append(self._get_sort_key_date(None))
        else:
            if self.reverse:
                val = reversed(val)
            for entry in val:
                response.append(self._get_sort_key_date(entry))
        return response

    def _get_sort_key_date(self, value):
        """
        This can be used to sort date values
        """
        if value is None:
            return datetime.datetime(datetime.MINYEAR, 1, 1)
        return value

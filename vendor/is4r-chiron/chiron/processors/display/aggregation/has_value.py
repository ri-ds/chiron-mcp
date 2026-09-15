import datetime
from collections import Counter

from ._base import AggregationMethod

from chiron.models import Concept
from chiron.query_engine import get_stattool
from chiron import chiron_settings


class HasValue(AggregationMethod):
    """
    Check for the existence of a value in the list. This can return a boolean
    result, a count of the number of matches, the date of the first or last
    match (based on the event_date_field for the collection), or all dates
    where this value occurred (again based on the event_date_field).
    """

    def __init__(self, id="has_value", label="has value", group="aggregate"):
        super().__init__(id, label, group)

    def get_header_display_value(self, oConcept, td_entry):
        labels = {
            "boolean": "has value",
            "count": "count",
            "earliest_date": "first occurrence date",
            "latest_date": "latest occurrence date",
            "all_dates": "all occurrence dates",
        }
        values = td_entry.get("aggregation_settings", {}).get("values", [])
        first_value = values[0] if values else ""
        addl_values = len(values) - 1
        if addl_values < 1:
            value_str = '"{}"'.format(first_value)
        else:
            value_str = '"{}" + {} more'.format(first_value, addl_values)
        return_value = td_entry.get("aggregation_settings", {}).get("return_value", "boolean")

        if return_value == "boolean":
            return "{} has value {}".format(oConcept.name, value_str)
        return "{} has value {} ({})".format(oConcept.name, value_str, labels[return_value])

    def check_requires_event_dates(self, td_entry):
        return_value = td_entry.get("aggregation_settings", {}).get("return_value", "boolean")
        if return_value in ["earliest_date", "latest_date", "all_dates"]:
            return True
        return False

    def get_inputs(self, chironuser, td_entry):
        concept_id = td_entry["concept_id"]
        oConcept = Concept.objects.get(permanent_id=concept_id)
        stats = get_stattool(chironuser, {}, oConcept)
        values = stats.lookup_unique_values(1000)
        options = []
        for val in values:
            options.append((val, val))
        inputs = [
            {
                "id": "values",
                "label": "value(s)",
                "type": "multiselect",
                "selected": td_entry.get("aggregation_settings", {}).get("values", ""),
                "options": options,
            },
            {
                "id": "return_value",
                "label": "return value",
                "type": "select",
                "selected": td_entry.get("aggregation_settings", {}).get(
                    "return_value", "boolean"
                ),
                "options": [
                    ("boolean", "True/False"),
                    ("count", "Count (how many times does value occur)"),
                    # ("earliest_date", "Date of first occurrence of value"),
                    # ("latest_date", "Date of most recent occurrence of value"),
                    # ("all_dates", "All dates where value occurred"),
                ],
            },
        ]
        # TODO: If I want these for events based on age as integer, need to first deal with wording,
        #  return data type, etc.
        if chiron_settings.CHIRON_EVENT_CONCEPT_TYPE == "date":
            inputs[1]["options"].append(("earliest_date", "Date of first occurrence of value"))
            inputs[1]["options"].append(("latest_date", "Date of most recent occurrence of value"))
            inputs[1]["options"].append(("all_dates", "All dates where value occurred"))
        return inputs

    def set_custom_settings(self, input_data):
        values = input_data.get("values", [])
        return_value = input_data.get("return_value", "boolean")
        return {
            "values": values,
            "return_value": return_value,
        }

    def calculate_agg_value(self, td_entry, value, display_processor_sort_value_func=None):
        selected_values = td_entry.get("aggregation_settings", {}).get("values", [])
        return_value = td_entry.get("aggregation_settings", {}).get("return_value", "boolean")
        concept_id = td_entry["concept_id"]
        value = self._merge_duplicates_for_different_subjects(concept_id, value)
        if return_value == "boolean":
            if not value:
                return False
            value = self._get_value_list_no_nulls(concept_id, value)
            if any(x in value for x in selected_values):
                return True
            return False
        elif return_value == "count":
            if not value:
                return 0
            value = self._get_value_list_no_nulls(concept_id, value)
            total_count = sum(
                [count for key, count in Counter(value).items() if key in selected_values]
            )
            return total_count
        else:
            if not value:
                return [] if return_value == "all_dates" else None
            event_date_field = td_entry["collection"]["event_date_field"]
            value = self._get_event_list(concept_id, event_date_field, value)
            value = [x[0] for x in value if x[1] in selected_values]
            if not value:
                return [] if return_value == "all_dates" else None
            value = list(set(value))
            value.sort()
            if return_value == "all_dates":
                return value
            elif return_value == "earliest_date":
                return value[0]
            elif return_value == "latest_date":
                return value[-1]

        # the code should never reach this point
        return None

    def get_display_value3(self, td_entry, value, default_value_method, output_type):
        if output_type == "python":
            return value
        return_value = td_entry.get("aggregation_settings", {}).get("return_value", "boolean")
        if return_value == "count":
            if output_type == "html":
                return str(value)
            return value
        if return_value in ["all_dates"]:
            if not value:
                return None
            if output_type == "json":
                return [self._date_to_string(x) for x in value]
            return chiron_settings.CHIRON_AGG_DELIMITER.join(
                [self._date_to_string(x) for x in value]
            )
        if return_value in ["earliest_date", "latest_date"]:
            return self._date_to_string(value)
        # t/f response
        if output_type in ["html", "csv"]:
            return str(value)
        return value

    def get_sort_key_function(
        self, display_processor_sort_value_func, column_index, reverse, aggregation_settings
    ):
        self.column_index = column_index
        self.display_processor_sort_value_func = display_processor_sort_value_func
        self.reverse = reverse
        self.aggregation_settings = aggregation_settings
        return_value = self.aggregation_settings.get("return_value", "boolean")
        if return_value in ["all_dates"]:
            return self.get_sort_key_date_list
        if return_value in ["earliest_date", "latest_date"]:
            return self.get_sort_key_date
        return self.get_sort_key

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

from ._base import AggregationMethod

from chiron.models import Collection
from chiron import chiron_settings


class ListAll(AggregationMethod):
    """
    List all values (including repeats) in same cell as semicolon-separated string.
    """

    def __init__(self, id="list_all", label="list all", group="list"):
        super().__init__(id, label, group)

    def get_header_display_value(self, oConcept, td_entry):
        return "{} (list all)".format(oConcept.name)

    def check_requires_event_dates(self, td_entry):
        ordering = td_entry.get("aggregation_settings", {}).get("list_all_ordering", "value")
        if ordering == "event_date":
            return True
        return False

    def get_inputs(self, chironuser, td_entry):
        inputs = [
            {
                "id": "list_all_include_nulls",
                "label": "include null/missing values",
                "type": "select",
                "selected": td_entry.get("aggregation_settings", {}).get(
                    "list_all_include_nulls", "no"
                ),
                "options": [("no", "no"), ("yes", "yes")],
            }
        ]
        # allow chronological sort only if longitudinal collection
        oCollection = Collection.objects.get(concept__permanent_id=td_entry["concept_id"])
        if oCollection.event_date_field:
            inputs.append(
                {
                    "id": "list_all_ordering",
                    "label": "sort multiple values in the same cell by",
                    "type": "select",
                    "selected": td_entry.get("aggregation_settings", {}).get(
                        "list_all_ordering", "value"
                    ),
                    "options": [
                        ("value", "value lowest to highest"),
                        ("event_date", "chronologically"),
                    ],
                }
            )
        return inputs

    def set_custom_settings(self, input_data):
        include_nulls = input_data.get("list_all_include_nulls", "no")
        ordering = input_data.get("list_all_ordering", "value")
        return {
            "list_all_include_nulls": include_nulls,
            "list_all_ordering": ordering,
        }

    def get_display_value3(self, td_entry, value, default_value_method, output_type):
        # value will be a list
        if not value:
            if output_type in ["html", "csv"]:
                return ""
            return value
        if len(value) == 1:
            if value[0] is None or value[0] == "":
                if output_type in ["html", "csv"]:
                    return "null"
            return default_value_method(value[0], output_type)
        out_values = []
        for single_value in value:
            if single_value is None or single_value == "":
                if output_type in ["html", "csv"]:
                    out_values.append("null")
                else:
                    out_values.append(None)
            else:
                out_values.append(default_value_method(single_value, output_type))
        if output_type in ["html", "csv"]:
            return chiron_settings.CHIRON_AGG_DELIMITER.join([str(x) for x in out_values])
        return [x for x in out_values]

    def calculate_agg_value(self, td_entry, value, display_processor_sort_value_func=None):
        if not value:
            return None
        concept_id = td_entry["concept_id"]
        include_nulls = td_entry.get("aggregation_settings", {}).get(
            "list_all_include_nulls", "no"
        )
        ordering = td_entry.get("aggregation_settings", {}).get("list_all_ordering", "value")
        value = self._merge_duplicates_for_different_subjects(concept_id, value)
        if ordering == "value":
            if include_nulls == "no":
                value = self._get_value_list_no_nulls(concept_id, value)
            else:
                value = self._get_value_list(concept_id, value)
            if not value:
                return None
            # value = self._merge_duplicates(concept_id, value)
            if display_processor_sort_value_func:
                value = sorted(value, key=display_processor_sort_value_func)
            else:
                value = sorted(value)
        elif ordering == "event_date":
            event_date_field = td_entry["collection"]["event_date_field"]
            if include_nulls == "no":
                value = self._get_event_list_no_nulls(concept_id, event_date_field, value)
            else:
                value = self._get_event_list(concept_id, event_date_field, value)
            if not value:
                return None
            value = sorted(value, key=lambda k: display_processor_sort_value_func(k[1]))
            value = sorted(value, key=lambda k: k[0])
            value = [x[1] for x in value]
        return value

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

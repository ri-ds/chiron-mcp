import copy

from .text import DisplayText


def display_value_function_custom(value, output_type):
    if value and "value" in value:
        return str(value["value"])
    if value:
        return value
    if output_type in ["html", "csv"]:
        return ""
    return None


class DisplayTextCustomSort(DisplayText):
    """
    When to use:

    * Text field where you want the sorting to be different from alphabetical
    * good for numbers stored as strings, such as ID numbers

    This processor requires the value be stored as a dict with a string display value and a
    numeric sort value:

    .. code-block:: python

        {
            "value" : "my value",
            "sort" : 1
        }
    """

    def set_sort_keygen_function(self):
        self.sort_keygen_function = self._custom_sort_value_method

    def set_display_function(self):
        self.display_function = display_value_function_custom

    def set_aggregation_methods(self):
        super().set_aggregation_methods()

        self.concept_id = self.concept.permanent_id
        self.requires_text_value = ["most_frequent", "has_value_text"]

    def get_data_type(self):
        """
        Returns a human-readable string describing the data type (text, integer, etc.).
        """
        return "text"

    def calculate_aggregate_value(self, value):
        aggregation_method_id = self.td_entry.get(
            "aggregation_method", self.get_default_aggregation_settings()["aggregation_method"]
        )

        aggregation_class = self._get_agg_option_by_id(aggregation_method_id)
        if aggregation_method_id in self.requires_text_value:
            value = copy.deepcopy(value)
            for entry in value:
                if self.concept_id in entry:
                    entry[self.concept_id] = entry[self.concept_id].get("value")
        return aggregation_class.calculate_agg_value(
            self.td_entry, value, self.sort_keygen_function
        )

    def _custom_sort_value_method(self, value):
        # print("get sort value", value)
        if isinstance(value, tuple):
            value = dict(value)
        if isinstance(value, str):
            if self.args.get("sort_data_type", "string") == "number":
                return int(value)
            return value
        if self.args.get("sort_data_type", "string") == "number":
            # print("num")
            if value is None:
                return float("-inf")
            return value["sort"]
        else:
            if value is None:
                return ""
            return str(value["sort"])

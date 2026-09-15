import re
import copy
import decimal
import json

from django.contrib.humanize.templatetags.humanize import intcomma

from chiron.processors.abstract import DisplayProcessor
from chiron.processors.display import aggregation


def get_sort_keygen_value_custom(value):
    if not value:
        return []
    if isinstance(value, tuple):
        value = dict(value)
    mod_val = []
    for text in re.split(r"(\d+)", str(value["val"])):
        mod_val.append(int(text) if text.isdigit() else text.lower())
    return mod_val


def get_display_value_custom(value, output_type):
    if value is None:
        if output_type in ["html", "csv"]:
            return ""
        return None
    # for some aggregation options (ex. average) value will already be converted from a dict
    # to a number
    if isinstance(value, float) or isinstance(value, int) or isinstance(value, decimal.Decimal):
        return value
    if isinstance(value, str):
        value = json.loads(value)
    if "num" in value and value["num"] is not None:
        if output_type == "html":
            return intcomma(value["num"])
        return value["num"]
    if "txt" in value:
        return value["txt"]
    return str(value)


class DisplayNumberWithCategories(DisplayProcessor):
    """
    When to use:

    * All values should be numbers, strings or null.

    * When importing during ETL, need to set cast_to_type "integer/string" or "float/string" which
      will store number values in the research database as {"num": 5} and string values as
      {"txt": "my value"}

    Optional arguments:

    * is_integer: (default: False) set to True if the number has no decimal value.
      NOTE: This does not round/force numbers to be integers, it only affects how histograms
      and statistics are calculated/displayed.

    """

    def set_sort_keygen_function(self):
        self.sort_keygen_function = get_sort_keygen_value_custom

    def set_display_function(self):
        self.display_function = get_display_value_custom

    def set_aggregation_methods(self):
        self.aggregation_methods = [
            aggregation.ListDistinct(),
            aggregation.CountDistinct(),
            aggregation.ListAll(),
            aggregation.CountAll(),
            aggregation.Average(),
            aggregation.Median(),
            aggregation.StdDev(),
            aggregation.Min(),
            aggregation.Max(),
            aggregation.Sum(),
            aggregation.Earliest(),
            aggregation.Latest(),
        ]
        # will set some additional variables that are needed for calculating aggregate values
        self.numeric_aggregation_methods = [
            self.aggregation_methods[4],
            self.aggregation_methods[5],
            self.aggregation_methods[6],
            self.aggregation_methods[7],
            self.aggregation_methods[8],
            self.aggregation_methods[9],
        ]
        self.dict_to_number_methods = [
            self.aggregation_methods[4],
            self.aggregation_methods[5],
            self.aggregation_methods[6],
            self.aggregation_methods[9],
        ]
        self.concept_id = self.concept.permanent_id

    def get_data_type(self):
        """
        Returns a human-readable string describing the data type (text, integer, etc.).
        """
        return "number"

    def use_subvalue(self, td_entry):
        """Should a subvalue be used for this table def entry.

        Complex concepts can have 1 or more subvalues. If a subvalue should be queried in place
        of the normal concept value, returns the name of the subvalue, otherwise returns None.
        """
        agg_method = td_entry.get("aggregation_method", "")
        if agg_method in ["min", "max", "median", "average", "std_dev", "sum"]:
            return "num"
        return None

    def calculate_aggregate_value(self, value):
        aggregation_method_id = self.td_entry.get("aggregation_method", "count_all")
        aggregation_class = self._get_agg_option_by_id(aggregation_method_id)
        if aggregation_class in self.numeric_aggregation_methods:
            # some aggregation methods need only records with numbers
            new_value = [x for x in value if x.get(self.concept_id, {}).get("num") is not None]
            # some aggregation methods expect a number for the value instead of a dict
            # this might have bad performance
            if aggregation_class in self.dict_to_number_methods:
                new_value = copy.deepcopy(new_value)
                for entry in new_value:
                    entry[self.concept_id] = entry[self.concept_id]["num"]
            response = aggregation_class.calculate_agg_value(
                self.td_entry, new_value, self.sort_keygen_function
            )
        else:
            response = aggregation_class.calculate_agg_value(
                self.td_entry, value, self.sort_keygen_function
            )
        return response

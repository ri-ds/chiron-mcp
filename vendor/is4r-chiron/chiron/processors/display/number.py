from sqlalchemy import func, Numeric

from chiron.processors.abstract import DisplayProcessor
from chiron.processors.display import aggregation
from chiron.query_engine import get_stattool

from chiron.processors import sort_functions, display_functions


class DisplayNumber(DisplayProcessor):
    """
    When to use:

    * All values should either be numbers or null

    Optional arguments:

    * is_integer: (default: False) set to True if the number has no decimal value.
      NOTE: This does not round/force numbers to be integers, it only affects how histograms
      and statistics are calculated/displayed.

    """

    def set_sort_keygen_function(self):
        self.sort_keygen_function = sort_functions.sort_keygen_float

    def set_display_function(self):
        self.display_function = display_functions.display_float

    def map_to_value(self, value):
        """
        Changes a value to a category value
        """
        map_settings = self.get_map_settings()
        if value is None:
            return None
        if value and map_settings["method"] == "round":
            return int(round(value, 0))
        if value and map_settings["method"] == "round_tens":
            position = (map_settings["scale"] - 2) * -1
            bin_size = int("9" * (map_settings["scale"] - 2))
            bin_min = int(round(value, position))
            bin_max = bin_min + bin_size
            return "{} - {}".format(bin_min, bin_max)
        return value

    def get_map_settings(self):
        if self.map_settings is not None:
            return self.map_settings
        if self.td_entry and self.td_entry.get("categorize"):
            stats = get_stattool(self.chironuser, concept=self.concept)
            min = stats.get_min(output_type="python")
            max = stats.get_max(output_type="python")
            diff = max - min
            # the scale must be an integer; it will affect the bin size and
            # therefore number of categories created
            scale = len(str(int(diff * 3)))
            if scale > 2:
                self.map_settings = {
                    "method": "round_tens",
                    "scale": scale,
                    "sort_function": sort_functions.sort_keygen_natural,
                    "display_function": display_functions.display_string,
                }
            else:
                self.map_settings = {
                    "method": "round",
                    "sort_function": sort_functions.sort_keygen_float,
                    "display_function": display_functions.display_integer,
                }
        else:
            self.map_settings = {}
        return self.map_settings

    def sql_alchemy_map_in_query(self, column):
        """Map existing values to new values during a SQL alchemy query.

        If stored value needs to be converted to a different value (ex. round date to decade),
        this can define the Postgres function(s) for doing that.
        """
        map_settings = self.get_map_settings()
        if not map_settings:
            return column
        if map_settings["method"] == "round_tens":
            round_position = -1 * (map_settings["scale"] - 2)
            internal = func.cast(column, Numeric)
            new_column = func.round(internal, round_position)
        else:
            internal = func.cast(column, Numeric)
            new_column = func.round(internal, 0)
        return new_column

    def sql_alchemy_map_after_query(self, value):
        """Conversion of mapped SQL alchemy values to a final query result.

        Takes the output resulting fom sql_alchemy_map_in_query() and converts it to a final
        query result. For example, if you rounded dates to the decade, you might want to convert
        that to a category string (1960 -> "1960s", 1970 -> "1970s"). This behavior could
        technically be handled fully in Postgres using a "CASE WHEN" statement, but that won't
        always be the most performant approach. The output of this will still get processed by
        get_display_value() as the final, final step.
        """
        map_settings = self.get_map_settings()
        if not map_settings or value is None:
            return value
        if map_settings["method"] == "round_tens":
            bin_size = int("9" * (map_settings["scale"] - 2))
            return "{} - {}".format(int(value), int(value + bin_size))
        return value

    def set_aggregation_methods(self):
        self.aggregation_methods = [
            aggregation.ListDistinct(),
            aggregation.ListAll(),
            aggregation.Average(),
            aggregation.Median(),
            aggregation.StdDev(),
            aggregation.Min(),
            aggregation.Max(),
            aggregation.Sum(),
            aggregation.CountDistinct(),
            aggregation.CountAll(),
            aggregation.MostFrequent(),
        ]
        if self.concept.collection.event_date_field:
            self.aggregation_methods.append(aggregation.Latest())
            self.aggregation_methods.append(aggregation.Earliest())

    def get_data_type(self):
        """
        Returns a human-readable string describing the data type (text, integer, etc.).
        """
        return "number"

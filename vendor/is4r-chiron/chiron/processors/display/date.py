import datetime

from sqlalchemy import func

from chiron.processors.abstract import DisplayProcessor
from chiron.processors.display import aggregation
from chiron.query_engine import get_stattool

from chiron.processors import sort_functions, display_functions


def _display_as_string(value):
    if isinstance(value, str):
        return value[:10]
    try:
        response = value.strftime("%Y-%m-%d")
    except Exception:
        response = ""
    return response


def _display_as_python_date(value):
    if isinstance(value, str):
        try:
            return datetime.datetime.strptime(value, "%Y-%m-%d")
        except Exception:
            return None
    return value


def get_display_value_custom(value, output_type):
    """returns a value to be used in an output file
    output type could be 'html', 'csv', etc.
    available output types will likely expand over time
    """
    if output_type == "python":
        return _display_as_python_date(value)
    return _display_as_string(value)


class DisplayDate(DisplayProcessor):
    """
    When to use:

    * All values should either be a Python datetime object or null
    * You only care about the date component, typically you will want the time in your
      datetime values set to 0:00.

    """

    def set_sort_keygen_function(self):
        self.sort_keygen_function = sort_functions.sort_keygen_date

    def set_display_function(self):
        self.display_function = get_display_value_custom

    def map_to_value(self, value):
        map_settings = self.get_map_settings()
        if value is None:
            return None
        if map_settings["method"] == "to_year":
            return value.year
        if map_settings["method"] == "to_decade":
            year = value.year
            return "{}s".format(round(year, -1))
        return value

    def get_map_settings(self):
        if self.map_settings is not None:
            return self.map_settings
        # default is by year
        if self.td_entry and self.td_entry.get("categorize"):
            map_settings = {
                "method": "to_year",
                "sort_function": sort_functions.sort_keygen_integer,
                "display_function": display_functions.display_integer_to_string,
            }
            # if a wide range of dates, convert to decade instead
            stats = get_stattool(self.chironuser, concept=self.concept)
            min = stats.get_min(output_type="python")
            max = stats.get_max(output_type="python")
            if min is not None and max is not None:
                print("minmix", min, max)
                date_delta = max - min
                if date_delta.days > 365 * 10:
                    map_settings = {
                        "method": "to_decade",
                        "sort_function": sort_functions.sort_keygen_string,
                        "display_function": display_functions.display_string,
                    }
            self.map_settings = map_settings
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
        if map_settings["method"] == "to_decade":
            new_column = func.extract("'decade'", column)
        else:
            new_column = func.date_part("year", column)
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
        if value and map_settings and map_settings["method"] == "to_decade":
            return "{}0s".format(int(value))
        return value

    def set_aggregation_methods(self):
        self.aggregation_methods = [
            aggregation.ListDistinct(),
            aggregation.ListAll(),
            aggregation.MinDate(),
            aggregation.MaxDate(),
            aggregation.CountDistinct(),
            aggregation.CountAll(),
            aggregation.MostFrequent(),
        ]

    def get_data_type(self):
        """
        Returns a human-readable string describing the data type (text, integer, etc.).
        """
        return "date"

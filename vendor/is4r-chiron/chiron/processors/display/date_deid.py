from .date import DisplayDate

from sqlalchemy import func

from chiron.query_engine import get_stattool
from chiron.processors import sort_functions, display_functions


class DisplayDateDeid(DisplayDate):
    """
    This is a deidentified alternative to the DateFieldProcessor. If you use it in place of the
    DateFieldProcessor, only the date year is presented to the user.

    Typically, this is used in situations where you want users who can view PHI to see/query the
    whole date, and other users to see/query only the year. To do this in a concept, you will
    set has_phi to true and set both cohort_def_processor_deid_alt and display_processor_deid_alt
    to this.

    If you only ever need to use year, an alternative would be to set only the year in the
    research database as an integer and use the NumberFieldProcessor.
    """

    def set_sort_keygen_function(self):
        self.sort_keygen_function = sort_functions.sort_keygen_integer

    def set_display_function(self):
        self.display_function = display_functions.display_integer

    def default_mapping(self, value):
        """
        When categorize is false, this will run in place of convert_to_category. Use when you
        want to alter the value every time.
        """
        # TODO: horribly inefficient to set map_settings every time
        self.map_settings = {
            "method": "to_year",
            "sort_function": sort_functions.sort_keygen_integer,
            "display_function": display_functions.display_integer,
        }
        if value is None:
            return None
        return value.year

    def map_to_value(self, value):
        map_settings = self.get_map_settings()
        if value is None:
            return None
        if value and map_settings["method"] == "to_year":
            return value.year
        if value and map_settings["method"] == "to_decade":
            year = value.year
            return "{}s".format(round(year, -1))
        return value

    def get_map_settings(self):
        if self.map_settings is not None:
            return self.map_settings
        if self.td_entry and self.td_entry.get("categorize"):
            stats = get_stattool(self.chironuser, concept=self.concept)
            # min and max will be the year as an integer
            min = stats.get_min(output_type="python")
            max = stats.get_max(output_type="python")
            date_delta = max - min
            if date_delta > 10:
                self.map_settings = {
                    "method": "to_decade",
                    "sort_function": sort_functions.sort_keygen_string,
                    "display_function": display_functions.display_string,
                }
            else:
                self.map_settings = {
                    "method": "to_year",
                    "sort_function": sort_functions.sort_keygen_integer,
                    "display_function": display_functions.display_integer_to_string,
                }
        else:
            self.map_settings = {
                "method": "to_year",
                "sort_function": sort_functions.sort_keygen_integer,
                "display_function": display_functions.display_integer,
            }
        return self.map_settings

    def sql_alchemy_map_in_query(self, column):
        """Map existing values to new values during a SQL alchemy query.

        If stored value needs to be converted to a different value (ex. round date to decade),
        this can define the Postgres function(s) for doing that.
        """
        map_settings = self.get_map_settings()
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
        if value and map_settings["method"] == "to_decade":
            return "{}0s".format(int(value))
        return value

    def get_data_type(self):
        """
        Returns a human-readable string describing the data type (text, integer, etc.).
        """
        return "year"

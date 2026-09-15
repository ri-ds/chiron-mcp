from chiron.processors.abstract import DisplayProcessor
from chiron.processors.display import aggregation
from chiron.query_engine import get_stattool

from chiron.processors.sort_functions import sort_keygen_generic
from chiron.processors.display_functions import display_generic


class DisplayText(DisplayProcessor):
    """
    When to use:

    * All values should either be a string or null
    * If possible values are a limited number of categories, consider using CategoryField
    * Good for IDs or free-text comments
    * Not great for long, multi-line free text - like notes - but shouldn't fail either

    """

    def get_data_type(self):
        """
        Returns a human-readable string describing the data type (text, integer, etc.).
        """
        return "text"

    def set_aggregation_methods(self):
        super().set_aggregation_methods()
        self.aggregation_methods.append(aggregation.HasValueText())

    def map_to_value(self, value):
        """
        Changes a value to a category value
        """
        map_settings = self.get_map_settings()
        if value is None:
            return None
        if value and map_settings["method"] == "top_n":
            if value in map_settings["top_values"]:
                return value
            return "(other)"
        return value

    def get_map_settings(self):
        if self.map_settings is not None:
            return self.map_settings
        stats = get_stattool(self.chironuser, concept=self.concept)
        values = stats.get_unique_values_with_counts(sort_by="uniquePatientCount")
        values = values[:5]
        top_values = [x["category"] for x in values]
        self.map_settings = {
            "method": "top_n",
            "top_value_count": 5,
            "top_values": top_values,
            "sort_function": sort_keygen_generic,
            "display_function": display_generic,
        }
        return self.map_settings

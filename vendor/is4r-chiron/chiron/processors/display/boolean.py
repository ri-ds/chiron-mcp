from chiron.processors.abstract import DisplayProcessor

from chiron.processors import sort_functions, display_functions


class DisplayBoolean(DisplayProcessor):
    """
    When to use:

    * All values should be true, false, or null
    """

    def set_sort_keygen_function(self):
        self.sort_keygen_function = sort_functions.sort_keygen_boolean

    def set_display_function(self):
        self.display_function = display_functions.display_boolean

    def get_data_type(self):
        """
        Returns a human-readable string describing the data type (text, integer, etc.).
        """
        return "boolean"

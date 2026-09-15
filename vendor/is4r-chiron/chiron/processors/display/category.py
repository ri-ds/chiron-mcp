from chiron.processors.abstract import DisplayProcessor
from chiron.processors.display import aggregation


class DisplayCategory(DisplayProcessor):
    """
    When to use:

    * All values should either be a string or null
    * Don't use if too many distinct values, use TextField instead
    * don't use if no values repeat (like IDs or free-text comments), use TextField instead
    * don't use if values are longer than one line of text

    """

    def get_data_type(self):
        """
        Returns a human-readable string describing the data type (text, integer, etc.).
        """
        return "category"

    def set_aggregation_methods(self):
        super().set_aggregation_methods()
        self.aggregation_methods.append(
            aggregation.HasValue(),
        )

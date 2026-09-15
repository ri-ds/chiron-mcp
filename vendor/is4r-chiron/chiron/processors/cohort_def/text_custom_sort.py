from .text import CohortDefText


class CohortDefTextCustomSort(CohortDefText):
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

    value_subfield = ".value"

    def get_fields_to_index(self):
        return [".sort", ".value"]

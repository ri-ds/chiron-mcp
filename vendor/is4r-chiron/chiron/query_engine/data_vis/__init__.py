from .float_histogram import FloatHistogram
from .integer_histogram import IntegerHistogram


def get_histogram_object(type, value_count, min_val, max_val):
    """Factory function to return the appropriate histogram object based on the type of data.

    :param type: The type of data to be binned. Options are float, integer, year, date, age.
    :type type: str
    :param value_count: The number of values in your data.
    :type value_count: int
    :param min_val: The minimum value to be binned.
    :type min_val: various
    :param max_val: The maximum value to be binned.
    :type max_val: various
    :return: A histogram object.
    :rtype: FloatHistogram, IntegerHistogram
    """
    if type == "year":
        return IntegerHistogram(value_count, min_val, max_val, number_is_year=True)
    if type == "integer":
        return IntegerHistogram(value_count, min_val, max_val)
    if type == "float":
        return FloatHistogram(value_count, min_val, max_val)
    raise ValueError("Invalid histogram type: {}".format(type))


__all__ = [
    "FloatHistogram",
    "IntegerHistogram",
]

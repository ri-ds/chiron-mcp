from natsort import natsort_keygen
import datetime


def sort_keygen_generic(value):
    if value is None:
        return ""
    return str(value)


def sort_keygen_integer(value):
    if value is None:
        return float("-inf")
    return float(value)


def sort_keygen_float(value):
    if value is None:
        return float("-inf")
    return float(value)


def sort_keygen_string(value):
    if value is None:
        return ""
    return value


def sort_keygen_boolean(value):
    if value is None:
        return -1
    if value is True:
        return 1
    return 0


def sort_keygen_date(value):
    if value is None:
        return datetime.datetime(datetime.MINYEAR, 1, 1)
    return value


sort_keygen_natural = natsort_keygen()

# def sort_keygen_natural(value):
#     return natsort_key(value)

# natural sort info
# https://github.com/SethMMorton/natsort#generating-a-reusable-sorting-key-and-sorting-in-place

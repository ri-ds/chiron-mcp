def display_integer(value, output_type):
    if output_type in ["html", "csv"]:
        if value is None:
            return ""
        return str(int(value))
    if value is None:
        return None
    return int(value)


def display_integer_to_string(value, output_type):
    if value is None:
        return ""
    return str(int(value))


def display_float(value, output_type):
    if output_type in ["html", "csv"]:
        if value is None:
            return ""
        return str(value)
    return value


def display_string(value, output_type):
    if value is None:
        return ""
    return value


def display_boolean(value, output_type):
    if output_type in ["html", "csv"]:
        return str(value)
    return value


def display_generic(value, output_type):
    """
    Converts a value stored in the research database to a display value.

    :param value: the raw value coming from the research database for this concept
    :type value: various
    :param output_type: the type of output being generated (html, csv, etc.)
    :type output_type: str, optional
    :return: a displayable representation of the value
    :rtype: str
    """
    if value is None:
        return ""
    return str(value)

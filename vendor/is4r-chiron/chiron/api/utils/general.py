import json


def convert_to_obj(val):
    """
    Checks if JSON string and if yes converts to object.

    :param val: The object or string to convert if needed
    :type val: str | dict
    :return: The converted object
    :rtype: dict
    """
    if isinstance(val, str):
        return json.loads(val)
    return val


def string_to_bool(val):
    """
    Converts a string to a boolean. Defaults to False. If boolean is passed, returns unmodified.
    """
    if isinstance(val, bool):
        return val
    return str(val).lower() in ["true", "1", "yes", "y"]

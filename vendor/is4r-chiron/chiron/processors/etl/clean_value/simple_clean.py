from dateutil.parser import parse
from dateutil.parser import ParserError
import datetime

from ._base import CleanValue
from chiron.processors.utils import convert_data_list_to_set


class SimpleClean(CleanValue):
    """
    Very generic, standard cleanup process for a variety of data types. Use this option when
    you don't need a lot of customization.

    Behavior:
    - Nice default set of features like stripping leading and trailing whitespace from strings,
      converting empty strings to null, etc.
    - if passed a single value, will process that value
    - if passed a list, will perform single value processing on each entry in the list

    Special cast_to_type options:
    - "integer/string" & "float/string" - use in conjunction with NumberWithCategories concepts
        - If input can be cast to a number, returns {"num": final_val, "val": final_val}
        - If input can't be cast to a number, returns {"txt": final_val, "val": final_val}

    :param cast_to_type: "str", "int", "float", "date", "bool", "integer/string", "float/string"
    :type cast_to_type: str or None to keep output type same as input type
    :param convert_list_to_set: multivalue list responses will have duplicates and nulls removed
      and be flattened out into a single value when possible
    :type convert_list_to_set: boolean
    """

    def __init__(self, cast_to_type=None, convert_list_to_set=True):
        super().__init__()
        self.cast_to_type = cast_to_type
        # a list of values will be returned as set of distinct vals
        self.convert_list_to_set = convert_list_to_set

    def describe_clean_process(self):
        if self.cast_to_type is None:
            return "if input is string, strips whitespace"
        return f"converted all values to {self.cast_to_type}"

    def clean(self, val):
        """
        Clean value, or if a list is passed clean each value individually.
        """
        # remove duplicates from **input** values when output contains mutable types
        if (
            isinstance(val, list)
            and self.convert_list_to_set
            and self.cast_to_type
            in [
                "integer/string",
                "float/string",
            ]
        ):
            val = convert_data_list_to_set(val)

        if isinstance(val, list):
            # clean each value
            response = []
            for single_val in val:
                response.append(self.clean_single_field(single_val))

            # remove duplicates from **return** values when output doesn't contain mutable types
            if self.convert_list_to_set and self.cast_to_type not in [
                "integer/string",
                "float/string",
            ]:
                response = convert_data_list_to_set(response)

            return response
        return self.clean_single_field(val)

    def clean_single_field(self, val):
        """
        Performs some minimal, basic cleanup on input value. Specific actions will depend on
        value in `self.cast_to_type`. If val is list, will perform cleanup on each val and return
        a list
        """
        if isinstance(val, str):
            val2 = val.strip()
            if val != val2:
                self._add_warning(val, "whitespace stripped")
                val = val2
        if not self.cast_to_type:
            return val
        if val is None:
            self._add_warning(val, "input value was null")
            return None
        if val == "":
            self._add_warning(val, "input value was an empty string")
            return None
        try:
            if self.cast_to_type in ["bool", "boolean"]:
                if isinstance(val, str) and val.lower() in ["true", "t", "yes", "y", "1"]:
                    return True
                if isinstance(val, str) and val.lower() in ["false", "f", "no", "n", "0"]:
                    return False
                if isinstance(val, str) and val.lower() in ["none", "null", "n/a", "unknown", ""]:
                    return None
                if val is None:
                    return None
                return True if val else False
            if self.cast_to_type in ["integer/string"]:
                final_val = round(float(val))
                return {"num": final_val, "val": final_val, "txt": None}
            if self.cast_to_type in ["float/string"]:
                final_val = float(val)
                return {"num": final_val, "val": final_val, "txt": None}
            if self.cast_to_type in ["str", "string"]:
                return str(val)
            if self.cast_to_type in ["varchar255"]:
                str_val = str(val)
                if len(str_val) > 255:
                    self._add_warning(val, "string truncated to 255 characters")
                    return str_val[:255]
                return str_val
            if self.cast_to_type in ["int", "integer"]:
                return round(float(val))
            if self.cast_to_type == "float":
                return float(val)
            if self.cast_to_type in ["date", "datetime"]:
                if isinstance(val, datetime.date):
                    return val
                return parse(val, ignoretz=True)
        except (ValueError, ParserError):
            if self.cast_to_type in ["integer/string", "float/string"]:
                final_val = str(val)
                return {"num": None, "val": final_val, "txt": final_val}
            self._add_warning(
                val, f"input value couldn't be cast to {self.cast_to_type} (set to null)"
            )
            return None
        raise ValueError(
            'cast_to_type options are "str", "int", "float" or "date", not "{}".'.format(
                self.cast_to_type
            )
        )

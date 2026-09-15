import math

from ._base import CleanValue
from chiron.processors.etl.clean_value.simple_clean import SimpleClean


class CurrentAgeClean(CleanValue):
    """
    Returns structure same as integer/string from SimpleClean. Anyone over 89 will show as
    "90 and above"
    """

    def __init__(self, convert_list_to_set=True):
        super().__init__()
        self.convert_list_to_set = convert_list_to_set
        self.input_date_cleaner = SimpleClean("float", self.convert_list_to_set)
        self.output_data_cleaner = SimpleClean("integer/string", self.convert_list_to_set)

    def describe_clean_process(self):
        return "age in years or '90 and above'"

    def clean(self, val):
        # first convert value to a float
        float_age = self.input_date_cleaner.clean(val)
        if isinstance(float_age, list):
            # if multiple values were returned, convert all to current_age
            processed_val = []
            for age in float_age:
                processed_val.append(self._clean_single_value(age))
        else:
            # if single float was returned, convert to current_age
            processed_val = self._clean_single_value(float_age)
        return self.output_data_cleaner.clean(processed_val)

    def _clean_single_value(self, val):
        if val is None:
            return None
        age = math.floor(val)
        if age > 89:
            age = "90 and above"
        return age

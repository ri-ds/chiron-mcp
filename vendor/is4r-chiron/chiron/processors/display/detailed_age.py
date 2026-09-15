from chiron.processors.display.number import DisplayNumber
from chiron.helpers import age_in_days_to_years_days


def age_in_days_to_label(value, output_type):
    if value is None:
        if output_type in ["html", "csv", "json"]:
            return ""
        return None
    years, days = age_in_days_to_years_days(value)
    if output_type in ["html", "json"]:
        return f"{years} years, {days} days"
    return value


class DisplayDetailedAge(DisplayNumber):
    def set_display_function(self):
        self.display_function = age_in_days_to_label

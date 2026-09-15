from ... import models
from ._abstract import AbstractEventOption
from .. import cohort_def_functions as cd_funcs


def try_int(val):
    try:
        response = int(val)
    except TypeError:
        response = val
    return response


class RelativeToTodayOption(AbstractEventOption):
    def is_deidentified(self):
        if not self.existing_rule:
            return True
        if self.existing_rule["days_ago"] % 365 == 0:
            return True
        return False

    def get_unique_name(self):
        return "relative_to_today"

    def get_option_title(self):
        return "relative to today"

    def get_option_data(self):
        data = super().get_option_data()
        criteria_set = cd_funcs.lookup_cohort_def_entry(self.cohort_def, self.entry_id)
        self.collection = models.Collection.objects.get(
            dataset=self.chironuser.dataset, permanent_id=criteria_set["collection_id"]
        )
        if self.collection.check_event_user_access_level(self.chironuser) == "deid":
            options = days_ago_options_deid
        else:
            options = days_ago_options
        days_ago = options[0][0]
        rule = criteria_set.get("event_rule", {})
        if rule["type"] == "relative_to_today":
            days_ago = rule.get("days_ago", days_ago)
        data["days_ago_options"] = options
        data["days_ago"] = days_ago
        return data

    def get_form_template(self):
        return "chiron/event_date_forms/relative_to_today.html"

    def create_event_rule(self):
        rule = {
            "type": "relative_to_today",
            "days_ago": try_int(self.cleaned.get("days_ago", None)),
        }
        return rule

    def event_rule_to_string(self):
        criteria_set = cd_funcs.lookup_cohort_def_entry(self.cohort_def, self.entry_id)
        self.collection = models.Collection.objects.get(
            dataset=self.chironuser.dataset, permanent_id=criteria_set["collection_id"]
        )
        if not self.existing_rule:
            return ""
        return "within the last {} days".format(self.existing_rule["days_ago"])


days_ago_options_deid = [
    (365, "1 year (365 days)"),
    (730, "2 years (730 days)"),
    (1095, "3 years (1095 days)"),
]

days_ago_options = [
    (1, "1 day (today)"),
    (2, "2 days"),
    (3, "3 days"),
    (4, "4 days"),
    (5, "5 days"),
    (6, "6 days"),
    (7, "7 days"),
    (8, "8 days"),
    (9, "9 days"),
    (10, "10 days"),
    (11, "11 days"),
    (12, "12 days"),
    (13, "13 days"),
    (14, "14 days"),
    (15, "15 days"),
    (20, "20 days"),
    (25, "25 days"),
    (30, "30 days"),
    (35, "35 days"),
    (40, "40 days"),
    (45, "45 days"),
    (50, "50 days"),
    (55, "55 days"),
    (60, "60 days"),
    (70, "70 days"),
    (80, "80 days"),
    (90, "90 days"),
    (100, "100 days"),
    (120, "120 days"),
    (150, "150 days"),
    (180, "180 days"),
    (240, "240 days"),
    (365, "1 year (365 days)"),
    (730, "2 years (730 days)"),
    (1095, "3 years (1095 days)"),
]

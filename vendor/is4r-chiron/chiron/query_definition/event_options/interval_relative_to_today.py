from ._abstract import AbstractEventOption
from .. import cohort_def_functions as cd_funcs
from ... import models
from chiron import chiron_settings


def try_int(val):
    try:
        response = int(val)
    except TypeError:
        response = val
    return response


class IntervalRelativeToTodayOption(AbstractEventOption):
    def is_deidentified(self):
        if not self.existing_rule:
            return True
        if self.existing_rule.get("start_date_days_ago", None):
            if self.existing_rule["start_date_days_ago"] % 365 == 0:
                return True
        if self.existing_rule.get("end_date_days_ago", None):
            if self.existing_rule["end_date_days_ago"] % 365 == 0:
                return True
        return False

    def get_unique_name(self):
        return "interval_relative_to_today"

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
        start_date_days_ago = options[0][0]
        end_date_days_ago = options[0][0]
        rule = criteria_set.get("event_rule", {})
        if rule.get("type") == "interval_relative_to_today":
            start_date_days_ago = rule.get("start_date_days_ago", start_date_days_ago)
            end_date_days_ago = rule.get("end_date_days_ago", end_date_days_ago)
        data["days_ago_options"] = options
        data["start_date_days_ago"] = start_date_days_ago
        data["end_date_days_ago"] = end_date_days_ago
        return data

    def get_form_template(self):
        return "chiron/event_date_forms/interval_relative_to_today.html"

    def validate_user_input(self, post_data):
        self.initial = post_data
        self.cleaned = {}
        self.errors = []
        self.error_fields = []
        start_date_days_ago = post_data.get("start_date_days_ago")
        if start_date_days_ago and not start_date_days_ago == "ignore":
            self.cleaned["start_date_days_ago"] = start_date_days_ago
        end_date_days_ago = post_data.get("end_date_days_ago")
        if end_date_days_ago and not end_date_days_ago == "ignore":
            self.cleaned["end_date_days_ago"] = end_date_days_ago
        if not self.cleaned:
            self.errors.append("Must select at least one.")
            self.error_fields.append("start_date_days_ago")
            self.error_fields.append("end_date_days_ago")
            return False
        return True

    def create_event_rule(self):
        rule = {
            "type": "interval_relative_to_today",
        }
        if "start_date_days_ago" in self.cleaned:
            rule["start_date_days_ago"] = try_int(self.cleaned.get("start_date_days_ago", None))
        if "end_date_days_ago" in self.cleaned:
            rule["end_date_days_ago"] = try_int(self.cleaned.get("end_date_days_ago", None))
        return rule

    def event_rule_to_string(self):
        criteria_set = cd_funcs.lookup_cohort_def_entry(self.cohort_def, self.entry_id)
        self.collection = models.Collection.objects.get(
            dataset=self.chironuser.dataset, permanent_id=criteria_set["collection_id"]
        )
        if not self.existing_rule:
            return ""
        lines = []
        if "start_date_days_ago" in self.existing_rule:
            lines.append(
                "event started within the last {} days".format(
                    self.existing_rule["start_date_days_ago"]
                )
            )
        if "end_date_days_ago" in self.existing_rule:
            lines.append(
                "event ended within the last {} days".format(
                    self.existing_rule["end_date_days_ago"]
                )
            )
        return chiron_settings.CHIRON_AGG_DELIMITER.join(lines)


days_ago_options_deid = [
    ("ignore", "[no restriction]"),
    (365, "1 year"),
    (730, "2 years"),
    (1095, "3 years"),
    (1461, "4 years"),
    (1826, "5 years"),
    (2191, "6 years"),
    (2556, "7 years"),
    (2922, "8 years"),
    (3287, "9 years"),
    (3652, "10 years"),
]

days_ago_options = [
    ("ignore", "[no restriction]"),
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
    (16, "16 days"),
    (17, "17 days"),
    (18, "18 days"),
    (19, "19 days"),
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
    (365, "1 year"),
    (730, "2 years"),
    (1095, "3 years"),
    (1461, "4 years"),
    (1826, "5 years"),
    (2191, "6 years"),
    (2556, "7 years"),
    (2922, "8 years"),
    (3287, "9 years"),
    (3652, "10 years"),
]

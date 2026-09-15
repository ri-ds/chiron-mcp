from dateutil.parser import parse

from ... import models
from ._abstract import AbstractEventOption
from .. import cohort_def_functions as cd_funcs


class DateRangeOption(AbstractEventOption):
    fields = [
        "date_min",
        "date_max",
    ]

    def is_deidentified(self):
        return False

    def get_unique_name(self):
        return "date_range"

    def get_option_title(self):
        return "date range"

    def get_option_data(self):
        data = super().get_option_data()
        criteria_set = cd_funcs.lookup_cohort_def_entry(self.cohort_def, self.entry_id)
        rule = criteria_set.get("event_rule", {})
        if rule.get("type") == "date_range":
            data["date_min"] = rule.get("date_min", "")
            data["date_max"] = rule.get("date_max", "")
        else:
            data["date_min"] = ""
            data["date_max"] = ""
        return data

    def get_form_template(self):
        return "chiron/event_date_forms/date_range.html"

    def validate_user_input(self, post_data):
        self.initial = post_data
        self.cleaned = {}
        self.errors = []
        self.error_fields = []
        for field in self.fields:
            val = post_data.get(field, None)
            if val:
                try:
                    date_val = parse(val)
                except Exception:
                    self.errors.append("Invalid date value.")
                    self.error_fields.append(field)
                    continue
                self.cleaned[field] = date_val.strftime("%m/%d/%Y")
        if self.errors:
            return False
        if not self.cleaned:
            self.errors.append("Must provide at least one value.")
            self.error_fields = self.fields
            return False
        return True

    def create_event_rule(self):
        rule = {
            "type": "date_range",
        }
        for field in self.fields:
            val = self.cleaned.get(field)
            if val:
                rule[field] = val
        return rule

    def event_rule_to_string(self):
        criteria_set = cd_funcs.lookup_cohort_def_entry(self.cohort_def, self.entry_id)
        self.collection = models.Collection.objects.get(
            dataset=self.chironuser.dataset, permanent_id=criteria_set["collection_id"]
        )
        if not self.existing_rule:
            return ""
        has_min = True if self.existing_rule.get("date_min") else False
        has_max = True if self.existing_rule.get("date_max") else False
        if has_min and has_max:
            return "{} <= {} date <= {}".format(
                self.existing_rule["date_min"],
                self.collection.name,
                self.existing_rule["date_max"],
            )
        elif has_min:
            return "{} date >= {}".format(
                self.collection.name,
                self.existing_rule["date_min"],
            )
        elif has_max:
            return "{} date <= {}".format(
                self.collection.name,
                self.existing_rule["date_max"],
            )

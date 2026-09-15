from ... import models
from ._abstract import AbstractEventOption
from .. import cohort_def_functions as cd_funcs


class AgeInDaysRangeOption(AbstractEventOption):
    fields = [
        "age_min",
        "age_max",
    ]

    def is_deidentified(self):
        return False

    def get_unique_name(self):
        return "age_in_days_range"

    def get_option_title(self):
        return "age range (days)"

    def get_option_data(self):
        data = super().get_option_data()
        criteria_set = cd_funcs.lookup_cohort_def_entry(self.cohort_def, self.entry_id)
        rule = criteria_set.get("event_rule", {})
        if rule.get("type") == "age_in_days_range":
            data["age_min"] = rule.get("age_min", "")
            data["age_max"] = rule.get("age_max", "")
        else:
            data["age_min"] = ""
            data["age_max"] = ""
        return data

    def get_form_template(self):
        return "chiron/event_date_forms/age_in_days_range.html"

    def validate_user_input(self, post_data):
        self.initial = post_data
        self.cleaned = {}
        self.errors = []
        self.error_fields = []
        for field in self.fields:
            val = post_data.get(field, None)
            if val or val == 0:
                try:
                    date_val = int(val)
                except Exception:
                    self.errors.append("Invalid integer value.")
                    self.error_fields.append(field)
                    continue
                self.cleaned[field] = date_val
        if self.errors:
            return False
        if not self.cleaned:
            self.errors.append("Must provide at least one value.")
            self.error_fields = self.fields
            return False
        return True

    def create_event_rule(self):
        rule = {
            "type": "age_in_days_range",
        }
        for field in self.fields:
            val = self.cleaned.get(field)
            if val or val == 0:
                rule[field] = val
        return rule

    def event_rule_to_string(self):
        criteria_set = cd_funcs.lookup_cohort_def_entry(self.cohort_def, self.entry_id)
        self.collection = models.Collection.objects.get(
            dataset=self.chironuser.dataset, permanent_id=criteria_set["collection_id"]
        )
        if not self.existing_rule:
            return ""
        has_min = True if self.existing_rule.get("age_min") is not None else False
        has_max = True if self.existing_rule.get("age_max") is not None else False
        if has_min and has_max:
            return "{} <= age in days <= {}".format(
                self.existing_rule["age_min"],
                self.existing_rule["age_max"],
            )
        elif has_min:
            return "age in days >= {}".format(
                self.existing_rule["age_min"],
            )
        elif has_max:
            return "age in days <= {}".format(
                self.existing_rule["age_max"],
            )

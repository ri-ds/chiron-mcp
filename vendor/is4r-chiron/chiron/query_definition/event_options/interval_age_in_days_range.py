from ... import models
from ._abstract import AbstractEventOption
from .. import cohort_def_functions as cd_funcs


class IntervalAgeInDaysRangeOption(AbstractEventOption):
    fields = ["age_start_min", "age_start_max", "age_end_min", "age_end_max"]

    def is_deidentified(self):
        return False

    def get_unique_name(self):
        return "interval_age_in_days_range"

    def get_option_title(self):
        return "age range (days)"

    def get_option_data(self):
        data = super().get_option_data()
        criteria_set = cd_funcs.lookup_cohort_def_entry(self.cohort_def, self.entry_id)
        rule = criteria_set.get("event_rule", {})
        if rule.get("type") == "interval_age_in_days_range":
            data["age_start_min"] = rule.get("age_start_min", "")
            data["age_start_max"] = rule.get("age_start_max", "")
            data["age_end_min"] = rule.get("age_end_min", "")
            data["age_end_max"] = rule.get("age_end_max", "")
        else:
            data["age_start_min"] = ""
            data["age_start_max"] = ""
            data["age_end_min"] = ""
            data["age_end_max"] = ""
        return data

    def get_form_template(self):
        return "chiron/event_date_forms/interval_age_in_days_range.html"

    def validate_user_input(self, post_data):
        self.initial = post_data
        self.cleaned = {}
        self.errors = []
        self.error_fields = []
        for field in self.fields:
            val = post_data.get(field, None)
            if val:
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
            "type": "interval_age_in_days_range",
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
        response = []
        # date start
        has_min = True if self.existing_rule.get("age_start_min") else False
        has_max = True if self.existing_rule.get("age_start_max") else False
        if has_min and has_max:
            response.append(
                "{} <= start age in days <= {}".format(
                    self.existing_rule["age_start_min"],
                    self.existing_rule["age_start_max"],
                )
            )
        elif has_min:
            response.append(
                "start age in days >= {}".format(
                    self.existing_rule["age_start_min"],
                )
            )
        elif has_max:
            response.append(
                "start age in days <= {}".format(
                    self.existing_rule["age_start_max"],
                )
            )
        # date end
        has_min = True if self.existing_rule.get("age_end_min") else False
        has_max = True if self.existing_rule.get("age_end_max") else False
        if has_min and has_max:
            response.append(
                "{} <= end age in days <= {}".format(
                    self.existing_rule["age_end_min"],
                    self.existing_rule["age_end_max"],
                )
            )
        elif has_min:
            response.append(
                "end age in days >= {}".format(
                    self.existing_rule["age_end_min"],
                )
            )
        elif has_max:
            response.append(
                "end age in days <= {}".format(
                    self.existing_rule["age_end_max"],
                )
            )
        return " and ".join(response)

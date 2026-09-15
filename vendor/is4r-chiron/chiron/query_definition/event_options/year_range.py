from dateutil.parser import parse

from ... import models
from .. import cohort_def_functions as cd_funcs
from .date_range import DateRangeOption


class YearRangeOption(DateRangeOption):
    """
    Deidentified substitution for DateRangeOption.
    This will open in place of DateRangeOption if the user only
    has deidentified permission on date fields.
    """

    def get_option_title(self):
        return "year range"

    def is_deidentified(self):
        if not self.existing_rule:
            return True
        if self.existing_rule.get("date_min", ""):
            if self.existing_rule["date_min"][0:5] != "01/01":
                return False
        if self.existing_rule.get("date_max", ""):
            if self.existing_rule["date_max"][0:5] != "12/31":
                return False
        return True

    def get_option_data(self):
        data = super().get_option_data()
        if data["date_min"]:
            data["date_min"] = data["date_min"][-4:]
        if data["date_max"]:
            data["date_max"] = data["date_max"][-4:]
        return data

    def get_form_template(self):
        return "chiron/event_date_forms/year_range.html"

    def event_rule_to_string(self):
        if not self.is_deidentified():
            return super().event_rule_to_string()
        criteria_set = cd_funcs.lookup_cohort_def_entry(self.cohort_def, self.entry_id)
        self.collection = models.Collection.objects.get(
            dataset=self.chironuser.dataset, permanent_id=criteria_set["collection_id"]
        )
        if not self.existing_rule:
            return ""
        has_min = True if self.existing_rule.get("date_min") else False
        has_max = True if self.existing_rule.get("date_max") else False
        if has_min and has_max:
            return "{} <= {} year <= {}".format(
                self.existing_rule["date_min"][-4:],
                self.collection.name,
                self.existing_rule["date_max"][-4:],
            )
        elif has_min:
            return "{} year >= {}".format(
                self.collection.name,
                self.existing_rule["date_min"][-4:],
            )
        elif has_max:
            return "{} year <= {}".format(
                self.collection.name,
                self.existing_rule["date_max"][-4:],
            )

    def validate_user_input(self, post_data):
        self.initial = post_data
        self.cleaned = {}
        self.errors = []
        self.error_fields = []
        for field in self.fields:
            val = post_data.get(field, None)
            if val:
                if field == "date_min":
                    val = "01/01/" + str(val)
                if field == "date_max":
                    val = "12/31/" + str(val)
                try:
                    date_val = parse(val)
                except Exception:
                    self.errors.append("Invalid year value. Please enter as 4 digit number.")
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

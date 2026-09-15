from dateutil.parser import parse

from ... import models
from .. import cohort_def_functions as cd_funcs
from .interval_date_range import IntervalDateRangeOption


class IntervalYearRangeOption(IntervalDateRangeOption):
    """
    Deidentified substitution for IntervalDateRangeOption
    """

    def get_option_title(self):
        return "year range"

    def is_deidentified(self):
        if not self.existing_rule:
            return True
        if self.existing_rule.get("date_start_min", ""):
            if self.existing_rule["date_start_min"][0:5] != "01/01":
                return False
        if self.existing_rule.get("date_end_min", ""):
            if self.existing_rule["date_end_min"][0:5] != "01/01":
                return False
        if self.existing_rule.get("date_start_max", ""):
            if self.existing_rule["date_start_max"][0:5] != "12/31":
                return False
        if self.existing_rule.get("date_end_max", ""):
            if self.existing_rule["date_end_max"][0:5] != "12/31":
                return False
        return True

    def get_form_template(self):
        return "chiron/event_date_forms/interval_year_range.html"

    def get_option_data(self):
        data = super().get_option_data()
        if data["date_start_min"]:
            data["date_start_min"] = data["date_start_min"][-4:]
        if data["date_start_max"]:
            data["date_start_max"] = data["date_start_max"][-4:]
        if data["date_end_min"]:
            data["date_end_min"] = data["date_end_min"][-4:]
        if data["date_end_max"]:
            data["date_end_max"] = data["date_end_max"][-4:]
        return data

    def validate_user_input(self, post_data):
        self.initial = post_data
        self.cleaned = {}
        self.errors = []
        self.error_fields = []
        for field in self.fields:
            val = post_data.get(field, None)
            if val:
                if field in ["date_start_min", "date_end_min"]:
                    val = "01/01/" + str(val)
                if field in ["date_start_max", "date_end_max"]:
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

    def event_rule_to_string(self):
        if not self.is_deidentified():
            return super().event_rule_to_string()
        criteria_set = cd_funcs.lookup_cohort_def_entry(self.cohort_def, self.entry_id)
        self.collection = models.Collection.objects.get(
            dataset=self.chironuser.dataset, permanent_id=criteria_set["collection_id"]
        )
        if not self.existing_rule:
            return ""
        response = []
        # date start
        has_min = True if self.existing_rule.get("date_start_min") else False
        has_max = True if self.existing_rule.get("date_start_max") else False
        if has_min and has_max:
            response.append(
                "{} <= {} start date <= {}".format(
                    self.existing_rule["date_start_min"][-4:],
                    self.collection.name,
                    self.existing_rule["date_start_max"][-4:],
                )
            )
        elif has_min:
            response.append(
                "{} start date >= {}".format(
                    self.collection.name,
                    self.existing_rule["date_start_min"][-4:],
                )
            )
        elif has_max:
            response.append(
                "{} start date <= {}".format(
                    self.collection.name,
                    self.existing_rule["date_start_max"][-4:],
                )
            )
        # date end
        has_min = True if self.existing_rule.get("date_end_min") else False
        has_max = True if self.existing_rule.get("date_end_max") else False
        if has_min and has_max:
            response.append(
                "{} <= {} end date <= {}".format(
                    self.existing_rule["date_end_min"][-4:],
                    self.collection.name,
                    self.existing_rule["date_end_max"][-4:],
                )
            )
        elif has_min:
            response.append(
                "{} end date >= {}".format(
                    self.collection.name,
                    self.existing_rule["date_end_min"][-4:],
                )
            )
        elif has_max:
            response.append(
                "{} end date <= {}".format(
                    self.collection.name,
                    self.existing_rule["date_end_max"][-4:],
                )
            )
        return " and ".join(response)

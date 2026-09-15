from ... import models
from ._abstract import AbstractEventOption
from .. import cohort_def_functions as cd_funcs


class NoRestrictionOption(AbstractEventOption):
    def is_deidentified(self):
        return True

    def get_unique_name(self):
        return "no_restriction"

    def get_option_title(self):
        return "no restriction"

    def get_option_data(self):
        data = super().get_option_data()
        return data

    def get_form_template(self):
        return "chiron/event_date_forms/no_restriction.html"

    def validate_user_input(self, post_data):
        self.initial = post_data
        self.cleaned = {}
        self.errors = []
        self.error_fields = []
        return True

    def create_event_rule(self):
        rule = {
            "type": "no_restriction",
        }
        return rule

    def event_rule_to_string(self):
        criteria_set = cd_funcs.lookup_cohort_def_entry(self.cohort_def, self.entry_id)
        self.collection = models.Collection.objects.get(
            dataset=self.chironuser.dataset, permanent_id=criteria_set["collection_id"]
        )
        if not self.existing_rule:
            return ""
        return "any date"

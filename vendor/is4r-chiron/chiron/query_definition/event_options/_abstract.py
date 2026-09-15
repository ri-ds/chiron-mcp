from abc import ABCMeta, abstractmethod

from django.template.loader import render_to_string

from .. import cohort_def_functions as cd_funcs


class AbstractEventOption:
    __metaclass__ = ABCMeta

    existing_rule = None
    initial = {}
    cleaned = {}
    errors = []
    error_fields = []

    def __init__(self, chironuser, cohort_def, entry_id):
        self.chironuser = chironuser
        self.cohort_def = cohort_def
        self.entry_id = entry_id
        criteria_set = cd_funcs.lookup_cohort_def_entry(self.cohort_def, self.entry_id)
        if (
            "event_rule" in criteria_set
            and criteria_set["event_rule"]["type"] == self.get_unique_name()
        ):
            self.existing_rule = criteria_set["event_rule"]

    def get_html_form(self, request):
        """
        Returns this option with an html form as a string
        """
        context = self.get_option_data()
        context["errors"] = self.errors
        context["error_fields"] = self.error_fields
        context["initial"] = self.get_initial_values()
        return render_to_string(self.get_form_template(), context, request=request)

    def get_initial_values(self):
        return self.initial if self.initial else self.existing_rule

    @abstractmethod
    def get_unique_name(self):
        """Returns a machine readable name slug"""
        pass

    @abstractmethod
    def get_option_title(self):
        """Returns a title for this form"""
        pass

    def get_option_data(self):
        """Returns a data structure representing the form"""
        data = {
            "option_id": self.get_unique_name(),
            "label": self.get_option_title(),
            "django_template": self.get_form_template(),
            "allowed": True,
        }
        return data

    @abstractmethod
    def get_form_template(self):
        """For backend-generated html, returns the Django template to use"""
        pass

    def validate_user_input(self, post_data):
        """Returns True or False.
        If True, also saves any data it needs to self.cleaned.
        """
        for key, value in post_data.items():
            self.cleaned[key] = value
        return True

    @abstractmethod
    def create_event_rule(self):
        """Returns the event rule dict that will be added to the cohort def.
        Must be run after validate_user_input()!
        """
        pass

    def event_rule_to_string(self):
        """
        Converts the event rule from the cohort def into a human-readable string
        """
        if self.existing_rule:
            return str(self.existing_rule)
        return ""

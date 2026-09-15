from django.template.loader import render_to_string

from .. import cohort_def_functions as cd_funcs
from chiron import models
from chiron import chiron_settings


from .date_range import DateRangeOption
from .year_range import YearRangeOption
from .interval_date_range import IntervalDateRangeOption
from .interval_year_range import IntervalYearRangeOption
from .relative_to_today import RelativeToTodayOption
from .relative_to_other_event import RelativeToOtherEventOption
from .interval_relative_to_today import IntervalRelativeToTodayOption
from .age_in_days_range import AgeInDaysRangeOption
from .interval_age_in_days_range import IntervalAgeInDaysRangeOption
from .no_restriction import NoRestrictionOption


def try_int(val):
    try:
        response = int(val)
    except TypeError:
        response = val
    return response


class EventOptionCollection:
    """
    Event options represent ways you can manipulate the cohort definition for a criteria set
    based on the date concepts defined in the related collection.
    Often multiple event options are available for a criteria set. This class will create and
    store the group of EventOption objects appropriate for the specified criteria set.
    """

    active_option_index = 0
    event_rule = None

    def __init__(self, chironuser, cohort_def, entry_id):
        self.chironuser = chironuser
        self.entry_id = entry_id
        self.cohort_def = cohort_def
        self.criteria_set = cd_funcs.lookup_cohort_def_entry(self.cohort_def, self.entry_id)
        if "event_rule" in self.criteria_set:
            self.event_rule = self.criteria_set["event_rule"]
        self.collection = models.Collection.objects.get(
            dataset=chironuser.dataset, permanent_id=self.criteria_set["collection_id"]
        )
        event_type = self.collection.get_event_type()
        event_concept_type = chiron_settings.CHIRON_EVENT_CONCEPT_TYPE
        if event_type == "interval" and event_concept_type == "date":
            self.set_forms_date_interval()
        elif event_type == "point" and event_concept_type == "date":
            self.set_forms_date_point()
        elif event_type == "interval" and event_concept_type == "detailed_age":
            self.set_forms_age_in_days_interval()
        elif event_type == "point" and event_concept_type == "detailed_age":
            self.set_forms_age_in_days_point()
        else:
            raise NotImplementedError("The selected combo of event types isn't an option")

    def set_forms_date_interval(self):
        if self.event_rule:
            rule_type = self.event_rule["type"]
            if rule_type == "interval_relative_to_today":
                self.active_option_index = 1
            if rule_type == "relative_to_other_event":
                self.active_option_index = 2
            if rule_type == "no_restriction":
                self.active_option_index = 3
        if self.collection.check_event_user_access_level(self.chironuser) == "normal":
            date_range_option = IntervalDateRangeOption(
                self.chironuser, self.cohort_def, self.entry_id
            )
        else:
            date_range_option = IntervalYearRangeOption(
                self.chironuser, self.cohort_def, self.entry_id
            )
        self.options = [
            date_range_option,
            IntervalRelativeToTodayOption(self.chironuser, self.cohort_def, self.entry_id),
            RelativeToOtherEventOption(self.chironuser, self.cohort_def, self.entry_id),
            NoRestrictionOption(self.chironuser, self.cohort_def, self.entry_id),
        ]

    def set_forms_date_point(self):
        if self.event_rule:
            rule_type = self.event_rule["type"]
            if rule_type == "relative_to_today":
                self.active_option_index = 1
            if rule_type == "relative_to_other_event":
                self.active_option_index = 2
            if rule_type == "no_restriction":
                self.active_option_index = 3
        if self.collection.check_event_user_access_level(self.chironuser) == "normal":
            date_range_option = DateRangeOption(self.chironuser, self.cohort_def, self.entry_id)
        else:
            date_range_option = YearRangeOption(self.chironuser, self.cohort_def, self.entry_id)
        self.options = [
            date_range_option,
            RelativeToTodayOption(self.chironuser, self.cohort_def, self.entry_id),
            RelativeToOtherEventOption(self.chironuser, self.cohort_def, self.entry_id),
            NoRestrictionOption(self.chironuser, self.cohort_def, self.entry_id),
        ]

    def set_forms_age_in_days_interval(self):
        rule_type = self.event_rule["type"]
        if rule_type == "relative_to_other_event":
            self.active_option_index = 1
        if rule_type == "no_restriction":
            self.active_option_index = 2
        self.options = [
            IntervalAgeInDaysRangeOption(self.chironuser, self.cohort_def, self.entry_id),
            RelativeToOtherEventOption(self.chironuser, self.cohort_def, self.entry_id),
            NoRestrictionOption(self.chironuser, self.cohort_def, self.entry_id),
        ]

    def set_forms_age_in_days_point(self):
        rule_type = self.event_rule["type"]
        if rule_type == "relative_to_other_event":
            self.active_option_index = 1
        if rule_type == "no_restriction":
            self.active_option_index = 2
        self.options = [
            AgeInDaysRangeOption(self.chironuser, self.cohort_def, self.entry_id),
            RelativeToOtherEventOption(self.chironuser, self.cohort_def, self.entry_id),
            NoRestrictionOption(self.chironuser, self.cohort_def, self.entry_id),
        ]

    def get_title(self):
        """
        Returns a human-readable title representing this option group
        """
        title = "Set Date Restriction for {} Event".format(self.collection.name.title())
        return title

    def get_data(self):
        """
        returns an array of dicts with related data for each event object. This data can be used
        to create a form to collect the user input needed for a "modify_event_rule"
        transformation.
        """
        data = []
        for event_form in self.options:
            data.append(event_form.get_option_data())
        return data

    def get_active_option(self):
        """
        The active option is either the one that's currently being used on the criteria set
        event definition or the default active option.
        """
        return self.options[self.active_option_index]

    def get_event_options(self):
        """
        Get all event options as a list
        """
        return self.options

    def get_event_option_by_type(self, option_type):
        event_type = self.collection.get_event_type()
        event_concept_type = chiron_settings.CHIRON_EVENT_CONCEPT_TYPE
        if event_type == "interval" and event_concept_type == "date":
            if option_type == "interval_date_range":
                return self.options[0]
            elif option_type == "interval_relative_to_today":
                return self.options[1]
            elif option_type == "relative_to_other_event":
                return self.options[2]
            elif option_type == "no_restriction":
                return self.options[3]
        elif event_type == "point" and event_concept_type == "date":
            if option_type == "date_range":
                return self.options[0]
            elif option_type == "relative_to_today":
                return self.options[1]
            elif option_type == "relative_to_other_event":
                return self.options[2]
            elif option_type == "no_restriction":
                return self.options[3]
        elif event_type == "interval" and event_concept_type == "detailed_age":
            if option_type == "interval_age_in_days_range":
                return self.options[0]
            if option_type == "relative_to_other_event":
                return self.options[1]
            elif option_type == "no_restriction":
                return self.options[2]
        elif event_type == "point" and event_concept_type == "detailed_age":
            if option_type == "age_in_days_range":
                return self.options[0]
            elif option_type == "relative_to_other_event":
                return self.options[1]
            elif option_type == "no_restriction":
                return self.options[2]
        return None

    def get_html(self, request):
        """
        Used for the built-in UI, will return HTML for all child event options.
        """
        form_entries = []
        for i, event_form in enumerate(self.options):
            form_entry = {}
            form_entry["is_active"] = True if i == self.active_option_index else False
            form_entry["form_title"] = event_form.get_option_title()
            form_entry["unique_name"] = event_form.get_unique_name()
            form_entry["form_html"] = event_form.get_html_form(request)
            form_entries.append(form_entry)
        context = {
            "form_entries": form_entries,
        }
        final_html = render_to_string(
            "chiron/cohort_def_display/event_date_form.html", context, request=request
        )
        return final_html

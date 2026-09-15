from ... import models
from ._abstract import AbstractEventOption
from .. import cohort_def_functions as cd_funcs

from chiron import query_definition as qdef


def try_int(val):
    try:
        response = int(val)
    except TypeError:
        response = val
    return response


date_options = [
    (-3652, "10 years before"),
    (-3287, "9 years before"),
    (-2922, "8 years before"),
    (-2556, "7 years before"),
    (-2191, "6 years before"),
    (-1826, "5 years before"),
    (-1461, "4 years before"),
    (-1095, "3 years before"),
    (-730, "2 years before"),
    (-365, "1 year before"),
    (-240, "240 days before"),
    (-180, "180 days before"),
    (-120, "120 days before"),
    (-100, "100 days before"),
    (-90, "90 days before"),
    (-60, "60 days before"),
    (-30, "30 days before"),
    (-20, "20 days before"),
    (-15, "15 days before"),
    (-14, "14 days before"),
    (-13, "13 days before"),
    (-12, "12 days before"),
    (-11, "11 days before"),
    (-10, "10 days before"),
    (-9, "9 days before"),
    (-8, "8 days before"),
    (-7, "7 days before"),
    (-6, "6 days before"),
    (-5, "5 days before"),
    (-4, "4 days before"),
    (-3, "3 days before"),
    (-2, "2 days before"),
    (-1, "1 day before"),
    (0, "same day as"),
    (1, "1 day after"),
    (2, "2 days after"),
    (3, "3 days after"),
    (4, "4 days after"),
    (5, "5 days after"),
    (6, "6 days after"),
    (7, "7 days after"),
    (8, "8 days after"),
    (9, "9 days after"),
    (10, "10 days after"),
    (11, "11 days after"),
    (12, "12 days after"),
    (13, "13 days after"),
    (14, "14 days after"),
    (15, "15 days after"),
    (20, "20 days after"),
    (30, "30 days after"),
    (45, "45 days after"),
    (60, "60 days after"),
    (90, "90 days after"),
    (100, "100 days after"),
    (120, "120 days after"),
    (180, "180 days after"),
    (240, "240 days after"),
    (365, "1 year after"),
    (730, "2 years after"),
    (1095, "3 years after"),
    (1461, "4 years after"),
    (1826, "5 years after"),
    (2191, "6 years after"),
    (2556, "7 years after"),
    (2922, "8 years after"),
    (3287, "9 years after"),
    (3652, "10 years after"),
]


class RelativeToOtherEventOption(AbstractEventOption):
    def is_deidentified(self):
        return True

    def get_unique_name(self):
        return "relative_to_other_event"

    def get_option_title(self):
        return "relative to other event"

    def get_option_data(self):
        data = super().get_option_data()
        criteria_set = cd_funcs.lookup_cohort_def_entry(self.cohort_def, self.entry_id)
        if qdef.check_criteria_set_has_custom_count_rule(criteria_set):
            data["allowed"] = False
            data["disallowed_reason"] = (
                "You can't create a relative date rule on a criteria"
                + "set that has a custom count rule."
            )
            return data
        oCollection = models.Collection.objects.get(
            dataset=self.chironuser.dataset, permanent_id=criteria_set["collection_id"]
        )

        # get info about other criteria set events that could be targeted
        other_event_criteria_sets = cd_funcs.get_all_event_criteria_sets(
            self.cohort_def, exclude_entry_ids=[criteria_set["entry_id"]]
        )
        # print("os", other_event_criteria_sets)
        data["other_events"] = []
        for cs in other_event_criteria_sets:
            # print("cs", cs)
            oCollectionOther = models.Collection.objects.get(
                dataset=self.chironuser.dataset, permanent_id=cs["collection_id"]
            )
            data["other_events"].append(
                {
                    "criteria_set_name": qdef.get_criteria_set_name(
                        self.chironuser, self.cohort_def, cs["entry_id"]
                    ),
                    "event_type": oCollectionOther.get_event_type(),
                    "criteria_set_entry_id": cs["entry_id"],
                }
            )

        data["collection_event_type"] = oCollection.get_event_type()
        data["existing_event_rule"] = criteria_set.get("event_rule", {})
        data["date_options"] = date_options
        return data

    def get_form_template(self):
        return "chiron/event_date_forms/relative_to_other_event.html"

    def validate_user_input(self, post_data):
        target_entry_id = post_data["target_entry_id"]
        self.cleaned["reference_date"] = post_data.get(
            "reference_date_{}".format(target_entry_id), "start"
        )
        range_start_days_from_target = post_data.get(
            "range_start_days_from_target_{}".format(target_entry_id), None
        )
        self.cleaned["range_start_days_from_target"] = int(range_start_days_from_target)
        self.cleaned["range_start_target"] = post_data.get(
            "range_start_target_{}".format(target_entry_id), "start"
        )
        range_end_days_from_target = post_data.get(
            "range_end_days_from_target_{}".format(target_entry_id), None
        )
        self.cleaned["range_end_days_from_target"] = int(range_end_days_from_target)
        self.cleaned["range_end_target"] = post_data.get(
            "range_end_target_{}".format(target_entry_id), "start"
        )
        self.cleaned["target_entry_id"] = target_entry_id
        # TODO: verify that end date is after start date
        return True

    def create_event_rule(self):
        rule = {
            "type": "relative_to_other_event",
            "reference_date": self.cleaned["reference_date"],
            "range_start_days_from_target": self.cleaned["range_start_days_from_target"],
            "range_start_target": self.cleaned["range_start_target"],
            "range_end_days_from_target": self.cleaned["range_end_days_from_target"],
            "range_end_target": self.cleaned["range_end_target"],
            "target_entry_id": self.cleaned["target_entry_id"],
        }
        return rule

    def event_rule_to_string(self):
        # try:
        criteria_set = cd_funcs.lookup_cohort_def_entry(self.cohort_def, self.entry_id)
        oCollection = models.Collection.objects.get(
            dataset=self.chironuser.dataset, permanent_id=criteria_set["collection_id"]
        )
        target_criteria_set = cd_funcs.lookup_cohort_def_entry(
            self.cohort_def, criteria_set["event_rule"]["target_entry_id"]
        )
        oTargetCollection = models.Collection.objects.get(
            dataset=self.chironuser.dataset, permanent_id=target_criteria_set["collection_id"]
        )
        target_event_name = qdef.get_criteria_set_name(
            self.chironuser, self.cohort_def, target_criteria_set["entry_id"]
        )
        if not self.existing_rule:
            return ""
        start_days = self._days_integer_to_string(
            self.existing_rule["range_start_days_from_target"]
        )
        end_days = self._days_integer_to_string(self.existing_rule["range_end_days_from_target"])
        if oCollection.get_event_type() == "interval":
            reference_date = self.existing_rule["reference_date"] + "s"
        else:
            reference_date = ""
        if oTargetCollection.get_event_type() == "interval":
            range_start_target = self.existing_rule["range_start_target"]
            range_end_target = self.existing_rule["range_end_target"]
        else:
            range_start_target = ""
            range_end_target = ""
        return "{} between {} {} {} and {} {} {}".format(
            reference_date,
            start_days,
            target_event_name,
            range_start_target,
            end_days,
            target_event_name,
            range_end_target,
        )
        # except Exception:
        #     return "[error reading event date rule]"

    def _days_integer_to_string(self, days_integer):
        if days_integer < 0:
            start_days = "{} days before".format(days_integer * (-1))
        elif days_integer == 0:
            start_days = "same day as"
        else:
            start_days = "{} days after".format(days_integer)
        return start_days

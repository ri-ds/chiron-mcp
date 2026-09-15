import math

from sqlalchemy import and_, or_

from chiron.processors.abstract import (
    CohortDefProcessor,
    CohortDefProcessorBuiltInUiMixin,
)
from chiron.query_engine import get_stattool
from chiron import helpers
from chiron.helpers import age_in_days_to_years_days


def age_in_days_to_label(age_in_days):
    years, days = age_in_days_to_years_days(age_in_days)
    return f"{years} years, {days} days"


class CohortDefDetailedAge(CohortDefProcessorBuiltInUiMixin, CohortDefProcessor):
    """
    When to use:

    * All values should either be numbers or null

    Optional arguments:

    * is_integer: (default: False) set to True if the number has no decimal value.
      NOTE: This does not round/force numbers to be integers, it only affects how histograms
      and statistics are calculated/displayed.

    """

    concept_type = "age"
    form_html_template = "chiron/processors/cohort_def_forms/age_field.html"
    form_js_template = "chiron/processors/cohort_def_forms/age_field.js"

    def __init__(self, chironuser, oDataset, oConcept, is_integer=False, *args, **kwargs):
        # pass is_integer='True' to mark as integer!
        super().__init__(chironuser, oDataset, oConcept, *args, **kwargs)
        self.is_integer = False if not is_integer else True

    def preprocess_statistics(self, cd):
        stats = get_stattool(self.chironuser, cd, self.concept, self.collection_prefilters)
        data = {}
        data["count_subjects_with_missing_values"] = stats.get_subjects_with_missing_values_count()
        data["count_missing_values"] = stats.get_missing_values_count()
        min_year, min_day = age_in_days_to_years_days(stats.get_min("python"))
        max_year, max_day = age_in_days_to_years_days(stats.get_max("python"))
        avg_year, avg_day = age_in_days_to_years_days(stats.get_avg("python"))
        data["stats"] = {
            "count_non_null": stats.get_non_null_values_count(),
            "min_year": min_year,
            "min_day": min_day,
            "max_year": max_year,
            "max_day": max_day,
            "avg_year": avg_year,
            "avg_day": avg_day,
            "unique_patients": stats.get_non_null_subject_count(),
        }
        data["histogram_data"] = stats.get_age_histogram()
        return data

    def aggregate_stats(self, stats):
        stats["count_subjects_with_missing_values"] = helpers.apply_min_limit(
            stats["count_subjects_with_missing_values"]
        )
        stats["count_missing_values"] = helpers.apply_min_limit(stats["count_missing_values"])
        stats["stats"]["count_non_null"] = helpers.apply_min_limit(
            stats["stats"]["count_non_null"]
        )
        stats["stats"]["unique_patients"] = helpers.apply_min_limit(
            stats["stats"]["unique_patients"]
        )
        for entry in stats["histogram_data"]:
            entry[1] = helpers.apply_min_limit(entry[1], set_to_zero=True)
        return stats

    def form_callback(self, get_data, cd):
        return self.get_statistics(cd)

    def form_callback_streaming(self, get_data, cd):
        data = self.form_callback(get_data, cd)
        yield data

    def get_form_options(self, cd, existing_cd_entry=None):
        """
        :include_null_and_missing:
        :existing_min: for editing query_type="date_range", min date filter as date string
        :existing_max:  for editing query_type="date_range", max date filter as date string
        :exclude_selected: if editing existing cd_entry, True if exclude_selected is checked
        """
        if existing_cd_entry is None:
            existing_cd_entry = {}
        existing_min = None
        existing_max = None
        if self.cleaned:
            existing_min = self.cleaned.get("minimum", None)
            existing_max = self.cleaned.get("maximum", None)
        else:
            if existing_cd_entry and "min" in existing_cd_entry:
                existing_min = existing_cd_entry["min"]
            if existing_cd_entry and "max" in existing_cd_entry:
                existing_max = existing_cd_entry["max"]
        include_null_and_missing = existing_cd_entry.get("include_null_and_missing", False)
        exclude_selected = existing_cd_entry.get("exclude_selected", False)
        existing_min_year, existing_min_day = age_in_days_to_years_days(existing_min)
        existing_max_year, existing_max_day = age_in_days_to_years_days(existing_max)
        return {
            "exclude_selected": exclude_selected,
            "include_null_and_missing": include_null_and_missing,
            "existing_min_year": existing_min_year,
            "existing_min_day": existing_min_day,
            "existing_max_year": existing_max_year,
            "existing_max_day": existing_max_day,
        }

    def validate_form(self, form_data):
        """
        :exclude_selected: (optional, default False) invert the query by excluding
          matching dates
        :include_null_and_missing: (optional, default False)
        :cd_numeric_min: minimum value as number
        :cd_numeric_max: maximum value as number
        """
        validated = True
        self.cleaned["include_null_and_missing"] = (
            True if form_data.get("include_null_and_missing") else False
        )
        self.cleaned["exclude_selected"] = True if form_data.get("exclude_selected") else False
        min_year = form_data.get("cd_age_min_year", None)
        min_day = form_data.get("cd_age_min_day", None)
        max_year = form_data.get("cd_age_max_year", None)
        max_day = form_data.get("cd_age_max_day", None)
        min_year = None if min_year == "" else min_year
        min_day = None if min_day == "" else min_day
        max_year = None if max_year == "" else max_year
        max_day = None if max_day == "" else max_day
        if (
            min_year is None
            and min_day is None
            and max_year is None
            and max_day is None
            and not self.cleaned["include_null_and_missing"]
        ):
            self.form_errors.append("Please enter a minimum or maximum age.")
            validated = False
        if min_year:
            try:
                min_year = float(min_year)
            except ValueError:
                self.form_errors.append("The min year must be a number.")
                validated = False
        if min_day:
            try:
                min_day = float(min_day)
            except ValueError:
                self.form_errors.append("The min day must be a number.")
                validated = False
        if max_year:
            try:
                max_year = float(max_year)
            except ValueError:
                self.form_errors.append("The max year must be a number.")
                validated = False
        if max_day:
            try:
                max_day = float(max_day)
            except ValueError:
                self.form_errors.append("The max day must be a number.")
                validated = False
        self.cleaned["minimum"] = None
        if min_year is not None or min_day is not None:
            min_year = 0 if min_year is None else min_year
            min_day = 0 if min_day is None else min_day
            self.cleaned["minimum"] = math.floor(min_year * 365.25) + min_day
        self.cleaned["maximum"] = None
        if max_year is not None or max_day is not None:
            max_year = 0 if max_year is None else max_year
            max_day = 0 if max_day is None else max_day
            self.cleaned["maximum"] = math.floor(max_year * 365.25) + max_day
        return validated

    def generate_cohort_def_entry(self, cd=None, existing_cd_entry=None):
        cd_entry = self._generate_cd_entry_template(
            {"min": self.cleaned["minimum"], "max": self.cleaned["maximum"]}
        )
        cd_entry["include_null_and_missing"] = self.cleaned["include_null_and_missing"]
        cd_entry["exclude_selected"] = self.cleaned["exclude_selected"]
        return cd_entry

    def display_entry_as_html(self, cd_entry, abbreviation="full"):
        response = ""
        if cd_entry.get("exclude_selected"):
            response = "exclude if: "
        if cd_entry.get("include_null_and_missing"):
            response += "{} not set".format(self.concept.name)
        has_min = False if "min" not in cd_entry or cd_entry["min"] in [None, ""] else True
        has_max = False if "max" not in cd_entry or cd_entry["max"] in [None, ""] else True
        if (has_min or has_max) and cd_entry.get("include_null_and_missing"):
            response += " OR "
        if has_min and has_max:
            response += "{} <= {} <= {}".format(
                age_in_days_to_label(cd_entry["min"]),
                self.concept.name,
                age_in_days_to_label(cd_entry["max"]),
            )
        elif has_min:
            response += "{} >= {}".format(
                self.concept.name,
                age_in_days_to_label(cd_entry["min"]),
            )
        elif has_max:
            response += "{} <= {}".format(
                self.concept.name,
                age_in_days_to_label(cd_entry["max"]),
            )
        return response

    def get_sql_alchemy_clause(self, cd_entry, table):
        min_limit = cd_entry.get("min", None)
        max_limit = cd_entry.get("max", None)
        include_nulls = cd_entry.get("include_null_and_missing", False)
        column = getattr(table.c, cd_entry["concept_id"])
        operators = []
        if include_nulls:
            operators.append(column.is_(None))
        if min_limit is not None and max_limit is not None:
            operators.append(and_(column >= min_limit, column <= max_limit))
        elif min_limit is not None:
            operators.append(column >= min_limit)
        elif max_limit is not None:
            operators.append(column <= max_limit)
        return or_(*operators)

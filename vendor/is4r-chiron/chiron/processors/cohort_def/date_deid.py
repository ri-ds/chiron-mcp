from dateutil.parser import parse

from chiron.query_engine import get_stattool
from chiron import helpers, chiron_settings

from .date import CohortDefDate


class CohortDefDateDeid(CohortDefDate):
    """
    This is a deidentified alternative to the DateFieldProcessor. If you use it in place of the
    DateFieldProcessor, only the date year is presented to the user.

    Typically, this is used in situations where you want users who can view PHI to see/query the
    whole date, and other users to see/query only the year. To do this in a concept, you will
    set has_phi to true and set both cohort_def_processor_deid_alt and display_processor_deid_alt
    to this.

    If you only ever need to use year, an alternative would be to set only the year in the
    research database as an integer and use the NumberFieldProcessor.

    """

    concept_type = "date_deid"
    form_html_template = "chiron/processors/cohort_def_forms/date_field_deid.html"
    form_js_template = "chiron/processors/cohort_def_forms/date_field_deid.js"
    # hide_form_if_missing_attributes = ["histogram_data_string"]

    def preprocess_statistics(self, cd):
        stats = get_stattool(self.chironuser, cd, self.concept, self.collection_prefilters)
        data = {}
        data["count_subjects_with_missing_values"] = stats.get_subjects_with_missing_values_count()
        data["count_missing_values"] = stats.get_missing_values_count()
        data["stats"] = {
            "count_non_null": stats.get_non_null_values_count(),
            "max": stats.get_max(),
            "min": stats.get_min(),
            "unique_patients": stats.get_non_null_subject_count(),
        }
        data["histogram_data"] = stats.get_number_histogram(is_integer=True, number_is_year=True)
        if chiron_settings.CHIRON_GET_QUERY_PERFORMANCE:
            data["perf"] = stats.time_analysis
            data["cache_mode"] = chiron_settings.CHIRON_USE_CACHES

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

    def validate_form(self, form_data):
        """
        :exclude_selected: (optional, default False) invert the query by excluding
          matching dates
        :include_null_and_missing: (optional, default False)
        :query_type: "date_range" or "relative_to_today"
        :cd_numeric_min: if query_type="date_range", the minimum year as YYYY
        :cd_numeric_max: if query_type="date_range", the maximum year as YYYY
        :days_ago: if query_type="relative_to_today", the number of days ago as an integer,
          for deidentified date query must be a multiple of 365
        """
        validated = True
        query_type = form_data.get("query_type", "date_range")
        self.cleaned["include_null_and_missing"] = (
            True if form_data.get("include_null_and_missing") else False
        )
        self.cleaned["exclude_selected"] = True if form_data.get("exclude_selected") else False
        if query_type == "date_range":
            self.cleaned["min"] = form_data.get("cd_numeric_min", None)
            self.cleaned["max"] = form_data.get("cd_numeric_max", None)
            if (
                not self.cleaned["min"]
                and not self.cleaned["max"]
                and not self.cleaned["include_null_and_missing"]
            ):
                self.form_errors.append("Please enter either a minimum or maximum value.")
                validated = False
            if self.cleaned["max"] and self.cleaned["min"]:
                try:
                    min = int(self.cleaned["min"])
                    max = int(self.cleaned["max"])
                    if max < min:
                        self.form_errors.append(
                            "The maximum year must be less than the minimum year."
                        )
                        validated = False
                except Exception:
                    pass
            if self.cleaned["min"]:
                try:
                    min = int(self.cleaned["min"])
                    if min < 1500 or min > 2200:
                        self.form_errors.append(
                            "The minimum value you entered is not a valid year."
                        )
                        validated = False
                except Exception:
                    self.form_errors.append("The minimum value you entered is not a valid year.")
                    validated = False
            if self.cleaned["max"]:
                try:
                    max = int(self.cleaned["max"])
                    if max < 1500 or max > 2200:
                        self.form_errors.append(
                            "The maximum value you entered is not a valid year."
                        )
                        validated = False
                except Exception:
                    self.form_errors.append("The maximum value you entered is not a valid year.")
                    validated = False
        elif query_type == "relative_to_today":
            try:
                self.cleaned["days_ago"] = int(form_data.get("days_ago", None))
            except Exception:
                self.form_errors.append("The number of days ago must be an integer.")
                validated = False
        self.cleaned["query_type"] = query_type
        return validated

    def generate_cohort_def_entry(self, cd=None, existing_cd_entry=None):
        query_type = self.cleaned["query_type"]
        cd_entry = dict()
        if query_type == "date_range":
            min = None
            max = None
            if self.cleaned["min"]:
                min = "1/1/{}".format(self.cleaned["min"])
            if self.cleaned["max"]:
                max = "12/31/{}".format(self.cleaned["max"])
            cd_entry = self._generate_cd_entry_template(
                {"min": min, "max": max, "query_type": query_type}
            )
        elif query_type == "relative_to_today":
            cd_entry = self._generate_cd_entry_template(
                {"days_ago": int(self.cleaned["days_ago"]), "query_type": query_type}
            )
        cd_entry["include_null_and_missing"] = self.cleaned["include_null_and_missing"]
        cd_entry["exclude_selected"] = self.cleaned["exclude_selected"]
        return cd_entry

    def can_run_deid_query(self, cd_entry):
        """
        The CD entry can be run if the start date is the first day of a year and the end
        date is the last day of a year. Or for relative to today, 'days_ago' should be a multiple
        of 365.
        """
        if cd_entry.get("query_type") == "date_range":
            min_str = cd_entry.get("min")
            max_str = cd_entry.get("max")
            if min_str:
                min = parse(min_str)
                if min.month != 1 or min.day != 1:
                    return False
            if max_str:
                max = parse(max_str)
                if max.month != 12 or max.day != 31:
                    return False
        elif cd_entry.get("query_type") == "relative_to_today":
            days_ago = cd_entry.get("days_ago", 0)
            if days_ago % 365 != 0:
                return False
        else:
            return False
        return True

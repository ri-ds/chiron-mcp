from datetime import date, timedelta

from dateutil.parser import parse
from sqlalchemy import and_, or_

from chiron import chiron_settings, helpers
from chiron.processors.abstract import CohortDefProcessor, CohortDefProcessorBuiltInUiMixin
from chiron.query_engine import get_stattool


class CohortDefDate(CohortDefProcessorBuiltInUiMixin, CohortDefProcessor):
    """
    When to use:

    * All values should either be a Python datetime object or null
    * You only care about the date component, typically you will want the time in your
      datetime values set to 0:00.

    """

    concept_type = "date"
    form_html_template = "chiron/processors/cohort_def_forms/date_field.html"
    form_js_template = "chiron/processors/cohort_def_forms/date_field.js"

    def preprocess_statistics(self, cd):
        data = {}
        stats = get_stattool(self.chironuser, cd, self.concept, self.collection_prefilters)
        data["count_subjects_with_missing_values"] = stats.get_subjects_with_missing_values_count()
        data["count_missing_values"] = stats.get_missing_values_count()
        max_date = stats.get_max()
        min_date = stats.get_min()
        data["stats"] = {
            "count_non_null": stats.get_non_null_values_count(),
            "unique_patients": stats.get_non_null_subject_count(),
        }
        if max_date:
            try:
                data["stats"]["max"] = max_date.strftime("%Y-%m-%d")
            except AttributeError:
                data["stats"]["max"] = max_date
        if min_date:
            try:
                data["stats"]["min"] = min_date.strftime("%Y-%m-%d")
            except AttributeError:
                data["stats"]["min"] = min_date
        data["histogram_data"] = stats.get_date_histogram()
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

    def _get_histogram_type(self, min_date, max_date):
        """
        yearly or monthly
        """
        if hasattr(self, "args") and "histogram_type" in self.args:
            return self.args["histogram_type"]
        diff = max_date - min_date
        if diff > timedelta(days=1461):  # about 4 years
            return "yearly"
        return "monthly"

    def _get_initial_form_val(self, input_name, existing_cd_entry, default=""):
        if input_name in self.cleaned:
            val = self.cleaned[input_name]
        elif existing_cd_entry and input_name in existing_cd_entry:
            val = existing_cd_entry[input_name]
        else:
            val = default
        if val is None:
            return ""
        return val

    def form_callback(self, get_data, cd):
        return self.get_statistics(cd)

    def form_callback_streaming(self, get_data, cd):
        data = self.form_callback(get_data, cd)
        yield data

    def get_form_options(self, cd, existing_cd_entry=None):
        """
        :query_type: "date_range" (default) or "relative_to_today"
        :existing_min: for editing query_type="date_range", min date filter as date string
        :existing_max:  for editing query_type="date_range", max date filter as date string
        :days_ago: for editing query_type="relative_to_today", days ago filter as integer
        :exclude_selected: if editing existing cd_entry, True if exclude_selected is checked
        :include_null_and_missing:
        """
        if existing_cd_entry is None:
            existing_cd_entry = {}
        existing_min = None
        existing_max = None
        days_ago = None
        query_type = self._get_initial_form_val("query_type", existing_cd_entry, "date_range")
        if query_type == "date_range":
            existing_min = self._get_initial_form_val("min", existing_cd_entry)
            existing_max = self._get_initial_form_val("max", existing_cd_entry)
        elif query_type == "relative_to_today":
            days_ago = self._get_initial_form_val("days_ago", existing_cd_entry)
        include_null_and_missing = existing_cd_entry.get("include_null_and_missing", False)
        exclude_selected = existing_cd_entry.get("exclude_selected", False)
        return {
            "exclude_selected": exclude_selected,
            "include_null_and_missing": include_null_and_missing,
            "query_type": query_type,
            "existing_min": existing_min,
            "existing_max": existing_max,
            "days_ago": days_ago,
        }

    def validate_form(self, form_data):
        """
        * **exclude_selected** - (optional, default False) invert the query by excluding
          matching dates
        * **include_null_and_missing** - (optional, default False)
        * **query_type** - "date_range" or "relative_to_today"
        * **cd_numeric_min** - if query_type="date_range", the minimum date ("MM/DD/YYYY" or any
          valid date string
        * **cd_numeric_max** - if query_type="date_range", the maximum date ("MM/DD/YYYY" or any
          valid date string
        * **days_ago** - if query_type="relative_to_today", the number of days ago as an integer
        """
        validated = True
        query_type = form_data.get("query_type", "date_range")
        self.cleaned["include_null_and_missing"] = (
            True if form_data.get("include_null_and_missing") else False
        )
        self.cleaned["exclude_selected"] = True if form_data.get("exclude_selected") else False
        if query_type == "date_range":
            input_min = form_data.get("cd_numeric_min", None)
            input_max = form_data.get("cd_numeric_max", None)
            output_min = None
            output_max = None
            if not input_min and not input_max and not self.cleaned["include_null_and_missing"]:
                self.form_errors.append("Please enter either a minimum or maximum value.")
                validated = False
            if input_max and input_min:
                try:
                    compare_min = parse(input_min)
                    compare_max = parse(input_max)
                    if compare_max < compare_min:
                        self.form_errors.append("The maximum must be less than the minimum.")
                        validated = False
                except Exception:
                    pass
            if input_min:
                try:
                    output_min = parse(input_min).strftime("%m/%d/%Y")
                except Exception:
                    self.form_errors.append("The minimum value you entered is not a valid date.")
                    validated = False
            if input_max:
                try:
                    output_max = parse(input_max).strftime("%m/%d/%Y")
                except Exception:
                    self.form_errors.append("The maximum value you entered is not a valid date.")
                    validated = False
            self.cleaned["min"] = output_min
            self.cleaned["max"] = output_max

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
            cd_entry = self._generate_cd_entry_template(
                {"min": self.cleaned["min"], "max": self.cleaned["max"], "query_type": query_type}
            )
        elif query_type == "relative_to_today":
            cd_entry = self._generate_cd_entry_template(
                {"days_ago": int(self.cleaned["days_ago"]), "query_type": query_type}
            )
        cd_entry["include_null_and_missing"] = self.cleaned["include_null_and_missing"]
        cd_entry["exclude_selected"] = self.cleaned["exclude_selected"]
        return cd_entry

    def display_entry_as_html(self, cd_entry, abbreviation="full"):
        response = ""
        if cd_entry.get("exclude_selected"):
            response = "exclude if: "
        query_type = cd_entry["query_type"]
        if query_type == "date_range":
            if cd_entry.get("include_null_and_missing"):
                response += "{} not set".format(self.concept.name)
            has_min = (
                False
                if "min" not in cd_entry or cd_entry["min"] is None or cd_entry["min"] == ""
                else True
            )
            has_max = (
                False
                if "max" not in cd_entry or cd_entry["max"] is None or cd_entry["max"] == ""
                else True
            )
            if (has_min or has_max) and cd_entry.get("include_null_and_missing"):
                response += " OR "
            if has_min and has_max:
                return response + "{} <= {} <= {}".format(
                    cd_entry["min"], self.concept.name, cd_entry["max"]
                )
            elif has_min:
                return response + "{} >= {}".format(
                    self.concept.name,
                    cd_entry["min"],
                )
            elif has_max:
                return response + "{} <= {}".format(
                    self.concept.name,
                    cd_entry["max"],
                )
            else:
                return response
        elif query_type == "relative_to_today":
            return response + "{} within the last {} days".format(
                self.concept.name, cd_entry["days_ago"]
            )
        return ""

    def get_sql_alchemy_clause(self, cd_entry, table):
        include_nulls = cd_entry.get("include_null_and_missing", False)
        column = getattr(table.c, cd_entry["concept_id"])
        query_type = cd_entry["query_type"]
        if query_type == "date_range":
            min_limit = cd_entry.get("min", None)
            if min_limit:
                min_limit = parse(min_limit)
            max_limit = cd_entry.get("max", None)
            if max_limit:
                max_limit = parse(max_limit)
            operators = []
            if include_nulls:
                operators.append(column.is_(None))
            if min_limit and max_limit:
                operators.append(and_(column >= min_limit, column <= max_limit))
            elif min_limit:
                operators.append(column >= min_limit)
            elif max_limit:
                operators.append(column <= max_limit)
            return or_(*operators)
        elif query_type == "relative_to_today":
            start_date = date.today() - timedelta(days=cd_entry["days_ago"])
            end_date = date.today()
            operators = []
            operators.append(and_(column >= start_date, column <= end_date))
            if include_nulls:
                operators.append(column.is_(None))
            return or_(*operators)

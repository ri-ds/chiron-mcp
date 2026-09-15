from sqlalchemy import and_, or_

from chiron.processors.abstract import CohortDefProcessor, CohortDefProcessorBuiltInUiMixin
from chiron.query_engine import get_stattool
from chiron import helpers, chiron_settings


class CohortDefNumber(CohortDefProcessorBuiltInUiMixin, CohortDefProcessor):
    """
    When to use:

    * All values should either be numbers or null

    Optional arguments:

    * is_integer: (default: False) set to True if the number has no decimal value.
      NOTE: This does not round/force numbers to be integers, it only affects how histograms
      and statistics are calculated/displayed.
    * number_is_year: (default: False) True if the number represents a calendar year like 2025.
      NOTE: This will modify how histograms and statistics are calculated/displayed to be better
      suited for year values.

    """

    concept_type = "number"
    form_html_template = "chiron/processors/cohort_def_forms/number_field.html"
    form_js_template = "chiron/processors/cohort_def_forms/number_field.js"

    def __init__(
        self,
        chironuser,
        oDataset,
        oConcept,
        is_integer=False,
        number_is_year=False,
        *args,
        **kwargs,
    ):
        super().__init__(chironuser, oDataset, oConcept, *args, **kwargs)
        self.is_integer = is_integer
        self.number_is_year = number_is_year

    def preprocess_statistics(self, cd):
        stats = get_stattool(self.chironuser, cd, self.concept, self.collection_prefilters)
        data = {}
        data["count_subjects_with_missing_values"] = stats.get_subjects_with_missing_values_count()
        data["count_missing_values"] = stats.get_missing_values_count()
        data["stats"] = {
            "count_non_null": stats.get_non_null_values_count(),
            "max": stats.get_max(),
            "min": stats.get_min(),
            "avg": stats.get_avg(),
            "unique_patients": stats.get_non_null_subject_count(),
        }
        data["histogram_data"] = stats.get_number_histogram(
            is_integer=self.is_integer, number_is_year=self.number_is_year
        )
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
        return {
            "exclude_selected": exclude_selected,
            "include_null_and_missing": include_null_and_missing,
            "existing_min": existing_min,
            "existing_max": existing_max,
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
        minimum = form_data.get("cd_numeric_min", None)
        maximum = form_data.get("cd_numeric_max", None)
        minimum = None if minimum == "" else minimum
        maximum = None if maximum == "" else maximum
        if minimum is None and maximum is None and not self.cleaned["include_null_and_missing"]:
            self.form_errors.append("Please enter a minimum or maximum value.")
            validated = False
        if minimum:
            try:
                minimum = float(minimum)
            except ValueError:
                self.form_errors.append("The min value must be a number.")
                validated = False
        if maximum:
            try:
                maximum = float(maximum)
            except ValueError:
                self.form_errors.append("The max value must be a number.")
                validated = False
        self.cleaned["minimum"] = minimum
        self.cleaned["maximum"] = maximum
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
                cd_entry["min"], self.concept.name, cd_entry["max"]
            )
        elif has_min:
            response += "{} >= {}".format(
                self.concept.name,
                cd_entry["min"],
            )
        elif has_max:
            response += "{} <= {}".format(
                self.concept.name,
                cd_entry["max"],
            )
        return response

    def get_sql_alchemy_bool_clause(self, table):
        column = getattr(table.c, self.concept.permanent_id)
        return or_(column != None, column != 0)  # noqa

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

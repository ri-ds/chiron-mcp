from sqlalchemy import and_, or_

from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from chiron.processors.abstract import CohortDefProcessor, CohortDefProcessorBuiltInUiMixin
from chiron.query_engine import get_stattool
from chiron import helpers, chiron_settings


class CohortDefNumberWithCategories(CohortDefProcessorBuiltInUiMixin, CohortDefProcessor):
    """
    When to use:

    * All values should be numbers, strings or null.

    * When importing during ETL, need to set cast_to_type "integer/string" or "float/string" which
      will store number values in the research database as {"num": 5} and string values as
      {"txt": "my value"}

    Optional arguments:

    * is_integer: (default: False) set to True if the number has no decimal value.
      NOTE: This does not round/force numbers to be integers, it only affects how histograms
      and statistics are calculated/displayed.

    """

    concept_type = "number_with_categories"
    form_html_template = "chiron/processors/cohort_def_forms/number_with_categories_field.html"
    form_js_template = "chiron/processors/cohort_def_forms/number_with_categories_field.js"

    def __init__(self, chironuser, oDataset, oConcept, is_integer=False, *args, **kwargs):
        # pass is_integer='True' to mark as integer!
        super().__init__(chironuser, oDataset, oConcept, *args, **kwargs)
        self.is_integer = False if not is_integer else True

    def preprocess_statistics(self, cd):
        data = {}
        stats = get_stattool(self.chironuser, cd, self.concept, self.collection_prefilters)
        data["count_subjects_with_missing_values"] = stats.get_subjects_with_missing_values_count()
        data["count_missing_values"] = stats.get_missing_values_count()
        data["stats"] = {
            "count_non_null": stats.get_non_null_values_count(subvalue="num"),
            "max": stats.get_max(),
            "min": stats.get_min(),
            "avg": stats.get_avg(),
            "unique_patients": stats.get_non_null_subject_count(subvalue="num"),
        }
        data["histogram_data"] = stats.get_number_histogram(
            is_integer=self.is_integer, subvalue="num"
        )
        data["values"] = stats.get_unique_values_with_counts(subvalue="txt")
        if data["values"]:
            data["max_count"] = data["values"][0]["count"]
        if chiron_settings.CHIRON_GET_QUERY_PERFORMANCE:
            data["perf"] = stats.time_analysis
            data["cache_mode"] = chiron_settings.CHIRON_USE_CACHES

        return data

    def aggregate_stats(self, stats):
        stats["count_subjects_with_missing_values"] = helpers.apply_min_limit(
            stats["count_subjects_with_missing_values"]
        )
        stats["count_missing_values"] = helpers.apply_min_limit(stats["count_missing_values"])
        if "max_count" in stats:
            stats["max_count"] = helpers.apply_min_limit(stats["max_count"])
        stats["stats"]["count_non_null"] = helpers.apply_min_limit(
            stats["stats"]["count_non_null"]
        )
        stats["stats"]["unique_patients"] = helpers.apply_min_limit(
            stats["stats"]["unique_patients"]
        )
        for entry in stats["histogram_data"]:
            entry[1] = helpers.apply_min_limit(entry[1], set_to_zero=True)
        for value in stats["values"]:
            value["count"] = helpers.apply_min_limit(value["count"])
            value["uniquePatientCount"] = helpers.apply_min_limit(value["uniquePatientCount"])
        return stats

    def get_fields_to_index(self):
        return [".txt", ".num"]

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
        response = {
            "exclude_selected": exclude_selected,
            "include_null_and_missing": include_null_and_missing,
            "existing_min": existing_min,
            "existing_max": existing_max,
        }
        response.update(self.get_form_options_category(cd, existing_cd_entry))
        return response

    def get_form_options_category(self, cd, existing_cd_entry=None):
        """
        :selected_values: if editing existing cd_entry, the values already selected
        :exclude_selected: if editing existing cd_entry, True if exclude_selected is checked
        """
        stats = get_stattool(self.chironuser, cd, self.concept, self.collection_prefilters)
        all_values = stats.lookup_unique_values(subvalue="txt")
        selected_values = []
        if "categories" in self.cleaned:
            selected_values = self.cleaned["categories"]
        elif existing_cd_entry and "categories" in existing_cd_entry:
            selected_values = existing_cd_entry["categories"]
        exclude_selected = False
        if existing_cd_entry:
            exclude_selected = existing_cd_entry.get("exclude_selected")
        return {
            "all_values": all_values,
            "selected_values": selected_values,
            "exclude_selected": exclude_selected,
        }

    def validate_form(self, form_data):
        validated = True

        # validate global fields
        self.cleaned["include_null_and_missing"] = (
            True if form_data.get("include_null_and_missing") else False
        )
        self.cleaned["exclude_selected"] = True if form_data.get("exclude_selected") else False

        # validate numeric data fields
        minimum = form_data.get("cd_numeric_min", None)
        maximum = form_data.get("cd_numeric_max", None)
        minimum = None if minimum == "" else minimum
        maximum = None if maximum == "" else maximum
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

        # validate text and at least one thing must be selected
        try:
            selected = form_data.getlist("selected_categories[]")
        except AttributeError:
            selected = form_data.get("selected_categories", [])
        self.cleaned["categories"] = [None if x == "" else x for x in selected]

        if (
            not self.cleaned["categories"]
            and minimum is None
            and maximum is None
            and not self.cleaned["include_null_and_missing"]
        ):
            self.form_errors.append("Please select a date range or non-numeric value.")
            validated = False

        return validated

    # def validate_form_categories(self, form_data):
    #     """
    #     :selected_categories: a list of categories to include (can include null as a
    #       selection)
    #     :exclude_selected: (optional, default False) invert the query by excluding
    #       provided values
    #     """
    #     try:
    #         selected = form_data.getlist("selected_categories[]")
    #     except AttributeError:
    #         selected = form_data.get("selected_categories")
    #     if not selected:
    #         self.cleaned["categories"] = []
    #         self.form_errors.append("Please select at least one value.")
    #         return False
    #     self.cleaned["categories"] = [None if x == "" else x for x in selected]
    #     return True

    def generate_cohort_def_entry(self, cd=None, existing_cd_entry=None):
        cd_entry = self._generate_cd_entry_template(
            {"min": self.cleaned["minimum"], "max": self.cleaned["maximum"]}
        )
        cd_entry["categories"] = self.cleaned["categories"]
        cd_entry["include_null_and_missing"] = self.cleaned["include_null_and_missing"]
        cd_entry["exclude_selected"] = self.cleaned["exclude_selected"]
        return cd_entry

    def display_entry_as_html(self, cd_entry, abbreviation="full"):
        responses = []
        if cd_entry.get("include_null_and_missing"):
            responses.append("{} not set".format(self.concept.name))
        number_response = self.build_html_string_for_numbers(cd_entry)
        if number_response:
            responses.append(number_response)
        if cd_entry.get("categories", []):
            cat_string = ", ".join(
                ('"{}"'.format(conditional_escape(t)) for t in cd_entry["categories"])
            )
            if len(cd_entry["categories"]) == 1:
                responses.append("{} = {}".format(self.concept.name, cat_string))
            else:
                responses.append("{} in {}".format(self.concept.name, cat_string))
        html = ""
        if cd_entry.get("exclude_selected", False):
            html += "EXCLUDE IF: "
        html += " OR ".join(responses)
        return html

    def build_html_string_for_numbers(self, cd_entry):
        response = ""
        has_min = False if "min" not in cd_entry or cd_entry["min"] in [None, ""] else True
        has_max = False if "max" not in cd_entry or cd_entry["max"] in [None, ""] else True
        if has_min and has_max:
            response = "{} <= {} <= {}".format(cd_entry["min"], self.concept.name, cd_entry["max"])
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

    def display_entry_as_html_catgories(self, cd_entry, abbreviation="full"):
        cat_list = []
        for category in cd_entry["categories"]:
            if category is None:
                cat_list.append(mark_safe("<em>[Not specified]</em>"))
            else:
                cat_list.append(category)
        cat_string = ", ".join(("{}".format(conditional_escape(t)) for t in cat_list))
        if len(cat_list) == 1:
            sign = "&ne;" if cd_entry.get("exclude_selected") else "="
            return "{} {} {}".format(self.concept.name, sign, cat_string)
        sign = "not in" if cd_entry.get("exclude_selected") else "in"
        return "{} {} {}".format(self.concept.name, sign, cat_string)

    def get_sql_alchemy_bool_clause(self, table):
        text_column = getattr(table.c, self.concept.permanent_id + "__txt")
        number_column = getattr(table.c, self.concept.permanent_id + "__num")
        text_clause = or_(text_column != None, text_column != "")  # noqa
        number_clause = or_(number_column != None, number_column != 0)  # noqa
        return and_(text_clause, number_clause)

    def get_sql_alchemy_clause(self, cd_entry, table):
        include_nulls = cd_entry.get("include_null_and_missing", False)
        terms = cd_entry["categories"]
        min_limit = cd_entry.get("min", None)
        max_limit = cd_entry.get("max", None)
        column = getattr(table.c, cd_entry["concept_id"])
        column_num = getattr(table.c, cd_entry["concept_id"] + "__num")
        column_txt = getattr(table.c, cd_entry["concept_id"] + "__txt")
        operators = []
        if include_nulls:
            operators.append(column.is_(None))
        if terms:
            operators.append(column_txt.in_(terms))
        if min_limit is not None and max_limit is not None:
            operators.append(and_(column_num >= min_limit, column_num <= max_limit))
        elif min_limit is not None:
            operators.append(column_num >= min_limit)
        elif max_limit is not None:
            operators.append(column_num <= max_limit)
        return or_(*operators)

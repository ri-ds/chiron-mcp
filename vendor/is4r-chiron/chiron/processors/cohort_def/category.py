from sqlalchemy import or_

from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape

from chiron.processors.abstract import CohortDefProcessor, CohortDefProcessorBuiltInUiMixin
from chiron.query_engine import get_stattool
from chiron import helpers, chiron_settings


class CohortDefCategory(CohortDefProcessorBuiltInUiMixin, CohortDefProcessor):
    """
    When to use:

    * All values should either be a string or null
    * Don't use if too many distinct values, use TextField instead
    * don't use if no values repeat (like IDs or free-text comments), use TextField instead
    * don't use if values are longer than one line of text

    """

    concept_type = "category"
    form_html_template = "chiron/processors/cohort_def_forms/category_field.html"
    form_js_template = "chiron/processors/cohort_def_forms/category_field.js"

    def get_concept_search_terms(self):
        """
        Return all the category names to help with searching for this concept
        """
        stats = get_stattool(self.chironuser, [], self.concept, self.collection_prefilters)
        values = stats.get_all_unique_strings(limit=2000)
        return "; ".join([str(x) for x in values])

    def preprocess_statistics(self, cd):
        """
        :values: a list of dicts with category, count, and uniquePatientCount for each
          category
        :max_count: the count for the category with the greatest number of records
        :count_missing_values: number of records with null or missing values
        :count_subjects_with_missing_values: number of subjects who have records with null or
          missing values
        """
        data = {}
        stats = get_stattool(self.chironuser, cd, self.concept, self.collection_prefilters)
        data["count_subjects_with_missing_values"] = stats.get_subjects_with_missing_values_count()
        data["count_missing_values"] = stats.get_missing_values_count()
        data["values"] = stats.get_unique_values_with_counts()
        if data["values"]:
            data["max_count"] = data["values"][0]["count"]
        if chiron_settings.CHIRON_GET_QUERY_PERFORMANCE:
            data["perf"] = stats.time_analysis
            data["cache_mode"] = chiron_settings.CHIRON_USE_CACHES

        return data

    def _apply_min_limit(self, value, min_limit, sub_value):
        if value < min_limit and value > 0:
            return sub_value
        return value

    def aggregate_stats(self, stats):
        stats["count_subjects_with_missing_values"] = helpers.apply_min_limit(
            stats["count_subjects_with_missing_values"]
        )
        stats["count_missing_values"] = helpers.apply_min_limit(stats["count_missing_values"])
        if "max_count" in stats:
            stats["max_count"] = helpers.apply_min_limit(stats["max_count"])
        for value in stats["values"]:
            value["count"] = helpers.apply_min_limit(value["count"])
            value["uniquePatientCount"] = helpers.apply_min_limit(value["uniquePatientCount"])
        return stats

    def form_callback(self, get_data, cd):
        return self.get_statistics(cd)

    def form_callback_streaming(self, get_data, cd):
        data = self.form_callback(get_data, cd)
        yield data

    def get_form_options(self, cd, existing_cd_entry=None):
        """
        :selected_values: if editing existing cd_entry, the values already selected
        :exclude_selected: if editing existing cd_entry, True if exclude_selected is checked
        """
        data = self.get_statistics(cd)
        all_values = [x["category"] for x in data["values"]]
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
        """
        :selected_categories: a list of categories to include (can include null as a
          selection)
        :exclude_selected: (optional, default False) invert the query by excluding
          provided values
        """
        try:
            selected = form_data.getlist("selected_categories[]")
        except AttributeError:
            selected = form_data.get("selected_categories")
        if not selected:
            self.cleaned["categories"] = []
            self.form_errors.append("Please select at least one value.")
            return False
        self.cleaned["categories"] = [None if x == "" else x for x in selected]
        self.cleaned["exclude_selected"] = form_data.get("exclude_selected")  # 'exclude' or None
        return True

    def generate_cohort_def_entry(self, cd=None, existing_cd_entry=None):
        cd_entry = self._generate_cd_entry_template()
        cd_entry["categories"] = self.cleaned["categories"]
        cd_entry["exclude_selected"] = True if self.cleaned["exclude_selected"] else False
        return cd_entry

    def display_entry_as_html(self, cd_entry, abbreviation="full"):
        cat_list = []
        for category in cd_entry["categories"]:
            if category is None:
                cat_list.append(mark_safe("<em>[Not specified]</em>"))
            else:
                cat_list.append(category)
        cat_string = ", ".join(('"{}"'.format(conditional_escape(t)) for t in cat_list))
        if len(cat_list) == 1:
            sign = "&ne;" if cd_entry.get("exclude_selected") else "="
            return "{} {} {}".format(self.concept.name, sign, cat_string)
        sign = "not in" if cd_entry.get("exclude_selected") else "in"
        return "{} {} {}".format(self.concept.name, sign, cat_string)

    def get_sql_alchemy_bool_clause(self, table):
        column = getattr(table.c, self.concept.permanent_id)
        return or_(column != None, column != "")  # noqa

    def get_sql_alchemy_clause(self, cd_entry, table):
        terms = cd_entry["categories"]
        include_nulls = None in terms
        terms = [x for x in terms if x is not None]
        column = getattr(table.c, cd_entry["concept_id"])
        if terms and include_nulls:
            return or_(column.in_(terms), column == None)  # noqa
        if terms:
            return column.in_(terms)
        if include_nulls:
            return column == None  # noqa

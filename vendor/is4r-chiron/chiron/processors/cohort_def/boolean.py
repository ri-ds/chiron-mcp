from sqlalchemy import or_

from chiron.processors import CohortDefCategory
from chiron.query_engine import get_stattool
from chiron import helpers, chiron_settings


class CohortDefBoolean(CohortDefCategory):
    """
    This is a subclass of CohortDefCategory and behaves similarly. When to use:

    * All values should be true, false, or null
    """

    concept_type = "boolean"

    def get_concept_search_terms(self):
        return ""

    def preprocess_statistics(self, cd):
        data = {}
        stats = get_stattool(self.chironuser, cd, self.concept, self.collection_prefilters)
        data["count_subjects_with_missing_values"] = stats.get_subjects_with_missing_values_count()
        data["count_missing_values"] = stats.get_missing_values_count()
        data["values"] = stats.get_unique_values_with_counts()
        for value in data["values"]:
            value["category"] = str(value["category"])
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
        for value in stats["values"]:
            value["count"] = helpers.apply_min_limit(value["count"])
            value["uniquePatientCount"] = helpers.apply_min_limit(value["uniquePatientCount"])
        return stats

    def get_form_options(self, cd, existing_cd_entry=None):
        """
        :selected_values: if editing existing cd_entry, the values already selected
        """
        selected_values = []
        selected_values = []
        if "categories" in self.cleaned:
            selected_values = self.cleaned["categories"]
        elif existing_cd_entry and "categories" in existing_cd_entry:
            selected_values = existing_cd_entry["categories"]
        selected_values_strings = []
        if True in selected_values:
            selected_values_strings.append("True")
        if False in selected_values:
            selected_values_strings.append("False")
        if None in selected_values:
            selected_values_strings.append(None)
        return {
            "all_values": ["True", "False"],
            "selected_values": selected_values_strings,
            "is_boolean_concept": True,
        }

    def validate_form(self, form_data):
        """
        :selected_categories: a list of categories to include (true, false, null)
        """
        try:
            selected = form_data.getlist("selected_categories[]")
        except AttributeError:
            selected = form_data.get("selected_categories")
        if not selected:
            self.cleaned["categories"] = []
            self.form_errors.append("Please select at least one value.")
            return False
        values = []
        for item in selected:
            if isinstance(item, bool):
                values.append(item)
            if item == "":
                values.append(None)
            else:
                values.append(item in ["True", "true", 1])
        self.cleaned["categories"] = values
        return True

    def generate_cohort_def_entry(self, cd=None, existing_cd_entry=None):
        cd_entry = self._generate_cd_entry_template()
        cd_entry["categories"] = self.cleaned["categories"]
        return cd_entry

    def display_entry_as_html(self, cd_entry, abbreviation="full"):
        cat_list = []
        if True in cd_entry["categories"]:
            cat_list.append("True")
        if False in cd_entry["categories"]:
            cat_list.append("False")
        if None in cd_entry["categories"]:
            cat_list.append("[not specified]")
        if len(cat_list) == 1:
            sign = "="
            return "{} {} {}".format(self.concept.name, sign, ", ".join(cat_list))
        sign = "in"
        return "{} {} {}".format(self.concept.name, sign, ", ".join(cat_list))

    def get_sql_alchemy_bool_clause(self, table):
        column = getattr(table.c, self.concept.permanent_id)
        return column == True  # noqa

    def get_sql_alchemy_clause(self, cd_entry, table):
        column = getattr(table.c, cd_entry["concept_id"])
        terms = cd_entry["categories"]  # can be True, False, or None
        operators = []
        for term in terms:
            operators.append(column.is_(term))
        return or_(*operators)

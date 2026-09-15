import re
import copy

from sqlalchemy import or_

from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape


from chiron.processors.abstract import (
    CohortDefProcessor,
    CohortDefProcessorBuiltInUiMixin,
)
from chiron.paginator import ReportPaginator
from chiron.query_engine import get_stattool
from chiron import chiron_settings


class CohortDefText(CohortDefProcessorBuiltInUiMixin, CohortDefProcessor):
    """
    When to use:

    * All values should either be a string or null
    * If possible values are a limited number of categories, consider using CategoryField
    * Good for IDs or free-text comments
    * Not great for long, multi-line free text - like notes - but shouldn't fail either

    """

    concept_type = "text"
    form_html_template = "chiron/processors/cohort_def_forms/text_field.html"
    form_js_template = "chiron/processors/cohort_def_forms/text_field.js"
    form_html_callback_template = "chiron/processors/cohort_def_forms/text_field_callback.html"
    terms_display_limit = 7

    def get_concept_search_terms(self):
        """
        Return all the category names to help with search, up to 2000
        """
        stats = get_stattool(self.chironuser, [], self.concept, self.collection_prefilters)
        values = stats.get_all_unique_strings(limit=2000)
        return "; ".join([str(x) for x in values])

    def preprocess_statistics(self, cd):
        # returns all matching values for this concept
        # search and pagination on this list are then implemented in the callback function
        data = {}
        stats = get_stattool(self.chironuser, cd, self.concept, self.collection_prefilters)
        data["values"] = stats.lookup_unique_values()
        data["count_missing_values"] = stats.get_missing_values_count()
        data["count_subjects_with_missing_values"] = stats.get_subjects_with_missing_values_count()
        data["perf"] = stats.time_analysis
        return data

    def aggregate_stats(self, stats):
        """
        This doesn't return any numbers, so no need to aggregate. If a text concept contains
        IDs or very specific comments, may want to hide the whole concept from users with
        aggregated access.
        """
        return stats

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

    def get_form_options(self, cd, existing_cd_entry=None):
        """
        :include_null_and_missing:
        :exclude_selected: if editing existing cd_entry, True if exclude_selected is checked
        :terms: List of terms as string separated by newlines
        """
        exclude_selected = False
        if existing_cd_entry:
            exclude_selected = existing_cd_entry.get("exclude_selected")
        include_null_and_missing = False
        if existing_cd_entry:
            include_null_and_missing = existing_cd_entry.get("include_null_and_missing")
        response = {
            "include_null_and_missing": include_null_and_missing,
            "exclude_selected": exclude_selected,
        }
        terms = self._get_initial_form_val("terms", existing_cd_entry)
        if terms:
            response["terms"] = "\n".join(terms)
        return response

    def form_callback(self, get_data, cd):
        """
        GET args:

        :search: (optional, default="") string with search term(s)
        :page: (optional, default=1) page number to retrieve as integer

        Response dict:

        * **first** - Index of first page
        * **last** - Index of last page
        * **previous** - Index of previous page
        * **next** - Index of next page
        * **pages** - Count of total pages
        """
        search_string = get_data.get("search", "")
        page = int(get_data.get("page", 1))
        records_per_page = int(get_data.get("records_per_page", 10))
        paginator = ReportPaginator(records_per_page, page)

        # get preprocessed list of unique values for this concept and cohort def
        precalc_data = self.get_statistics(cd)

        # filter by search string if search string
        if search_string:
            value_dict = {}  # use a dict instead of a list because it is faster to search
            # check regex if applicable, otherwise do normal search
            if search_string.startswith("/") and search_string.endswith("/"):
                # Handle regex search string
                for value in precalc_data["values"]:
                    regex_string = search_string.strip("/")
                    regex_match = re.search(regex_string, value)
                    if regex_match and value not in value_dict:
                        value_dict[value] = 1
            else:
                # Handle search string
                search_string = search_string.lower()
                for value in precalc_data["values"]:
                    if search_string in value.lower() and value not in value_dict:
                        value_dict[value] = 1
            values = list(value_dict.keys())
        else:
            values = precalc_data["values"]

        data = {}
        results = []
        skip = paginator.get_skip_value()
        for val in values[skip : skip + paginator.limit]:
            results.append({"unique_values": val})
        data["count"] = len(values)
        data["paginated_results"] = results
        data["count_subjects_with_missing_values"] = precalc_data[
            "count_subjects_with_missing_values"
        ]
        data["count_missing_values"] = precalc_data["count_missing_values"]
        # add in the paginator data
        paginator.set_collection_count(data["count"])
        data["paginator"] = paginator.json()
        if get_data.get("json_flavor", "original") == "select2":
            data = self._format_results_for_select2(data)
        if chiron_settings.CHIRON_GET_QUERY_PERFORMANCE:
            data["perf"] = precalc_data["perf"]
            data["cache_mode"] = chiron_settings.CHIRON_USE_CACHES
        return data

    def _format_results_for_select2(self, data):
        """
        https://select2.org
        """
        results = []
        for value in data["paginated_results"]:
            results.append(
                {
                    "id": value["unique_values"],
                    "text": value["unique_values"],
                }
            )
        return {"results": results}

    def form_callback_streaming(self, get_data, cd):
        data = self.form_callback(get_data, cd)
        yield data

    def generate_callback_html(self, oConcept, form_data):
        """
        GET args:

        * **search** - (optional, default="") string with search term(s)
        * **page** - (optional, default=1) page number to retrieve as integer

        Response dict:

        * **count** - Total count of matching results
        * **html** - HTML string of results
        """
        context = {
            "paginated_results": form_data.get("paginated_results"),
            "paginator": form_data.get("paginator"),
        }
        return {
            "count": form_data.get("count"),
            "html": render_to_string(
                "chiron/processors/cohort_def_forms/text_field_callback.html", context
            ),
        }

    def validate_form(self, form_data):
        """Validate Form

        Validates incoming form data.

        form_data fields:
        - chiron_text_field_selection: string with different terms separated by newline
        - exclude_selected: (optional, default False) invert the query by excluding provided values
        - include_null_and_missing: (optional, default False)

        :param form_data: Form data to validate
        :type form_data: dict
        :return: Validation pass or fail.
        :rtype: bool
        """
        # Get parameters
        # exclude_selected will be 'exclude' or None
        self.cleaned["exclude_selected"] = True if form_data.get("exclude_selected") else False
        self.cleaned["include_null_and_missing"] = (
            True if form_data.get("include_null_and_missing") else False
        )
        selected = form_data.get("chiron_text_field_selection", "")
        # Build entries list
        entries = [item.strip() for item in selected.splitlines()]
        # Initialize terms list
        terms = []
        # Use a set to track seen terms to avoid O(n²) duplicate checking
        seen_terms = set()
        # Get list of matching values from the research database
        stats = get_stattool(chironuser=self.chironuser, concept=self.concept)
        matching_values = stats.lookup_bulk_values(entries)
        # Convert matching_values to a set for O(1) lookups
        matching_values_set = set(matching_values)
        # Iterate through entries and validate them.
        # Set validated to false and add errors where applicable
        for entry in entries:
            if entry and entry not in seen_terms:
                if entry.startswith("/") and entry.endswith("/"):
                    regex_val = entry[1:-1]
                    try:
                        re.compile(regex_val)
                    except re.error as e:
                        self.form_errors.append("Regex error: {}".format(str(e)))
                elif entry not in matching_values_set:
                    self.form_warnings.append("Entry {} not found".format(entry))

                # Add to both the set (for O(1) duplicate checking) and list (for order preservation)
                seen_terms.add(entry)
                terms.append(entry)
        # Fail validation and add error if there are no values
        # and "include_null_and_missing" is not set
        if not terms and not self.cleaned["include_null_and_missing"]:
            self.form_errors.append("Please enter at least one value.")
        # Add terms
        self.cleaned["terms"] = terms
        if self.form_errors:
            return False
        ignore_warnings = form_data.get("ignore_warnings", False)
        if not ignore_warnings and self.form_warnings:
            return False
        return True

    def generate_cohort_def_entry(self, cd=None, existing_cd_entry=None):
        cd_entry = self._generate_cd_entry_template({"terms": self.cleaned["terms"]})
        cd_entry["exclude_selected"] = self.cleaned["exclude_selected"]
        cd_entry["include_null_and_missing"] = self.cleaned["include_null_and_missing"]
        return cd_entry

    def display_entry_as_html(self, cd_entry, abbreviation="full"):
        terms = copy.copy(cd_entry["terms"])
        if cd_entry.get("include_null_and_missing"):
            terms.append(mark_safe("<em>[Not specified]</em>"))

        if len(terms) <= self.terms_display_limit or abbreviation == "full":
            term_string = ", ".join(('"{}"'.format(conditional_escape(t)) for t in terms))
        else:
            term_string = ", ".join(
                (
                    '"{}"'.format(conditional_escape(t))
                    for t in terms[0 : self.terms_display_limit - 1]
                )
            )
            term_string += " ... ({} more), ".format(len(terms) - self.terms_display_limit)
            term_string += conditional_escape(terms[-1])
        if len(terms) == 1:
            sign = "&ne;" if cd_entry.get("exclude_selected") else "="
            return "{} {} {}".format(self.concept.name, sign, term_string)
        sign = "not in" if cd_entry.get("exclude_selected") else "in"
        return "{} {} {}".format(self.concept.name, sign, term_string)

    def _get_terms(self, cd_entry):
        terms = []
        for val in cd_entry["terms"]:
            if val.startswith("/") and val.endswith("/"):
                regex_val = val[1:-1]
                terms.append(re.compile(regex_val))
            elif val.startswith("/") and val.endswith("/i"):
                regex_val = val[1:-2]
                terms.append(re.compile(regex_val, re.IGNORECASE))
            else:
                terms.append(val)
        if cd_entry.get("include_null_and_missing"):
            terms.append("")
            terms.append(None)
        return terms

    def get_sql_alchemy_bool_clause(self, table):
        column = getattr(table.c, self.concept.permanent_id)
        return or_(column != None, column != "")  # noqa

    def get_sql_alchemy_clause(self, cd_entry, table):
        terms = cd_entry["terms"]
        include_nulls = cd_entry.get("include_null_and_missing", False)
        column = getattr(table.c, cd_entry["concept_id"])
        # Separate and handle regex terms from non-regex terms
        regex_list = []
        nonregex_terms = []
        for entry in terms:
            if entry.startswith("/") and entry.endswith("/"):
                regex_val = entry[1:-1]
                regex_list.append(column.regexp_match(regex_val))
            else:
                nonregex_terms.append(entry)
        # Matching terms
        matching_terms = column.in_(nonregex_terms)
        if regex_list:
            matching_terms = or_(matching_terms, *regex_list)
        # Create initial expression
        if (nonregex_terms or regex_list) and include_nulls:
            return or_(matching_terms, column.is_(None))
        if nonregex_terms or regex_list:
            return matching_terms
        if include_nulls:
            return column.is_(None)

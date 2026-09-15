import re
import copy

from sqlalchemy import or_
from sqlalchemy import cast, String
from sqlalchemy.dialects.postgresql import array, ARRAY
from django.utils.html import conditional_escape

from chiron.api.utils.general import string_to_bool
from chiron.processors import CohortDefText
from chiron.query_engine import get_stattool


class CohortDefOntology(CohortDefText):
    """
    When to use:
    * For linking terms to externally loaded ontologies
    * All values should either be a string or null,
         and should correspond to existing id's in one of the ontology we are
         currently using

    """

    concept_type = "ontology"
    form_html_template = "chiron/processors/cohort_def_forms/text_field.html"
    form_js_template = "chiron/processors/cohort_def_forms/text_field.js"
    form_html_callback_template = "chiron/processors/cohort_def_forms/text_field_callback.html"
    terms_display_limit = 7
    apihelper = None
    prepend_split_str = ": "
    results_list_limit = 1000

    def _load_apihelper(self):
        """
        Instantiates the ontology interface class if it hasn't been yet
        """
        from ontologies.interface_class import OntologyInterface as OI

        if self.apihelper is None:
            self.apihelper = OI(self.args["ontology_id"])
        return

    def _prepend_codes_encode(self, result):
        prepend_code = self.args["prepend_code"]
        prepend_result = result
        if prepend_code:
            for ont_item in result:
                ont_item["label"] = ont_item["code"] + self.prepend_split_str + ont_item["label"]
        return prepend_result

    def _prepend_codes_decode(self, entries):
        prepend_code = self.args["prepend_code"]

        def entry_map(e):
            e_idx = e.find(self.prepend_split_str)
            if e_idx > -1:
                return e[e_idx + len(self.prepend_split_str) :]
            return e

        prepend_result = entries
        if prepend_code:
            prepend_result = list(map(entry_map, entries))
        return prepend_result

    def _filter_values(self, result, cd, filter_data_exists):
        """
        @purpose:
            filters the ontology results list by codes existing in the dataset
        @params:
            result : list of ui formatted ontology results, with at minimum, a 'code' key
            cd: cohort definition
        @returns:
            filtered result, list of ui formatted ontology results
        """
        # don't run a query if there are no results to filter
        if len(result) == 0:
            return []
        values = set(map(lambda r: r["code"], result))
        if filter_data_exists:
            stats = get_stattool(self.chironuser, cd, self.concept, self.collection_prefilters)
            existing_dict = stats.lookup_ontology_codes(
                codes=values, include_counts=self.args["include_counts"]
            )
            filtered_result = []
            for r in result:
                if r["code"] in existing_dict:
                    r["hasDescendants"] = existing_dict[r["code"]]["hasDescendants"]
                    if "count" in existing_dict[r["code"]]:
                        r["count"] = existing_dict[r["code"]]["count"]
                        r["uniqueSubjectCount"] = existing_dict[r["code"]]["uniqueSubjectCount"]
                    filtered_result.append(r)
            return self._prepend_codes_encode(filtered_result)
        return self._prepend_codes_encode(result)

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
        data["values"] = stats.lookup_unique_values(subvalue="label")
        data["count_missing_values"] = stats.get_missing_values_count()
        ontology_counts = stats.lookup_ontology_codes(codes=["chiron_unrecognized_code"])
        data["count_unknown_ontology_values"] = (
            ontology_counts["chiron_unrecognized_code"]
            if "chiron_unrecognized_code" in ontology_counts
            else {}
        )
        data["count_subjects_with_missing_values"] = stats.get_subjects_with_missing_values_count()
        # NOTE: right now the UI always starts with filter_data_exists=True, so we can cache
        # the first (root) set of ontology items knowing that will be true. But if that ever
        # changes, caching this info might add time instead of saving it.
        self._load_apihelper()
        root_items = self.apihelper.get_root_elements(items_per_page=self.results_list_limit)[
            "data"
        ]
        root_items = self._filter_values(root_items, cd, filter_data_exists=True)
        data["root_items"] = root_items
        data["perf"] = stats.time_analysis
        return data

    def aggregate_stats(self, stats):
        """
        This doesn't return any numbers, so no need to aggregate. If a text concept contains
        IDs or very specific comments, may want to hide the whole concept from users with
        aggregated access.
        """
        return stats

    def get_form_options(self, cd, existing_cd_entry=None):
        """
        :include_null_and_missing:
        :exclude_selected: if editing existing cd_entry, True if exclude_selected is checked
        :terms: List of terms as ontology item objects {code, label, leaf}
        """
        exclude_selected = False
        include_null_and_missing = False
        include_ontology_unknown = False
        if existing_cd_entry:
            exclude_selected = existing_cd_entry.get("exclude_selected")
            include_null_and_missing = existing_cd_entry.get("include_null_and_missing")
            include_ontology_unknown = existing_cd_entry.get("include_ontology_unknown")
        response = {
            "include_null_and_missing": include_null_and_missing,
            "exclude_selected": exclude_selected,
            "include_ontology_unknown": include_ontology_unknown,
        }
        terms = self._get_initial_form_val("terms", existing_cd_entry)
        if terms:
            response["terms"] = terms

        return response

    def _perform_search(self, search_string, cd, base_stats, filter_data_exists):
        """
        @purpose:
            get all items that match the provided search string
        @params:
            search_string : list of ui formatted ontology results, with at minimum, a 'code' key
            cd: cohort definition
            base_stats: data dict generated by method preprocess_statistics()
            filter_data_exists: True if we only want items that are in our cohort
        @returns:
            list of ui formatted ontology results
        """
        # if this is toggled, then we search as normal
        if filter_data_exists:
            value_dict = {}  # use a dict instead of a list because it is faster to search
            # check regex if applicable, otherwise do normal search
            if search_string.startswith("/") and search_string.endswith("/"):
                # Handle regex search string
                for i, value in enumerate(base_stats["values"]):
                    regex_string = search_string.strip("/")
                    regex_match = re.search(regex_string, value)
                    if regex_match and value not in value_dict:
                        value_dict[value] = 1
            else:
                # Handle search string
                search_string = search_string.lower()
                for i, value in enumerate(base_stats["values"]):
                    if search_string in value.lower() and value not in value_dict:
                        value_dict[value] = 1
            values = list(value_dict.keys())[: self.results_list_limit]
            results = self._filter_values(
                self.apihelper.hydrate_label_list(values), cd, filter_data_exists
            )
            return results
        # if it is not, then we want to search the ontology service
        # currently does not support regex
        search_string = search_string.lower()
        results = self._prepend_codes_encode(self.apihelper.find_element(search_string))
        return results[: self.results_list_limit]

    def _lookup_item(self, code_string, cd, filter_data_exists):
        """
        @purpose:
            get info about specified item as well as info about all parents and children
        @params:
            code_string : code for ontology item of interest
            cd: cohort definition
            filter_data_exists: True if we only want items that are in our cohort
        @returns:
            ui formatted ontology results for item, parents (list), and children (list)
        """
        term = self.apihelper.get_item(code_string)
        term_code = term["code"]
        parents_list = self.apihelper.get_parent_elements(
            code_string, items_per_page=self.results_list_limit
        )["data"]
        children_list = self.apihelper.get_child_elements(
            code_string, items_per_page=self.results_list_limit
        )["data"]
        parents_dict = {item["code"]: item for item in parents_list}
        children_dict = {item["code"]: item for item in children_list}

        # combine 3 groups of values to run as one query
        combined_items = {**parents_dict, **children_dict}
        combined_items[term_code] = term
        results = self._filter_values(combined_items.values(), cd, filter_data_exists)

        # copy results back out into separate lists
        term = None
        parents = []
        children = []
        for item in results:
            code = item["code"]
            if code in parents_dict.keys():
                parents.append(item)
            if code in children_dict.keys():
                children.append(item)
            if code == term_code:
                term = item
        return term, parents, children

    def form_callback(self, get_data, cd):
        """
        GET args:

        :ontology_class: (optional, default=ONT_ROOT_ID) string of the bioontology class id
        :search: (optional, default="") string with search term(s) to directly query from db

        Response data dict:

        * **count** - integer, unique values
        * **action_results** - list of objects containing unique_values field
        * **parent_id** - string, bioontology.org class id of parent
        """
        search_string = get_data.get("search", "")
        filter_data_exists = string_to_bool(get_data.get("filter_data_exists", "true"))
        code_string = get_data.get("ontology_class")
        base_stats = self.get_statistics(cd)
        count = len(base_stats["values"])
        self._load_apihelper()
        term = None
        parents = []

        # if search string specified, use it to look up ontology items
        if search_string:
            results = self._perform_search(search_string, cd, base_stats, filter_data_exists)

        # if ontology item specified, get info about children, parents, and item itself
        elif code_string:
            term, parents, results = self._lookup_item(code_string, cd, filter_data_exists)

        # no search string and no ontology item, return info about "root items"
        # i.e. ontology items with no parents
        else:
            if filter_data_exists and "root_items" in base_stats:
                results = base_stats["root_items"]
            else:
                results = self.apihelper.get_root_elements(items_per_page=self.results_list_limit)[
                    "data"
                ]
                results = self._filter_values(results, cd, filter_data_exists)

        results.sort(key=lambda r: r["label"])
        data = {
            "count": count,
            "action_results": results,
            "parents": parents,
            "term": term,
            "count_subjects_with_missing_values": base_stats["count_subjects_with_missing_values"],
            "count_unknown_ontology_values": base_stats["count_unknown_ontology_values"],
            "count_missing_values": base_stats["count_missing_values"],
        }
        return data

    def form_callback_streaming(self, get_data, cd):
        data = self.form_callback(get_data, cd)
        yield data

    def validate_form(self, form_data):
        """Validate Form

        Validates incoming form data.

        form_data fields:
        - chiron_ontology_field_selection: string with different labels or code terms separated by
            newline
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
        self.cleaned["include_ontology_unknown"] = (
            True if form_data.get("include_ontology_unknown") else False
        )
        selected = form_data.get("chiron_ontology_field_selection", "")
        self._load_apihelper()

        stats = get_stattool(chironuser=self.chironuser, concept=self.concept)
        terms = []
        entry_idx = 0
        if isinstance(selected, str):
            entries = [item.strip() for item in selected.splitlines()]
        else:
            entries = selected

        # remove prepended codes from any label selected entries
        entries = self._prepend_codes_decode(entries)

        # need to find ontology matches, get the codes
        matching_codes_hydrated = self.apihelper.hydrate_code_list(entries)
        matching_labels_hydrated = self.apihelper.hydrate_label_list(entries)
        ontology_matches = matching_codes_hydrated + matching_labels_hydrated
        code_label_lookup = {}
        label_code_lookup = {}
        for m in ontology_matches:
            code_label_lookup[m["code"]] = m["label"]
            label_code_lookup[m["label"]] = m["code"]

        # Get list of matching values from the dataset, using only the existing codes
        # nonexistent selection happens with the include_ontology_unknown toggle
        if len(list(code_label_lookup.keys())) > 0:
            matching_codes = stats.lookup_ontology_codes(
                list(code_label_lookup.keys()), include_counts=False
            )
            matching_codes = set(matching_codes.keys())
        else:
            matching_codes = []
        for entry in entries:
            if entry:
                # get code from either code list or label list
                if entry in code_label_lookup:
                    entry_code = entry
                elif entry in label_code_lookup:
                    entry_code = label_code_lookup[entry]
                else:
                    entry_code = None

                if entry_code:
                    # if it exists but not in the dataset
                    if entry_code not in matching_codes:
                        self.form_warnings.append("Entry {} not found in dataset".format(entry))
                    else:
                        entry_item = None
                        for item in ontology_matches:
                            if item["code"] == entry_code:
                                entry_item = item
                                break

                        if entry_item:
                            if entry_item not in terms:
                                terms.append(entry_item)
                        # if it exists in the data but not in the ontology
                        else:
                            self.form_warnings.append(
                                "Entry {} not found in ontology".format(entry)
                            )
                # if it doesn't exist anywhere
                else:
                    self.form_warnings.append("Entry {} not found".format(entry))

            entry_idx += 1

        # Fail validation and add error if there are no values
        # and "include_null_and_missing" is not set
        if (
            not terms
            and not self.cleaned["include_null_and_missing"]
            and not self.cleaned["include_ontology_unknown"]
        ):
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
        self._load_apihelper()
        terms = self.cleaned["terms"]
        cd_entry = self._generate_cd_entry_template(
            {
                "terms": self._prepend_codes_encode(terms),
            }
        )
        cd_entry["exclude_selected"] = self.cleaned["exclude_selected"]
        cd_entry["include_null_and_missing"] = self.cleaned["include_null_and_missing"]
        cd_entry["include_ontology_unknown"] = self.cleaned["include_ontology_unknown"]
        return cd_entry

    def display_entry_as_html(self, cd_entry, abbreviation="full"):
        self._load_apihelper()
        item_terms = copy.copy(cd_entry["terms"])
        terms = list(map(lambda t: t["label"], item_terms))
        if cd_entry.get("include_null_and_missing"):
            terms.append("[Not specified]")
        if cd_entry.get("include_ontology_unknown"):
            terms.append("[All unmatched codes]")
        if len(terms) == 1:
            sign = "&ne;" if cd_entry.get("exclude_selected") else "="
            return "{} {} {} and dependent terms".format(self.concept.name, sign, ", ".join(terms))
        sign = "not in" if cd_entry.get("exclude_selected") else "in"

        if len(terms) <= self.terms_display_limit:
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

        return "{} {} {} and dependent terms".format(self.concept.name, sign, term_string)

    def _get_terms(self, cd_entry):
        self._load_apihelper()
        terms = set([])
        for v in cd_entry["terms"]:
            terms.add(v["code"])
        ont_list = list(terms)
        if cd_entry.get("include_null_and_missing"):
            ont_list.append("")
            ont_list.append(None)
        if cd_entry["include_ontology_unknown"]:
            ont_list.append("chiron_unrecognized_code")
        return ont_list

    def get_sql_alchemy_clause(self, cd_entry, table):
        codes = self._get_terms(cd_entry)
        include_nulls = cd_entry.get("include_null_and_missing", False)
        code_column = getattr(table.c, cd_entry["concept_id"] + "__code")
        hierarchy_column = getattr(table.c, cd_entry["concept_id"] + "__hierarchy")
        if codes and include_nulls:
            code_array_literal = cast(array(codes), ARRAY(String(150)))
            return or_(
                # code_column.in_(codes),
                code_column is None,
                hierarchy_column.overlap(code_array_literal),
            )
        if codes:
            code_array_literal = cast(array(codes), ARRAY(String(150)))
            # return or_(code_column.in_(codes), hierarchy_column.overlap(code_array_literal))
            return hierarchy_column.overlap(code_array_literal)
        if include_nulls:
            return column is None  # noqa
        return None

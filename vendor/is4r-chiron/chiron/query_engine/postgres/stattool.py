from datetime import datetime
from sqlalchemy.exc import CompileError

from chiron.query_engine.abstract_stattool import AbstractStatTool
from chiron.query_engine.postgres.sql_alchemy_queries.query_builder import SqlAlchemyQueryBuilder
from chiron.query_engine.display import get_display_values
from chiron.query_engine.postgres.database import get_sql_alchemy_db_engine

from chiron.query_engine.postgres.data_vis import create_date_histogram as date_hist
from chiron.query_engine.postgres.data_vis import create_age_histogram as age_hist
from chiron.query_engine.data_vis import get_histogram_object
from chiron import helpers


from chiron.query_definition.table import Table


class StatToolPostgres(AbstractStatTool):
    def run(self, label, statement, return_scope="all"):
        """Runs a function or method and collects performance/data info.

        :param label: what to call this query in any logs or print statements
        :param statement: the sqlalchemy statement to run
        :param return_scope: "all", "first_row", "first_col", "first_val"
        :return: executed statement result
        """
        start = datetime.now()
        try:
            sql_string = str(statement.compile(compile_kwargs={"literal_binds": True}))
        except CompileError:
            sql_string = str(statement)
        helpers.print_query_info(f"--START {label}")
        helpers.print_query_info(sql_string)
        with get_sql_alchemy_db_engine(self.dataset).connect() as conn:
            if return_scope == "all":
                response = []
                for row in conn.execute(statement):
                    response.append(list(row))
            elif return_scope == "first_row":
                response = conn.execute(statement).first()
            elif return_scope == "first_col":
                response = []
                for row in conn.execute(statement):
                    response.append(row[0])
            else:  # first_val
                response = conn.execute(statement).first()[0]
        if self.analyze_performance:
            end = datetime.now()
            diff = round((end - start).total_seconds(), 1)
            helpers.print_query_info(f"query completed in {diff} seconds")
        helpers.print_query_info(f"--END {label}")
        return response

    def build_table_for_stat(self, concept_id, aggregation):
        """Generate a generic table object for a concept when there is no table definition.

        :param str concept_id: The permanent_id of the concept to use
        :param str aggregation: The aggregation method to use ("avg", "min", etc.)
        :return: a query_definition.table object
        """
        table_def = {
            "fields": [
                {
                    "entry_id": "dummyid",
                    "concept_id": concept_id,
                    "aggregate": True,
                    "aggregation_method": aggregation,
                }
            ]
        }
        table = Table(self.chironuser, self.cohort.cohort_def, table_def)
        return table

    def _save_to_stat_cache(self, keys, stat_value):
        """Save a value to the cache for a specific stat.

        :param keys: The list of values that uniquely identify the stat, typically this will
          be the name of the stat followed by any specific parameters related to the stat.
        :type keys: list
        :param stat_value: the value of the stat
        :type stat_value: any
        """
        reference_point = self.cache
        for index, key in enumerate(keys):
            if index != len(keys) - 1:
                if key not in reference_point:
                    reference_point[key] = {}
                reference_point = reference_point[key]
            else:
                reference_point[key] = stat_value
        return stat_value

    def _get_from_stat_cache(self, keys):
        """Get a value from the cache for a specific stat.

        :param keys: the list of values that uniquely identify the stat
        :type keys: list
        :return: whether that stat was in the cache, the value of the stat
        :rtype: (bool, any)
        """
        reference_point = self.cache
        for key in keys:
            if key not in reference_point:
                return False, None
            reference_point = reference_point[key]
        return True, reference_point

    def get_non_null_subject_count(self, subvalue=None):
        """Count subjects with at least one non-null value for this concept.

        :param str subvalue: For complex (dict) data types, the name of subvalue to reference,
          or None to reference main value
        :return: count of subjects with at least one value for concept
        :rtype: integer
        """
        cache_keys = ["non_null_subject_count", subvalue]
        is_cached, cached_value = self._get_from_stat_cache(cache_keys)
        if is_cached:
            return cached_value
        builder = SqlAlchemyQueryBuilder(
            self.chironuser,
            self.cohort,
            target_collection=self.concept.collection,
            prefilters=self.collection_prefilters,
        )
        statement = builder.get_sql_statement_not_null_subject_count(self.concept, subvalue)
        subject_count = self.run("stat1", statement, "first_val")
        cached_value = self._save_to_stat_cache(cache_keys, subject_count)
        return cached_value

    def get_non_null_values_count(self, subvalue=None):
        """Count number of non-null values for this concept.

        :param str subvalue: For complex (dict) data types, the name of subvalue to reference,
          or None to reference main value
        :return: count total non-null values for concept
        :rtype: integer
        """
        cache_keys = ["non_null_values_count", subvalue]
        is_cached, cached_value = self._get_from_stat_cache(cache_keys)
        if is_cached:
            return cached_value
        builder = SqlAlchemyQueryBuilder(
            self.chironuser,
            self.cohort,
            target_collection=self.concept.collection,
            prefilters=self.collection_prefilters,
        )
        statement = builder.get_sql_statement_not_null_value_count(self.concept, subvalue)
        value_count = self.run("stat2", statement, "first_val")
        cached_value = self._save_to_stat_cache(cache_keys, value_count)
        return cached_value

    def get_missing_values_count(self, subvalue=None):
        """Count of values that are None or empty string.

        If concept is in a subcollection, also includes count of subjects with no subcol record.

        :param str subvalue: For complex (dict) data types, the name of subvalue to reference,
          or None to reference main value
        :return: count total null or empty values for concept
        :rtype: integer
        """
        cache_keys = ["missing_values_count", subvalue]
        is_cached, cached_value = self._get_from_stat_cache(cache_keys)
        if is_cached:
            return cached_value
        builder = SqlAlchemyQueryBuilder(
            self.chironuser,
            self.cohort,
            target_collection=self.concept.collection,
            prefilters=self.collection_prefilters,
        )
        statement = builder.get_sql_statement_null_value_count(self.concept)
        value_count = self.run("stat3A", statement, "first_val")
        cached_value = self._save_to_stat_cache(cache_keys, value_count)
        return cached_value

    def get_subjects_with_missing_values_count(self, subvalue=None):
        """Count of subjects with no values for this concept.

        A subject will have no values for the concept if there are no records in this collection
        associated with the subject, or if all the records associated have values of None or
        empty string.

        :param str subvalue: For complex (dict) data types, the name of subvalue to reference,
          or None to reference main value
        :return: count total subjects with no values for this concept
        :rtype: integer
        """
        cache_keys = ["subjects_with_missing_values_count", subvalue]
        is_cached, cached_value = self._get_from_stat_cache(cache_keys)
        if is_cached:
            return cached_value
        builder = SqlAlchemyQueryBuilder(
            self.chironuser,
            self.cohort,
            target_collection=self.concept.collection,
            prefilters=self.collection_prefilters,
        )
        statement = builder.get_sql_statement_null_subject_count(self.concept)
        subject_count = self.run("stat3B", statement, "first_val")
        cached_value = self._save_to_stat_cache(cache_keys, subject_count)
        return cached_value

    def get_min(self, output_type="json"):
        """Returns the minimum value for a concept.

        :param str output_type: "html", "python", "json","csv" - This information will be used to
          set appropriate data values. For example, if "csv" is selected then dates will be
          converted to date strings.
        :return: The minimum value, data type will depend on Concept data type and selected
          output_type.
        """
        cache_keys = ["min_value", output_type]
        is_cached, cached_value = self._get_from_stat_cache(cache_keys)
        if is_cached:
            return cached_value
        """The minimum value for this concept."""
        concept_id = self.concept.permanent_id
        processor = self.concept.get_cohort_def_processor(self.chironuser)
        if processor.concept_type in ["date", "date_deid"]:
            table = self.build_table_for_stat(concept_id, "min_date")
        else:
            table = self.build_table_for_stat(concept_id, "min")
        builder = SqlAlchemyQueryBuilder(
            self.chironuser,
            self.cohort,
            table,
            target_collection=self.concept.collection,
            prefilters=self.collection_prefilters,
        )
        statement = builder.get_sql_statement(0, 1)
        response = self.run("stat5", statement)
        response = builder.run_after_query_aggregation_modification(response)
        response = get_display_values(response, self.chironuser, self.cohort, table, output_type)
        cached_value = self._save_to_stat_cache(cache_keys, response[0][0])
        return cached_value

    def get_max(self, output_type="json"):
        """Returns the maximum value for a concept.

        :param str output_type: "html", "python", "json","csv" - This information will be used to
          set appropriate data values. For example, if "csv" is selected then dates will be
          converted to date strings.
        :return: The minimum value, data type will depend on Concept data type and selected
          output_type.
        """
        cache_keys = ["max_value", output_type]
        is_cached, cached_value = self._get_from_stat_cache(cache_keys)
        if is_cached:
            return cached_value
        concept_id = self.concept.permanent_id
        processor = self.concept.get_cohort_def_processor(self.chironuser)
        if processor.concept_type in ["date", "date_deid"]:
            table = self.build_table_for_stat(concept_id, "max_date")
        else:
            table = self.build_table_for_stat(concept_id, "max")
        builder = SqlAlchemyQueryBuilder(
            self.chironuser,
            self.cohort,
            table,
            target_collection=self.concept.collection,
            prefilters=self.collection_prefilters,
        )
        statement = builder.get_sql_statement(0, 1)
        response = self.run("stat6", statement)
        response = builder.run_after_query_aggregation_modification(response)
        response = get_display_values(response, self.chironuser, self.cohort, table, output_type)
        cached_value = self._save_to_stat_cache(cache_keys, response[0][0])
        return cached_value

    def get_avg(self, output_type="json"):
        """Returns the average value for a concept.

        :param str output_type: "html", "python", "json","csv" - This information will be used to
          set appropriate data values. For example, if "csv" is selected then dates will be
          converted to date strings.
        :return: The minimum value, data type will depend on Concept data type and selected
          output_type.
        :rtype: float
        """
        cache_keys = ["avg_value", output_type]
        is_cached, cached_value = self._get_from_stat_cache(cache_keys)
        if is_cached:
            return cached_value
        concept_id = self.concept.permanent_id
        table = self.build_table_for_stat(concept_id, "average")
        builder = SqlAlchemyQueryBuilder(
            self.chironuser,
            self.cohort,
            table,
            target_collection=self.concept.collection,
            prefilters=self.collection_prefilters,
        )
        statement = builder.get_sql_statement(0, 1)
        response = self.run("stat7", statement)
        response = builder.run_after_query_aggregation_modification(response)
        response = get_display_values(response, self.chironuser, self.cohort, table, output_type)
        value = response[0][0]
        cached_value = self._save_to_stat_cache(cache_keys, value)
        return cached_value

    def get_number_histogram(self, is_integer=False, number_is_year=False, subvalue=None):
        """Get list of bin labels and counts representing a histogram for a numeric concept.

        :param bool number_is_year: Year histograms may handle bin grouping differently.
        :param str subvalue: For complex (dict) data types, the name of subvalue to reference,
          or None to reference main value
        :return: label/count pairs for each bin
        :rtype: list of lists
        """
        cache_keys = ["number_histogram", is_integer, number_is_year, subvalue]
        is_cached, cached_value = self._get_from_stat_cache(cache_keys)
        if is_cached:
            return cached_value
        min_val = self.get_min(output_type="python")
        max_val = self.get_max(output_type="python")
        value_count = self.get_non_null_values_count(subvalue=subvalue)
        if min_val is None or max_val is None:
            return []
        if number_is_year:
            histogram = get_histogram_object("year", value_count, min_val, max_val)
        elif is_integer:
            histogram = get_histogram_object("integer", value_count, min_val, max_val)
        else:
            histogram = get_histogram_object("float", value_count, min_val, max_val)
        histogram_bins = histogram.get_bins()
        builder = SqlAlchemyQueryBuilder(
            self.chironuser,
            self.cohort,
            target_collection=self.concept.collection,
            prefilters=self.collection_prefilters,
        )
        statement = builder.get_sql_statement_for_histogram(
            self.concept, histogram.bin_cutoffs, subvalue
        )
        result = self.run("stat8", statement)
        response = []
        previous_bin_index = None
        for row in result:
            bin_index = row[0] - 1
            # postgres will not return any bins with 0 count, but we want them in our API response
            if previous_bin_index is not None and previous_bin_index != bin_index - 1:
                while previous_bin_index < bin_index - 1:
                    previous_bin_index += 1
                    entry = [histogram_bins[previous_bin_index]["label"], 0]
                    response.append(entry)
            entry = [histogram_bins[bin_index]["label"], row[1]]
            response.append(entry)
            previous_bin_index = bin_index
        cached_value = self._save_to_stat_cache(cache_keys, response)
        return cached_value

    def get_age_histogram(self, subvalue=None):
        """Get list of bin labels and counts representing a histogram for an age.

        :param str subvalue: For complex (dict) data types, the name of subvalue to reference,
          or None to reference main value
        :return: label/count pairs for each bin
        :rtype: list of lists
        """
        cache_keys = ["age_histogram", subvalue]
        is_cached, cached_value = self._get_from_stat_cache(cache_keys)
        if is_cached:
            return cached_value
        min_val = self.get_min(output_type="python")
        max_val = self.get_max(output_type="python")
        if min_val is None or max_val is None:
            return []
        if min_val == max_val:
            return []
        min_val = int(float(min_val))
        max_val = int(float(max_val))
        bin_limits = age_hist.get_histogram_bin_limits(min_val, max_val, is_integer=True)
        histogram_bins = age_hist.get_histogram_bins(min_val, max_val)
        builder = SqlAlchemyQueryBuilder(
            self.chironuser,
            self.cohort,
            target_collection=self.concept.collection,
            prefilters=self.collection_prefilters,
        )
        statement = builder.get_sql_statement_for_histogram(self.concept, bin_limits, subvalue)
        response = self.run("stat8b", statement)
        histogram_data = {}
        for row in response:
            histogram_data[row[0]] = row[1]
        response = []
        for bin in histogram_bins:
            val = histogram_data.get(bin[1], 0)
            response.append([bin[0], val])
        # TODO: do I need to process data into display values?
        cached_value = self._save_to_stat_cache(cache_keys, response)
        return cached_value

    def get_date_histogram(self, subvalue=None):
        """Get list of bin labels and counts representing a histogram for a date concept.

        :param str subvalue: For complex (dict) data types, the name of subvalue to reference,
          or None to reference main value
        :return: label/count pairs for each bin
        :rtype: list of lists
        """
        cache_keys = ["date_histogram", subvalue]
        is_cached, cached_value = self._get_from_stat_cache(cache_keys)
        if is_cached:
            return cached_value
        min_val = self.get_min(output_type="python")
        max_val = self.get_max(output_type="python")
        if min_val is None or max_val is None:
            return []
        bin_limits = date_hist.get_histogram_bin_limits(min_val, max_val)
        histogram_bins = date_hist.get_histogram_bins(min_val, max_val)
        builder = SqlAlchemyQueryBuilder(
            self.chironuser,
            self.cohort,
            target_collection=self.concept.collection,
            prefilters=self.collection_prefilters,
        )
        statement = builder.get_sql_statement_for_date_histogram(self.concept, bin_limits)
        response = self.run("stat8c", statement)
        histogram_data = {}
        for row in response:
            histogram_data[row[0]] = row[1]
        response = []
        for bin in histogram_bins:
            val = histogram_data.get(bin[1], 0)
            response.append([bin[0], val])
        # TODO: do I need to process data into display values?
        cached_value = self._save_to_stat_cache(cache_keys, response)
        return cached_value

    def lookup_ontology_codes(self, codes=None, include_counts=False):
        """Finds which ontology codes are in the cohort/dataset.

        This is specific to the ontology datatype which includes a hierarchy
        field to define the hierarchy. Ontology codes with existing descendants
        will also be included even if not present in the data themselves.

        The optional count values are "count" for the number of code (and all
        descendant codes) occurrences and "uniqueSubjectCount" is the total
        number of unique subjects associated with this code (and all descendant
        codes).

        :param array codes: The list of ontology codes to check, or None to get all codes
        :param bool include_counts: Include columns for record and subject counts (slower)
        :return: dict of key=code, value={count, uniqueSubjectCount} if include_counts, else
            value is empty dict; Any codes with count=0 are excluded from dict.
        :rtype: dict
        """
        builder = SqlAlchemyQueryBuilder(
            self.chironuser,
            self.cohort,
            target_collection=self.concept.collection,
            prefilters=self.collection_prefilters,
        )
        statement = builder.get_sql_statement_for_ontology_codes(self.concept, codes)
        response = self.run("stat25", statement)
        count_dict = {}
        for row in response:
            count_dict[row[0]] = {
                "hasDescendants": row[1],
            }
        if include_counts:
            statement = builder.get_sql_statement_for_ontology_counts(self.concept, codes)
            response = self.run("stat26", statement)
            for row in response:
                count_dict[row[0]]["count"] = row[1]
                count_dict[row[0]]["uniqueSubjectCount"] = row[2]
        return count_dict

    def get_unique_values_with_counts(self, sort_by="count", subvalue=None):
        """Get a list of unique concept values with frequency counts.

        For each distinct value, returns the value along with how many times
        that value appears in the dataset and for how many distinct subjects.

        :param sort_by: sorts from highest to lowest for specified count field
        :type sort_by: "count" or "uniquePatientCount"
        :return: list of dicts with "category", "count", "uniquePatientCount"
        :rtype: list of dicts
        """
        builder = SqlAlchemyQueryBuilder(
            self.chironuser,
            self.cohort,
            target_collection=self.concept.collection,
            prefilters=self.collection_prefilters,
        )
        statement = builder.get_sql_statement_for_unique_values_with_counts(self.concept, subvalue)
        response = self.run("stat9", statement)
        count_list = []
        for row in response:
            count_list.append(
                {
                    "category": row[0],
                    "count": row[1],
                    "uniquePatientCount": row[2],
                }
            )
        count_list = sorted(count_list, key=lambda d: d[sort_by], reverse=True)
        return count_list

    def lookup_unique_values(self, limit=None, subvalue=None):
        """Get a list of unique concept values.

        :param limit: the maximum number of values to return
        :type limit: integer, or None to return all values
        :return: all distinct values for the concept
        :rtype: list
        """
        builder = SqlAlchemyQueryBuilder(
            self.chironuser,
            self.cohort,
            target_collection=self.concept.collection,
            prefilters=self.collection_prefilters,
        )
        statement = builder.get_sql_statement_for_unique_values(self.concept, limit, subvalue)
        response = self.run("stat21", statement, "first_col")
        return response

    def get_all_unique_strings(self, limit=None):
        # TODO: implement this method or remove it
        builder = SqlAlchemyQueryBuilder(
            self.chironuser,
            self.cohort,
            target_collection=self.concept.collection,
            prefilters=self.collection_prefilters,
        )

        # build sql for ALL unique values
        statement = builder.get_sql_statement_for_unique_values(self.concept, limit)
        response = self.run("stat23", statement, "first_col")
        return response

    def lookup_bulk_values(self, search_list, subvalue=None):
        builder = SqlAlchemyQueryBuilder(
            self.chironuser,
            self.cohort,
            target_collection=self.concept.collection,
            prefilters=self.collection_prefilters,
        )

        # build sql for ALL unique values
        statement = builder.get_sql_statement_for_unique_values(
            self.concept, len(search_list), subvalue
        )

        # limit based on the search
        table = builder.query_info.get_sql_alchemy_table_for_concept(self.concept)
        column = builder._get_column(table, self.concept, subvalue)
        statement = statement.where(column.in_(search_list))
        response = self.run("stat22", statement, "first_col")
        return response

    def get_concept_search_ids(self, search_param):
        builder = SqlAlchemyQueryBuilder(
            self.chironuser,
            self.cohort,
        )

        statement = builder.get_sql_statement_for_concept_search(search_param)
        response = self.run("stat24", statement, "first_col")
        return response

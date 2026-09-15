from sqlalchemy import select, func, distinct, or_, and_
from sqlalchemy import cast, String
from sqlalchemy.dialects.postgresql import array, ARRAY


from chiron.query_engine.postgres.sql_alchemy_queries.query_info import QueryInfo
from chiron.query_engine.postgres.sql_alchemy_queries.alias_manager import AliasManager
from chiron.query_engine.postgres.sql_alchemy_queries.sections.select_builder import (
    SelectStatementBuilder,
)
from chiron.query_engine.postgres.sql_alchemy_queries.sections.from_builder import (
    FromStatementBuilder,
)
from chiron.query_engine.postgres.sql_alchemy_queries.sections.group_by_builder import (
    GroupByStatementBuilder,
)
from chiron.query_engine.postgres.sql_alchemy_queries.sections.order_by_builder import (
    OrderByStatementBuilder,
)
from chiron.query_engine.postgres.sql_alchemy_queries.sections.where_builder import (
    WhereStatementBuilder,
)


class SqlAlchemyQueryBuilder:
    """Builds a SQL string to run a Chiron query."""

    def __init__(self, chironuser, cohort, table=None, target_collection=None, prefilters=None):
        self.chironuser = chironuser
        self.dataset = chironuser.dataset
        self.cohort = cohort
        self.table = table
        self.query_info = QueryInfo(self.dataset, cohort, table, target_collection, prefilters)
        self.alias_manager = AliasManager(self.query_info)
        self.prefilters = prefilters if prefilters else {}
        self.select_builder = SelectStatementBuilder(
            chironuser, cohort, table, self.query_info, self.alias_manager, self.prefilters
        )
        self.from_builder = FromStatementBuilder(
            chironuser, cohort, table, self.query_info, self.alias_manager, self.prefilters
        )
        self.where_builder = WhereStatementBuilder(
            chironuser, cohort, table, self.query_info, self.alias_manager, self.prefilters
        )
        self.group_builder = GroupByStatementBuilder(
            chironuser, cohort, table, self.query_info, self.alias_manager, self.prefilters
        )
        self.order_builder = OrderByStatementBuilder(
            chironuser, cohort, table, self.query_info, self.alias_manager, self.prefilters
        )

    def get_sql_statement(self, skip=0, limit=None):
        """Get a report.

        :param int skip: for pagination number of records to skip
        :param int limit:  for pagination maximum number of records to return
        :return: SQL alchemy statement object
        """
        statement = self.select_builder.modify_statement()
        statement = self.from_builder.modify_statement(statement)
        statement = self.where_builder.modify_statement(statement)
        statement = self.group_builder.modify_statement(statement)
        statement = self.order_builder.modify_statement(statement)
        if skip:
            statement = statement.offset(skip)
        if limit:
            statement = statement.limit(limit)
        return statement

    def get_sql_statement_record_count(self):
        """Get the record count for a report.

        :return: SQL alchemy statement object
        """
        # include_aggregated_fields=False due to count not caring if fields are aggregated
        # will provide the same result either way, but will be faster with False
        statement = self.select_builder.modify_statement(include_aggregated_fields=False)
        statement = self.from_builder.modify_statement(statement)
        statement = self.where_builder.modify_statement(statement)
        statement = self.group_builder.modify_statement(statement)
        outer_statement = select(func.count()).select_from(statement.subquery())
        return outer_statement

    def _get_subject_id_inner_statement(self):
        subject_table = self.query_info.get_sql_alchemy_table_for_subject()
        statement = select(subject_table.c._subject_id)
        statement = self.from_builder.modify_statement(statement)
        statement = self.where_builder.modify_statement(statement)
        statement = statement.group_by(subject_table.c._subject_id)
        return statement

    def get_sql_statement_subject_count(self):
        """Get the subject count for the cohort definition.

        :return: SQL alchemy statement object
        """
        statement = self._get_subject_id_inner_statement()
        outer_statement = select(func.count()).select_from(statement.subquery())
        return outer_statement

    def get_sql_statement_subject_ids(self):
        """Get a list of subject IDs for the cohort definition.

        :return: SQL alchemy statement object
        """
        subject_table = self.query_info.get_sql_alchemy_table_for_subject()
        statement = select(subject_table.c._subject_id).distinct()
        statement = self.from_builder.modify_statement(statement)
        statement = self.where_builder.modify_statement(statement)
        # statement = self.group_builder.modify_statement(statement)
        statement = statement.order_by(subject_table.c._subject_id)
        return statement

    def get_sql_statement_not_null_subject_count(self, oConcept, subvalue=None):
        """Get the count of subjects with at least 1 value for the concept.

        :param obj oConcept: The model object for the Concept
        :param str subvalue: For complex (dict) concepts, optionally specify a subvalue to look
          for.
        :return: SQL alchemy statement object
        """
        table = self.query_info.get_sql_alchemy_table_for_concept(oConcept)
        coll_table = self.query_info.get_sql_alchemy_table_for_collection(oConcept.collection)
        column = self._get_column(table, oConcept, subvalue)
        statement = self._get_subject_id_inner_statement()
        # add lookup table if not already included
        core_lookup_tables = self.query_info.get_core_lookup_tables()
        if (
            oConcept.multivalue
            and table not in core_lookup_tables[oConcept.collection.permanent_id]
        ):
            statement = statement.outerjoin(table, coll_table.c._id == table.c._collection_id)
        statement = statement.where(column != None)  # noqa
        outer_statement = select(func.count()).select_from(statement.subquery())
        return outer_statement

    def get_sql_statement_null_subject_count(self, oConcept):
        """Get the count of subjects with no values for the concept.

        A subject will have no values for the concept if there are no records in this collection
        associated with the subject, or if all the records associated have values of None or
        empty string.

        :param obj oConcept: The model object for the Concept
        :return: SQL alchemy statement object
        """
        table = self.query_info.get_sql_alchemy_table_for_concept(oConcept)
        coll_table = self.query_info.get_sql_alchemy_table_for_collection(oConcept.collection)
        column = getattr(table.c, oConcept.permanent_id)
        statement = self._get_subject_id_inner_statement()
        # add lookup table if not already included
        core_lookup_tables = self.query_info.get_core_lookup_tables()
        if (
            oConcept.multivalue
            and table not in core_lookup_tables[oConcept.collection.permanent_id]
        ):
            statement = statement.outerjoin(table, coll_table.c._id == table.c._collection_id)
        statement = statement.where(column == None)  # noqa
        statement = statement.where(coll_table.c._id != None)  # noqa
        outer_statement = select(func.count()).select_from(statement.subquery())
        return outer_statement

    def _get_column(self, table, oConcept, subvalue=None, apply_map=True):
        if subvalue:
            field_name = "{}__{}".format(oConcept.permanent_id, subvalue)
            column = getattr(table.c, field_name)
        else:
            column = getattr(table.c, oConcept.permanent_id)
        if apply_map:
            processor = oConcept.get_display_processor(self.chironuser)
            column = processor.sql_alchemy_map_in_query(column)
        return column

    def get_sql_statement_not_null_value_count(self, oConcept, subvalue):
        """Get the count of non-null values for the concept.

        :param obj oConcept: The model object for the Concept
        :param str subvalue: For complex (dict) concepts, optionally specify a subvalue to look
          for.
        :return: SQL alchemy statement object
        """
        column_table = self.query_info.get_sql_alchemy_table_for_concept(oConcept)
        collection_table = self.query_info.get_sql_alchemy_table_for_collection(
            oConcept.collection
        )
        column = self._get_column(column_table, oConcept, subvalue)
        statement = select(collection_table.c._id, column)
        statement = self.from_builder.modify_statement(statement)
        statement = self.where_builder.modify_statement(statement)
        # TODO: should I also look for empty strings?
        core_lookup_tables = self.query_info.get_core_lookup_tables()
        if (
            oConcept.multivalue
            and column_table not in core_lookup_tables[oConcept.collection.permanent_id]
        ):
            statement = statement.outerjoin(
                column_table, collection_table.c._id == column_table.c._collection_id
            )
        statement = statement.where(column != None)  # noqa
        statement = statement.distinct()
        outer_statement = select(func.count()).select_from(statement.subquery())
        return outer_statement

    def get_sql_statement_null_value_count(self, oConcept):
        """Get the count of null values for the concept.

        :param obj oConcept: The model object for the Concept
        :return: SQL alchemy statement object
        """
        column_table = self.query_info.get_sql_alchemy_table_for_concept(oConcept)
        collection_table = self.query_info.get_sql_alchemy_table_for_collection(
            oConcept.collection
        )
        column = getattr(column_table.c, oConcept.permanent_id)
        statement = select(func.count(distinct(collection_table.c._id)))
        statement = self.from_builder.modify_statement(statement)
        statement = self.where_builder.modify_statement(statement)
        # TODO: should I also look for empty strings?
        # add lookup table if not already included
        core_lookup_tables = self.query_info.get_core_lookup_tables()
        if (
            oConcept.multivalue
            and column_table not in core_lookup_tables[oConcept.collection.permanent_id]
        ):
            statement = statement.outerjoin(
                column_table, collection_table.c._id == column_table.c._collection_id
            )
        statement = statement.where(column == None)  # noqa
        return statement

    def get_sql_statement_subject_with_no_subcol_count(self, oConcept):
        """Get the count of subjects that don't have any records associated with the concept.

        :param obj oConcept: The model object for the Concept
        :return: SQL alchemy statement object
        """
        subject_table = self.query_info.get_sql_alchemy_table_for_subject()
        table, m2m_table = self.query_info.get_sql_alchemy_table_for_collection(
            oConcept.collection, include_m2m=True
        )
        statement = self._get_subject_id_inner_statement()
        table = table.alias()
        if m2m_table is not None:
            subquery = select(m2m_table.c._subject_id).distinct()
        else:
            subquery = select(table.c._subject_id).distinct()
        statement = statement.where(subject_table.c._subject_id.not_in(subquery))
        outer_statement = select(func.count()).select_from(statement)
        return outer_statement

    def get_sql_statement_for_histogram(self, oConcept, bin_limits, subvalue=None):
        """Get the SQL statement for a histogram on numbers.

        :param obj oConcept: The model object for the Concept
        :param min_val: The minimum number to start the histogram
        :param max_val:  The maximum number to end the histogram
        :param str subvalue: For complex (dict) concepts, optionally specify a subvalue to look
          for.
        :return: SQL alchemy statement object
        """
        column_table = self.query_info.get_sql_alchemy_table_for_concept(oConcept)
        collection_table = self.query_info.get_sql_alchemy_table_for_collection(
            oConcept.collection
        )
        column = self._get_column(column_table, oConcept, subvalue, apply_map=False)
        statement = select(collection_table.c._id, column).distinct()
        statement = self.from_builder.modify_statement(statement)
        statement = self.where_builder.modify_statement(statement)
        core_lookup_tables = self.query_info.get_core_lookup_tables()
        if (
            oConcept.multivalue
            and column_table not in core_lookup_tables[oConcept.collection.permanent_id]
        ):
            statement = statement.outerjoin(
                column_table, collection_table.c._id == column_table.c._collection_id
            )
        statement = statement.where(column != None)  # noqa
        statement = statement.subquery().alias()
        outer_column = self._get_column(statement, oConcept, subvalue)
        # TODO: this is a hack to make sure the last bin is inclusive
        bin_limits[-1] += 0.000001
        buckets = func.width_bucket(outer_column, bin_limits)
        outer = select(buckets.label("buckets"), func.count())
        outer = outer.select_from(statement)
        outer = outer.group_by(buckets)
        outer = outer.order_by(buckets)
        return outer

    def get_sql_statement_for_date_histogram(self, oConcept, bin_limits):
        """Get the SQL statement for a histogram on dates.

        :param obj oConcept: The model object for the Concept
        :param date min_val: The minimum date to start the histogram
        :param date max_val:  The maximum date to end the histogram
        :return: SQL alchemy statement object
        """
        column_table = self.query_info.get_sql_alchemy_table_for_concept(oConcept)
        collection_table = self.query_info.get_sql_alchemy_table_for_collection(
            oConcept.collection
        )
        column = getattr(column_table.c, oConcept.permanent_id)
        statement = select(collection_table.c._id, column).distinct()
        statement = self.from_builder.modify_statement(statement)
        statement = self.where_builder.modify_statement(statement)
        core_lookup_tables = self.query_info.get_core_lookup_tables()
        if (
            oConcept.multivalue
            and column_table not in core_lookup_tables[oConcept.collection.permanent_id]
        ):
            statement = statement.outerjoin(
                column_table, collection_table.c._id == column_table.c._collection_id
            )
        statement = statement.where(column != None)  # noqa
        statement = statement.subquery().alias()
        outer_column = getattr(statement.c, oConcept.permanent_id)
        buckets = func.width_bucket(outer_column, bin_limits)
        outer = select(buckets.label("buckets"), func.count())
        outer = outer.select_from(statement)
        outer = outer.group_by(buckets)
        outer = outer.order_by(buckets)
        return outer

    def get_sql_statement_for_unique_values(self, oConcept, limit, subvalue=None):
        """Get a query for a list of unique values

        :param obj oConcept: The model object for the Concept
        :param int limit: The maximum number of values to return
        :param str subvalue: For complex (dict) concepts, optionally specify a subvalue to look
          for.
        :return: SQL alchemy statement object
        """
        column_table = self.query_info.get_sql_alchemy_table_for_concept(oConcept)
        collection_table = self.query_info.get_sql_alchemy_table_for_collection(
            oConcept.collection
        )
        column = self._get_column(column_table, oConcept, subvalue)
        statement = select(column)
        statement = self.from_builder.modify_statement(statement)
        statement = self.where_builder.modify_statement(statement)
        core_lookup_tables = self.query_info.get_core_lookup_tables()
        if (
            oConcept.multivalue
            and column_table not in core_lookup_tables[oConcept.collection.permanent_id]
        ):
            statement = statement.outerjoin(
                column_table, collection_table.c._id == column_table.c._collection_id
            )
        statement = statement.where(column != None)  # noqa
        statement = statement.order_by(column)
        if limit:
            statement = statement.limit(limit)
        return statement.distinct()

    def get_sql_statement_for_unique_values_with_counts(self, oConcept, subvalue=None):
        """Get a query for a list of unique values and count of occurences for each value.

        :param obj oConcept: The model object for the Concept
        :param str subvalue: For complex (dict) concepts, optionally specify a subvalue to look
          for.
        :return: SQL alchemy statement object
        """
        column_table = self.query_info.get_sql_alchemy_table_for_concept(oConcept)
        collection_table = self.query_info.get_sql_alchemy_table_for_collection(
            oConcept.collection
        )
        subject_table = self.query_info.get_sql_alchemy_table_for_subject()
        column = self._get_column(column_table, oConcept, subvalue)
        statement = select(
            column,
            func.count(distinct(collection_table.c._id)).label("count"),
            func.count(distinct(subject_table.c._subject_id)).label("uniquePatientCount"),
        )
        statement = self.from_builder.modify_statement(statement)
        statement = self.where_builder.modify_statement(statement)
        core_lookup_tables = self.query_info.get_core_lookup_tables()
        if (
            oConcept.multivalue
            and column_table not in core_lookup_tables[oConcept.collection.permanent_id]
        ):
            statement = statement.outerjoin(
                column_table, collection_table.c._id == column_table.c._collection_id
            )
        statement = statement.where(column != None)  # noqa
        statement = statement.group_by(column)
        statement = statement.order_by(column)
        return statement

    def get_sql_statement_for_ontology_codes(self, oConcept, codes):
        return self._build_ontology_query("codes", oConcept, codes)

    def get_sql_statement_for_ontology_counts(self, oConcept, codes):
        return self._build_ontology_query("counts", oConcept, codes)

    def _build_ontology_query(self, type, oConcept, codes):
        """Get a query for a list of unique values and count of occurences for each value.

        :param obj oConcept: The model object for the Concept
        :param str subvalue: For complex (dict) concepts, optionally specify a subvalue to look
          for.
        :return: SQL alchemy statement object
        """
        column_table = self.query_info.get_sql_alchemy_table_for_concept(oConcept)
        collection_table = self.query_info.get_sql_alchemy_table_for_collection(
            oConcept.collection
        )
        subject_table = self.query_info.get_sql_alchemy_table_for_subject()
        hierarchy_column = self._get_column(column_table, oConcept, "hierarchy")
        unnested_column = func.unnest(hierarchy_column).label("myvalue")
        code_column = self._get_column(column_table, oConcept, "code")
        is_parent_column = (func.unnest(hierarchy_column) != code_column).label("isParent")
        if type == "counts":
            columns = [
                unnested_column,
                func.count(distinct(collection_table.c._id)).label("count"),
                func.count(distinct(subject_table.c._subject_id)).label("uniquePatientCount"),
            ]
        else:
            columns = [unnested_column, is_parent_column]
        statement = select(*columns)
        statement = self.from_builder.modify_statement(statement)
        # we can further filter to use only records with the codes of interest, which speeds up the query
        where_clause = self.where_builder.build_full_where_clause()
        if codes:
            code_array_literal = cast(array(codes), ARRAY(String(150)))
            code_filter_clause = hierarchy_column.overlap(code_array_literal)
            if where_clause is None:
                where_clause = code_filter_clause
            else:
                where_clause = and_(where_clause, code_filter_clause)
        if where_clause is not None:
            statement = statement.where(where_clause)
        core_lookup_tables = self.query_info.get_core_lookup_tables()
        if (
            oConcept.multivalue
            and column_table not in core_lookup_tables[oConcept.collection.permanent_id]
        ):
            statement = statement.outerjoin(
                column_table, collection_table.c._id == column_table.c._collection_id
            )
        # statement = statement.where(column != None)  # noqa
        if type == "counts":
            statement = statement.group_by(unnested_column)
        else:
            statement = statement.group_by(unnested_column, is_parent_column)
        if type == "counts":
            outer_columns = statement.c
        else:
            outer_columns = [
                statement.c.myvalue,
                func.bool_or(statement.c.isParent).label("hasDescendants"),
            ]
        statement2 = select(*outer_columns)
        if codes:
            statement2 = statement2.where(statement.c.myvalue.in_(codes))
        if type != "counts":
            statement2 = statement2.group_by(statement.c.myvalue)
        statement2 = statement2.order_by(statement.c.myvalue)
        return statement2

    def run_after_query_aggregation_modification(self, records):
        """Run final processing of aggregation values for a SQL result.

        Aggregation on a report column is accomplished through a combination of Postgres
        functions and post-processing in Python. Pass the SQL output for a report
        to this method to run all the post-processing.

        :param list records: The dataset to process.
        :return: a list of processed records.
        """
        query_modifiers = self.query_info.after_query_modifiers
        new_records = []
        for row in records:
            new_row = list(row)
            for idx, mod_func in query_modifiers.items():
                new_row[idx] = mod_func(row[idx])
            new_records.append(new_row)
        return new_records

    def get_sql_statement_for_concept_search(self, search_param):
        """Get a query for a list of concept ids based upon a search string.

        :param str search_param: The string to search on
        :return: SQL alchemy statement object
        """
        search_table = self.query_info.get_sql_alchemy_table_for_concept_search()
        statement = select(
            search_table.c.concept_id,
        )
        statement = statement.where(
            or_(
                search_table.c.concept_name.ilike(f"%{search_param}%"),
                search_table.c.concept_description.ilike(f"%{search_param}%"),
                search_table.c.categories.ilike(f"%{search_param}%"),
                search_table.c.other_search_terms.ilike(f"%{search_param}%"),
                search_table.c.ngram_search.ilike(f"%{search_param}%"),
            )
        )

        return statement.distinct()

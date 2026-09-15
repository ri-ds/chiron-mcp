from sqlalchemy import select, func, and_, or_

from chiron.query_engine.postgres.sql_alchemy_queries.aggregation import get_postgres_aggregator
from chiron.query_engine.postgres.sql_alchemy_queries import AbstractSqlAlchemyPartBuilder
from chiron.query_engine.postgres.sql_alchemy_queries.sections.where_builder import (
    WhereStatementBuilder,
)


class SelectStatementBuilder(AbstractSqlAlchemyPartBuilder):
    def modify_statement(self, include_aggregated_fields=True):
        core_collections = self.query_info.get_core_collections()
        column_list = []
        for idx, field in enumerate(self.table.internal_table_def["fields"]):
            column = None
            after_query_modifier = None
            field_concept = field["concept"]
            field_collection = field["concept"].collection
            collection_table = self.query_info.get_sql_alchemy_table_for_collection(
                field_collection
            )
            concept_table = self.query_info.get_sql_alchemy_table_for_concept(field_concept)
            if not field.get("aggregate"):
                column = self._get_column(concept_table, field).label(field["entry_id"])
            elif include_aggregated_fields:
                aggregator = get_postgres_aggregator(self.chironuser, field)
                if field_collection in core_collections:
                    column = self.create_agg_statement(
                        aggregator, concept_table, collection_table, field
                    )
                else:
                    column = self.create_agg_subquery(
                        aggregator, concept_table, collection_table, field
                    )
                after_query_modifier = aggregator.get_after_query_modifier()
            column_list.append(column)
            if after_query_modifier:
                self.query_info.register_after_query_modifier(idx, after_query_modifier)
            if column is not None:
                self.query_info.register_sortable_column(field["entry_id"], column)
        if not column_list:
            column_list.append(None)
        statement = select(*column_list)
        return statement

    def _get_column(self, table, field):
        processor = field["concept"].get_display_processor(self.chironuser, field)
        field_name = field["concept_id"]
        subvalue = processor.use_subvalue(field)
        if subvalue:
            field_name = "{}__{}".format(field_name, subvalue)
        column = getattr(table.c, field_name)
        column = processor.sql_alchemy_map_in_query(column)
        return column

    def create_agg_statement(self, aggregator, concept_table, collection_table, field):
        """Generates SELECT entry for an aggregated query when there is no subquery."""
        column_alias = field["entry_id"]
        return aggregator.create_agg_statement(
            concept_table, collection_table, double_aggregation=False, column_alias=column_alias
        )

    def create_agg_subquery(self, aggregator, concept_table, collection_table, field):
        entry_id = field["entry_id"]
        oConcept = field["concept"]
        subquery_type = self.alias_manager.TYPE_SELECT
        """Generate SELECT value for one aggregated column requiring a subquery."""
        where_builder = WhereStatementBuilder(
            self.chironuser, self.cohort, self.table, self.query_info, self.alias_manager
        )
        subquery_concept_table = self.alias_manager.get_concept_alias(
            subquery_type, entry_id, oConcept
        )
        subquery_collection_table, m2m_table = self.alias_manager.get_collection_alias(
            subquery_type, entry_id, oConcept.collection, include_m2m=True
        )
        aggregation_criteria_set = field.get("aggregation_criteria_set", None)
        clause_groups, addl_alias_refs = where_builder.get_clauses_related_to_collection(
            field["concept"].collection,
            field["entry_id"],
            aggregation_criteria_set,
        )

        # SELECT section
        statement = select(
            aggregator.create_agg_statement(
                subquery_concept_table, subquery_collection_table, double_aggregation=True
            )
        )

        # WHERE section
        subject_table = self.query_info.get_sql_alchemy_table_for_subject()
        where_sections = []
        filter1, m2m_referenced, extra_join = self._join_subquery_to_main_query(
            field, subquery_collection_table, subject_table, m2m_table
        )
        for clause_group in clause_groups:
            if len(clause_group) > 0:
                where_sections.append(and_(*clause_group))
        statement = statement.where(filter1)
        if where_sections:
            statement = statement.where(or_(*where_sections))

        # FROM section
        if m2m_referenced:
            statement = statement.select_from(m2m_table)
            statement = statement.outerjoin(
                subquery_collection_table,
                subquery_collection_table.c._id == m2m_table.c._collection_id,
            )
        else:
            statement = statement.select_from(subquery_collection_table)
        collection_aliases = self.alias_manager.get_aliases(subquery_type, entry_id, "collection")
        for alias_ref in addl_alias_refs:
            collection_aliases += self.alias_manager.get_aliases(
                subquery_type, alias_ref, "collection"
            )
        # longitudinal queries will have other collections joined by subject_id
        for entry in collection_aliases:
            if entry["alias"] != subquery_collection_table:
                statement = statement.join(
                    entry["alias"],
                    entry["alias"].c._subject_id == subquery_collection_table.c._subject_id,
                )
        # add any needed lookup tables
        lookup_aliases = self.alias_manager.get_aliases(subquery_type, entry_id, "lookup")
        for alias_ref in addl_alias_refs:
            lookup_aliases += self.alias_manager.get_aliases(subquery_type, alias_ref, "lookup")
        for entry in lookup_aliases:
            statement = statement.outerjoin(
                entry["alias"], entry["alias"].c._collection_id == entry["parent_alias"].c._id
            )
        if extra_join:
            statement = statement.outerjoin(extra_join[0], extra_join[1])

        # generate final subquery column
        response = aggregator.create_outer_agg_statement(
            statement.scalar_subquery(), concept_table, entry_id
        )
        return response

    def _join_subquery_to_main_query(
        self, field, subquery_collection_table, subject_table, m2m_table
    ):
        """Returns a WHERE filter that joins an aggregated subquery to the main query

        By default will join to subject._id. If the output is stacked by a subcollection that
        shares a subcollection relationship with this field, will join by that relationship
        instead.
        """
        core_collections = self.query_info.get_core_collections()
        oCollection = field["concept"].collection
        m2m_referenced = False
        extra_join = None
        # don't use subcollection relationships if this is a longitudinal query
        is_longitudinal = self.query_info.check_collection_in_longitudinal_combo(oCollection)
        if not is_longitudinal:
            for oCoreCollection in core_collections:
                # use subcollection relationships if available
                oRel = self.query_info.find_subcollection_relationship(
                    oCollection, oCoreCollection
                )
                if oRel:
                    subquery_type = self.alias_manager.TYPE_SELECT
                    entry_id = field["entry_id"]
                    if oRel.get_pk_collection() == oCollection:
                        field = oRel.pk_concept.permanent_id
                        to_collection = oRel.get_fk_collection()
                        to_field = oRel.fk_concept.permanent_id
                        to_table = self.query_info.get_sql_alchemy_table_for_concept(
                            oRel.fk_concept
                        )
                        outer_table = self.query_info.get_sql_alchemy_table_for_collection(
                            to_collection
                        )
                        if to_table == outer_table:
                            outer_column = getattr(outer_table.c, to_field)
                            inner_column = getattr(subquery_collection_table.c, field)
                            return outer_column == inner_column, m2m_referenced, extra_join
                        else:
                            to_table_alias = to_table.alias()
                            response1 = outer_table.c._id == to_table_alias.c._collection_id
                            response2 = (
                                subject_table.c._subject_id
                                == subquery_collection_table.c._subject_id
                            )
                            pk_column = getattr(subquery_collection_table.c, field)
                            fk_column = getattr(to_table_alias.c, to_field)
                            extra_join = (to_table_alias, pk_column == fk_column)
                            return and_(response1, response2), m2m_referenced, extra_join
                    else:
                        field = oRel.fk_concept.permanent_id
                        # the field table could be a lookup table
                        field_table_alias = self.alias_manager.get_concept_alias(
                            subquery_type, entry_id, oRel.fk_concept
                        )
                        to_collection = oRel.get_pk_collection()
                        to_field = oRel.pk_concept.permanent_id
                        outer_table = self.query_info.get_sql_alchemy_table_for_collection(
                            to_collection
                        )
                        outer_column = getattr(outer_table.c, to_field)
                        inner_column = getattr(field_table_alias.c, field)
                        return outer_column == inner_column, m2m_referenced, extra_join
        if m2m_table is not None:
            filter = subject_table.c._id == m2m_table.c._subject_id
            m2m_referenced = True
        else:
            filter = subject_table.c._id == subquery_collection_table.c._subject_id
        return filter, m2m_referenced, extra_join

    def _build_subquery_select_entry(self, table, field):
        aggregation_approach = self.lookup_aggregation_approach(field["aggregation_method"])
        column = getattr(table.c, field["concept_id"])
        if aggregation_approach == "value_only":
            return func.json_agg(column)
        if aggregation_approach == "with_id_and_date":
            if field["concept"].collection.event_date_field:
                date_field = field["concept"].collection.event_date_field.permanent_id
                date_column = getattr(table.c, date_field)
                row_agg = func.row(table.c._id, date_column, column)
                return func.json_agg(row_agg)
            else:
                row_agg = func.row(table.c._id, "NULL", column)
                return func.json_agg(row_agg)
        # default is value with ID
        row_agg = func.row(table.c._id, column)
        return func.json_agg(row_agg)

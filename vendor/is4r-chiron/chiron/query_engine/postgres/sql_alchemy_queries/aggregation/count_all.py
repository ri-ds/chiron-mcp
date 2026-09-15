from sqlalchemy import func

from chiron.query_engine.postgres.sql_alchemy_queries.aggregation._abstract import (
    AbstractPostgresAggregator,
)


class PgAggCountAll(AbstractPostgresAggregator):
    def create_agg_statement(
        self, concept_table, collection_table, double_aggregation=False, column_alias=None
    ):
        statement = self._generic_create_agg_statement_value_id(
            concept_table, collection_table, column_alias
        )
        if double_aggregation:
            return statement
        return func.json_arr_to_count_all(statement)

    def create_outer_agg_statement(self, subquery, table, column_alias=None):
        response = func.json_arr_set_to_count_all(subquery)
        if column_alias:
            response = response.label(column_alias)
        return response

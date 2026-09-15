from sqlalchemy import func

from chiron.query_engine.postgres.sql_alchemy_queries.aggregation._abstract import (
    AbstractPostgresAggregator,
)


class PgAggListDistinct(AbstractPostgresAggregator):
    def __init__(self, chironuser, td_entry):
        handler = td_entry["concept"]._instantiate_concept_handler(chironuser=chironuser)
        self.data_type = handler.get_stored_data_type()
        super().__init__(chironuser, td_entry)

    def _get_agg_function(self):
        data_type = self.data_type
        # dates might be rounded to years depending on PHI access
        if self.data_type == "date":
            if self.chironuser.access_level != self.chironuser.AccessLevel.PHI:
                if self.td_entry["concept"].has_phi:
                    data_type = "integer"
        if data_type == "integer":
            return func.json_arr_to_list_distinct_int
        if data_type == "float":
            return func.json_arr_to_list_distinct_float
        if data_type == "date":
            return func.json_arr_to_list_distinct_date
        if data_type == "boolean":
            return func.json_arr_to_list_distinct_bool
        return func.json_arr_to_list_distinct

    def _get_outer_agg_function(self):
        data_type = self.data_type
        # dates might be rounded to years depending on PHI access
        if self.data_type == "date":
            if self.chironuser.access_level != self.chironuser.AccessLevel.PHI:
                if self.td_entry["concept"].has_phi:
                    data_type = "integer"
        if data_type == "integer":
            return func.json_arr_set_to_list_distinct_int
        if data_type == "float":
            return func.json_arr_set_to_list_distinct_float
        if data_type == "date":
            return func.json_arr_set_to_list_distinct_date
        if data_type == "boolean":
            return func.json_arr_set_to_list_distinct_bool
        return func.json_arr_set_to_list_distinct

    def create_agg_statement(
        self, concept_table, collection_table, double_aggregation=False, column_alias=None
    ):
        statement = self._generic_create_agg_statement_value_only2(concept_table, column_alias)
        if double_aggregation:
            return statement
        agg_func = self._get_agg_function()
        return agg_func(statement)

    def create_outer_agg_statement(self, subquery, table, column_alias=None):
        outer_agg_func = self._get_outer_agg_function()
        response = outer_agg_func(subquery)
        if column_alias:
            response = response.label(column_alias)
        return response

    def after_query_modifier(self, value):
        if len(value) == 0:
            return None
        if len(value) == 1 and value[0] in [None, ""]:
            return None
        return value

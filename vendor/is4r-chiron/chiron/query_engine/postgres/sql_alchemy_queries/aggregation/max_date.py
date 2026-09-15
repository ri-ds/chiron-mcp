from sqlalchemy import func

from chiron.query_engine.postgres.sql_alchemy_queries.aggregation._abstract import (
    AbstractPostgresAggregator,
)


class PgAggMaxDate(AbstractPostgresAggregator):
    def __init__(self, chironuser, td_entry):
        self.max_ordinal = td_entry.get("aggregation_settings", {}).get(
            "max_date_ordinal_position", 1
        )
        handler = td_entry["concept"]._instantiate_concept_handler(chironuser=chironuser)
        self.data_type = handler.get_stored_data_type()
        super().__init__(chironuser, td_entry)

    def _get_agg_function(self):
        # may only get year depending on user PHI permissions
        if self.chironuser.access_level != self.chironuser.AccessLevel.PHI:
            if self.td_entry["concept"].has_phi:
                return func.json_arr_to_list_all_int
        return func.json_arr_to_list_all_date

    def _get_outer_agg_function(self):
        # may only get year depending on user PHI permissions
        if self.chironuser.access_level != self.chironuser.AccessLevel.PHI:
            if self.td_entry["concept"].has_phi:
                return func.json_arr_set_to_list_all_int
        return func.json_arr_set_to_list_all_date

    def create_agg_statement(
        self, concept_table, collection_table, double_aggregation=False, column_alias=None
    ):
        agg_func = self._get_agg_function()
        statement = self._generic_create_agg_statement_value_id(
            concept_table, collection_table, column_alias
        )
        if double_aggregation:
            return statement
        response = agg_func(statement)
        response = func.array_remove(response, None)
        response = func.get_array_position_reverse(response, self.max_ordinal)
        return response

    def create_outer_agg_statement(self, subquery, table, column_alias=None):
        outer_agg_func = self._get_outer_agg_function()
        response = outer_agg_func(subquery)
        response = func.array_remove(response, None)
        response = func.get_array_position_reverse(response, self.max_ordinal)
        if column_alias:
            response = response.label(column_alias)
        return response

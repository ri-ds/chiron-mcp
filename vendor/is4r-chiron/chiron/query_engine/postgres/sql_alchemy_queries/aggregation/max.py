from sqlalchemy import func

from chiron.query_engine.postgres.sql_alchemy_queries.aggregation._abstract import (
    AbstractPostgresAggregator,
)


class PgAggMax(AbstractPostgresAggregator):
    def __init__(self, chironuser, td_entry):
        self.max_ordinal = td_entry.get("aggregation_settings", {}).get("max_ordinal_position", 1)
        self.return_value = td_entry.get("aggregation_settings", {}).get(
            "max_return_value", "value"
        )
        handler = td_entry["concept"]._instantiate_concept_handler(chironuser=chironuser)
        self.data_type = handler.get_stored_data_type()
        super().__init__(chironuser, td_entry)

    def _get_agg_function(self):
        if self.data_type == "integer":
            return func.json_arr_to_list_all_int
        if self.data_type == "float":
            return func.json_arr_to_list_all_float
        if isinstance(self.data_type, dict) and self.data_type.get("num") == "integer":
            return func.json_arr_to_list_all_int
        if isinstance(self.data_type, dict) and self.data_type.get("num") == "float":
            return func.json_arr_to_list_all_float
        # default to float value
        return func.json_arr_to_list_all_float

    def _get_outer_agg_function(self):
        if self.data_type == "integer":
            return func.json_arr_set_to_list_all_int
        elif self.data_type == "float":
            return func.json_arr_set_to_list_all_float
        if isinstance(self.data_type, dict) and self.data_type.get("num") == "integer":
            return func.json_arr_set_to_list_all_int
        if isinstance(self.data_type, dict) and self.data_type.get("num") == "float":
            return func.json_arr_set_to_list_all_float
        # default to float value
        return func.json_arr_set_to_list_all_float

    def create_agg_statement(
        self, concept_table, collection_table, double_aggregation=False, column_alias=None
    ):
        agg_func = self._get_agg_function()
        response = None
        if self.return_value in ["value", "count"]:
            statement = self._generic_create_agg_statement_value_id(
                concept_table, collection_table, column_alias
            )
        else:
            statement = self._generic_create_agg_statement_value_date_id(
                concept_table, collection_table, column_alias
            )
        if double_aggregation:
            return statement
        if self.return_value == "value":
            response = agg_func(statement)
            response = func.array_remove(response, None)
            response = func.get_array_position_reverse(response, self.max_ordinal)
        elif self.return_value == "count":
            response = agg_func(statement)
            response = func.array_remove(response, None)
            response = func.count_array_position_reverse(response, self.max_ordinal)
        elif self.return_value == "all_dates":
            response = func.get_all_dates_for_value_at_position_reverse(
                statement, self.max_ordinal
            )
        elif self.return_value == "earliest_date":
            response = func.get_all_dates_for_value_at_position_reverse(
                statement, self.max_ordinal
            )
            response = func.get_array_position(response, 1)
        elif self.return_value == "latest_date":
            response = func.get_all_dates_for_value_at_position_reverse(
                statement, self.max_ordinal
            )
            response = func.get_array_position_reverse(response, 1)
        return response

    def create_outer_agg_statement(self, subquery, table, column_alias=None):
        outer_agg_func = self._get_outer_agg_function()
        response = None
        if self.return_value == "value":
            response = outer_agg_func(subquery)
            response = func.array_remove(response, None)
            response = func.get_array_position_reverse(response, self.max_ordinal)
        elif self.return_value == "count":
            response = outer_agg_func(subquery)
            response = func.array_remove(response, None)
            response = func.count_array_position_reverse(response, self.max_ordinal)
        elif self.return_value == "all_dates":
            response = func.json_arr_set_to_json_arr(subquery)
            response = func.get_all_dates_for_value_at_position_reverse(response, self.max_ordinal)
        elif self.return_value == "earliest_date":
            response = func.json_arr_set_to_json_arr(subquery)
            response = func.get_all_dates_for_value_at_position_reverse(response, self.max_ordinal)
            response = func.get_array_position(response, 1)
        elif self.return_value == "latest_date":
            response = func.json_arr_set_to_json_arr(subquery)
            response = func.get_all_dates_for_value_at_position_reverse(response, self.max_ordinal)
            response = func.get_array_position_reverse(response, 1)
        if column_alias:
            response = response.label(column_alias)
        return response

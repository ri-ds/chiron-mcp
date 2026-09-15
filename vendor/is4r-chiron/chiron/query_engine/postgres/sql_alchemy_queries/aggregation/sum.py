from sqlalchemy import func

from chiron.query_engine.postgres.sql_alchemy_queries.aggregation._abstract import (
    AbstractPostgresAggregator,
)
from chiron import helpers


class PgAggSum(AbstractPostgresAggregator):
    def __init__(self, chironuser, td_entry):
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
        """
        Gets all values as JSON array of ID/value pair objects. If not double aggregation, removes
        nulls and calculates the average.
        """
        agg_func = self._get_agg_function()
        statement = self._generic_create_agg_statement_value_id(
            concept_table, collection_table, column_alias
        )
        if double_aggregation:
            return statement
        response = agg_func(statement)
        response = func.array_remove(response, None)
        response = func.array_sum(response)
        return response

    def create_outer_agg_statement(self, subquery, table, column_alias=None):
        """
        Receives a JSON array of ID/value pair objects. Merges into one array, removes nulls, and
        calculates the average.
        """
        outer_agg_func = self._get_outer_agg_function()
        response = outer_agg_func(subquery)
        response = func.array_remove(response, None)
        response = func.array_sum(response)
        if column_alias:
            response = response.label(column_alias)
        return response

    def after_query_modifier(self, value):
        """
        Round to 3 significant digits or return None if null.
        """
        if value is None:
            return None
        value = helpers.round_sig_3(value, round_whole_number=False)
        return value

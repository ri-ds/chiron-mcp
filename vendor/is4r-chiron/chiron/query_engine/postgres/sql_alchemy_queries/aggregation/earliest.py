from sqlalchemy import func

from chiron.query_engine.postgres.sql_alchemy_queries.aggregation._abstract import (
    AbstractPostgresAggregator,
)
from chiron import chiron_settings


class PgAggEarliest(AbstractPostgresAggregator):
    def __init__(self, chironuser, td_entry):
        self.position = td_entry.get("aggregation_settings", {}).get(
            "earliest_ordinal_position", 1
        )
        handler = td_entry["concept"]._instantiate_concept_handler(chironuser=chironuser)
        self.data_type = handler.get_stored_data_type()
        super().__init__(chironuser, td_entry)

    def _get_agg_function(self):
        if chiron_settings.CHIRON_EVENT_CONCEPT_TYPE == "detailed_age":
            if self.data_type == "integer":
                return func.json_arr_to_list_all_by_age_int
            if self.data_type == "float":
                return func.json_arr_to_list_all_by_age_float
            if self.data_type == "date":
                return func.json_arr_to_list_all_by_age_date
            if self.data_type == "boolean":
                return func.json_arr_to_list_all_by_age_bool
            return func.json_arr_to_list_all_by_age
        if self.data_type == "integer":
            return func.json_arr_to_list_all_chron_int
        if self.data_type == "float":
            return func.json_arr_to_list_all_chron_float
        if self.data_type == "date":
            return func.json_arr_to_list_all_chron_date
        if self.data_type == "boolean":
            return func.json_arr_to_list_all_chron_bool
        return func.json_arr_to_list_all_chron

    def _get_outer_agg_function(self):
        if chiron_settings.CHIRON_EVENT_CONCEPT_TYPE == "detailed_age":
            if self.data_type == "integer":
                return func.json_arr_set_to_list_all_by_age_int
            elif self.data_type == "float":
                return func.json_arr_set_to_list_all_by_age_float
            elif self.data_type == "date":
                return func.json_arr_set_to_list_all_by_age_date
            elif self.data_type == "boolean":
                return func.json_arr_set_to_list_all_by_age_bool
            return func.json_arr_set_to_list_all_by_age
        if self.data_type == "integer":
            return func.json_arr_set_to_list_all_chron_int
        elif self.data_type == "float":
            return func.json_arr_set_to_list_all_chron_float
        elif self.data_type == "date":
            return func.json_arr_set_to_list_all_chron_date
        elif self.data_type == "boolean":
            return func.json_arr_set_to_list_all_chron_bool
        return func.json_arr_set_to_list_all_chron

    def create_agg_statement(
        self, concept_table, collection_table, double_aggregation=False, column_alias=None
    ):
        agg_func = self._get_agg_function()
        statement = self._generic_create_agg_statement_value_date_id(
            concept_table, collection_table, column_alias
        )
        if double_aggregation:
            return statement
        response = agg_func(statement)
        response = func.get_array_position(response, self.position)
        return response

    def create_outer_agg_statement(self, subquery, table, column_alias=None):
        outer_agg_func = self._get_outer_agg_function()
        response = outer_agg_func(subquery)
        response = func.get_array_position(response, self.position)
        if column_alias:
            response = response.label(column_alias)
        return response

    # def after_query_modifier(self, value):
    #     value = self.flatten_agg_result_id_date_value(value)
    #     if not value:
    #         return None
    #     position = self.td_entry.get("aggregation_settings", {}).get(
    #         "earliest_ordinal_position", 1
    #     )
    #     if len(value) < position:
    #         return None
    #     value = sorted(value, key=lambda x: (x[2] is None, x[2]))
    #     sorted_list = sorted(value, key=lambda x: (x[1] is None, x[1]))
    #     return sorted_list[position - 1][2]

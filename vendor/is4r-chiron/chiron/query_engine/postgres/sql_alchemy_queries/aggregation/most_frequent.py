from sqlalchemy import func

from chiron.query_engine.postgres.sql_alchemy_queries.aggregation._abstract import (
    AbstractPostgresAggregator,
)


class PgAggMostFrequent(AbstractPostgresAggregator):
    def __init__(self, chironuser, td_entry):
        self.position = td_entry.get("aggregation_settings", {}).get(
            "most_frequent_ordinal_position", 1
        )
        self.return_value = td_entry.get("aggregation_settings", {}).get(
            "most_frequent_return_value", "value"
        )
        handler = td_entry["concept"]._instantiate_concept_handler(chironuser=chironuser)
        self.data_type = handler.get_stored_data_type()
        super().__init__(chironuser, td_entry)

    def _get_frequency_value_func(self):
        if self.return_value == "value":
            return func.array_frequency_values
        if self.return_value == "count":
            return func.array_frequency_counts
        return func.array_frequency_values_and_counts

    def _get_agg_function(self):
        data_type = self.data_type
        # dates might be rounded to years depending on PHI access
        if self.data_type == "date":
            if self.chironuser.access_level != self.chironuser.AccessLevel.PHI:
                if self.td_entry["concept"].has_phi:
                    data_type = "integer"
        if data_type == "integer":
            return func.json_arr_to_list_all_int
        if data_type == "float":
            return func.json_arr_to_list_all_float
        if data_type == "date":
            return func.json_arr_to_list_all_date
        if data_type == "boolean":
            return func.json_arr_to_list_all_bool
        return func.json_arr_to_list_all

    def _get_outer_agg_function(self):
        data_type = self.data_type
        # dates might be rounded to years depending on PHI access
        if self.data_type == "date":
            if self.chironuser.access_level != self.chironuser.AccessLevel.PHI:
                if self.td_entry["concept"].has_phi:
                    data_type = "integer"
        if data_type == "integer":
            return func.json_arr_set_to_list_all_int
        elif data_type == "float":
            return func.json_arr_set_to_list_all_float
        elif data_type == "date":
            return func.json_arr_set_to_list_all_date
        elif data_type == "boolean":
            return func.json_arr_set_to_list_all_bool
        return func.json_arr_set_to_list_all

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
        freq_func = self._get_frequency_value_func()
        response = freq_func(response)
        response = func.get_array_position(response, self.position)
        return response

    def create_outer_agg_statement(self, subquery, table, column_alias=None):
        outer_agg_func = self._get_outer_agg_function()
        response = outer_agg_func(subquery)
        response = func.array_remove(response, None)
        freq_func = self._get_frequency_value_func()
        response = freq_func(response)
        response = func.get_array_position(response, self.position)
        if column_alias:
            response = response.label(column_alias)
        return response

    def after_query_modifier(self, value):
        if self.return_value == "count" and not value:
            return 0
        if self.return_value == "value_and_count":
            if not value:
                return "(0)"
            if value.endswith("true"):
                return value.replace("true", "True")
            if value.endswith("false"):
                return value.replace("false", "False")
        return value

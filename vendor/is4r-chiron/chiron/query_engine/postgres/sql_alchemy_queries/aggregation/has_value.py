from sqlalchemy import func

from chiron.query_engine.postgres.sql_alchemy_queries.aggregation._abstract import (
    AbstractPostgresAggregator,
)


class PgAggHasValue(AbstractPostgresAggregator):
    def __init__(self, chironuser, td_entry):
        self.selected_values = td_entry.get("aggregation_settings", {}).get("values", [])
        self.return_value = td_entry.get("aggregation_settings", {}).get("return_value", "boolean")
        handler = td_entry["concept"]._instantiate_concept_handler(chironuser=chironuser)
        self.data_type = handler.get_stored_data_type()
        super().__init__(chironuser, td_entry)

    def _get_agg_function(self):
        if self.return_value == "boolean":
            return func.json_arr_to_list_distinct
        elif self.return_value == "count":
            return func.json_arr_to_list_all

    def _get_outer_agg_function(self):
        if self.return_value == "boolean":
            return func.json_arr_set_to_list_distinct
        elif self.return_value == "count":
            return func.json_arr_set_to_list_all
        return func.json_arr_set_to_json_arr

    def values_to_postgres_array_string(self):
        quoted_values = []
        for value in self.selected_values:
            quoted_values.append('"' + value + '"')
        response = "{" + ", ".join(quoted_values) + "}"
        return response

    def create_agg_statement(
        self, concept_table, collection_table, double_aggregation=False, column_alias=None
    ):
        agg_func = self._get_agg_function()
        if self.return_value == "boolean":
            statement = self._generic_create_agg_statement_value_only2(concept_table, column_alias)
        elif self.return_value == "count":
            statement = self._generic_create_agg_statement_value_id(
                concept_table, collection_table, column_alias
            )
        else:  # date
            statement = self._generic_create_agg_statement_value_date_id(
                concept_table, collection_table, column_alias
            )
        if double_aggregation:
            return statement
        if self.return_value == "boolean":
            response = agg_func(statement)
            response = func.values_exist_in_array(response, self.values_to_postgres_array_string())
        elif self.return_value == "count":
            response = agg_func(statement)
            response = func.count_values_in_array(response, self.values_to_postgres_array_string())
        else:  # date response
            response = func.get_dates_for_values_in_json_arr(
                statement, self.values_to_postgres_array_string()
            )
            if self.return_value == "all_dates":
                response = func.all_array_to_distinct(response)
            if self.return_value == "earliest_date":
                response = func.get_array_position(response, 1)
            if self.return_value == "latest_date":
                response = func.get_array_position_reverse(response, 1)
        return response

    def create_outer_agg_statement(self, subquery, table, column_alias=None):
        outer_agg_func = self._get_outer_agg_function()
        response = outer_agg_func(subquery)
        if self.return_value == "boolean":
            response = func.values_exist_in_array(response, self.values_to_postgres_array_string())
        elif self.return_value == "count":
            response = func.count_values_in_array(response, self.values_to_postgres_array_string())
        else:
            response = func.get_dates_for_values_in_json_arr(
                response, self.values_to_postgres_array_string()
            )
            if self.return_value == "all_dates":
                response = func.all_array_to_distinct(response)
            if self.return_value == "earliest_date":
                response = func.get_array_position(response, 1)
            if self.return_value == "latest_date":
                response = func.get_array_position_reverse(response, 1)
        if column_alias:
            response = response.label(column_alias)
        return response

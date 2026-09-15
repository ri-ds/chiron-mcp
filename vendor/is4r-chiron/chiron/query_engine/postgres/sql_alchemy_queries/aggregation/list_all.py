from sqlalchemy import func

from chiron.query_engine.postgres.sql_alchemy_queries.aggregation._abstract import (
    AbstractPostgresAggregator,
)
from chiron import chiron_settings


class PgAggListAll(AbstractPostgresAggregator):
    def __init__(self, chironuser, td_entry):
        self.remove_nulls = False
        self.remove_null_dates = False
        self.ordering = td_entry.get("aggregation_settings", {}).get("list_all_ordering", "value")
        if td_entry.get("aggregation_settings", {}).get("list_all_include_nulls", "no") == "no":
            if self.ordering == "event_date":
                self.remove_nulls = True
                self.remove_null_dates = True
            else:
                self.remove_nulls = True
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
        if self.ordering == "event_date":
            if chiron_settings.CHIRON_EVENT_CONCEPT_TYPE == "detailed_age":
                if data_type == "integer":
                    return func.json_arr_to_list_all_by_age_int
                if data_type == "float":
                    return func.json_arr_to_list_all_by_age_float
                if data_type == "date":
                    return func.json_arr_to_list_all_by_age_date
                if data_type == "boolean":
                    return func.json_arr_to_list_all_by_age_bool
                return func.json_arr_to_list_all_by_age
            if data_type == "integer":
                return func.json_arr_to_list_all_chron_int
            if data_type == "float":
                return func.json_arr_to_list_all_chron_float
            if data_type == "date":
                return func.json_arr_to_list_all_chron_date
            if data_type == "boolean":
                return func.json_arr_to_list_all_chron_bool
            return func.json_arr_to_list_all_chron
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
        if self.ordering == "event_date":
            if chiron_settings.CHIRON_EVENT_CONCEPT_TYPE == "detailed_age":
                if data_type == "integer":
                    return func.json_arr_set_to_list_all_by_age_int
                elif data_type == "float":
                    return func.json_arr_set_to_list_all_by_age_float
                elif data_type == "date":
                    return func.json_arr_set_to_list_all_by_age_date
                elif data_type == "boolean":
                    return func.json_arr_set_to_list_all_by_age_bool
                return func.json_arr_set_to_list_all_by_age
            if data_type == "integer":
                return func.json_arr_set_to_list_all_chron_int
            elif data_type == "float":
                return func.json_arr_set_to_list_all_chron_float
            elif data_type == "date":
                return func.json_arr_set_to_list_all_chron_date
            elif data_type == "boolean":
                return func.json_arr_set_to_list_all_chron_bool
            return func.json_arr_set_to_list_all_chron
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
        if self.ordering == "event_date":
            statement = self._generic_create_agg_statement_value_date_id(
                concept_table, collection_table, column_alias
            )
        else:
            statement = self._generic_create_agg_statement_value_id(
                concept_table, collection_table, column_alias
            )
        if double_aggregation:
            return statement
        response = agg_func(statement)
        if self.remove_nulls:
            response = func.array_remove(response, None)
        return response

    def create_outer_agg_statement(self, subquery, table, column_alias=None):
        outer_agg_func = self._get_outer_agg_function()
        response = outer_agg_func(subquery)
        if self.remove_nulls:
            response = func.array_remove(response, None)
        if column_alias:
            response = response.label(column_alias)
        return response

    def after_query_modifier(self, value):
        if len(value) == 0:
            return None
        if len(value) == 1 and value[0] in [None, ""]:
            return None
        return value

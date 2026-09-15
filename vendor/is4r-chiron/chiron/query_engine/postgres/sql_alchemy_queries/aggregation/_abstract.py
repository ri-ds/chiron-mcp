from abc import ABC, abstractmethod

from sqlalchemy import func


class AbstractPostgresAggregator(ABC):
    """
    Handles aggregation of a report field for research data coming from Posgres.
    """

    def __init__(self, chironuser, td_entry):
        """
        :param obj chironuser: The chironuser requesting this report
        :param dict td_entry: The table def entry for the aggregated column
        """
        self.chironuser = chironuser
        self.td_entry = td_entry
        self.processor = self.td_entry["concept"].get_display_processor(
            self.chironuser, self.td_entry
        )
        self.subvalue = self.processor.use_subvalue(self.td_entry)

    def get_column(self, table):
        """Get a reference to the SQL alchemy column where the data will come from.

        :param obj table: the SQL Alchemy table containing this column
        :return:
        """
        if self.subvalue:
            field_name = "{}__{}".format(self.td_entry["concept_id"], self.subvalue)
            column = getattr(table.c, field_name)
        else:
            column = getattr(table.c, self.td_entry["concept_id"])
        processor = self.td_entry["concept"].get_display_processor(self.chironuser, self.td_entry)
        column = processor.sql_alchemy_map_in_query(column)
        return column

    @abstractmethod
    def create_agg_statement(
        self, concept_table, collection_table, double_aggregation=False, column_alias=None
    ):
        """Create the SQL query statement to get the aggregated data for this column.

        :param obj concept_table: the SQL Alchemy table where the concept data is stored
        :param obj collection_table: the SQL Alchemy table for the collection the concept is
          associated with
        :param bool double_aggregation: Will the subqery this returns be aggregated again
          using create_outer_agg_statement()
        :param obj column_alias: an optional alias for the subquery column
        :return: the sql alchemy subquery
        """
        raise NotImplementedError("Abstract method has not been implemented")

    @abstractmethod
    def create_outer_agg_statement(self, subquery, table, column_alias=None):
        """Create the SQL query statement to get the double aggregated data for this column.

        Some aggregate queries need to aggregate the data twice, once for a 1:many join between
        the main table (defined in the main FROM statement) and the subquery table that points to
        where this data is stored, and another aggregation for using GROUP BY in the main table.

        :param obj subquery: the subquery that pulls the
        :param obj table:
        :param obj column_alias: an optional alias for the subquery column
        :return: the double aggregated sql alchemy subquery
        """
        raise NotImplementedError("Abstract method has not been implemented")

    def get_after_query_modifier(self):
        """Returns a function that should be used to modify query values after SQL is run."""
        return getattr(self, "after_query_modifier", None)

    def flatten_agg_result_value_only(self, value):
        """Returns a list of distinct, non-null values."""
        if isinstance(value, list) and len(value) == 1 and value[0] is None:
            return None
        if value and isinstance(value[0], list):
            distinct_values = set()
            for sublist in value:
                if sublist:
                    for item in sublist:
                        distinct_values.add(item)
            distinct_values.discard(None)
        else:
            distinct_values = set()
            for item in value:
                distinct_values.add(item)
            distinct_values.discard(None)
        return list(distinct_values)

    def flatten_agg_result_id_and_value(self, value, remove_nulls=False):
        """Returns a list of distinct id/value tuples."""
        if isinstance(value, list) and len(value) == 1:
            first_entry = value[0]
            if first_entry is None:
                return None
            if isinstance(first_entry, dict) and first_entry.get("f1") is None:
                return None
        # some queries will return list of lists of dicts
        if value and isinstance(value[0], list):
            added_values = set()
            for sublist in value:
                if sublist:
                    for item in sublist:
                        if item is not None and item["f1"] is not None:
                            added_value_entry = (item["f1"], item["f2"])
                            added_values.add(added_value_entry)
            value = list(added_values)
        # for normal list of dicts, need to remove duplicates records by ID
        else:
            added_values = set()
            for item in value:
                if item is not None and item["f1"] is not None:
                    added_value_entry = (item["f1"], item["f2"])
                    added_values.add(added_value_entry)
            value = list(added_values)
        if remove_nulls:
            value = [x for x in value if x[1] is not None]
        return value

    def flatten_agg_result_id_date_value(self, value, remove_nulls=False, remove_null_dates=False):
        """Returns a list of distinct id/date/value tuples."""
        if isinstance(value, list) and len(value) == 1:
            first_entry = value[0]
            if first_entry is None:
                return None
            if isinstance(first_entry, dict) and first_entry.get("f1") is None:
                return None
        # some queries will return list of lists of dicts
        if value and isinstance(value[0], list):
            added_values = set()
            for sublist in value:
                if sublist:
                    for item in sublist:
                        if item is not None and item["f1"] is not None:
                            added_value_entry = (item["f1"], item["f2"], item["f3"])
                            added_values.add(added_value_entry)
            value = list(added_values)
        # for normal list of dicts, need to remove duplicates records by ID
        else:
            added_values = set()
            for item in value:
                if item is not None and item["f1"] is not None:
                    added_value_entry = (item["f1"], item["f2"], item["f3"])
                    added_values.add(added_value_entry)
            value = list(added_values)
        if remove_nulls:
            value = [x for x in value if x[2] is not None]
        if remove_null_dates:
            value = [x for x in value if x[1] is not None]
        return value

    def _generic_create_agg_statement_value_only(self, table, column_alias=None):
        column = self.get_column(table)
        response = func.json_agg(column)
        if column_alias:
            response = response.label(column_alias)
        return response

    def _generic_create_agg_statement_value_only2(self, table, column_alias=None):
        column = self.get_column(table)
        row_func = func.row(column)
        response = func.json_agg(row_func)
        if column_alias:
            response = response.label(column_alias)
        return response

    def _generic_create_outer_agg_statement_value_only(self, subquery, table, column_alias=None):
        response = func.json_agg(subquery)
        if column_alias:
            response = response.label(column_alias)
        return response

    def _generic_create_agg_statement_value_id(
        self, concept_table, collection_table, column_alias=None
    ):
        id_column = collection_table.c._id
        column = self.get_column(concept_table)
        row_func = func.row(id_column, column)
        response = func.json_agg(row_func)
        if column_alias:
            response = response.label(column_alias)
        return response

    def _generic_create_outer_agg_statement_value_id(self, subquery, table, column_alias=None):
        response = func.json_agg(subquery)
        if column_alias:
            response = response.label(column_alias)
        return response

    def _generic_create_agg_statement_value_date_id(
        self, concept_table, collection_table, column_alias=None
    ):
        id_column = collection_table.c._id
        column = self.get_column(concept_table)
        if self.td_entry["concept"].collection.event_date_field:
            date_field = self.td_entry["concept"].collection.event_date_field.permanent_id
            date_column = getattr(collection_table.c, date_field)
            row_func = func.row(id_column, date_column, column)
            response = func.json_agg(row_func)
        else:
            row_func = func.row(id_column, "NULL", column)
            response = func.json_agg(row_func)
        if column_alias:
            response = response.label(column_alias)
        return response

    def _generic_create_outer_agg_statement_value_date_id(
        self, subquery, table, column_alias=None
    ):
        response = func.json_agg(subquery)
        if column_alias:
            response = response.label(column_alias)
        return response

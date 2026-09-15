from chiron.query_engine.postgres.sql_alchemy_queries import AbstractSqlAlchemyPartBuilder


class GroupByStatementBuilder(AbstractSqlAlchemyPartBuilder):
    def modify_statement(self, statement):
        if self.table is None:
            return statement.distinct()
        sortable_columns = self.query_info.sortable_columns
        group_by = []
        has_aggregated_fields = False
        for field in self.table.internal_table_def["fields"]:
            if field.get("aggregate"):
                has_aggregated_fields = True
            else:
                column = sortable_columns[field["entry_id"]]
                group_by.append(column)
        if has_aggregated_fields:
            statement = statement.group_by(*group_by)
        else:
            # statement = statement.distinct()
            # in testing I found that GROUP BY is often faster than DISTINCT in general
            statement = statement.group_by(*group_by)
        return statement

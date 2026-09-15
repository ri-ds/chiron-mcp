from chiron.query_engine.postgres.sql_alchemy_queries import AbstractSqlAlchemyPartBuilder


class OrderByStatementBuilder(AbstractSqlAlchemyPartBuilder):
    def modify_statement(self, statement):
        sortable_columns = self.query_info.sortable_columns
        for entry in self.table.internal_table_def.get("sort", []):
            if entry["entry_id"] in sortable_columns:
                column = sortable_columns[entry["entry_id"]]
                if entry.get("direction", 1) == 1:
                    statement = statement.order_by(column.asc())
                else:
                    statement = statement.order_by(column.desc())
        return statement

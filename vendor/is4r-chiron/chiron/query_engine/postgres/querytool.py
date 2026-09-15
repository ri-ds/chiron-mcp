import pandas as pd
from natsort import natsort_keygen
from datetime import datetime
from sqlalchemy.exc import CompileError


from chiron.query_engine.abstract_querytool import AbstractQueryTool
from chiron.query_engine.postgres.sql_alchemy_queries.query_builder import SqlAlchemyQueryBuilder
from chiron.query_engine.display import get_display_values
from chiron.query_engine.postgres.database import get_sql_alchemy_db_engine
from chiron import helpers
from chiron.cache import CachedCohortWrapper


class QueryToolPostgres(AbstractQueryTool):
    def run(self, label, statement, return_scope="all"):
        """Runs a function or method and collects performance/data info.

        :param label: what to call this query in any logs or print statements
        :param statement: the sqlalchemy statement to run
        :param return_scope: "all", "first_row", "first_col", "first_val"
        :return: executed statement result
        """
        start = datetime.now()
        try:
            sql_string = str(statement.compile(compile_kwargs={"literal_binds": True}))
        except CompileError:
            sql_string = str(statement)
        helpers.print_query_info(f"--START {label}")
        helpers.print_query_info(sql_string)
        with get_sql_alchemy_db_engine(self.dataset).connect() as conn:
            if return_scope == "all":
                response = []
                for row in conn.execute(statement):
                    response.append(list(row))
            elif return_scope == "first_row":
                response = conn.execute(statement).first()
            elif return_scope == "first_col":
                response = []
                for row in conn.execute(statement):
                    response.append(row[0])
            else:  # first_val
                response = conn.execute(statement).first()[0]
        if self.analyze_performance:
            end = datetime.now()
            diff = round((end - start).total_seconds(), 1)
            helpers.print_query_info(f"query completed in {diff} seconds")
        helpers.print_query_info(f"--END {label}")
        return response

    def get_report_preview(self, output_type="html", skip=0, limit=10):
        """Returns a paginated report dataset.

        :param str output_type: "html", "python", "json","csv" - This information will be used to
          set appropriate data values. For example, if "csv" is selected then dates will be
          converted to date strings.
        :type output_type: string, default="html"
        :param skip: the number of records to skip for pagination
        :type skip: integer, default=0
        :param limit: the number of records to limit for pagination
        :type limit: integer, default=10
        :return: A tuple with the paginated dataset, the subject count, and the record count.
          Counts are for the full dataset, not just the paginated section.
        :rtype: (list of dicts, integer, integer)
        """
        builder2 = SqlAlchemyQueryBuilder(self.chironuser, self.cohort, self.table)
        # get the subject count
        subject_count = self.get_cohort_count()
        # get the record count
        count_statement = builder2.get_sql_statement_record_count()
        record_count = self.run("recordcount", count_statement, "first_val")
        # get the paginated records
        statement = builder2.get_sql_statement(skip=skip, limit=limit)
        response = self.run("preview", statement)
        response = builder2.run_after_query_aggregation_modification(response)
        response = get_display_values(
            response, self.chironuser, self.cohort, self.table, output_type
        )
        return response, subject_count, record_count

    def get_full_report(self, output_type):
        """Returns an entire (non-paginated) report dataset.

        :param output_type: "html", "python", "json","csv" - This information will be used to
          set appropriate data values. For example, if "csv" is selected then dates will be
          converted to date strings.
        :type output_type: string
        :return: The full dataset generated based on the defined cohort def and table def.
        :rtype: list of dicts
        """
        builder2 = SqlAlchemyQueryBuilder(self.chironuser, self.cohort, self.table)
        statement = builder2.get_sql_statement()
        response = self.run("fullreport", statement)
        response = builder2.run_after_query_aggregation_modification(response)
        response = get_display_values(
            response, self.chironuser, self.cohort, self.table, output_type
        )
        return response

    def get_cohort_count(self):
        """Returns the count of subjects in your cohort.

        The number of subjects matching your cohort def. Note the table_def is irrelevant.

        :return: Subject count
        :rtype: integer
        """
        # get values from cache if available
        if self.cohort.cohort_def:
            if self.cache_mode in [
                QueryToolPostgres.CACHE_MODE_READ,
                QueryToolPostgres.CACHE_MODE_READ_WRITE,
            ]:
                cache_tool = CachedCohortWrapper(self.chironuser, self.cohort)
                oCache = cache_tool.find_matching_cache_entry()
                if oCache:
                    helpers.print_query_info("used cache to get patient count")
                    return oCache.count
        builder2 = SqlAlchemyQueryBuilder(self.chironuser, self.cohort, self.table)
        statement = builder2.get_sql_statement_subject_count()
        subject_count = self.run("subjectcount", statement, "first_val")
        # save results to cache
        if self.cohort.cohort_def:
            if self.cache_mode in [
                QueryToolPostgres.CACHE_MODE_WRITE,
                QueryToolPostgres.CACHE_MODE_READ_WRITE,
            ]:
                cache_tool = CachedCohortWrapper(self.chironuser, self.cohort)
                cache_tool.save_new_cache_entry(subject_count)
        return subject_count

    def run_analysis(self, analysis):
        """Gets analysis view query result, which is a pandas pivottable.

        :params analysis: The object defining the analysis definition to use.
        :type analysis: Analysis object
        :return: The dataset generated based on the cohort def and the provided analysis object.
        :rtype: pandas pivottable
        """
        table = self._define_table_for_analysis_view(analysis)
        self.table = table
        builder2 = SqlAlchemyQueryBuilder(self.chironuser, self.cohort, self.table)
        statement = builder2.get_sql_statement()
        response = self.run("runanalysis", statement)
        response = builder2.run_after_query_aggregation_modification(response)
        data = get_display_values(
            response, self.chironuser, self.cohort, self.table, output_type="python"
        )
        row_headers = [x["label"] for x in analysis.extended_analysis_def.get("rows", [])]
        col_headers = [x["label"] for x in analysis.extended_analysis_def.get("cols", [])]
        field_headers = [x["label"] for x in table.table_def.get("fields", [])]
        df = pd.DataFrame.from_records(data, columns=field_headers)
        # pivot_table throws away "none" values, so convert to string to keep

        try:
            pivottable = pd.pivot_table(
                df, values="subject count", index=row_headers, columns=col_headers, aggfunc="sum"
            )  # to show totals: margins=True, margins_name="Total"
        except ValueError:
            pivottable = pd.pivot_table(
                df, values="subject count", index=row_headers, columns=col_headers, aggfunc="sum"
            )
        pivottable = pivottable.fillna(0).astype(int)
        pivottable.sort_values(by=row_headers, inplace=True, key=natsort_keygen())
        if self.chironuser.access_level == self.chironuser.AccessLevel.AGG:
            pivottable = self._analysis_view_aggregate_pivottable(pivottable)
        return pivottable

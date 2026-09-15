from abc import ABC, abstractmethod
from collections import OrderedDict
from datetime import datetime

from chiron.query_definition import Cohort, Table
from chiron import helpers
from chiron import chiron_settings


class AbstractQueryTool(ABC):
    """Run queries against a research dataset.

    This class and the StatTool class handle all interactions between the website and
    the database containing research data. For modularity and to make sure data access rules
    are enforced, all queries against the database should go through this class instead of
    hitting the database directly.

    :param chironuser: The active chironuser. If no user (for example, in a management command),
      set to None
    :type chironuser: ChironUser model object
    :param cohort_def: the cohort definition for the query
    :type cohort_def: dict
    :param table_def: the table definition for the query, if relevant
    :type table_def: dict, default=None
    :param analyze_performance: collect additional data about query performance
    :type analyze_performance: boolean, default=True
    :param analyze_data: collect data about query results (this can be very slow, should only
      be used when troubleshooting)
    :type analyze_data: boolean, default=False
    :param cache_mode: whether to use/create cached data when available
    :type cache_mode: constant string: CACHE_MODE_OFF, CACHE_MODE_READ, CACHE_MODE_WRITE,
      CACHE_MODE_READ_WRITE
    """

    CACHE_MODE_OFF = None  # don't use cache
    CACHE_MODE_READ = "r"  # use cached data when available but don't save to cache
    CACHE_MODE_WRITE = "w"  # don't use cached data but save to cache when appropriate
    CACHE_MODE_READ_WRITE = "rw"  # read/write from cache whenever possible

    def __init__(
        self,
        chironuser,
        cohort_def,
        table_def=None,
        analyze_performance=True,
        analyze_data=False,
        cache_mode="rw",
    ):
        self.chironuser = chironuser
        self.dataset = chironuser.dataset
        self.cohort = Cohort(chironuser, cohort_def)
        self.table = None
        if table_def is not None:
            self.table = Table(chironuser, cohort_def, table_def)
        self.analyze_performance = analyze_performance
        self.analyze_data = analyze_data
        self.cohort_count = None
        self.cohort_ids = None
        self.cache_mode = cache_mode
        self.time_analysis = OrderedDict()
        self.data_analysis = OrderedDict()

    def run(self, func, *args):
        """Runs a function or method and collects performance/data info.

        Calls to functions or methods that perform queries can be run using this
        method, which will optionally collect additional data about the query
        performance and data returned.

        :param func: the Python method/function to run
        :type func: function
        :param args: the arguments to pass to the function
        :type args: any number of arguments of any type
        """
        start = datetime.now()
        response = func(*args)
        if self.analyze_performance:
            end = datetime.now()
            diff = round((end - start).total_seconds(), 1)
            helpers.print_query_info("report pipeline: {} seconds: {}".format(diff, func.__name__))
            self.time_analysis[func.__name__] = "{} seconds".format(diff)
        if self.analyze_data:
            self.data_analysis[func.__name__] = helpers.to_json_string(response, 4)[:100000]
        return response

    @abstractmethod
    def get_full_report(self, output_type):
        """Returns an entire (non-paginated) report dataset.

        :param output_type: "html", "python", "json","csv" - This information will be used to
          set appropriate data values. For example, if "csv" is selected then dates will be
          converted to date strings.
        :type output_type: string
        :return: The full dataset generated based on the defined cohort def and table def.
        :rtype: list of dicts
        """
        raise NotImplementedError("Abstract method has not been implemented")

    @abstractmethod
    def get_report_preview(self, output_type="html", skip=0, limit=10):
        """Returns a paginated report dataset.

        :param output_type: "html", "python", "json","csv" - This information will be used to
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
        raise NotImplementedError("Abstract method has not been implemented")

    @abstractmethod
    def get_cohort_count(self):
        """Returns the count of subjects in your cohort.

        The number of subjects matching your cohort def. Note the table_def is irrelevant.

        :return: Subject count
        :rtype: integer
        """
        raise NotImplementedError("Abstract method has not been implemented")

    @abstractmethod
    def run_analysis(self, analysis):
        """Gets analysis view query result, which is a pandas pivottable.

        :params analysis: The object defining the analysis definition to use.
        :type analysis: Analysis object
        :return: The dataset generated based on the cohort def and the provided analysis object.
        :rtype: pandas pivottable
        """
        raise NotImplementedError("Abstract method has not been implemented")

    def _define_table_for_cohort_count(self):
        """Returns an empty Table object to use for getting cohort counts."""
        oConcept = self.chironuser.dataset.root_collection.event_id_field
        empty_table_def = {
            "fields": [
                {
                    "entry_id": "cohort_count_entry",
                    "concept_id": oConcept.permanent_id,
                }
            ],
            "sort": [],
        }
        return Table(self.chironuser, self.cohort, empty_table_def)

    def _define_table_for_analysis_view(self, analysis):
        """Converts analysis object into a table object."""
        subject_id_concept = self.chironuser.dataset.root_collection.event_id_field
        table_def = {"fields": [], "sort": []}
        for entry in analysis.extended_analysis_def.get("rows", []):
            table_def["fields"].append(
                {
                    "concept_id": entry["concept_id"],
                    "entry_id": entry["entry_id"],
                    "label": entry["label"],
                    "categorize": True,
                }
            )
            table_def["sort"].append(
                {
                    "entry_id": entry["entry_id"],
                    "direction": 1,
                }
            )
        for entry in analysis.extended_analysis_def.get("cols", []):
            table_def["fields"].append(
                {
                    "concept_id": entry["concept_id"],
                    "entry_id": entry["entry_id"],
                    "label": entry["label"],
                    "categorize": True,
                }
            )
            table_def["sort"].append(
                {
                    "entry_id": entry["entry_id"],
                    "direction": 1,
                }
            )
        table_def["fields"].append(
            {
                "concept_id": subject_id_concept.permanent_id,
                "entry_id": "patient_count_entry",
                "label": "subject count",
                "aggregate": True,
                "aggregation_method": "count_distinct",
            }
        )
        return Table(self.chironuser, self.cohort.cohort_def, table_def)

    def _analysis_view_aggregate_pivottable(self, df):
        """Modifies the provided data frame to hide

        The pivottables returned in analysis view may need to obscure some values if the user
        has a permission level that only allows them to see aggregated data. For example, subject
        counts below the minimum limit (CHIRON_AGG_SUBJECT_COUNT_MIN_LIMIT) will be converted
        to "<5", "<10", etc.
        """
        df = df.astype(str)
        min_limit = chiron_settings.CHIRON_AGG_SUBJECT_COUNT_MIN_LIMIT
        low_vals = map(str, range(1, min_limit + 1))  # creates array ["1", "2", ...]
        df[df.isin(low_vals)] = "<{}".format(min_limit)
        return df

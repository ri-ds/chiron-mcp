from datetime import datetime
from collections import OrderedDict
from abc import ABC, abstractmethod

from chiron import helpers
from chiron.query_definition import Cohort


class AbstractStatTool(ABC):
    """Get statistics about a concept.

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

    def __init__(
        self,
        chironuser,
        cohort_def=None,
        concept=None,
        collection_prefilters=None,
        analyze_performance=True,
        analyze_data=False,
    ):
        self.chironuser = chironuser
        self.dataset = chironuser.dataset
        cohort_def = cohort_def if cohort_def else []
        self.cohort = Cohort(chironuser, cohort_def)
        self.concept = concept
        self.collection_prefilters = collection_prefilters
        self.analyze_performance = analyze_performance
        self.analyze_data = analyze_data
        self.time_analysis = OrderedDict()
        self.data_analysis = OrderedDict()
        # store data and statistics to avoid recalculating
        self.subject_concept_interim_data = None
        self.cache = {}

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
            helpers.print_query_info("stats pipeline: {} seconds: {}".format(diff, func.__name__))
            self.time_analysis[func.__name__] = "{} seconds".format(diff)
        if self.analyze_data:
            self.data_analysis[func.__name__] = helpers.to_json_string(response, 4)
        return response

    def _build_concept_table_def(self, sort_data=True):
        sort = []
        if sort_data:
            sort.append({"entry_id": "dummyid", "direction": 1})
        concept_table_def = {
            "fields": [
                {
                    "entry_id": "dummyid",
                    "concept_id": self.concept.permanent_id,
                    "aggregate": False,
                    "aggregation_method": None,
                }
            ],
            "sort": sort,
        }
        return concept_table_def

    def _get_subject_concept_interim_data(self):
        """
        subject_concept_interim_data is an interim dataset that's used as a starting point for a
        lot of calculations. It's a list of tuples (subject_id, concept_id, sort_value, value).
        It gets saved as property the first time it's calculated.
        """
        pass

    def _get_concept_interim_data(self):
        """
        Return all concept values as a list
        """
        pass

    @abstractmethod
    def get_non_null_subject_count(self, subvalue=None):
        """Count subjects with at least one non-null value for this concept.

        :return: count of subjects with at least one value for concept
        :rtype: integer
        """
        raise NotImplementedError("Abstract method has not been implemented")

    @abstractmethod
    def get_non_null_values_count(self, subvalue=None):
        """Count number of non-null values for this concept.

        :return: count total non-null values for concept
        :rtype: integer
        """
        raise NotImplementedError("Abstract method has not been implemented")

    @abstractmethod
    def get_missing_values_count(self):
        """Count of values that are None or empty string.

        If concept is in a subcollection, also includes count of subjects with no subcol record.

        :return: count total null or empty values for concept
        :rtype: integer
        """
        raise NotImplementedError("Abstract method has not been implemented")

    @abstractmethod
    def get_subjects_with_missing_values_count(self):
        """Count of subjects with no values for this concept.

        A subject will have no values for the concept if there are no records in this collection
        associated with the subject, or if all the records associated have values of None or
        empty string.

        :return: count total subjects with no values for this concept
        :rtype: integer
        """
        raise NotImplementedError("Abstract method has not been implemented")

    @abstractmethod
    def get_min(self, output_type="json"):
        """The minimum value for this concept."""
        raise NotImplementedError("Abstract method has not been implemented")

    @abstractmethod
    def get_max(self, output_type="json"):
        """The maximum value for this concept."""
        raise NotImplementedError("Abstract method has not been implemented")

    @abstractmethod
    def get_avg(self, output_type="json"):
        """The average value for this concept."""
        raise NotImplementedError("Abstract method has not been implemented")

    @abstractmethod
    def get_number_histogram(self, is_integer=False, number_is_year=False, subvalue=None):
        """Generate a histogram for concepts with numeric data."""
        raise NotImplementedError("Abstract method has not been implemented")

    @abstractmethod
    def get_age_histogram(self):
        """Generate a histogram for concepts with ages."""
        raise NotImplementedError("Abstract method has not been implemented")

    @abstractmethod
    def get_date_histogram(self):
        """Generate a histogram for concepts with dates."""
        raise NotImplementedError("Abstract method has not been implemented")

    @abstractmethod
    def lookup_unique_values(self, limit=None, subvalue=None):
        """Get a list of unique concept values.

        :param limit: the maximum number of values to return
        :type limit: integer, or None to return all values
        :return: all distinct values for the concept
        :rtype: list
        """
        raise NotImplementedError("Abstract method has not been implemented")

    @abstractmethod
    def get_all_unique_strings(self, limit=None):
        """Specific for number with categories field, returns just the distinct
        categories.
        """
        raise NotImplementedError("Abstract method has not been implemented")

    @abstractmethod
    def get_unique_values_with_counts(self, sort_by="count", subvalue=None):
        """Get a list of unique concept values with frequency counts.

        For each distinct value, returns the value along with how many times
        that value appears in the dataset and for how many distinct subjects.

        :param limit: the maximum number of values to return
        :type limit: integer, or None to return all values
        :return: list of dicts with "category", "count", "uniquePatientCount"
        :rtype: list of dicts
        """
        raise NotImplementedError("Abstract method has not been implemented")

    @abstractmethod
    def lookup_bulk_values(self, search_list):
        """Lookup Bulk Search

        Lookup multiple search values.

        WARNING: A user could possibly use this function to guess values
        in the database they might not have access to.  If you need it to
        use permissions, make sure the concept is marked as PHI.

        :param search_list: List of terms to search
        :type search_list: list
        :return: List of matching entries
        :rtype: list
        """
        raise NotImplementedError("Abstract method has not been implemented")

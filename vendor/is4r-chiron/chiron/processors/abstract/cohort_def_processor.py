from abc import ABCMeta, abstractmethod

from django.utils.html import conditional_escape

from chiron import helpers
from chiron.cache import CachedConceptStatsWrapper
from chiron.query_definition import Cohort
from chiron.models import SystemChironUser


class CohortDefProcessor:
    """
    Handles how a concept gets applied in queries. It is associated with a concept in the data
    dictionary using the ``Concept.cohort_def_processor`` field.

    IMPORTANT METHOD WORKFLOWS:

    Getting Statistics About a Concept:

    - preprocess_statistics() - generates a Python dict of statistical data about the concept
    - get_statistics() - access data from preprocess(), either directly or from a cache

    Creating a Cohort Def Entry:

    - get_form_options() - data needed to generate a cohort def form
    - form_callback() - allows forms to load iteratively or be interactive using AJAX
    - form_callback_streaming() - can yield multiple responses for HttpStreaming
    - validate_form() - checks if a form submission is valid
    - generate_cohort_def_entry() - converts form submission into a dict to be added to cohort def

    Using a Cohort Def Entry:

    - display_entry_as_string()
    - display_entry_as_html()
    """

    __metaclass__ = ABCMeta

    concept_type = "undefined"

    def __init__(self, chironuser, oDataset, oConcept, **kwargs):
        self.chironuser = chironuser if chironuser else SystemChironUser(oDataset)
        self.dataset = oDataset
        self.concept = oConcept
        self.prefilter_value = kwargs.get("prefilter_value", None)
        self.collection_prefilters = self.concept.get_collection_prefilters(self.prefilter_value)
        self.cleaned = {}
        self.form_errors = []
        self.form_warnings = []
        self.args = {}
        for key, value in kwargs.items():
            self.args[key] = value

    def preprocess_statistics(self, cd):
        """
        If there is data needed to render the cohort def form, it can be retrieved/calculated here.
        NOTE: Don't access directly! Instead, use ``self.get_statistics()`` which will
        manage caching of this data.

        :param cd: the cohort definition to use
        :type cd: list of dicts
        :return: key/value pairs of data
        :rtype: dict
        """
        return {}

    def get_statistics(self, cd):
        """
        Will decide when to use cache vs when to run preprocess_statistics() method.
        There shouldn't be any need to override this method.
        note: There is no cache implemented yet, so just returns preprocess_statistics()
        results directly.

        :param cd: the cohort definition to use
        :type cd: list of dicts
        :return: key/value pairs of data
        :rtype: dict
        """
        # use cached stats if available
        cohort = Cohort(self.chironuser, cd)
        cache_tool = CachedConceptStatsWrapper(
            self.chironuser, cohort, self.concept, self.prefilter_value
        )
        oCache = cache_tool.find_matching_cache_entry()
        if oCache:
            helpers.print_query_info("concept statistics retrieved from cache")
            stats = oCache.get_stats()
            stats["perf"] = {}
            return stats
        # if no cached stats, generate stats and save to cache before returning
        stats = self.preprocess_statistics(cd)
        cache_tool.save_new_cache_entry(stats)
        if self.chironuser.access_level == self.chironuser.AccessLevel.AGG:
            stats = self.aggregate_stats(stats)
        return stats

    @abstractmethod
    def aggregate_stats(self, stats):
        """
        Convert stats to hide any non-aggregated data. This is run automatically as needed
        when you use the `get_statistics()` method.
        """
        raise NotImplementedError(
            "This CohortDefProcessor doesn't define an aggregate_stats method."
        )

    @abstractmethod
    def get_form_options(self, cd, existing_cd_entry=None):
        """
        Returns any data needed to render a form for creating a cohort def entry
        """
        raise NotImplementedError(
            "This CohortDefProcessor doesn't define a get_form_options method."
        )

    @abstractmethod
    def form_callback(self, get_data):
        """
        Used when the form needs to collect data by AJAX in order to work properly.
        Data returned by this will be passed to the form as JSON data.

        :param get_data: the HTTP GET arguments from the client
        :type get_data: dict
        :return: the response to be returned to the client
        :rtype: dict
        """
        raise NotImplementedError("This CohortDefProcessor doesn't define a form_callback method.")

    @abstractmethod
    def form_callback_streaming(self, get_data):
        """
        Same as form callback but can yield data multiple times to be returned using
        streaming HTTP

        :param get_data: the HTTP GET arguments from the client
        :type get_data: dict
        :return: the response(s) to be returned to the client
        :rtype: iterator of dicts
        """
        raise NotImplementedError("This CohortDefProcessor doesn't define a form_callback method.")

    def validate_form(self, form_data):
        """
        If provided form validates, returns True and populates self.cleaned dict with any data
        needed to generate a cohort def entry. If validation fails, returns False and adds
        error message strings to self.errors list.

        :param form_data: the HTTP POST arguments from the client
        :type form_data: dict
        :return: whether form validated
        :rtype: boolean
        """
        for key, value in form_data.items():
            self.cleaned[key] = value
        return True

    def get_fields_to_index(self):
        """ """
        root_field = ""
        return [root_field]

    @abstractmethod
    def generate_cohort_def_entry(self, cd=None, existing_cd_entry=None):
        """
        Creates a cohort def entry dict that can be added to the cohort definition.
        NOTE: This should only be run after validate_form has successfully run.

        :param cd: the cohort definition to add this entry to
        :type cd: list of dicts
        :param existing_cd_entry: cohort def entry if editing existing
        :type existing_cd_entry: dict
        :return: the cohort def entry
        :rtype: dict
        """
        raise NotImplementedError(
            "This CohortDefProcessor doesn't define a generate_cohort_def_entry method."
        )

    def display_entry_as_string(self, cd_entry):
        """
        Converts cd_entry dict into a human-readable string

        :param cd_entry: the cohort def entry to convert
        :type cd_entry: dict
        :return: the human-readable string (**cannot** contain HTML formatting tags)
        :rtype: string
        """
        return conditional_escape(cd_entry)

    def display_entry_as_html_full(self, cd_entry):
        html = self.display_entry_as_html(cd_entry, "full")
        if cd_entry.get("prefilter_value"):
            html = "<em>({})</em> {}".format(cd_entry["prefilter_value"], html)
        return html

    def display_entry_as_html_abbreviated(self, cd_entry):
        html = self.display_entry_as_html(cd_entry, "abbreviated")
        if cd_entry.get("prefilter_value"):
            html = "<em>({})</em> {}".format(cd_entry["prefilter_value"], html)
        return html

    def display_entry_as_html(self, cd_entry, abbreviation="full"):
        """
        Converts cd_entry dict into a human-readable HTML-formatted string

        SECURITY: This string should be displayable as HTML without risk of XSS, etc.
          If the string incorporates user-input text that hasn't already been sanitized/
          escaped, it should be dealt with here.

        :param cd_entry: the cohort def entry to convert
        :type cd_entry: dict
        :return: the human-readable string (**can** contain HTML formatting tags)
        :rtype: string
        """
        return conditional_escape(cd_entry)

    @abstractmethod
    def get_sql_alchemy_clause(self, cd_entry, table):
        """Returns the argument to pass to a sql alchemy WHERE expression for this filter.

        Converts the filter definition provided by cd_entry to an expression that will be used
        to build a SQL query. The expression will reference the provided sql alchemy table.

        """
        raise NotImplementedError(
            "This CohortDefProcessor doesn't define a get_sql_alchemy_clause method."
        )

    def get_sql_alchemy_bool_clause(self, table):
        """Defines how to use this concept to filter subjects for permission groups.

        Concepts used to filter permission groups (defined in the data dictionary
        PermissionGroup.concept_for_allowed_subjects) need to define when to include/exclude
        subjects.
        """
        column = getattr(table.c, self.concept.permanent_id)
        return column != None  # noqa

    def get_concept_search_terms(self):
        """
        The concept list is searchable. By default, search includes the concept ID,
        the concept name, the concept description, and all parent category names.

        To add additional search terms, return them here as a single string. This method is called
        after all the data is loaded, so it can query the research data to include patient data
        values.
        """
        return ""

    # def summarize(self, cd):
    #     """
    #     Some summary statistics about this concept (shouldn't be any need to override this
    #     method)
    #     """
    #     data = {}
    #     collection = mongo_db.get_subject_mongo_col()
    #     field_name = self.concept.permanent_id
    #     oConcept = models.Concept.objects.get(permanent_id=field_name)
    #     agg = query_engine.start_aggregation_pipeline(
    #         self.user,
    #         cd,
    #         output_concepts=[self.concept],
    #         preserve_null_and_empty_arrays=False,
    #     )
    #     # get all records for field that are missing or null
    #     agg.append({"$match": {oConcept.get_full_mongo_field_name(): {"$ne": None}}})
    #     # count unique subjects
    #     agg.append(
    #         {
    #             "$group": {
    #                 "_id": None,
    #                 "value_count": {"$sum": 1},
    #                 "unique_value_set": {
    #                     "$addToSet": "${}".format(oConcept.get_full_mongo_field_name())
    #                 },
    #                 "unique_patient_set": {"$addToSet": "$_id"},
    #             }
    #         }
    #     )
    #     agg.append(
    #         {
    #             "$project": {
    #                 "_id": 0,
    #                 "value_count": 1,
    #                 "unique_value_count": {"$size": "$unique_value_set"},
    #                 "unique_patient_count": {"$size": "$unique_patient_set"},
    #             }
    #         }
    #     )
    #     data["value_count"] = 0
    #     data["unique_value_count"] = 0
    #     data["unique_patient_count"] = 0
    #     cohort_data = collection.aggregate(agg, allowDiskUse=True)
    #     value_list = list(cohort_data)
    #     if value_list:
    #         data["value_count"] = value_list[0]["value_count"]
    #         data["unique_value_count"] = value_list[0]["unique_value_count"]
    #         data["unique_patient_count"] = value_list[0]["unique_patient_count"]
    #     return data

    def _generate_cd_entry_template(self, additional_args={}):
        """
        Generates a universal base that can be used by self.generate_cohort_def_entry()

        :param additional_args: concept-specific values to include in cd_entry
        :type additional_args: dict
        :return: a cd_entry with concept_id and entry_id set
        :rtype: dict
        """
        response = additional_args
        response["entry_id"] = helpers.generate_entry_id()
        response["concept_id"] = self.concept.permanent_id
        if self.prefilter_value:
            response["prefilter_value"] = self.prefilter_value
        return response

    def can_run_deid_query(self, cd_entry):
        """
        Only for fields that are used as deid alternatives. Determines if the specified cd_entry
        can be applied to the query in a deidentified fashion.
        """
        return False

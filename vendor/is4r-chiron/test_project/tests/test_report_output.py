# from django.test import TestCase
from rest_framework.reverse import reverse

from chiron import chiron_settings
from .utils.base_testcase import BaseTestCase


class ReportOutputTest(BaseTestCase):
    """
    Runs saved reports and tests that the report data output is correct. Saved reports come from
    the test_project.

    How to add a test:
    1. generate and save a new report in the test_project
    2. save test_project database using management command `save_test_project_state`
    3. get JSON output with http://localhost:8000/api/report_tools/[report_id]/export_json/
    4. Copy the JSON output to directory query_engine/tests/test_output_data/
    5. add your test here
    """

    @classmethod
    def setUpTestData(cls):
        cls.initialize_chiron()
        cls.load_dataset(cls.DS1_STORED)
        cls.testuser = {
            "dataset_name": cls.DS1_STORED,
            "username": "testuser",
            "access_level": "phi",
            "permission_groups": ["all"],
        }

    def test_root_collection_simple_data_types(self):
        """
        Results from queries on root collection including nulls, overloaded
        fields, exclude. Only simple data types, not multi-value dicts. i.e. text, category,
        boolean, date, integer, float
        """
        self.setup_user(**self.testuser)
        for i in range(2, 14):
            if i in [8, 9]:
                # TODO: regex not working
                continue
            self.check_report(i, "query{}.json".format(i))

    def test_subcollection_simple_data_types(self):
        """
        Results from queries on subcollection including nulls, overloaded
        fields, exclude. Only simple data types, not multi-value dicts. i.e. text, category,
        boolean, date, integer, float
        """
        self.setup_user(**self.testuser)
        for i in range(14, 26):
            if i in [18, 19]:
                # TODO: regex isn't supported yet
                continue
            if i in [20]:
                # TODO: On reports that filter on an overloaded field in a subcollection and
                #    stack by the same subcollection, the non-matching values in the overloaded
                #    entry don't get filtered out. I'm not even sure they should, but it
                #    is different from previous behavior.
                continue
            self.check_report(i, "query{}.json".format(i))
        i = 135
        self.check_report(i, "query{}.json".format(i))

    def test_root_collection_complex_data_types(self):
        """
        Results from queries on root collection for complex data types: i.e. data that needs
        to be stored in postgres as multiple fields
        """
        self.setup_user(**self.testuser)
        for i in [27, 29, 30, 31]:
            if i in [27, 29]:
                # TODO: Number with category fields are not sorting correctly.
                continue
            self.check_report(i, "query{}.json".format(i))

    def test_subcollection_complex_data_types(self):
        """
        Results from queries on subcollection for complex data types: i.e. data that needs
        to be stored in postgres as multiple fields
        """
        self.setup_user(**self.testuser)
        for i in [34, 35, 36, 37, 39, 41, 42, 43]:
            if i in [35, 36, 43]:
                # TODO: Number with category fields are not sorting correctly.
                continue
            if i in [39]:
                # TODO: regex not supported yet
                continue
            self.check_report(i, "query{}.json".format(i))

    def test_prefiltered_concepts(self):
        """
        Results from queries on prefiltered fields - includes both complex and simple data types
        """
        self.setup_user(**self.testuser)
        for i in [44, 46, 47, 48, 49, 50, 51, 52]:
            self.check_report(i, "query{}.json".format(i))

    def test_event_filters(self):
        """
        event dates on criteria sets
        """
        self.setup_user(**self.testuser)
        for i in range(55, 66):
            self.check_report(i, "query{}.json".format(i))
        # TODO: Chain of 3 relative events not working
        for i in [99]:
            self.check_report(i, "query{}.json".format(i))

    def test_event_filters_self_referential(self):
        """
        relative event dates on criteria sets that reference same collection
        """
        self.setup_user(**self.testuser)
        for i in range(66, 69):
            self.check_report(i, "query{}.json".format(i))

    def test_subcollection_count_filters(self):
        """
        event dates on criteria sets
        """
        self.setup_user(**self.testuser)
        for i in range(69, 75):
            if i in [74]:
                # TODO: I don't believe this one is possible with our SQL approach. I do get the
                #  desired patient count (6), but with the encounter class stacked in the report,
                #  it's only going to return records for the 4 subjects who have that type
                #  of encounter. Might want to review this with Michael.
                continue
            self.check_report(i, "query{}.json".format(i))

    def test_simple_data_type_aggregation(self):
        """
        event dates on criteria sets
        """
        self.setup_user(**self.testuser)
        for i in range(84, 88):
            self.check_report(i, "query{}.json".format(i))
        for i in range(90, 91):
            self.check_report(i, "query{}.json".format(i))

    def test_complex_data_type_aggregation(self):
        """
        event dates on criteria sets
        """
        self.setup_user(**self.testuser)
        for i in range(88, 90):
            if i == 88:
                # TODO: some complex data types aren't sorting within cell correctly when
                #  aggregating to list_distinct or list_all
                continue
            if i == 89:
                # TODO: I don't plan to support TextCustomSort concepts going forward, should
                #   eventually remove all code and tests related to it.
                continue
            self.check_report(i, "query{}.json".format(i))

    def test_date_pairs_with_aggregation(self):
        self.setup_user(**self.testuser)
        for i in range(91, 92):
            self.check_report(i, "query{}.json".format(i))
        for i in range(93, 99):
            self.check_report(i, "query{}.json".format(i))
        # TODO: relative date chains of 3+ with mixed stacking/aggregation still don't work. I
        #   think to do this we would have to figure out the date chain of 3+ and then build the
        #   query using a date chain instead of a date pair. Should be possible, but this will
        #   be a lot of work.
        # for i in range(100, 102):
        #     self.check_report(i, "query{}.json".format(i))

    def test_aggregate_filter_by_criteria_set(self):
        self.setup_user(**self.testuser)
        for i in range(102, 103):
            self.check_report(i, "query{}.json".format(i))

    def test_collection_relationships(self):
        self.setup_user(**self.testuser)
        for i in range(103, 109):
            if i == 108:
                # TODO: agg aliquot should notice that we're stacking by encounter and it has
                #  an indirect subcollection relationship to encounters through samples.
                continue
            self.check_report(i, "query{}.json".format(i))
        for i in range(111, 112):
            self.check_report(i, "query{}.json".format(i))

    def test_export_has_perf(self):
        self.setup_user(**self.testuser)
        url = reverse("chiron:api:report_tools-list") + "{}/export_json/".format(2)

        chiron_settings.CHIRON_GET_QUERY_PERFORMANCE = True
        response = self.client.get(url)
        # response = self.make_request("GET", url, user=self.testuser)
        self.assertEqual(response.status_code, 200)
        print(response.data)
        self.assertTrue("perf" in response.data, "did not find perf in response")
        self.assertTrue("cache_mode" in response.data, "did not find cache_mode in response")

        chiron_settings.CHIRON_GET_QUERY_PERFORMANCE = False
        response = self.client.get(url)
        # response = self.make_request("GET", url, user=self.testuser)
        self.assertTrue(
            "perf" not in response.data, "found perf in response when its not supposed to"
        )
        self.assertTrue(
            "cache_mode" not in response.data,
            "found cache_mode in response when its not supposed to",
        )

    def test_preview_has_perf(self):
        self.setup_user(**self.testuser)
        url = reverse("chiron:api:report_tools-list") + "{}/preview/".format(2)

        chiron_settings.CHIRON_GET_QUERY_PERFORMANCE = True
        response = self.client.get(url)
        # response = self.make_request("GET", url, user=self.testuser)
        self.assertEqual(response.status_code, 200)
        self.assertTrue("perf" in response.data, "did not find perf in response")
        self.assertTrue("cache_mode" in response.data, "did not find cache_mode in response")

        chiron_settings.CHIRON_GET_QUERY_PERFORMANCE = False
        response = self.client.get(url)
        # response = self.make_request("GET", url, user=self.testuser)
        self.assertTrue(
            "perf" not in response.data, "found perf in response when its not supposed to"
        )
        self.assertTrue(
            "cache_mode" not in response.data,
            "found cache_mode in response when its not supposed to",
        )

    def test_sum_aggregation(self):
        self.setup_user(**self.testuser)
        self.check_report(136, "query136.json")

# from django.test import TestCase
from rest_framework.reverse import reverse

from .utils.base_testcase import BaseTestCase


class AccessLevelTest(BaseTestCase):
    """
    Tests related to a user's access level on a dataset (ChironUser.access_level), which restricts
    access to PHI and non-aggregated data.
    """

    @classmethod
    def setUpTestData(cls):
        cls.initialize_chiron()
        cls.load_dataset(cls.DS1_STORED)
        cls.testuser1 = {
            "dataset_name": cls.DS1_STORED,
            "username": "testuser1",
            "access_level": "deid",
            "permission_groups": ["married"],
        }
        cls.testuser2 = {
            "dataset_name": cls.DS1_STORED,
            "username": "testuser2",
            "access_level": "agg",
            "permission_groups": ["all"],
        }

    def test_phi_viewing_restrictions_on_reports(self):
        """
        User "demouser" should not have access to view PHI concepts.
        """
        # Two PHI concepts should be hidden. One PHI date concept should be converted to year.
        self.setup_user(**self.testuser1)
        self.check_report(75, "query{}.json".format(75))

    def test_phi_querying_restrictions_on_reports(self):
        """
        User "demouser" should not have access to reports when a PHI concept is used in the cohort
        def.
        """
        self.setup_user(**self.testuser1)
        # root PHI concept in cohort def
        url = reverse("chiron:api:report_tools-list") + "{}/export_json/".format(77)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # subcol PHI concept in cohort def
        url = reverse("chiron:api:report_tools-list") + "{}/export_json/".format(78)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # date PHI concept in cohort def is too specific (lower than 1 year level)
        url = reverse("chiron:api:report_tools-list") + "{}/export_json/".format(79)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # date PHI concept in cohort def is not too specific, this one is accessible
        url = reverse("chiron:api:report_tools-list") + "{}/export_json/".format(80)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_phi_restrictions_on_stats(self):
        """
        User "demouser" should not have access to statistics for PHI concepts.
        """
        oChironuser = self.setup_user(**self.testuser1)
        # should only see data for limited subjects
        self.check_stats(oChironuser.dataset, "permission_test_race", "stat1.json")
        # should only see data for limited subjects
        self.check_stats(oChironuser.dataset, "test_permission_subcol", "stat2.json")
        # shouldn't be able to query PHI concept
        url = reverse("chiron:api:concepts-list") + "{}/cohort_def_callback/".format(
            "patient_id_phi"
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        # shouldn't be able to query PHI concept
        url = reverse("chiron:api:concepts-list") + "{}/cohort_def_callback/".format(
            "phi_subcol_concept"
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        # should be able to query date with alt processor giving year only
        self.check_stats(oChironuser.dataset, "subcol_phi_date", "stat3.json")

    def test_exclude_from_aggregated_setting(self):
        """
        Concepts have an exclude_from_aggregated_setting that should make them inaccessible
        to users with access_level = "agg"
        """
        self.setup_user(**self.testuser1)
        url = reverse("chiron:api:concepts-list") + "{}/cohort_def_callback/".format(
            "test_exclude_from_aggregated"
        )
        # test user should be able to see stats for concept
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.setup_user(**self.testuser2)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    # We no longer allow users with AGG access level to see statistics at all.
    # This decision may change in the future, so keeping this code for now but commenting it out.
    def test_agg_access_level_on_stats(self):
        """Stats for user with aggregated access level should either be modified to hide small
        numbers or blocked altogether. Currently, chiron is set up to do the latter.
        """
        oChironuser = self.setup_user(**self.testuser2)
        # AGG users are no longer allowed to se stats. This may change in the future, so I'm
        # commenting out these tests instead of deleting them.
        # # category
        # self.check_stats(oChironuser.dataset, "subcol_simple_enc_class", "stat30.json")
        # self.check_stats(oChironuser.dataset, "gender", "stat35.json")
        # # number
        # self.check_stats(oChironuser.dataset, "subcol_simple_base_cost", "stat31.json")
        # # boolean
        # self.check_stats(oChironuser.dataset, "subcol_simple_paid", "stat32.json")
        # # number with categories
        # self.check_stats(oChironuser.dataset, "payer_coverage_float_with_text", "stat33.json")
        # # date deid
        # self.check_stats(oChironuser.dataset, "subcol_simple_encounter_date", "stat34.json")

        # We want to test that AGG users always get a 403 when trying to access stats
        # category
        self.check_stats_are_blocked(oChironuser.dataset, "subcol_simple_enc_class")
        self.check_stats_are_blocked(oChironuser.dataset, "gender")
        # number
        self.check_stats_are_blocked(oChironuser.dataset, "subcol_simple_base_cost")
        # boolean
        self.check_stats_are_blocked(oChironuser.dataset, "subcol_simple_paid")
        # number with categories
        self.check_stats_are_blocked(oChironuser.dataset, "payer_coverage_float_with_text")
        # date deid
        self.check_stats_are_blocked(oChironuser.dataset, "subcol_simple_encounter_date")

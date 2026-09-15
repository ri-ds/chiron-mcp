# from django.test import TestCase
from rest_framework.reverse import reverse

from .utils.base_testcase import BaseTestCase


class DatasetPermissionTests(BaseTestCase):
    """
    Tests data access restrictions related to datasets
    """

    @classmethod
    def setUpTestData(cls):
        cls.initialize_chiron()
        cls.load_dataset(cls.DS1_STORED)
        cls.load_dataset(cls.DS2_STORED)
        cls.testuser_a = {
            "dataset_name": cls.DS1_STORED,
            "username": "testuser",
            "permission_groups": ["married"],
        }
        cls.testuser_b = {
            "dataset_name": cls.DS1_STORED,
            "username": "testuser",
            "permission_groups": ["study group C"],
        }

    def test_permission_group_subject_filtering(self):
        """
        User should only be able to see subjects allowed by their permission groups
        """
        # create the user needed
        self.setup_user(**self.testuser_a)
        # test user
        self.check_report(81, "query{}.json".format(81))

    def test_permission_group_subject_filtering_m2m_subcol(self):
        """
        For a subcollection associated with multiple subjects, users should be able to see
        records where at least 1 allowed subject is associated, otherwise the record should
        be hidden.
        """
        # create the user needed
        self.setup_user(**self.testuser_b)
        # test user
        self.check_report(112, "query{}.json".format(112))

    def test_permission_group_report_query_by_blocked_concept(self):
        """
        User should not be able to view a report that uses a blocked concept in the cohort def
        """
        self.setup_user(**self.testuser_a)
        url = reverse("chiron:api:report_tools-list") + "{}/export_json/".format(76)
        response = self.client.get(url, {})
        self.assertEqual(response.status_code, 403)

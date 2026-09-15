# from django.test import TestCase
from rest_framework.reverse import reverse

from .utils.base_testcase import BaseTestCase
from chiron.models import Dataset


class DatasetPermissionTests(BaseTestCase):
    """
    Tests data access restrictions related to datasets
    """

    @classmethod
    def setUpTestData(cls):
        cls.initialize_chiron()
        cls.load_dataset(cls.DS1_STORED)
        cls.load_dataset(cls.DS2_STORED)
        cls.testuser = {
            "dataset_name": cls.DS1_STORED,
            "username": "testuser",
            "access_level": "phi",
            "permission_groups": ["all"],
            "addl_dataset_access": [
                {
                    "dataset_name": cls.DS2_STORED,
                    "access_level": "phi",
                }
            ],
        }
        cls.testuser1 = {
            "dataset_name": None,
            "username": "testuser1",
        }

    def _get_concept_stats(self, concept_id):
        url = reverse("chiron:api:concepts-list") + f"{concept_id}/cohort_def_callback/"
        data = {}
        response = self.client.get(url, data)
        return response

    def test_no_dataset_selected(self):
        """
        User shouldn't be able to query data without selecting a dataset
        """
        oChironUser = self.setup_user(start_session=False, **self.testuser)
        # oUser = get_user_model().objects.get(username="admin")
        self.log_in(oChironUser.user)
        # attempt to get data without defining a session dataset should return BadRequest error
        response = self._get_concept_stats("patient_id")
        self.assertEqual(response.status_code, 400)
        # attempt to get data without defining a session dataset should return BadRequest error
        response = self._get_concept_stats("Id_zuetgefscg")
        self.assertEqual(response.status_code, 400)

    def test_chironuser_autocreate_on(self):
        """
        If autocreate is turned on for a dataset, user should be able to set as the active
        dataset and run queries using default permissions.
        """
        self.setup_user(**self.testuser1)
        oDataset = Dataset.objects.get(unique_id=self.DS1_STORED)
        # attempt to set the dataset should succeed and redirect to the workspace
        response = self.start_dataset_session(oDataset, follow=True)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(response.status_code, 200)
        # attempt to query concept in active dataset should work
        response = self._get_concept_stats("patient_id")
        self.assertEqual(response.status_code, 200)
        # attempt to query concept in active dataset but inaccessible with default permission group
        response = self._get_concept_stats("test_permission_blocked")
        self.assertEqual(response.status_code, 404)

    def test_chironuser_autocreate_off(self):
        """
        If autocreate is not turned on for a dataset, user should not be able to set as the active
        dataset and shouldn't be able to query the dataset.
        """
        self.setup_user(**self.testuser1)
        oDataset = Dataset.objects.get(unique_id=self.DS2_STORED)
        # attempt to set the dataset should fail, second redirect pointing back to /select_dataset
        response = self.start_dataset_session(oDataset, follow=True)
        self.assertEqual(response.redirect_chain[1][1], 302)
        self.assertEqual(response.redirect_chain[1][0], "/select_dataset")
        # attempt to query without an active dataset should give forbidden error
        response = self._get_concept_stats("Id_zuetgefscg")
        self.assertEqual(response.status_code, 403)

    def test_wrong_active_dataset_with_permission_groups(self):
        """
        User should not be able to query the inactive dataset. This one tests context where
        permission groups are being used in the active dataset.
        """
        self.setup_user(**self.testuser)
        oDataset = Dataset.objects.get(unique_id=self.DS1_STORED)
        self.start_dataset_session(oDataset)
        # attempt to query concept in active dataset should work
        response = self._get_concept_stats("patient_id")
        self.assertEqual(response.status_code, 200)
        # attempt to query concept outside of active dataset should fail
        response = self._get_concept_stats("Id_zuetgefscg")
        self.assertEqual(response.status_code, 404)

    def test_wrong_active_dataset_without_permission_groups(self):
        """
        User should not be able to query the inactive dataset. This one tests context where
        permission groups are not being used in the active dataset.
        """
        self.setup_user(**self.testuser)
        oDataset = Dataset.objects.get(unique_id=self.DS2_STORED)
        self.start_dataset_session(oDataset)
        # attempt to query concept in active dataset should work
        response = self._get_concept_stats("Id_ujftofurne")
        self.assertEqual(response.status_code, 200)
        # attempt to query concept outside of active dataset should fail
        response = self._get_concept_stats("patient_id")
        self.assertEqual(response.status_code, 404)

    # TODO: Need to decide how it should be handled when someone tries to get report data from
    #   a different dataset than the active dataset (or when there's no active dataset)
    # def test_report_dataset_switching(self):
    #     """
    #     Directly accessing a report should automatically change the active dataset, as long
    #     as the user is allowed to see the report.
    #     """
    #     oUser = get_user_model().objects.get(username="admin")
    #     self.log_in(oUser)
    #     oDataset = Dataset.objects.get(unique_id="dataset2")
    #     self.start_dataset_session(oDataset)
    #     # should be able to get a report from dataset "default" even though it's not active
    #     url = reverse("chiron:api:report_tools-list") + "{}/export_json/".format(4)
    #     response = self.client.get(url, {})
    #     self.assertEqual(response.status_code, 200)
    #     output = response.json()
    #     datafile = "query4.json"
    #     f = open(os.path.join(self.expected_data_dir, datafile), encoding="utf-8")
    #     expected = json.load(f)
    #     self.assertEqual(output["records"], expected)

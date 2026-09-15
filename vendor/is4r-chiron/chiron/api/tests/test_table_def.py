import json

from django.core.management import call_command
from rest_framework import status
from rest_framework.reverse import reverse

from chiron.api.tests.utils.base_endpoint_test import BaseApiTestCase


class TableDefAPITest(BaseApiTestCase):
    """
    Defines the Table Def tests
    """

    def setUp(self):
        """
        Setup any data needed in the tests
        """
        call_command("chiron_restore_dd")

        self.testuser = self.create_user()

        self.deid_user = self.create_user(userdata={"username": "deid_user"})
        self.agg_user = self.create_user(userdata={"username": "agg_user"}, access_level="agg")
        self.phi_user = self.create_user(userdata={"username": "phi_user"}, access_level="phi")

    #         self.text_concept = Concept.objects.filter(
    #             cohort_def_processor__name="CohortDefText", published=True
    #         ).first()

    def test_table_def_list_invalid_requests(self):
        """
        Tests that the table def list returns appropriate HTTP errors on invalid requests
        """
        url = reverse("chiron:api:table_def-list")
        # a request without an authorized user
        response = self.make_request("GET", url, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # a request for active snapshot but no snapshots exist
        response = self.make_request("GET", url, {}, user=self.testuser)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_access_level(self):
        url = reverse("chiron:api:table_def-list")
        # users with aggregated access can't view reports so they don't need these endpoints
        response = self.make_request("GET", url, user=self.agg_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # other users should have access but it's still an invalid request
        response = self.make_request("GET", url, user=self.deid_user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.make_request("GET", url, user=self.phi_user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_table_def_retrieve_invalid_requests(self):
        """
        Tests that the table def retrieve returns appropriate HTTP errors on invalid requests
        """
        url = reverse("chiron:api:table_def-detail", args=[1000])
        # a request without an authorized user
        response = self.make_request("GET", url, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # a request without valid table def ID
        response = self.make_request("GET", url, {}, user=self.testuser)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_table_def_create_invalid_requests(self):
        """
        Tests that the table def create returns appropriate HTTP errors on invalid requests
        """
        url = reverse("chiron:api:table_def-list")
        # a request without an authorized user
        response = self.make_request("POST", url, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # a request without transformation definition
        response = self.make_request("POST", url, {}, user=self.testuser)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_table_def_create(self):
        """
        Test applying a transformation to a table def and retrieving new table def
        """
        url = reverse("chiron:api:table_def-list")

        response = self.make_request(
            "POST",
            url,
            {"transformation": {"type": "add_entry", "concept_id": "gender"}},
            user=self.testuser,
        )

        # check that response is OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = json.loads(response.content)
        self.assertTrue(response_data.get("transformation_successful"))
        self.assertTrue(response_data.get("table_def"))
        self.assertTrue(response_data.get("extended_table_def"))
        self.assertIsNone(response_data.get("previous_snapshot_id"))
        self.assertIsNone(response_data.get("next_snapshot_id"))
        self.assertTrue(response_data.get("snapshot_id"))

        # check that created table_def can be retrieved using the snapshot id
        snapshot_id = response_data.get("snapshot_id")
        url = reverse("chiron:api:table_def-detail", args=[snapshot_id])
        response = self.make_request("GET", url, {}, user=self.testuser)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response_data.get("table_def"))
        self.assertTrue(response_data.get("extended_table_def"))
        self.assertIsNone(response_data.get("previous_snapshot_id"))
        self.assertIsNone(response_data.get("next_snapshot_id"))
        self.assertTrue(response_data.get("snapshot_id"))

        # check that created table_def can be retrieved as active snapshot
        url = reverse("chiron:api:table_def-list")
        response = self.make_request("GET", url, {}, user=self.testuser)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response_data.get("table_def"))
        self.assertTrue(response_data.get("extended_table_def"))
        self.assertIsNone(response_data.get("previous_snapshot_id"))
        self.assertIsNone(response_data.get("next_snapshot_id"))
        self.assertTrue(response_data.get("snapshot_id"))

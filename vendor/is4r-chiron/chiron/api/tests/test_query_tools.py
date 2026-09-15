from django.core.management import call_command
from rest_framework import status
from rest_framework.reverse import reverse

from chiron.api.tests.utils.base_endpoint_test import BaseApiTestCase

from chiron.query_engine import get_db_writer
from chiron.models import Dataset


class QueryToolsTests(BaseApiTestCase):
    def setUp(self):
        call_command("chiron_restore_dd")

        # initialize the database
        oDataset = Dataset.objects.get(pk=1)
        writer = get_db_writer(oDataset, use_staging=False)
        writer.initialize_database(None)

        self.deid_user = self.create_user(userdata={"username": "deid_user"})
        self.agg_user = self.create_user(userdata={"username": "agg_user"}, access_level="agg")
        self.phi_user = self.create_user(userdata={"username": "phi_user"}, access_level="phi")

    def test_unauth_request(self):
        url = reverse("chiron:api:query_tools-list")
        response = self.make_request("GET", url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_access_level(self):
        # users with aggregated access can't see endpoints with patient-level data
        url = reverse("chiron:api:query_tools-list") + "export_csv/"
        response = self.make_request("GET", url, user=self.agg_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        url = reverse("chiron:api:query_tools-list") + "preview_metadata/"
        response = self.make_request("GET", url, user=self.agg_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        url = reverse("chiron:api:query_tools-list") + "preview/"
        response = self.make_request("GET", url, user=self.agg_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # users with aggregated access can see list and count endpoints (no patient-level data)
        url = reverse("chiron:api:query_tools-list")
        response = self.make_request("GET", url, user=self.agg_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        url = reverse("chiron:api:query_tools-list") + "count/"
        response = self.make_request("GET", url, user=self.agg_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # users with deid or phi access can see all endpoints in query_tools
        url = reverse("chiron:api:query_tools-list") + "export_csv/"
        response = self.make_request("GET", url, user=self.deid_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        url = reverse("chiron:api:query_tools-list") + "preview_metadata/"
        response = self.make_request("GET", url, user=self.deid_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        url = reverse("chiron:api:query_tools-list") + "preview/"
        response = self.make_request("GET", url, user=self.deid_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

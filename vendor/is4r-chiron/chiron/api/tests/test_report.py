from rest_framework import status
from rest_framework.reverse import reverse

from chiron.api.tests.utils.base_endpoint_test import BaseApiTestCase


class ReportTests(BaseApiTestCase):
    def setUp(self):
        self.deid_user = self.create_user(userdata={"username": "deid_user"})
        self.agg_user = self.create_user(userdata={"username": "agg_user"}, access_level="agg")
        self.phi_user = self.create_user(userdata={"username": "phi_user"}, access_level="phi")

    def test_unauth_request(self):
        url = reverse("chiron:api:reports-list")
        response = self.make_request("GET", url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_access_level(self):
        url = reverse("chiron:api:reports-list")
        # users with aggregated access can't view reports so they don't need these endpoints
        response = self.make_request("GET", url, user=self.agg_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # other users should have access
        response = self.make_request("GET", url, user=self.deid_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.make_request("GET", url, user=self.phi_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

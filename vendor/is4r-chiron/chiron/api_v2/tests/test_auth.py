from importlib.metadata import PackageNotFoundError, version as get_version

from rest_framework import status
from rest_framework.reverse import reverse

from chiron.api.tests.utils.base_endpoint_test import BaseApiTestCase


class AuthTests(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        try:
            self.expected_version = "v" + get_version("chiron")
        except PackageNotFoundError:
            self.expected_version = "v0.0.0"

    def test_unauth_request(self):
        url = reverse("chiron:api_v2:auth-list")
        response = self.make_request("GET", url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("user"), None)
        self.assertEqual(response.data.get("chironVersion"), self.expected_version)

    def test_auth_request(self):
        url = reverse("chiron:api_v2:auth-list")
        testuser = self.create_user()
        response = self.make_request("GET", url, user=testuser)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("user").get("id"), testuser.id)
        self.assertEqual(response.data.get("chironVersion"), self.expected_version)

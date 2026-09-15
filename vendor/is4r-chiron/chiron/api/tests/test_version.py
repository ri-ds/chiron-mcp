from rest_framework import status
from rest_framework.reverse import reverse

from chiron.api.tests.utils.base_endpoint_test import BaseApiTestCase


class versionTests(BaseApiTestCase):
    def test_request(self):
        url = reverse("chiron:api:version-list")
        response = self.make_request("GET", url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue("chiron" in response.data.keys())

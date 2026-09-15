from rest_framework import status
from rest_framework.reverse import reverse

from chiron.api.tests.utils.base_endpoint_test import BaseApiTestCase


class ConceptTests(BaseApiTestCase):
    def test_unauth_list(self):
        url = reverse("chiron:api_v2:concepts-list", ["default"])
        response = self.make_request("GET", url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauth_retrieve(self):
        url = reverse("chiron:api_v2:concepts-detail", ["default", "test_concept"])
        response = self.make_request("GET", url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.make_request("PUT", url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.make_request("DELETE", url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_auth_missing(self):
        url = reverse("chiron:api_v2:concepts-detail", ["default", "test_concept"])
        test_user = self.create_user()
        response = self.make_request("GET", url, user=test_user)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_auth_list(self):
        url = reverse("chiron:api_v2:concepts-list", ["default"])
        test_user = self.create_user()
        test_concept = self.create_concept()
        response = self.make_request("GET", url, user=test_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("count"), 1)
        concept = response.data.get("results")[0]
        self.assertEqual(concept.get("permanent_id"), test_concept.permanent_id)

    def test_unauth_update(self):
        url = reverse("chiron:api_v2:concepts-list", ["default"])
        response = self.make_request("GET", url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauth_delete(self):
        url = reverse("chiron:api_v2:concepts-list", ["default"])
        response = self.make_request("GET", url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

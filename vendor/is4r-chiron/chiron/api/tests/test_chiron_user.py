from rest_framework import status
from rest_framework.reverse import reverse

from chiron.api.tests.utils.base_endpoint_test import BaseApiTestCase


class MeTests(BaseApiTestCase):
    def test_unauth_request(self):
        url = reverse("chiron:api:me-list")
        response = self.make_request("GET", url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_auth_request(self):
        url = reverse("chiron:api:me-list")

        user = self.create_user({"last_name": "User", "first_name": "Test"})
        response = self.make_request("GET", url, user=user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("id"), user.id)
        self.assertEqual(response.data.get("username"), user.username)
        self.assertEqual(response.data.get("name"), f"{user.first_name} {user.last_name}")
        self.assertEqual(response.data.get("email"), user.email)
        chironuser = user.chironuser_set.get(dataset_id=1)
        self.assertEqual(response.data.get("access_level"), chironuser.access_level)
        self.assertEqual(response.data.get("chiron_user_id"), chironuser.id)

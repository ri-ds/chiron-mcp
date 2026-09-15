"""Regression test for the /api/me/ multi-dataset HTTP 500 fix.

A Django user has one ChironUser *per dataset*. The `me` endpoint used
`ChironUser.objects.get(user=user)`, which raised `MultipleObjectsReturned`
(HTTP 500) for any user with access to more than one dataset. The fix resolves
the ChironUser for the request's active dataset (with a deterministic fallback).
"""

from rest_framework import status
from rest_framework.reverse import reverse

from chiron.api.tests.utils.base_endpoint_test import BaseApiTestCase
from chiron.models import ChironUser, Dataset


class MeMultiDatasetRegressionTests(BaseApiTestCase):
    def test_me_does_not_500_with_multiple_chironusers(self):
        user = self.create_user(userdata={"username": "phi_user"}, access_level="phi")
        # Give the same Django user a ChironUser in a second dataset.
        second = Dataset.objects.create(
            unique_id="second-ds", display_name="Second DS", database_name="second_ds"
        )
        ChironUser.objects.create(user=user, dataset=second)
        self.assertEqual(ChironUser.objects.filter(user=user).count(), 2)

        # make_request sets the session's active dataset to id=1.
        url = reverse("chiron:api:me-list")
        response = self.make_request("GET", url, user=user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], user.id)
        self.assertEqual(response.data["access_level"], "phi")
        self.assertIsNotNone(response.data["chiron_user_id"])

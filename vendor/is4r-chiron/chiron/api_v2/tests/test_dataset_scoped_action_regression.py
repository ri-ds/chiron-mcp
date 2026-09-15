"""Regression tests for the v2 dataset-scoped-action HTTP 500 fixes.

The v2 router mounts these viewsets under `…/<dataset_string>/…`, so DRF passes
`dataset_string` as a view kwarg. Actions whose signature did not accept it
raised `TypeError: … got an unexpected keyword argument 'dataset_string'`,
surfacing as HTTP 500. These tests pin the endpoints to 200 and check that the
returned action URLs are in the v2 (dataset-scoped) namespace.
"""

from rest_framework import status
from rest_framework.reverse import reverse

from chiron.api.tests.utils.base_endpoint_test import BaseApiTestCase


class DatasetScopedActionRegressionTests(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(userdata={"username": "phi_user"}, access_level="phi")

    def test_query_tools_list_v2_does_not_500(self):
        url = reverse("chiron:api_v2:query_tools-list", ["default"])
        response = self.make_request("GET", url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # URLs must be rewritten into the dataset-scoped v2 namespace
        self.assertIn("/api/v2/", response.data["count"])
        self.assertTrue(response.data["count"].endswith("/query_tools/count"))
        for key in ("count", "preview", "preview_metadata", "export_csv"):
            self.assertIn(key, response.data)

    def test_report_tools_retrieve_v2_does_not_500(self):
        url = reverse("chiron:api_v2:report_tools-detail", ["default", 1])
        response = self.make_request("GET", url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("/api/v2/", response.data["preview"])
        self.assertIn("/1/preview", response.data["preview"])

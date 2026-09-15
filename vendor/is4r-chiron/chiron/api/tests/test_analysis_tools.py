from rest_framework import status
from rest_framework.reverse import reverse

from chiron.api.tests.utils.base_endpoint_test import BaseApiTestCase


class AnalysisToolsTests(BaseApiTestCase):
    def setUp(self):
        self.testuser = self.create_user()

    def test_unauth_request(self):
        url = reverse("chiron:api:analysis_tools-list")
        response = self.make_request("GET", url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_show_hide_analysis_view(self):
        # these endpoints should be turned off if CHIRON_SHOW_ANALYSIS_VIEW=False
        url = reverse("chiron:api:analysis_tools-list")
        response = self.make_request("GET", url, {}, user=self.testuser)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # TODO: set CHIRON_SHOW_ANALYSIS_VIEW=False and it should fail
        #   I don't know how to do this without a separate test_settings file.

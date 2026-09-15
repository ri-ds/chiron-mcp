from rest_framework import status
from rest_framework.reverse import reverse

from chiron.api.tests.utils.base_endpoint_test import BaseApiTestCase


class CollectionAPITest(BaseApiTestCase):
    """
    Collection API endpoint Test Case
    """

    def test_unauth_request(self):
        """Test Unauthorized Request
        Test for unauthorized use of the Collection API endpoint.
        """
        # Get URL for API call
        url = reverse("chiron:api:collections-list")
        # Check that response is 403 forbidden
        response = self.make_request("GET", url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_auth_request(self):
        """Test Authorized Request
        Test authorized usage of the Collection API endpoint.
        """
        # Get URL for API call
        url = reverse("chiron:api:collections-list")
        response = self.make_request("GET", url, user=self.create_user())
        self.assertEqual(response.status_code, status.HTTP_200_OK)

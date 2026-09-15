from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.reverse import reverse
from chiron.models import (
    ChironUser,
    Collection,
    Processor,
    Source,
    Category,
    Concept,
)

from chiron.api.tests.utils.base_endpoint_test import BaseApiTestCase


class ConceptAPITest(BaseApiTestCase):
    """
    Concept API endpoint Test Case
    """

    def setUp(self):
        """Setup
        Setup needed for Concept API tests.
        This is where database objects, users, and other such prerequisites are added.
        """
        # Create test Django User and corresponding Chiron User for testing
        self.testuser = get_user_model().objects.create_user(
            "testuser", "test@example.com", "testpass", first_name="Test", last_name="User"
        )
        self.testchironuser = ChironUser.objects.create(user=self.testuser, dataset_id=1)
        # Create test items
        self.testcollection = Collection.objects.create(
            permanent_id="testcollection-1", name="Test Collection", dataset_id=1
        )
        self.testprocessor = Processor.objects.create(
            name="testprocessor-1", is_source_processor=True
        )
        self.testsource = Source.objects.create(
            name="testsource-1",
            collection=self.testcollection,
            processor=self.testprocessor,
        )
        self.testcategory = Category.objects.create(
            unique_id="testcategory-1", name="Test Category", dataset_id=1
        )
        self.testconcept1 = Concept.objects.create(
            permanent_id="testconcept-1",
            name="Test Concept 1",
            collection=self.testcollection,
            category=self.testcategory,
            source=self.testsource,
        )

    def test_unauth_request(self):
        """Test Unauthorized Request
        Test for unauthorized use of the Concept API endpoint.
        """
        # Get URL for API call
        url = reverse("chiron:api:concepts-list")
        # Check that response is 403 forbidden
        response = self.make_request("GET", url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_auth_request(self):
        """Test Authorized Request
        Test authorized usage of the Concept API endpoint.
        """
        # Get URL for API call
        url = reverse("chiron:api:concepts-list")
        response = self.make_request("GET", url, user=self.testuser)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

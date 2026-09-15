from rest_framework import status
from rest_framework.reverse import reverse
from chiron.models import Collection, Processor, Source, Category, Concept

from chiron.api.tests.utils.base_endpoint_test import BaseApiTestCase


class ConceptCategoryAPITest(BaseApiTestCase):
    """
    Category API endpoint Test Case.
    """

    def setUp(self):
        """Setup
        Setup needed for Category API tests.
        This is where database objects, users, and other such prerequisites are added.
        """
        self.testuser = self.create_user()
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
        testsubcat1 = Category.objects.create(
            unique_id="testcategory-2", name="Test Sub Category", dataset_id=1
        )
        testsubcat2 = Category.objects.create(
            unique_id="testcategory-3", name="Another Sub Category", dataset_id=1
        )
        self.testcategory.child_set.add(
            testsubcat1,
            testsubcat2,
        )
        self.testconcept1 = Concept.objects.create(
            permanent_id="testconcept-1",
            name="Test Concept 1",
            collection=self.testcollection,
            category=self.testcategory,
            source=self.testsource,
            include_in_cohort_def=True,
            include_in_table_def=True,
        )
        self.testconcept2 = Concept.objects.create(
            permanent_id="testconcept-2",
            name="Test Concept 2",
            collection=self.testcollection,
            category=self.testcategory,
            source=self.testsource,
            include_in_cohort_def=False,
            include_in_table_def=True,
        )

        Concept.objects.create(
            permanent_id="testsubconcept-1",
            name="Test Sub Concept 1",
            collection=self.testcollection,
            category=testsubcat1,
            source=self.testsource,
            include_in_cohort_def=True,
            include_in_table_def=True,
        )
        Concept.objects.create(
            permanent_id="testsubconcept-2",
            name="Test Sub Concept 2",
            collection=self.testcollection,
            category=testsubcat2,
            source=self.testsource,
            include_in_cohort_def=True,
            include_in_table_def=True,
        )

    def test_unauth_request(self):
        """Test Unauthorized Request
        Test for unauthorized use of the Category API endpoint.
        """
        # Get URL for API call
        url = reverse("chiron:api:concept_categories-list")
        # Check that response is 403 forbidden

        response = self.make_request("GET", url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list(self):
        """Tests the listing of all categories.
        This should only display those categories that have no parent category
        """
        # Get URL for API call
        url = reverse("chiron:api:concept_categories-list")

        # the collection categories should not display subcategories or concepts
        response = self.make_request("GET", url, user=self.testuser)
        self.assertEqual("top", response.data.get("category_id"))
        self.assertNotEqual(None, response.data.get("categories"))
        self.assertNotEqual(None, response.data.get("concepts"))

    def test_retreive(self):
        """Test the retreiveing of a single category"""
        url = reverse("chiron:api:concept_categories-detail", [self.testcategory.id])
        response = self.make_request("GET", url, user=self.testuser)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.testcategory.id, response.data.get("category_id"))
        self.assertNotEqual(None, response.data.get("categories"))
        self.assertNotEqual(None, response.data.get("concepts"))

    def test_update(self):
        """Test the updating of a category
        This is not allowed and should not return any data
        """
        url = reverse("chiron:api:concept_categories-detail", [self.testcategory.id])
        response = self.make_request("PUT", url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.make_request("PATCH", url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.make_request("PUT", url, user=self.testuser)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        response = self.make_request("PATCH", url, user=self.testuser)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete(self):
        """Test the deleting of a category
        This is not allowed and should not return any data
        """
        url = reverse("chiron:api:concept_categories-detail", [self.testcategory.id])
        response = self.make_request("DELETE", url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(user=self.testuser)
        response = self.make_request("DELETE", url, user=self.testuser)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_concept_type(self):
        """Test the retreiveing of a single category for table and cohort based concepts"""
        url = reverse("chiron:api:concept_categories-detail", [self.testcategory.id])
        response = self.make_request("GET", f"{url}?concept_type=table", user=self.testuser)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.testcategory.id, response.data.get("category_id"))

        total_subcategories = len(self.testcategory.child_set.all())
        total_concepts = len(self.testcategory.concepts.all())
        total_table_concepts = len(self.testcategory.concepts.filter(include_in_table_def=True))
        total_cohort_concepts = len(self.testcategory.concepts.filter(include_in_cohort_def=True))

        self.assertEqual(total_subcategories, len(response.data.get("categories")))
        self.assertEqual(total_table_concepts, len(response.data.get("concepts")))

        response = self.make_request("GET", f"{url}?concept_type=cohort", user=self.testuser)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.testcategory.id, response.data.get("category_id"))
        self.assertEqual(total_subcategories, len(response.data.get("categories")))
        self.assertEqual(
            total_cohort_concepts,
            len(response.data.get("concepts")),
        )

        response = self.make_request("GET", f"{url}?concept_type=invalid", user=self.testuser)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.testcategory.id, response.data.get("category_id"))
        self.assertEqual(total_subcategories, len(response.data.get("categories")))
        self.assertEqual(total_concepts, len(response.data.get("concepts")))

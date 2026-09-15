from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from chiron.models import (
    ChironUser,
    PermissionGroup,
    Concept,
    Source,
    Collection,
    Processor,
    ConceptHandler,
    Category,
    Dataset,
    Project,
)
from rest_framework.reverse import reverse

from chiron.processors.registration import ProcessorRegistry


class BaseApiTestCase(APITestCase):
    """
    Base API test case
    """

    def setUp(self):
        ProcessorRegistry.update_registry()
        return super().setUp()

    def create_user(self, userdata={}, access_level=None):
        """Creates a user based on data that is passed in
        Arguments:
            userdata {Dict} -- Dict representing thee user fields
            access_level {Str} -- set chiron_user.access_level, if None then uses default value
        Returns:
            User -- The created user
        """
        username = userdata.get("username", "testuser")
        email = userdata.get("email", "test.user@example.com")
        password = userdata.get("password", "secret1234")

        # create the User and ChironUser
        user, _ = get_user_model().objects.get_or_create(
            username=username, email=email, defaults=userdata
        )
        user.set_password(password)
        user.save()
        chironuser, created = ChironUser.objects.get_or_create(user=user, dataset_id=1)

        # if the permission groups are set, append the "all" group so that no data will be hidden
        permission_group = PermissionGroup.objects.filter(name="all", dataset_id=1).first()

        if permission_group:
            chironuser.permission_groups.add(permission_group)
        if access_level:
            chironuser.access_level = access_level
            chironuser.save()
        return user

    def generate_and_authenticate_user(self, user=None):
        """
        Helper function to use passed in user object or generate one
        for authentication purposes
        Keyword Arguments:
            user {User} -- A User object to use for authentication or generate
                one if None (default: {None})
        Returns:
            User -- The user that is used for authentication
        """
        if not user:
            # create a user object if nothing is passed
            user = self.create_user(
                {
                    "username": "testuser",
                    "email": "test.user@example.com",
                    "password": "secret123",
                    "first_name": "Test",
                    "last_name": "User",
                }
            )

        # authentiate as user
        self.client.force_login(user=user)

        # return user if needed
        return user

    def make_standard_request(self, method, url, data=None, user=None):
        """like make_request but doesn't change format to json; use for non-API requests"""
        if user:
            self.generate_and_authenticate_user(user)
        if method == "POST":
            return self.client.post(url, data)
        if method == "GET":
            return self.client.get(url, data)
        if method == "PUT":
            return self.client.put(url, data)
        if method == "PATCH":
            return self.client.patch(url, data)
        if method == "DELETE":
            return self.client.delete(url, data)

    def set_session_dataset(self, user, dataset_id):
        url = reverse("chiron:select_dataset")
        data = {"dataset_id": dataset_id}
        self.make_standard_request("POST", url, data=data, user=user)

    def make_request(self, method, url, data=None, user=None):
        if user:
            self.generate_and_authenticate_user(user)
            self.set_session_dataset(user, 1)
        if method == "POST":
            return self.client.post(url, data, format="json")
        if method == "GET":
            return self.client.get(url, data, format="json")
        if method == "PUT":
            return self.client.put(url, data, format="json")
        if method == "PATCH":
            return self.client.patch(url, data, format="json")
        if method == "DELETE":
            return self.client.delete(url, data, format="json")

    def create_concept(self, concept_type="TextHandler"):
        num_concepts = Concept.objects.count()
        new_num = num_concepts + 1
        collection, _ = Collection.objects.get_or_create(
            dataset_id=1, permanent_id="test_collection", name="Test Collection"
        )
        processor, _ = Processor.objects.get_or_create(
            name="test_source_processor",
            is_source_processor=True,
            python_path="chiron.path.here",
        )

        source, _ = Source.objects.get_or_create(
            name="test_source",
            collection=collection,
            processor=processor,
        )
        category, _ = Category.objects.get_or_create(
            dataset_id=1,
            unique_id="test_category",
            name="Test Category",
        )
        concept_handler, _ = ConceptHandler.objects.get_or_create(
            name=concept_type,
            python_path=f"chiron.processors.concept_handlers.standard_concept_handlers.{concept_type}",  # noqa
        )
        return Concept.objects.create(
            permanent_id=f"test_concept_{new_num}",
            name=f"Test Concept #{new_num}",
            name_plural=None,
            description=f"Description for concept #{new_num}",
            source=source,
            concept_handler=concept_handler,
            collection=collection,
            category=category,
            order=1,
            published=True,
            include_in_cohort_def=True,
            include_in_table_def=True,
            include_in_analysis_def=True,
        )

    def create_project(self, name="Test Project", dataset="default"):
        dataset, _ = Dataset.objects.get_or_create(display_name=dataset)
        project, _ = Project.objects.get_or_create(name=name, dataset=dataset)

        return project

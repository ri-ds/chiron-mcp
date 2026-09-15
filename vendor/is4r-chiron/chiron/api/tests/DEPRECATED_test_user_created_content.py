import json
import os
from rest_framework import status
from rest_framework.reverse import reverse

from django.core import management
from django.conf import settings

from chiron.models import UserCreatedContent, ChironUser

from chiron.api.tests.utils.base_endpoint_test import BaseApiTestCase


class UserCreatedContentTest(BaseApiTestCase):
    """
    UserCreatedContent API endpoint Test Case
    """

    def setUp(self):
        management.call_command(
            "loaddata", os.path.join(settings.BASE_DIR, "test_project/chiron_config/fixtures.json")
        )
        self.testuser = self.create_user()
        cohort_def = [
            {
                "entry_type": "criteria_set",
                "entry_id": "AfW8u0dISDQV",
                "collection_id": "subject",
                "list": [
                    {
                        "entry_id": "WDxkY1OTtqio",
                        "concept_id": "gender",
                        "categories": ["F"],
                    }
                ],
            }
        ]

        self.created_content = UserCreatedContent.objects.create(
            dataset_id=1,
            name="MY UCF",
            description="Description for MY UCF",
            type="cohort",
            creator=self.testuser.chironuser_set.all()[0],
            public=False,
            definition=json.dumps(
                {"cohort_def": cohort_def, "table_def": ["blinded_id_gublthtygs"], "sort_def": []}
            ),
        )

        # create some public contents
        for i in range(5):
            UserCreatedContent.objects.create(
                dataset_id=1,
                name=f"Public UCF #{i}",
                description=f"Description for UCF #{i}",
                type="cohort",
                creator=self.testuser.chironuser_set.all()[0],
                public=True,
                definition=json.dumps(
                    {
                        "cohort_def": cohort_def,
                        "table_def": ["blinded_id_gublthtygs"],
                        "sort_def": [],
                    }
                ),
            )

        # create some owner projects
        for i in range(5):
            user = self.create_user(
                {
                    "username": f"testuser{i}",
                    "email": f"testuser{i}@example.com",
                    "first_name": f"Test{i}",
                    "last_name": f"User{i}",
                    "password": "secret1234",
                }
            )
            UserCreatedContent.objects.create(
                dataset_id=1,
                name=f"My UCF #{i}",
                description="Description for an owned UCF",
                type="cohort",
                public=False,
                creator=user.chironuser_set.all()[0],
                definition=json.dumps(
                    {
                        "cohort_def": cohort_def,
                        "table_def": ["blinded_id_gublthtygs"],
                        "sort_def": [],
                    }
                ),
            )

        # create some shared with testuser
        all_users = [u for u in ChironUser.objects.all()]
        i = 0
        for u in all_users:
            content = UserCreatedContent.objects.create(
                dataset_id=1,
                name=f"Shared UCF #{i}",
                description="Description for a shared UCF",
                type="cohort",
                public=False,
                creator=u,
                definition=json.dumps(
                    {
                        "cohort_def": cohort_def,
                        "table_def": ["blinded_id_gublthtygs"],
                        "sort_def": [],
                    }
                ),
            )

            # add the other users
            share_with = [au for au in all_users if au.user.username != u.user.username]
            content.share_with.add(*share_with)
            self.shared_content = content
            i += 1

    def test_unauth_request(self):
        """Test Unauthorized Request
        Test for unauthorized use of the Collection API endpoint.
        """
        # Get URL for API call
        url = reverse("chiron:api:user_created_content-list")
        # Check that response is 403 forbidden
        response = self.make_request("GET", url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_access_level(self):
        deid_user = self.create_user(userdata={"username": "deid_user"})
        agg_user = self.create_user(userdata={"username": "agg_user"}, access_level="agg")
        phi_user = self.create_user(userdata={"username": "phi_user"}, access_level="phi")
        url = reverse("chiron:api:user_created_content-list")
        # users with aggregated access can't view reports so they don't need these endpoints
        response = self.make_request("GET", url, user=agg_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # other users should have access
        response = self.make_request("GET", url, user=deid_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.make_request("GET", url, user=phi_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_auth_request(self):
        """Test Authorized Request
        Test authorized usage of the Collection API endpoint.
        """
        # Get URL for API call
        url = reverse("chiron:api:user_created_content-list")
        response = self.make_request("GET", url, user=self.create_user())
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_content_query_params(self):
        # Get URL for API call
        url = reverse("chiron:api:user_created_content-list")

        # default query
        response = self.make_request("GET", url, {"type": "cohort"}, user=self.create_user())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = json.loads(response.content)
        self.assertEqual(response_data.get("count"), 12)

        # only ones that I own
        response = self.make_request(
            "GET", url, {"type": "cohort", "state": "mine"}, user=self.create_user()
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = json.loads(response.content)
        self.assertEqual(response_data.get("count"), 7)

        # only public ones
        response = self.make_request(
            "GET", url, {"type": "cohort", "state": "public_only"}, user=self.create_user()
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = json.loads(response.content)
        self.assertEqual(response_data.get("count"), 5)

        # only shared ones
        response = self.make_request(
            "GET", url, {"type": "cohort", "state": "shared_only"}, user=self.create_user()
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = json.loads(response.content)
        self.assertEqual(response_data.get("count"), 5)

    def test_update_user_created_content(self):
        # Get URL for API call
        content = UserCreatedContent.objects.filter(creator__user=self.testuser).first()
        url = reverse("chiron:api:user_created_content-detail", args=[content.id])

        response = self.make_request(
            "PATCH", url, {"type": "cohort", "name": f"{content.name} Updated"}, user=self.testuser
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = json.loads(response.content)
        self.assertEqual(response_data.get("name"), f"{content.name} Updated")

        response = self.make_request(
            "PATCH",
            url,
            {"type": "cohort", "definition": content.definition},
            user=self.testuser,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = json.loads(response.content)
        self.assertNotEqual(response_data.get("definition"), "[]")

    def test_get_cohort_def_as_shared_user(self):
        # Get URL for API call
        url = reverse("chiron:api:user_created_content-detail", args=[-1])
        response = self.make_request(
            "GET",
            url,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.make_request(
            "GET",
            url,
            user=self.testuser,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # test for content I created
        url = reverse("chiron:api:user_created_content-detail", args=[self.created_content.id])
        response = self.make_request(
            "GET",
            url,
            user=self.testuser,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # test for content that has been shared with me
        url = reverse("chiron:api:user_created_content-detail", args=[self.shared_content.id])
        response = self.make_request(
            "GET",
            url,
            user=self.testuser,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

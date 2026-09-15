from unittest.mock import patch

from django.core import mail
from django.test import override_settings
from rest_framework import status
from rest_framework.reverse import reverse

from chiron.api.tests.utils.base_endpoint_test import BaseApiTestCase


class ReportTests(BaseApiTestCase):
    def setUp(self):
        self.deid_user = self.create_user(
            userdata={"username": "deid_user", "email": "deid_user@example.com"}
        )
        self.deid_user_two = self.create_user(
            userdata={"username": "deid_user_two", "email": "deid_user_two@example.com"}
        )
        self.agg_user = self.create_user(
            userdata={"username": "agg_user", "email": "agg_user@example.com"},
            access_level="agg",
        )
        self.phi_user = self.create_user(userdata={"username": "phi_user"}, access_level="phi")
        self.project = self.create_project()

    def test_basic_request_with_expected_structure(self):
        url = reverse("chiron:api_v2:reports-create-form", ["default"])
        response = self.make_request("GET", url, user=self.phi_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test top-level keys
        assert "status" in response.data
        assert "title" in response.data
        assert "errors" in response.data
        assert "data" in response.data

        # Test nested keys under 'data'
        assert "fForm" in response.data["data"]
        assert "oReports" in response.data["data"]

        # Test keys under 'fForm'
        assert "shared_options" in response.data["data"]["fForm"]
        assert "project_selection" in response.data["data"]["fForm"]

        # Test structure of list items (if they exist)
        if response.data["data"]["fForm"]["shared_options"]:
            shared_option = response.data["data"]["fForm"]["shared_options"][0]
            assert "username" in shared_option
            assert "user_id" in shared_option
            assert "checked" in shared_option

        if response.data["data"]["fForm"]["project_selection"]:
            project_item = response.data["data"]["fForm"]["project_selection"][0]
            assert "label" in project_item
            assert "value" in project_item

        if response.data["data"]["oReports"]:
            report_item = response.data["data"]["oReports"][0]
            assert "label" in report_item
            assert "value" in report_item

    def test_create_basic_report(self):
        url = reverse("chiron:api_v2:reports-create-form", ["default"])
        data = {
            "overwrite_query_def_with_active": "no",
            "project": self.project.id,
            "project_other": "",
            "description": "",
            "share_with": [],
            "dataset": 1,
            "name": "Custom Report",
        }

        response = self.make_request("POST", url, data=data, user=self.phi_user)
        self.assertEqual(response.status_code, 200)

        assert "complete" == response.data["status"]
        assert "chiron.manager.reportCreated" == response.data["onSuccess"]
        assert [""] == response.data["errors"]

        url = reverse("chiron:api_v2:reports-list", ["default"])

        response = self.make_request("GET", url, user=self.phi_user)
        self.assertEqual(response.status_code, 200)

        assert "results" in response.data
        assert "count" in response.data
        assert "next" in response.data
        assert "previous" in response.data
        assert response.data["count"] > 0

        custom_report = next(
            (item for item in response.data["results"] if item["name"] == "Custom Report"),
            None,
        )

        assert custom_report["name"] == "Custom Report"
        assert not custom_report["public"]

    def test_create_report_being_public(self):
        url = reverse("chiron:api_v2:reports-create-form", ["default"])
        data = {
            "overwrite_query_def_with_active": "no",
            "project": self.project.id,
            "project_other": "",
            "description": "",
            "share_with": [],
            "dataset": 1,
            "name": "Public Report",
            "public": "on",
        }

        response = self.make_request("POST", url, data=data, user=self.phi_user)
        self.assertEqual(response.status_code, 200)

        url = reverse("chiron:api_v2:reports-list", ["default"])
        response = self.make_request("GET", url, user=self.phi_user)
        self.assertEqual(response.status_code, 200)

        custom_report = next(
            (item for item in response.data["results"] if item["name"] == "Public Report"),
            None,
        )

        assert custom_report["public"]
        assert custom_report["name"] == "Public Report"

    @patch("chiron.chiron_settings.CHIRON_EMAIL_NOTIFICATIONS", False)
    def test_create_report_with_shared_users(self):
        url = reverse("chiron:api_v2:reports-create-form", ["default"])
        data = {
            "overwrite_query_def_with_active": "no",
            "project": self.project.id,
            "project_other": "",
            "description": "",
            "share_with": [self.deid_user.id],
            "dataset": 1,
            "name": "Shared User Report",
        }

        response = self.make_request("POST", url, data=data, user=self.phi_user)
        self.assertEqual(response.status_code, 200)

        url = reverse("chiron:api_v2:reports-list", ["default"])
        response = self.make_request("GET", url, user=self.phi_user)
        self.assertEqual(response.status_code, 200)

        custom_report = next(
            (item for item in response.data["results"] if item["name"] == "Shared User Report"),
            None,
        )

        assert custom_report["name"] == "Shared User Report"
        assert custom_report["public"] is False

        assert len(custom_report["share_with"]) == 1, (
            f"Expected 1 shared user, found {len(custom_report['share_with'])}"
        )

        # Validate share_with structure
        share_with = custom_report["share_with"]
        assert isinstance(share_with, list), "share_with should be a list"
        assert len(share_with) == 1, f"Expected exactly 1 shared user, found {len(share_with)}"

        # Validate the shared user
        shared_user_entry = share_with[0]
        assert "user" in shared_user_entry, "Missing 'user' key in share_with entry"

        user_info = shared_user_entry["user"]
        assert user_info["username"] == "deid_user", (
            f"Expected username 'deid_user', got '{user_info['username']}'"
        )

        # Check email was not sent
        assert len(mail.outbox) == 0, "Email should not have been sent"

    @patch("chiron.chiron_settings.CHIRON_EMAIL_NOTIFICATIONS", True)
    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_create_report_with_email_notification_sent(self):
        url = reverse("chiron:api_v2:reports-create-form", ["default"])
        data = {
            "overwrite_query_def_with_active": "no",
            "project": self.project.id,
            "project_other": "",
            "description": "",
            "share_with": [self.deid_user.id],
            "dataset": 1,
            "name": "Email Notification Report",
        }

        response = self.make_request("POST", url, data=data, user=self.phi_user)
        self.assertEqual(response.status_code, 200)

        url = reverse("chiron:api_v2:reports-list", ["default"])
        response = self.make_request("GET", url, user=self.phi_user)
        self.assertEqual(response.status_code, 200)

        custom_report = next(
            (
                item
                for item in response.data["results"]
                if item["name"] == "Email Notification Report"
            ),
            None,
        )

        assert custom_report["name"] == "Email Notification Report"

        # Check email was sent
        assert len(mail.outbox) == 1
        email = mail.outbox[0]

        assert "A saved item has been shared with you" in email.subject
        assert email.to == ["deid_user@example.com"]

    @patch("chiron.chiron_settings.CHIRON_EMAIL_NOTIFICATIONS", False)
    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_edit_report_sharing_with_users_no_notification(self):
        # Create the form first
        url = reverse("chiron:api_v2:reports-create-form", ["default"])
        data = {
            "overwrite_query_def_with_active": "no",
            "project": self.project.id,
            "project_other": "",
            "description": "",
            "share_with": [],
            "dataset": 1,
            "name": "Private Empty Report",
        }
        self.make_request("POST", url, data=data, user=self.phi_user)
        assert len(mail.outbox) == 0, "Email should not have been sent"

        # Check the creation and make sure there are no shared users
        url = reverse("chiron:api_v2:reports-list", ["default"])
        response = self.make_request("GET", url, user=self.phi_user)
        report = response.data["results"][0]
        assert len(report["share_with"]) == 0, (
            f"Expected exactly 0 shared users, found {len(report['share_with'])}"
        )

        # Now edit the report to add a shared user
        url = reverse(
            "chiron:api_v2:reports-edit-form",
            [
                "default",
                report["id"],
            ],
        )
        data = {
            "overwrite_query_def_with_active": "no",
            "project": self.project.id,
            "project_other": "",
            "description": "",
            "share_with": [self.deid_user.id],
            "dataset": 1,
            "name": "Edit Report Sharing With Users",
        }

        response = self.make_request("POST", url, data=data, user=self.phi_user)
        self.assertEqual(response.status_code, 200)
        assert len(mail.outbox) == 0, "Email should have not been sent"

        # Get the report again to check the shared users
        url = reverse("chiron:api_v2:reports-list", ["default"])
        response = self.make_request("GET", url, user=self.phi_user)
        self.assertEqual(response.status_code, 200)

        report = response.data["results"][0]
        assert len(report["share_with"]) == 1, (
            f"Expected exactly 1 shared user, found {len(report['share_with'])}"
        )
        assert len(mail.outbox) == 0, "Email should not have been sent"

    @patch("chiron.chiron_settings.CHIRON_EMAIL_NOTIFICATIONS", True)
    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_edit_report_sharing_with_users_with_notification(self):
        # Create the form first
        url = reverse("chiron:api_v2:reports-create-form", ["default"])
        data = {
            "overwrite_query_def_with_active": "no",
            "project": self.project.id,
            "project_other": "",
            "description": "",
            "share_with": [],
            "dataset": 1,
            "name": "Private Empty Report",
        }
        self.make_request("POST", url, data=data, user=self.phi_user)
        assert len(mail.outbox) == 0, "Email should not have been sent"

        # Check the creation and make sure there are no shared users
        url = reverse("chiron:api_v2:reports-list", ["default"])
        response = self.make_request("GET", url, user=self.phi_user)
        report = response.data["results"][0]
        assert len(report["share_with"]) == 0, (
            f"Expected exactly 0 shared users, found {len(report['share_with'])}"
        )

        # Now edit the report to add a shared user
        url = reverse(
            "chiron:api_v2:reports-edit-form",
            [
                "default",
                report["id"],
            ],
        )
        data = {
            "overwrite_query_def_with_active": "no",
            "project": self.project.id,
            "project_other": "",
            "description": "",
            "share_with": [self.deid_user.id],
            "dataset": 1,
            "name": "Edit Report Sharing With Users",
        }

        response = self.make_request("POST", url, data=data, user=self.phi_user)
        self.assertEqual(response.status_code, 200)
        assert len(mail.outbox) == 1, "Email should have been sent"

        # Get the report again to check the shared users
        url = reverse("chiron:api_v2:reports-list", ["default"])
        response = self.make_request("GET", url, user=self.phi_user)
        self.assertEqual(response.status_code, 200)

        report = response.data["results"][0]
        assert len(report["share_with"]) == 1, (
            f"Expected exactly 1 shared user, found {len(report['share_with'])}"
        )

    @patch("chiron.chiron_settings.CHIRON_EMAIL_NOTIFICATIONS", False)
    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_share_form_sharing_with_additional_user(self):
        # Create the form first
        url = reverse("chiron:api_v2:reports-create-form", ["default"])
        data = {
            "overwrite_query_def_with_active": "no",
            "project": self.project.id,
            "project_other": "",
            "description": "",
            "share_with": [self.deid_user.id],
            "dataset": 1,
            "name": "Private Empty Report To Share",
        }
        self.make_request("POST", url, data=data, user=self.phi_user)
        assert len(mail.outbox) == 0, "Email should not have been sent"

        # Check the creation and make sure there are no shared users
        url = reverse("chiron:api_v2:reports-list", ["default"])
        response = self.make_request("GET", url, user=self.phi_user)
        report = response.data["results"][0]
        assert len(report["share_with"]) == 1, (
            f"Expected exactly 1 shared users, found {len(report['share_with'])}"
        )

        response = self.make_request("POST", url, data=data, user=self.phi_user)
        assert len(mail.outbox) == 0, "Email should not have been sent"

        url = reverse(
            "chiron:api_v2:reports-share-form",
            [
                "default",
                report["id"],
            ],
        )

        data = {"share_with": [self.deid_user.id, self.deid_user_two.id]}
        response = self.make_request("POST", url, data=data, user=self.phi_user)
        self.assertEqual(response.status_code, 200)
        assert len(mail.outbox) == 0, "Email should not have been sent"
        assert "complete" == response.data["status"]
        assert [""] == response.data["errors"]

        url = reverse("chiron:api_v2:reports-list", ["default"])
        response = self.make_request("GET", url, user=self.phi_user)

        report = response.data["results"][0]
        assert len(report["share_with"]) == 2, (
            f"Expected exactly 2 shared users, found {len(report['share_with'])}"
        )

        # todo: can't add agg user to share

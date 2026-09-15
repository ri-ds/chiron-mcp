import json
from datetime import datetime

from django.urls import reverse
from django.shortcuts import get_object_or_404
from django.utils.text import slugify

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import exceptions
from rest_framework import renderers

from chiron.api.permissions import SubjectLevelAccess
from chiron.api.utils.authentication import CsrfExemptSessionAuthentication
from chiron.api.utils import export as export_utils
from chiron import models, chiron_settings
from chiron.api.renderers import ReportToolsTemplateRenderer
from chiron.api.permissions import DatasetSelector
from chiron.models import ChironUser
from chiron.api.utils.report import send_email_report_notification


class ReportToolsViewSet(viewsets.ViewSet):
    """API endpoints to run queries against a dataset related to a saved report. Also API endpoints
    to perform special operations on reports such as setting rules for sharing.
    """

    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated, DatasetSelector, SubjectLevelAccess]
    renderer_classes = [
        renderers.JSONRenderer,  # matches application/json request
        ReportToolsTemplateRenderer,  # matches text/plain request
        renderers.BrowsableAPIRenderer,  # matches text/html request
    ]

    def list(self, request):
        url_for_viewset = request.build_absolute_uri(reverse("chiron:api:report_tools-list"))
        response = {
            "share": url_for_viewset + "[pk]/share",
            "load_as_active": url_for_viewset + "[pk]/load_as_active",
            "preview": url_for_viewset + "[pk]/preview",
            "export_csv": url_for_viewset + "[pk]/export_csv",
            "export_json": url_for_viewset + "[pk]/export_json",
        }
        return Response(response)

    def retrieve(self, request, pk):
        url_for_viewset = request.build_absolute_uri(reverse("chiron:api:report_tools-list"))
        response = {
            "share": url_for_viewset + str(pk) + "/share",
            "load_as_active": url_for_viewset + str(pk) + "/load_as_active",
            "preview": url_for_viewset + str(pk) + "/preview",
            "export_csv": url_for_viewset + str(pk) + "/export_csv",
        }
        return Response(response)

    @action(detail=True, methods=["POST"], name="Share Report")
    def share(self, request, pk, *args, **kwargs):
        """
        Pass an array of all ChironUser IDs to share with. Any preexisting sharing will be erased.

        Note that reports set to "public" are automatically shared with everyone regardless of
        what's set with sharing.
        """
        # make sure the user has access to the content
        user_content = get_object_or_404(models.UserCreatedContent, pk=pk)
        new_share_ids = json.loads(request.body.decode("utf-8"))

        if user_content.creator != request.chironuser:
            # only the creator can update
            raise exceptions.PermissionDenied(detail="You do not have access to make changes")

        if chiron_settings.CHIRON_EMAIL_NOTIFICATIONS:
            previous_share_ids = list(
                models.ContentSharing.objects.filter(content__id=pk).values_list(
                    "chironuser__id", flat=True
                )
            )
        else:
            previous_share_ids = None

        # remove all sharing
        models.ContentSharing.objects.filter(content__id=pk).delete()

        # add back the new ones
        for chiron_user_id in new_share_ids:
            models.ContentSharing.objects.create(
                content=user_content, chironuser=models.ChironUser.objects.get(id=chiron_user_id)
            )

        # Send email notifications if they are enabled
        if chiron_settings.CHIRON_EMAIL_NOTIFICATIONS:
            # Iterate through Chiron User IDs and send email notifications where applicable
            for chiron_user_id in new_share_ids:
                if chiron_user_id not in previous_share_ids:
                    chiron_user = ChironUser.objects.get(pk=chiron_user_id)
                    send_email_report_notification(
                        chiron_user,
                        user_content,
                        request.build_absolute_uri(reverse("chiron:reports")),
                    )

        return Response({})

    @action(detail=True, methods=["POST"], name="Load Report as Active")
    def load_as_active(self, request, pk, *args, **kwargs):
        """
        Will set this report's cohort def and table def as the active snapshot in the
        CohortDefSnapshot and TableDefSnapshot models. It will also erase the snapshot history
        in both tables.
        """
        oContent = get_object_or_404(models.UserCreatedContent, pk=pk)
        oChironUser = request.chironuser
        cohort_def = oContent.get_def_value("cohort_def")
        table_def = oContent.get_def_value("table_def")

        models.CohortDefSnapshot.clear_history(oChironUser)
        oCohortDef = models.CohortDefSnapshot(chironuser=oChironUser)
        oCohortDef.set_cohort_def(cohort_def)
        oCohortDef.save()

        models.TableDefSnapshot.clear_history(oChironUser)
        oTableDef = models.TableDefSnapshot(chironuser=oChironUser)
        oTableDef.set_table_def(table_def)
        oTableDef.save()

        response = {}
        return Response(response)

    @action(detail=True, methods=["GET"], name="Export Report as CSV")
    def export_csv(self, request, pk, *args, **kwargs):
        """
        Get a CSV for the specified report ID with a full dataset.

        :response: the CSV file
        :rtype: text/csv HTTP response
        """
        oContent = get_object_or_404(models.UserCreatedContent, pk=pk)
        cohort_def = oContent.get_def_value("cohort_def")
        table_def = oContent.get_def_value("table_def")
        file_name = slugify(oContent.name) + datetime.now().strftime("_%Y-%m-%d")
        # Generate CSV
        response = export_utils.generate_cohort_csv(
            cohort_def, table_def, request.chironuser, file_name
        )
        # Return response
        return response

    @action(detail=True, methods=["GET"], name="Export Report as JSON")
    def export_json(self, request, pk, *args, **kwargs):
        """
        Get a JSON response for the specified report ID with a full dataset.

        :param output_type: how output data should be formatted, options are "html", "json", "csv"
        :type output_type: str, default="json"
        :response: the JSON file
        :rtype: HTTP response
        """
        params = request.GET if request.method == "GET" else request.data
        oContent = get_object_or_404(models.UserCreatedContent, pk=pk)
        cohort_def = oContent.get_def_value("cohort_def")
        table_def = oContent.get_def_value("table_def")
        output_type = params.get("output_type", "json")
        # Generate JSON
        response = export_utils.generate_cohort_json(
            cohort_def, table_def, request.chironuser, output_type
        )
        return Response(response)

    @action(detail=True, methods=["GET"], name="Preview Report Dataset")
    def preview(self, request, pk, *args, **kwargs):
        """
        Get a paginated dataset based on the specified report ID.

        :param sort_field: Ignore default sort order and sort by the field associated with the
          provided table def entry ID
        :param output_type: how output data should be formatted, options are "html", "json", "csv"
        :type output_type: str, default="json"
        :type sort_field: string, optional
        :param records_per_page: How many records per page when paginating
        :type records_per_page: int, default=10
        :param page: The page number to fetch
        :type page: int, default=1

        RESPONSE IF SUCCESS:

        :record_count: (int)
        :subject_count: (int)
        :page_number_current: (int)
        :page_number_max: (int)
        :page_first_index: (int) The index of the first record on this page
        :page_last_index: (int) The index of the last record on this page
        :extended_table_def: (list)
        :data: (2D array of strings) The records returned for this page
        :warnings: (array of strings) Warning messages to display to the user

        RESPONSE IF FAIL:

        :preview_failed: True
        :extended_table_def: (list)
        :warnings: (array of strings) Warning messages to display to the user
        :errors: (array of strings) Error messages that explain why the query failed
        """
        params = request.GET
        oContent = get_object_or_404(models.UserCreatedContent, pk=pk)
        input_cohort_def = oContent.get_def_value("cohort_def")
        input_table_def = oContent.get_def_value("table_def")
        if params.get("sort_field"):
            input_table_def["sort"] = [
                {
                    "entry_id": params["sort_field"],
                    "direction": int(params.get("sort_direction", 1)),
                }
            ]
        response = export_utils.get_paginated_preview(
            input_cohort_def,
            input_table_def,
            request.chironuser,
            params,
        )
        response["report_id"] = oContent.id
        return Response(response)

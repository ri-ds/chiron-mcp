from django.urls import reverse

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import renderers

from chiron.api.permissions import SubjectLevelAccess, DatasetSelector
from chiron.api.utils.authentication import CsrfExemptSessionAuthentication
from chiron.api.utils import export as export_utils
from chiron import query_definition as qdef
from chiron.api.renderers import QueryToolsTemplateRenderer
from chiron.query_engine import get_querytool
from chiron.api_v2.permissions import CanViewWorkspacePermission


class QueryToolsViewSet(viewsets.ViewSet):
    """Run queries against a dataset that are related to a cohort or a results table."""

    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [
        IsAuthenticated,
        DatasetSelector,
        SubjectLevelAccess,
        CanViewWorkspacePermission,
    ]
    renderer_classes = [
        renderers.JSONRenderer,  # matches application/json request
        QueryToolsTemplateRenderer,  # matches text/plain request
        renderers.BrowsableAPIRenderer,  # matches text/html request
    ]

    def list(self, request, *args, **kwargs):
        # NB: *args/**kwargs are required because the v2 router mounts this action
        # under a dataset-scoped route (…/<dataset_string>/query_tools/) and passes
        # `dataset_string` as a view kwarg. Without it, list() raised
        # TypeError: list() got an unexpected keyword argument 'dataset_string' (HTTP 500).
        url_for_viewset = request.build_absolute_uri(reverse("chiron:api:query_tools-list"))
        response = {
            "count": url_for_viewset + "count",
            "preview_metadata": url_for_viewset + "preview_metadata",
            "preview": url_for_viewset + "preview",
            "export_csv": url_for_viewset + "export_csv",
        }
        return Response(response)

    @action(detail=False, methods=["GET", "POST"], name="Count Subjects")
    def count(self, request, *args, **kwargs):
        """
        Get the count of subjects in a cohort.

        The POST method is provided to allow passing of long query parameters. It works exactly the
        same as the GET method.

        :param cohort_def: The cohort def to use. If not provided, the active cohort_def or an
          empty cohort def will be used.
        :type cohort_def: list, optional

        RESPONSE

        :count: (integer) The number of subjects in the cohort
        :cohort_def: The cohort def that was used.
        """
        # Get input Cohort Def
        input_cohort_def = self._get_cohort_def(request)
        data_tool = get_querytool(request.chironuser, input_cohort_def)
        count = data_tool.get_cohort_count()
        # Assemble and return response
        response = {
            "count": str(count),
            "cohort_def": input_cohort_def,
        }
        return Response(response)

    @action(detail=False, methods=["GET", "POST"], name="Preview Dataset")
    def export_csv(self, request, *args, **kwargs):
        """
        Get a CSV with a full dataset.

        The POST method is provided to allow passing of long query parameters. It works exactly the
        same as the GET method.

        :param cohort_def: The cohort def to use. If not provided, the active cohort_def
          will be used if available or an empty cohort def.
        :type cohort_def: list, optional
        :param table_def: The table_def to use. If not provided, the active table_def
          will be used if available or an empty table_def.
        :type table_def: list, optional

        :response: the CSV file
        :rtype: text/csv HTTP response
        """
        cohort_def = self._get_cohort_def(request)
        table_def = self._get_table_def(request)
        # Generate CSV
        response = export_utils.generate_cohort_csv(cohort_def, table_def, request.chironuser)
        # Return response
        return response

    @action(detail=False, methods=["GET", "POST"], name="Preview Dataset")
    def preview_metadata(self, request, *args, **kwargs):
        """
        Returns metadata about a dataset without actually running the query, which enables it
        to run faster than the `preview` method

        The POST method is provided to allow passing of long query parameters. It works exactly the
        same as the GET method.

        :param cohort_def: The cohort def to use. If not provided, the active cohort_def
          will be used if available or an empty cohort def.
        :type cohort_def: list, optional
        :param table_def: The table_def to use. If not provided, the active table_def
          will be used if available or an empty table_def.
        :type table_def: list, optional

        RESPONSE IF SUCCESS:

        :warnings: (array of strings) Warning messages to display to the user
        :extended_table_def: (list)
        :pipeline: (list) DEPRECATED The MongoDB aggregate pipeline for this query

        RESPONSE IF FAIL:

        :warnings: (array of strings) Warning messages to display to the user
        :errors: (array of strings) Error messages that explain why the query failed
        :preview_failed: True
        :extended_table_def: (list)
        """
        # get the query definition
        params = request.GET if request.method == "GET" else request.data

        input_cohort_def = self._get_cohort_def(request)
        input_table_def = self._get_table_def(request)

        response = export_utils.get_paginated_preview_metadata(
            input_cohort_def,
            input_table_def,
            request.chironuser,
            params,
        )
        return Response(
            response,
            template_name="chiron/table_def_display/preview_display.html",
        )

    @action(detail=False, methods=["GET", "POST"], name="Preview Dataset")
    def preview(self, request, *args, **kwargs):
        """
        Get a paginated  dataset.

        The POST method is provided to allow passing of long query parameters. It works exactly the
        same as the GET method.

        :param cohort_def: The cohort def to use. If not provided, the active cohort_def
          will be used if available or an empty cohort def.
        :type cohort_def: list, optional
        :param table_def: The table_def to use. If not provided, the active table_def
          will be used if available or an empty table_def.
        :type table_def: list, optional
        :param output_type: how output data should be formatted, options are "html", "json", "csv"
        :type output_type: str, default="json"
        :param records_per_page: How many records per page when paginating
        :type records_per_page: int, default=10
        :param page: The page number to fetch
        :type page: int, default=1

        RESPONSE IF SUCCESS:

        :warnings: (array of strings) Warning messages to display to the user
        :record_count: (int)
        :subject_count: (int)
        :extended_table_def: (list)
        :paginator: (dict of integers) includes first_index, last_index, current_page,
          previous_page, next_page, last_page, total_records
        :data: (2D array of strings) The records returned for this page;  if a value is also
          associated with a link, a concept return a dict with "link" and "value" instead of a
          string

        RESPONSE IF FAIL:

        :warnings: (array of strings) Warning messages to display to the user
        :errors: (array of strings) Error messages that explain why the query failed
        :preview_failed: True
        :extended_table_def: (list)
        """
        # get the query definition
        params = request.GET if request.method == "GET" else request.data

        input_cohort_def = self._get_cohort_def(request)
        input_table_def = self._get_table_def(request)

        response = export_utils.get_paginated_preview(
            input_cohort_def,
            input_table_def,
            request.chironuser,
            params,
        )
        return Response(
            response,
            template_name=None,
        )

    def _get_cohort_def(self, request):
        """
        Gets the cohort def from the query parameters or uses the active snapshot if none provided
        """
        return qdef.get_active_cohort_def(request)

    def _get_table_def(self, request):
        """
        Gets the table def from the query parameters or uses the active snapshot if none provided
        """
        return qdef.get_active_table_def(request)

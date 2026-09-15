import json

from django.urls import reverse

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import renderers

from chiron.api.permissions import AnalysisViewOn, DatasetSelector
from chiron.api.utils.authentication import CsrfExemptSessionAuthentication
from chiron.api.utils.general import convert_to_obj, string_to_bool
from chiron import query_definition as qdef
from chiron.api.renderers import AnalysisToolsTemplateRenderer
from chiron.query_engine import get_querytool
from chiron.api.utils import export as export_utils
from chiron.api_v2.permissions import CanViewWorkspacePermission


class AnalysisToolsViewSet(viewsets.ViewSet):
    """API endpoints for queries against a dataset that are related to a pivottable."""

    permission_classes = [
        IsAuthenticated,
        DatasetSelector,
        AnalysisViewOn,
        CanViewWorkspacePermission,
    ]
    authentication_classes = [CsrfExemptSessionAuthentication]
    renderer_classes = [
        renderers.JSONRenderer,  # matches application/json request
        AnalysisToolsTemplateRenderer,  # matches text/plain request
        renderers.BrowsableAPIRenderer,  # matches text/html request
    ]

    def list(self, request, *args, **kwargs):
        url_for_viewset = request.build_absolute_uri(reverse("chiron:api:analysis_tools-list"))
        response = {
            "run_analysis": url_for_viewset + "preview_metadata",
            "export_csv": url_for_viewset + "export_csv",
        }
        return Response(response)

    @action(detail=False, methods=["GET", "POST"], name="Run Analysis")
    def run_analysis(self, request, *args, **kwargs):
        """
        Get the analysis dataset.

        The POST method is provided to allow passing of long query parameters. It works exactly the
        same as the GET method.

        :param cohort_def: The cohort def to use. If not provided, the active cohort_def or an
          empty cohort def will be used.
        :type cohort_def: list, optional
        :param analysis_def: The analysis def to use. If not provided, the active analysis_def or
          an empty analysis_def def will be used.
        :type analysis_def: dict, optional

        RESPONSE

        :data: (list) The dataset
        :cohort_def: The cohort def that was used.
        :analysis_def: The analysis def that was used.

        """
        params = request.GET if request.method == "GET" else request.data
        data_view_mode = params.get("data_view_mode", "active")
        if data_view_mode == "all":
            input_cohort_def = []
        else:
            input_cohort_def = self._get_cohort_def(request)
        input_analysis_def = self._get_analysis_def(request)
        if not input_analysis_def.get("rows") and not input_analysis_def.get("cols"):
            dataset = None
            dataset_html = ""
        else:
            cohort = qdef.Cohort(request.chironuser, input_cohort_def)
            analysis = qdef.Analysis(request.chironuser, input_analysis_def)
            querytool = get_querytool(request.chironuser, cohort.cohort_def)
            df = querytool.run_analysis(analysis)
            dataset = json.loads(df.to_json(orient="split"))
            dataset_html = df.to_html(classes=["table", "table-bordered table-sm"])
        response = {
            "dataset": dataset,
            "cohort_def": input_cohort_def,
            "analysis_def": input_analysis_def,
        }

        response["pivot_table_html"] = dataset_html

        return Response(
            response,
            template_name="chiron/analysis_def_display/pivottable.html",
        )

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
        params = request.GET if request.method == "GET" else request.data
        use_active_cohort = string_to_bool(params.get("use_active_cohort", True))
        if use_active_cohort:
            cohort_def = self._get_cohort_def(request)
        else:
            cohort_def = []
        analysis_def = self._get_analysis_def(request)
        # Generate CSV
        response = export_utils.generate_pivottable_csv(
            cohort_def, analysis_def, request.chironuser
        )
        # Return response
        return response

    def _get_cohort_def(self, request):
        """
        Gets the cohort def from the query parameters or uses the active snapshot if none provided
        """
        if request.method == "GET" and "cohort_def" in request.GET:
            return convert_to_obj(request.GET["cohort_def"])
        elif request.method == "POST":
            if "cohort_def" in request.data:
                return request.data["cohort_def"]
        return qdef.get_active_cohort_def(request)

    def _get_analysis_def(self, request):
        """
        Gets the table def from the query parameters or uses the active snapshot if none provided
        """
        if request.method == "GET" and "table_def" in request.GET:
            return convert_to_obj(request.GET["analysis_def"])
        elif request.method == "POST":
            if "analysis_def" in request.data:
                return request.data["analysis_def"]
        return qdef.get_active_analysis_def(request)

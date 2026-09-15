from django.urls import reverse

from rest_framework.response import Response
from chiron.api.permissions import AnalysisViewOn
from chiron.api.viewsets.analysis_tools import AnalysisToolsViewSet
from chiron.api_v2.permissions import DatasetUrlPermission, CanViewWorkspacePermission
from rest_framework.permissions import IsAuthenticated


class AnalysisToolsViewSetV2(AnalysisToolsViewSet):
    """API endpoints for queries against a dataset that are related to a pivottable."""

    permission_classes = [
        IsAuthenticated,
        DatasetUrlPermission,
        AnalysisViewOn,
        CanViewWorkspacePermission,
    ]

    def list(self, request, *args, **kwargs):
        url_for_viewset = request.build_absolute_uri(reverse("chiron:api:analysis_tools-list"))
        url_for_viewset = url_for_viewset.replace("/api/", "/api/v2/" + str(request.dataset) + "/")
        response = {
            "run_analysis": url_for_viewset + "preview_metadata",
            "export_csv": url_for_viewset + "export_csv",
        }
        return Response(response)

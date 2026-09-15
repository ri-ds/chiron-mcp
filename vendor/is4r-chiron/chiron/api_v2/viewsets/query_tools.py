from django.urls import reverse

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from chiron.api.permissions import SubjectLevelAccess
from chiron.api_v2.permissions import DatasetUrlPermission, CanViewWorkspacePermission
from chiron.api.viewsets.query_tools import QueryToolsViewSet


class QueryToolsViewSetV2(QueryToolsViewSet):
    """Run queries against a dataset that are related to a cohort or a results table."""

    permission_classes = [
        IsAuthenticated,
        DatasetUrlPermission,
        SubjectLevelAccess,
        CanViewWorkspacePermission,
    ]

    def list(self, request, *args, **kwargs):
        # Mirror ReportToolsViewSetV2.list: accept the dataset_string kwarg and rewrite
        # the action URLs into the dataset-scoped v2 namespace (the inherited v1 list
        # both crashed on the kwarg and returned v1-namespaced URLs under /api/v2/).
        url_for_viewset = request.build_absolute_uri(reverse("chiron:api:query_tools-list"))
        url_for_viewset = url_for_viewset.replace("/api/", "/api/v2/" + str(request.dataset) + "/")
        response = {
            "count": url_for_viewset + "count",
            "preview_metadata": url_for_viewset + "preview_metadata",
            "preview": url_for_viewset + "preview",
            "export_csv": url_for_viewset + "export_csv",
        }
        return Response(response)

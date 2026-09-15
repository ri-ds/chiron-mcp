from chiron import models
from rest_framework.permissions import IsAuthenticated
from chiron.api.permissions import AnalysisViewOn
from chiron.api.viewsets.analysis_def import AnalysisDefViewSet
from chiron.api_v2.permissions import DatasetUrlPermission, CanViewWorkspacePermission
from django.shortcuts import get_object_or_404
from chiron import query_definition as qdef
from rest_framework.response import Response


class AnalysisDefViewSetV2(AnalysisDefViewSet):
    """API endpoints for defining an analysis def - a data structure that specifies the structure
    of a pivottable.
    """

    permission_classes = [
        IsAuthenticated,
        DatasetUrlPermission,
        AnalysisViewOn,
        CanViewWorkspacePermission,
    ]

    def retrieve(self, request, pk=None, *args, **kwargs):
        """
        Retrieve a specific analysis def from the AnalysisDefSnapshot model.

        RESPONSE:

        :analysis_def: the analysis definition used for the query
        :extended_analysis_def: the analysis definition with additional details for display
        :warnings: (list) user-friendly warnings (analysis def can still be queried)
        :errors: (list) user-friendly errors (analysis def cannot be queried)
        :snapshot_id: (int) ID of analysis def snapshot
        :previous_snapshot_id: (int/None) ID of previous snapshot
        :next_snapshot_id: (int/None) ID of next snapshot
        """
        oSnapshot = get_object_or_404(
            models.AnalysisDefSnapshot.objects.filter(chironuser=request.chironuser), pk=pk
        )
        # data = JSONParser().parse(request)
        set_to_active = self.request.query_params.get("set_to_active", False)
        if not oSnapshot.is_active and set_to_active:
            models.AnalysisDefSnapshot.set_active(request.chironuser, oSnapshot.id)
        analysis_def = oSnapshot.get_analysis_def()
        ad_validated = qdef.clean_analysis_def(
            analysis_def, request.chironuser, include_metadata=True
        )
        response = {
            "analysis_def": ad_validated["analysis_def"],
            "extended_analysis_def": ad_validated["extended_analysis_def"],
            "warnings": ad_validated["warnings"],
            "errors": ad_validated["errors"],
            "snapshot_id": oSnapshot.id,
            "previous_snapshot_id": oSnapshot.get_previous_id(),
            "next_snapshot_id": oSnapshot.get_next_id(),
        }
        return Response(response)

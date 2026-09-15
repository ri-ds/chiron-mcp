import json

from django.shortcuts import get_object_or_404

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from rest_framework import renderers

from chiron import models
from chiron.api.utils.authentication import CsrfExemptSessionAuthentication
from chiron.api.utils import analysis_def as analysis_utils
from chiron.api.permissions import AnalysisViewOn, DatasetSelector
from chiron import query_definition as qdef
from chiron.api.utils.general import convert_to_obj
from chiron.api.renderers import AnalysisDefTemplateRenderer
from chiron.api_v2.permissions import CanViewWorkspacePermission


class AnalysisDefViewSet(viewsets.ViewSet):
    """API endpoints for defining an analysis def - a data structure that specifies the structure
    of a pivottable.
    """

    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [
        IsAuthenticated,
        DatasetSelector,
        AnalysisViewOn,
        CanViewWorkspacePermission,
    ]
    renderer_classes = [
        renderers.JSONRenderer,  # matches application/json request
        AnalysisDefTemplateRenderer,  # matches text/plain request
        renderers.BrowsableAPIRenderer,  # matches text/html request
    ]

    def list(self, request, *args, **kwargs):
        """
        Returns the current active analysis_def saved in the AnalysisDefSnapshot cue.
        Does not return a list as the method name implies.

        RESPONSE:

        :analysis_def: the analysis definition used for the query
        :extended_analysis_def: the analysis definition with additional details for display
        :warnings: (list) user-friendly warnings (analysis def can still be queried)
        :errors: (list) user-friendly errors (analysis def cannot be queried)
        :snapshot_id: (int) ID of analysis def snapshot
        :previous_snapshot_id: (int/None) ID of previous snapshot
        :next_snapshot_id: (int/None) ID of next snapshot
        """
        oSnapshot = models.AnalysisDefSnapshot.get_active_snapshot(request.chironuser)
        if oSnapshot:
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
        else:
            response = {}
        return Response(
            response,
            template_name="chiron/analysis_def_display/analysis_metadata.html",
        )

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
        oSnapshot = get_object_or_404(models.AnalysisDefSnapshot, pk=pk)
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

    def create(self, request, *args, **kwargs):
        """
        Applies a transformation definition to an analysis definition and returns a new analysis
        definition. If no analysis_def is provided, the active analysis def is used.

        :param transformation: the transformation definition
        :type transformation: dict
        :param analysis_def: the analysis def; if not provided, active analysis def will be used
        :type analysis_def: list, optional

        FAIL RESPONSE:

        :transformation_successful: False
        :analysis_def: Since the transformation failed, simply returns your original analysis def
        :transformation_errors: list of error messages regarding the failed transformation

        SUCCESS RESPONSE:

        :transformation_successful: True
        :analysis_def: the new analysis def with the transformation applied
        :extended_analysis_def: the new analysis definition with additional details for display
        :warnings: (list) warnings about new analysis def (analysis def can still be queried)
        :errors: (list) errors about new analysis def (analysis def cannot be queried)
        :snapshot_id: integer ID of analysis def snapshot
        :previous_snapshot_id: integer ID of previous snapshot or None
        :next_snapshot_id: integer ID of next snapshot or None
        """
        data = json.loads(request.body.decode("utf-8"))
        if "transformation" not in data:
            return Response({}, status=status.HTTP_400_BAD_REQUEST)
        input_analysis_def = data.get("analysis_def", qdef.get_active_analysis_def(request))
        current_chironuser = request.chironuser if hasattr(request, "chironuser") else None
        analysis_def = qdef.clean_analysis_def(input_analysis_def, current_chironuser)
        transformation = data.get("transformation")
        transformation_func = analysis_utils.transformation_function_lookup[transformation["type"]]
        response = transformation_func(request.chironuser, analysis_def, transformation)

        # Add extended analysis def to response
        if response["transformation_successful"]:
            ad_validated = qdef.clean_analysis_def(
                response["analysis_def"], current_chironuser, include_metadata=True
            )
            response["extended_analysis_def"] = ad_validated["extended_analysis_def"]
            response["warnings"] = ad_validated["warnings"]
            response["errors"] = ad_validated["errors"]
            oSnapshot = qdef.set_active_analysis_def(request, response["analysis_def"])
            response["snapshot_id"] = oSnapshot.id
            response["previous_snapshot_id"] = oSnapshot.get_previous_id()
            response["next_snapshot_id"] = oSnapshot.get_next_id()

        # Return JSON Reponse
        return Response(response)

    def _get_analysis_def(self, request):
        """
        Gets the analysis def from the query parameters or uses the active snapshot if none
        provided
        """
        if request.method == "GET" and "analysis_def" in request.GET:
            return convert_to_obj(request.GET["analysis_def"])
        elif request.method == "POST":
            if "analysis_def" in request.data:
                return request.data["analysis_def"]
        return qdef.get_active_analysis_def(request)

    @action(detail=False, methods=["get", "post"])
    def associated_concept_ids(self, request, *args, **kwargs):
        """
        Get a list of all concepts that are referenced in the analysis definition. If no analysis
        def is provided, the active analysis def will be used.
        The POST method behaves the same way as the GET method and is provided to accommodate large
        analysis definitions.
        """
        analysis_def = self._get_analysis_def(request)
        response = {}
        response["concept_ids"] = qdef.get_analysis_def_concept_ids(analysis_def)
        return Response(response)

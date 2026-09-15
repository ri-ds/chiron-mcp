import json

from django.shortcuts import get_object_or_404

from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework import status
from rest_framework import renderers

from chiron import models
from chiron.api.utils import cohort_def as cohort_utils
from chiron import query_definition as qdef
from chiron.api.utils.authentication import CsrfExemptSessionAuthentication
from chiron.api.renderers import CohortDefTemplateRenderer
from chiron.api.permissions import DatasetSelector
from chiron.api.permissions import SubjectLevelAccess
from chiron.api_v2.permissions import CanViewWorkspacePermission


class CohortDefViewSet(viewsets.ViewSet):
    """API endpoints for defining a cohort def - a data structure that specifies rules for what
    subjects to include in a cohort.
    """

    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        DatasetSelector,
        SubjectLevelAccess,
        CanViewWorkspacePermission,
    ]
    renderer_classes = [
        renderers.JSONRenderer,  # matches application/json request
        CohortDefTemplateRenderer,  # matches text/plain request
        renderers.BrowsableAPIRenderer,  # matches text/html request
    ]

    # kwargs handles dataset_string parameter (unused here)
    def list(self, request, **kwargs):
        """
        Returns the current active cohort_def saved in the CohortDefSnapshot cue. Does not return
        a list as the method name implies.

        RESPONSE:

        :cohort_def: the cohort definition used for the query
        :extended_cohort_def: the cohort definition with additional details for display
        :warnings: (list) user-friendly warnings (cohort def can still be queried)
        :errors: (list) user-friendly errors (cohort def cannot be queried)
        :snapshot_id: (int) ID of cohort def snapshot
        :previous_snapshot_id: (int/None) ID of previous snapshot
        :next_snapshot_id: (int/None) ID of next snapshot
        """
        oSnapshot = models.CohortDefSnapshot.get_active_snapshot(request.chironuser)
        cohort_def = []
        if oSnapshot:
            cohort_def = oSnapshot.get_cohort_def()

        cohort = qdef.Cohort(request.chironuser, cohort_def)
        response = {
            "cohort_def": cohort.cohort_def,
            "extended_cohort_def": cohort.extended_cohort_def,
            "describe": qdef.describe_cohort_def(cohort.extended_cohort_def),
            "warnings": cohort.warnings,
            "errors": cohort.errors,
            "snapshot_id": oSnapshot.id if oSnapshot else None,
            "previous_snapshot_id": oSnapshot.get_previous_id() if oSnapshot else None,
            "next_snapshot_id": oSnapshot.get_next_id() if oSnapshot else None,
        }
        return Response(
            response,
            template_name="chiron/cohort_def_display/active_cohort_display.html",
        )

    # kwargs handles dataset_string parameter (unused here)
    def retrieve(self, request, pk=None, **kwargs):
        """
        Retrieve a specific cohort def from the CohortDefSnapshot model.

        RESPONSE:

        :cohort_def: the cohort definition used for the query
        :extended_cohort_def: the cohort definition with additional details for display
        :warnings: (list) user-friendly warnings (cohort def can still be queried)
        :errors: (list) user-friendly errors (cohort def cannot be queried)
        :snapshot_id: (int) ID of cohort def snapshot
        :previous_snapshot_id: (int/None) ID of previous snapshot
        :next_snapshot_id: (int/None) ID of next snapshot
        """
        oSnapshot = get_object_or_404(models.CohortDefSnapshot, pk=pk)
        # data = JSONParser().parse(request)
        set_to_active = request.query_params.get("set_to_active", False)
        if not oSnapshot.is_active and set_to_active:
            models.CohortDefSnapshot.set_active(request.chironuser, oSnapshot.id)
        cohort_def = oSnapshot.get_cohort_def()
        cohort = qdef.Cohort(request.chironuser, cohort_def)
        response = {
            "cohort_def": cohort.cohort_def,
            "extended_cohort_def": cohort.extended_cohort_def,
            "describe": qdef.describe_cohort_def(cohort.extended_cohort_def),
            "warnings": cohort.warnings,
            "errors": cohort.errors,
            "snapshot_id": oSnapshot.id,
            "previous_snapshot_id": oSnapshot.get_previous_id(),
            "next_snapshot_id": oSnapshot.get_next_id(),
        }
        return Response(response)

    def create(self, request, *args, **kwargs):
        """
        Applies a transformation definition to a cohort definition and returns a new cohort
        definition. If no cohort_def is provided, the active cohort def is used.

        :param transformation: the transformation definition
        :type transformation: dict
        :param cohort_def: the cohort definition; if not provided, active cohort def will be used
        :type cohort_def: list, optional

        FAIL RESPONSE:

        :transformation_successful: False
        :cohort_def: Since the transformation failed, it simply returns your original cohort def
        :transformation_errors: list of error messages regarding the failed transformation
        :transformation_warnings: list of warning messages regarding the failed transformation

        SUCCESS RESPONSE:

        :transformation_successful: True
        :cohort_def: the new cohort def with the transformation applied
        :extended_cohort_def: the new cohort definition with additional details for display
        :warnings: (list) warnings about new cohort def (cohort def can still be queried)
        :errors: (list) errors about new cohort def (cohort def cannot be queried)
        :snapshot_id: integer ID of cohort def snapshot
        :previous_snapshot_id: integer ID of previous snapshot or None
        :next_snapshot_id: integer ID of next snapshot or None
        """
        data = json.loads(request.body.decode("utf-8"))
        if "transformation" not in data:
            return Response({}, status=status.HTTP_400_BAD_REQUEST)
        if "cohort_def" in data:
            input_cohort_def = data.get("cohort_def")
        else:
            input_cohort_def = qdef.get_active_cohort_def(request)
        current_user = request.chironuser if hasattr(request, "user") else None
        cohort = qdef.Cohort(current_user, input_cohort_def)
        transformation = data.get("transformation")
        transformation_func = cohort_utils.transformation_function_lookup[transformation["type"]]
        response = transformation_func(request.chironuser, cohort.cohort_def, transformation)

        if response["transformation_successful"]:
            cohort = qdef.Cohort(current_user, response["cohort_def"])
            response["extended_cohort_def"] = cohort.extended_cohort_def
            response["warnings"] = cohort.warnings
            response["errors"] = cohort.errors
            oSnapshot = qdef.set_active_cohort_def(request, response["cohort_def"])
            response["describe"] = qdef.describe_cohort_def(cohort.extended_cohort_def)
            response["snapshot_id"] = oSnapshot.id
            response["previous_snapshot_id"] = oSnapshot.get_previous_id()
            response["next_snapshot_id"] = oSnapshot.get_next_id()
        # Return JSON Reponse
        return Response(response)

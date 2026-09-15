import json

from django.shortcuts import get_object_or_404

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action

from chiron.api.permissions import SubjectLevelAccess, DatasetSelector
from chiron import models
from chiron.api.utils.authentication import CsrfExemptSessionAuthentication
from chiron.api.utils import table_def as table_utils
from chiron import query_definition as qdef
from chiron.api.utils.general import convert_to_obj
from chiron.api_v2.permissions import CanViewWorkspacePermission


class TableDefViewSet(viewsets.ViewSet):
    """API endpoints for defining a table def - a data structure that specifies the columns and
    sort order of a report table.
    """

    permission_classes = [
        IsAuthenticated,
        DatasetSelector,
        SubjectLevelAccess,
        CanViewWorkspacePermission,
    ]
    authentication_classes = [CsrfExemptSessionAuthentication]

    def list(self, request, *args, **kwargs):
        """
        Returns the current active table_def saved in the TableDefSnapshot cue.
        Does not return a list as the method name implies.

        RESPONSE:

        :table_def: the table definition used for the query
        :extended_table_def: the table definition with additional details for display
        :warnings: (list) user-friendly warnings (table def can still be queried)
        :errors: (list) user-friendly errors (table def cannot be queried)
        :snapshot_id: (int) ID of table def snapshot
        :previous_snapshot_id: (int/None) ID of previous snapshot
        :next_snapshot_id: (int/None) ID of next snapshot
        """
        oSnapshot = models.TableDefSnapshot.get_active_snapshot(request.chironuser)
        if not oSnapshot:
            return Response("No active snapshot for user", status=status.HTTP_400_BAD_REQUEST)
        table_def = oSnapshot.get_table_def()
        oCohortDefSnapshot = models.CohortDefSnapshot.get_active_snapshot(request.chironuser)
        if not oCohortDefSnapshot:
            cohort_def = []
        else:
            cohort_def = oCohortDefSnapshot.get_cohort_def()
        table = qdef.Table(request.chironuser, cohort_def, table_def)
        response = {
            "table_def": table.table_def,
            "extended_table_def": table.extended_table_def,
            "warnings": table.warnings,
            "errors": table.errors,
            "snapshot_id": oSnapshot.id,
            "previous_snapshot_id": oSnapshot.get_previous_id(),
            "next_snapshot_id": oSnapshot.get_next_id(),
        }
        return Response(response)

    def retrieve(self, request, pk=None, *args, **kwargs):
        """
        Retrieve a specific table def from the TableDefSnapshot model.

        RESPONSE:

        :table_def: the table definition used for the query
        :extended_table_def: the table definition with additional details for display
        :warnings: (list) user-friendly warnings (table def can still be queried)
        :errors: (list) user-friendly errors (table def cannot be queried)
        :snapshot_id: (int) ID of table def snapshot
        :previous_snapshot_id: (int/None) ID of previous snapshot
        :next_snapshot_id: (int/None) ID of next snapshot
        """
        oSnapshot = get_object_or_404(models.TableDefSnapshot, pk=pk)
        # data = JSONParser().parse(request)
        set_to_active = self.request.query_params.get("set_to_active", False)
        if not oSnapshot.is_active and set_to_active:
            models.TableDefSnapshot.set_active(request.chironuser, oSnapshot.id)
        table_def = oSnapshot.get_table_def()
        table = qdef.Table(request.chironuser, [], table_def)
        response = {
            "table_def": table.table_def,
            "extended_table_def": table.extended_table_def,
            "warnings": table.warnings,
            "errors": table.errors,
            "snapshot_id": oSnapshot.id,
            "previous_snapshot_id": oSnapshot.get_previous_id(),
            "next_snapshot_id": oSnapshot.get_next_id(),
        }
        return Response(response)

    def create(self, request, *args, **kwargs):
        """
        Applies a transformation definition to a table definition and returns a new table
        definition. The active table def is used.

        :param transformation: the transformation definition
        :type transformation: dict

        FAIL RESPONSE:

        :transformation_successful: False
        :table_def: Since the transformation failed, it simply returns your original table def
        :transformation_errors: list of error messages regarding the failed transformation

        SUCCESS RESPONSE:

        :transformation_successful: True
        :table_def: the new table def with the transformation applied
        :extended_table_def: the new table definition with additional details for display
        :warnings: (list) warnings about new table def (table def can still be queried)
        :errors: (list) errors about new table def (table def cannot be queried)
        :snapshot_id: integer ID of table def snapshot
        :previous_snapshot_id: integer ID of previous snapshot or None
        :next_snapshot_id: integer ID of next snapshot or None
        """
        data = json.loads(request.body.decode("utf-8"))
        if "transformation" not in data:
            return Response({}, status=status.HTTP_400_BAD_REQUEST)
        input_table_def = data.get("table_def", qdef.get_active_table_def(request))
        chironuser = request.chironuser if hasattr(request, "chironuser") else None
        table = qdef.Table(chironuser, [], input_table_def)
        transformation = data.get("transformation")
        transformation_func = table_utils.transformation_function_lookup[transformation["type"]]
        response = transformation_func(request.chironuser, table.table_def, transformation)

        # Add extended cohort def to response
        if response["transformation_successful"]:
            table = qdef.Table(chironuser, [], response["table_def"])
            response["extended_table_def"] = table.extended_table_def
            response["warnings"] = table.warnings
            response["errors"] = table.errors
            oSnapshot = qdef.set_active_table_def(request, response["table_def"])
            response["snapshot_id"] = oSnapshot.id
            response["previous_snapshot_id"] = oSnapshot.get_previous_id()
            response["next_snapshot_id"] = oSnapshot.get_next_id()

        # Return JSON Reponse
        return Response(response)

    def _get_table_def(self, request):
        """
        Gets the table def from the query parameters or uses the active snapshot if none provided
        """
        if request.method == "GET" and "table_def" in request.GET:
            return convert_to_obj(request.GET["table_def"])
        elif request.method == "POST":
            if "table_def" in request.data:
                return request.data["table_def"]
        return qdef.get_active_table_def(request)

    @action(detail=False, methods=["get", "post"])
    def associated_concept_ids(self, request, *args, **kwargs):
        """
        Get a list of all concepts that are referenced in the table definition. If no table def is
        provided, the active table def will be used.
        The POST method behaves the same way as the GET method and is provided to accomodate large
        table definitons.
        """
        table_def = self._get_table_def(request)
        response = {}
        response["concept_ids"] = qdef.get_table_def_concept_ids(table_def)
        return Response(response)

from django.shortcuts import get_object_or_404
from chiron.api.viewsets.table_def import TableDefViewSet

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


from chiron.api.permissions import SubjectLevelAccess
from chiron import models
from chiron import query_definition as qdef

from chiron.api_v2.permissions import DatasetUrlPermission, CanViewWorkspacePermission


class TableDefViewSetV2(TableDefViewSet):
    """API endpoints for defining a table def - a data structure that specifies the columns and
    sort order of a report table.
    """

    permission_classes = [
        IsAuthenticated,
        DatasetUrlPermission,
        SubjectLevelAccess,
        CanViewWorkspacePermission,
    ]

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
        oSnapshot = get_object_or_404(
            models.TableDefSnapshot.objects.filter(chironuser=request.chironuser), pk=pk
        )
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

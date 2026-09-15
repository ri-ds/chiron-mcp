from rest_framework import permissions

from chiron import models
from chiron.api_v2.permissions import DatasetUrlPermission, CanViewWorkspacePermission
from chiron.api.viewsets.cohort_def import CohortDefViewSet
from chiron.api.permissions import SubjectLevelAccess


class CohortDefViewSetV2(CohortDefViewSet):
    """API endpoints for defining a cohort def - a data structure that specifies rules for what
    subjects to include in a cohort.
    """

    permission_classes = [
        permissions.IsAuthenticated,
        DatasetUrlPermission,
        SubjectLevelAccess,
        CanViewWorkspacePermission,
    ]

    def get_queryset(self):
        chironuser = self.request.chironuser
        # Get initial queryset
        queryset = models.CohortDefSnapshot.objects.filter(chironuser=chironuser)
        return queryset

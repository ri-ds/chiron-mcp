from rest_framework import permissions
from django.core.exceptions import PermissionDenied
from chiron import models
from chiron.authorization import get_request_chironuser
from django.shortcuts import get_object_or_404


class DatasetUrlPermission(permissions.BasePermission):
    """
    For API requests that require a dataset be defined. This will create a value for
    request.dataset and for request.chironuser.
    """

    def has_permission(self, request, view):
        # get the dataset
        dataset_name = view.kwargs.get("dataset_string", None)
        oDataset = get_object_or_404(models.Dataset.objects, unique_id=dataset_name)

        # get the chironuser
        oChironUser = get_request_chironuser(request, oDataset)
        if not oChironUser:
            raise PermissionDenied("The user doesn't have permission to access this dataset.")

        # add dataset and chironuser to the request
        request.dataset = oDataset
        request.chironuser = oChironUser
        return True


class CanViewWorkspacePermission(permissions.BasePermission):
    """
    For API requests that access workspace functionality, i.e. concepts, table, aggregate.
    Should only be used after permission_class DatasetSelector (API v1) or DatasetUrlPermission (API v2)
    to ensure request.chironuser has been set.
    """

    def has_permission(self, request, view):
        if not hasattr(request, "chironuser") or not request.chironuser:
            raise AttributeError(
                "request.chironuser must be set before running CanViewWorkspacePermission."
            )
        if not request.chironuser.can_view_workspace:
            raise PermissionDenied(
                "The chiron user doesn't have permission to access to workspace functionality."
            )
        return True

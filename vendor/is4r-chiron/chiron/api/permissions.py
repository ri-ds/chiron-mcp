from rest_framework import permissions
from django.core.exceptions import BadRequest, PermissionDenied

from chiron.authorization import get_request_dataset, get_request_chironuser
from chiron import chiron_settings


class DatasetSelector(permissions.BasePermission):
    """
    For API requests that require a dataset be defined. This will create a value for
    request.dataset and for request.chironuser.
    """

    def has_permission(self, request, view):
        # get the dataset
        oDataset = get_request_dataset(request)
        if not oDataset:
            raise BadRequest(
                "This Chiron instance has multiple datasets "
                "but the dataset wasn't defined in the session."
            )
        # get the chironuser
        oChironUser = get_request_chironuser(request, oDataset)
        if not oChironUser:
            raise PermissionDenied("The user doesn't have permission to access this dataset.")
        # add dataset and chironuser to the request
        request.dataset = oDataset
        request.chironuser = oChironUser
        return True


class UserCreatedContentPermission(permissions.BasePermission):
    """Object-level control for UserCreatedContent this user is allowed to access. Access is
    allowed if the object is public, shared with the user, or created by the user.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user

        # allow read access to public, shared with, or users' created content
        if request.method in permissions.SAFE_METHODS:
            return (
                obj.public
                or obj.share_with.filter(user=user).count() > 0
                or obj.creator.user == user
            )

        # allow update/delete access only to owner
        return obj.creator.user == user


class AnalysisViewOn(permissions.BasePermission):
    """
    Checks chiron settings to see if the analysis view is turned on.
    """

    def has_permission(self, request, view):
        return chiron_settings.CHIRON_SHOW_ANALYSIS_VIEW


class SubjectLevelAccess(permissions.BasePermission):
    """
    Checks if user isn't allowed to see subject level data (i.e. they can only see aggregated data).
    Should only be used after permission_class DatasetSelector (API v1) or DatasetUrlPermission (API v2)
    to ensure request.chironuser has been set.
    """

    def has_permission(self, request, view):
        if not hasattr(request, "chironuser") or not request.chironuser:
            raise AttributeError(
                "request.chironuser must be set before running SubjectLevelAccess permission class."
            )
        u = request.chironuser
        if u.access_level in [u.AccessLevel.PHI, u.AccessLevel.DEID]:
            return True
        return False

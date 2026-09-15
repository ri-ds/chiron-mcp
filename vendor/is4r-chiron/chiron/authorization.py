from functools import wraps
from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import redirect
from django.conf import settings
from django.shortcuts import resolve_url
from django.contrib.auth import REDIRECT_FIELD_NAME

from . import models


def user_is_staff(user):
    """
    how to use as a decorator:
    from django.contrib.auth.decorators import user_passes_test
    @user_passes_test(user_is_staff)
    """
    return user.is_staff


def get_request_dataset(request):
    """
    Returns the dataset from the request if can be identified, otherwise None.
    Raises error if no Django session
    """
    # verify that session exists
    if not hasattr(request, "session"):
        raise ImproperlyConfigured("Chiron requires the Django Session Middleware")
    oDataset = None
    # try to get the dataset from the session
    dataset_id = request.session.get("dataset_id")
    if dataset_id:
        oDataset = models.Dataset.objects.filter(id=dataset_id).first()
        if not oDataset:
            return None
    else:
        # if there's only one dataset then use that
        qDataset = models.Dataset.objects.all()
        if qDataset.count() == 1:
            oDataset = qDataset[0]
    return oDataset


def get_request_chironuser(request, oDataset):
    """
    Gets the Chiron user for the request/dataset. If none exists, may create one depending
    on Chiron settings. Otherwise, returns None.
    """
    # verify that user exists
    if not hasattr(request, "user"):
        raise ImproperlyConfigured("Chiron requires the Django Authentication Middleware")

    # ensure user is authenticated before getting chiron_user
    if not request.user.is_authenticated:
        return None

    # get the existing chironuser
    oChironUser = models.ChironUser.objects.filter(user=request.user, dataset=oDataset).first()
    # or create a new chiron user if allowed
    if not oChironUser and oDataset.autocreate_chiron_user:
        oChironUser = models.ChironUser(
            user=request.user,
            dataset=oDataset,
            access_level=oDataset.auto_access_level,
            can_view_workspace=oDataset.auto_can_view_workspace,
            can_view_subject_details=oDataset.auto_can_view_subject_details,
        )
        oChironUser.save()
        qDefaultPerm = models.DefaultPermissionGroup.objects.filter(dataset=oDataset)
        for oDefaultPerm in qDefaultPerm:
            oChironUser.permission_groups.add(oDefaultPerm.permission_group)
    return oChironUser


def dataset_selector(function):
    """
    View decorator for views that require a dataset or chironuser be specified.
    Sets request.dataset and request.chironuser.
    """

    def wrap(request, *args, **kwargs):
        # get the dataset
        oDataset = get_request_dataset(request)
        if not oDataset:
            return redirect("chiron:select_dataset")
        # get the chironuser
        oChironUser = get_request_chironuser(request, oDataset)
        if not oChironUser:
            # I used to return 403 but then there's no way for the user to fix the problem
            # raise PermissionDenied("The user doesn't have permission to access this dataset.")
            return redirect("chiron:select_dataset")
        # add dataset and chironuser to the request
        request.dataset = oDataset
        request.chironuser = oChironUser
        # continue with view
        response = function(request, *args, **kwargs)
        return response

    wrap.__doc__ = function.__doc__
    wrap.__name__ = function.__name__
    return wrap


def request_passes_test(test_func, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME):
    """
    This is a copy of Django's built-in decorator user_passes_test, except it looks
    at the whole request object, not just the user.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if test_func(request):
                return view_func(request, *args, **kwargs)
            path = request.build_absolute_uri()
            resolved_login_url = resolve_url(login_url or settings.LOGIN_URL)
            # If the login url is the same scheme and net location then just
            # use the path as the "next" url.
            login_scheme, login_netloc = urlparse(resolved_login_url)[:2]
            current_scheme, current_netloc = urlparse(path)[:2]
            if (not login_scheme or login_scheme == current_scheme) and (
                not login_netloc or login_netloc == current_netloc
            ):
                path = request.get_full_path()
            return redirect("chiron:home")

        return _wrapped_view

    return decorator


def can_view_workspace(request):
    """
    how to use as a decorator:
    from django.contrib.auth.decorators import user_passes_test
    @user_passes_test(can_view_workspace, redirect_field_name=None)
    """
    if hasattr(request, "chironuser"):
        if request.chironuser.can_view_workspace:
            return True
    return False


def can_view_subject_details(request):
    """
    how to use as a decorator:
    from django.contrib.auth.decorators import user_passes_test
    @user_passes_test(can_view_subject_details, redirect_field_name=None)
    """
    if hasattr(request, "chironuser"):
        if request.chironuser.can_view_subject_details:
            if request.chironuser.access_level != request.chironuser.AccessLevel.AGG:
                return True
    return False

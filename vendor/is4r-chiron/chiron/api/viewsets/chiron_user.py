from django.db.models import Q

from rest_framework import viewsets, permissions
from rest_framework.response import Response

from chiron import models
from chiron import authorization
from chiron.api import serializers
from chiron.api.permissions import DatasetSelector


class ChironUserViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows users to be viewed or edited."""

    queryset = models.ChironUser.objects.all()
    serializer_class = serializers.ChironUserSerializer
    permission_classes = [permissions.IsAuthenticated, DatasetSelector]

    def get_queryset(self):
        queryset = models.ChironUser.objects.order_by("user__last_name")
        term_param = self.request.query_params.get("term")
        active_param = self.request.query_params.get("active")
        if term_param:
            queryset = queryset.filter(
                Q(user__first_name__icontains=term_param)
                | Q(user__last_name__icontains=term_param)
                | Q(user__email__icontains=term_param)
            )

        if active_param:
            value = active_param != "false"
            queryset = queryset.filter(user__is_active=value)

        return queryset


class MeViewSet(viewsets.GenericViewSet):
    """API endpoint that shows the logged-in users' information."""

    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        """
        Returns the current logged-in user's information

        RESPONSE:

        :id: (int) the Django User ID
        :chiron_user_id: (int) the ChironUser ID
        :username: (str)
        :is_staff: (bool) can view admin page
        :name: (str) full name of user
        :email: (str)
        :access_level: (str)
        """
        user = self.request.user
        # A Django user has one ChironUser *per dataset*, so a bare
        # ChironUser.objects.get(user=user) raised MultipleObjectsReturned (HTTP 500)
        # for any user with access to more than one dataset. Resolve the ChironUser for
        # the request's active dataset; fall back deterministically to the user's
        # lowest-id ChironUser when there is no active-dataset context (this is a v1
        # legacy endpoint; the React UI uses /api/v2/auth/).
        oDataset = authorization.get_request_dataset(request)
        chiron_user = None
        if oDataset is not None:
            chiron_user = authorization.get_request_chironuser(request, oDataset)
        if chiron_user is None:
            chiron_user = (
                models.ChironUser.objects.filter(user=user)
                .order_by("dataset_id", "id")
                .first()
            )
        serializer = serializers.MeSerializer(
            {
                "id": user.id,
                "username": user.username,
                "is_staff": user.is_staff,
                "name": user.get_full_name(),
                "email": user.email,
                "access_level": chiron_user.access_level if chiron_user else None,
                "chiron_user_id": chiron_user.id if chiron_user else None,
            }
        )
        return Response(serializer.data)

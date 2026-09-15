from django.db.models import Q

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound


from chiron import models
from chiron.api import serializers
from chiron.api.utils.pagination import LargeResultsSetPagination
from chiron.api.utils.authentication import CsrfExemptSessionAuthentication

from ..permissions import UserCreatedContentPermission, SubjectLevelAccess


class UserCreatedContentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Reports (UserCreatedContent where type="table").
    Query String Parameters:
        - type: Type for User Created Content. Can be cohort, cohort_auto, or table.
        - state: Filter mode to use. Can be set to "shared_only", "public_only", or "mine".
            - shared_only: Return entries that are shared with the current user.
            - public_only: Return entries that are marked as public.
            - mine: Return entries that have the current user as the creator.
        - my_items_only: Filter for entries created by the current user.
        - search: Search for User Created Content by name.
        - page_size: Page size for response. Default 1000, Maximum 10000.
    """

    permission_classes = [IsAuthenticated, SubjectLevelAccess, UserCreatedContentPermission]
    serializer_class = serializers.UserCreatedContentSerializer
    pagination_class = LargeResultsSetPagination
    authentication_classes = [CsrfExemptSessionAuthentication]

    def get_serializer_context(self):
        """Get Serializer Context
        Sets context for serializer.
        Values that need to be passed into the serializer can be added here.
        :return: Serializer context
        :rtype: dict
        """
        context = super(UserCreatedContentViewSet, self).get_serializer_context()
        context.update({"request": self.request})
        return context

    def get_queryset(self):
        """Get Queryset
        Sets queryset for User Created Content.
        This is where query string parameters are applied.
        Note that any query string parameters added here should be added to the
        User Created Content Viewset class docstring.
        :return: Queryset to use for API call
        :rtype: class: django.db.models.query.QuerySet
        """
        # Get initial queryset
        queryset = models.UserCreatedContent.objects.distinct()

        # if type param is set then filter based on criteria
        type_param = self.request.query_params.get("type")
        if type_param:
            if any(type_param in i for i in models.UserCreatedContent.TYPE_CHOICES):
                queryset = queryset.filter(type=type_param)
            else:
                raise NotFound(
                    detail="Requested type does not match known User Created Content type."
                )

        # handle state params to do some filtering based on value
        state_param = self.request.query_params.get("state")
        if state_param:
            if state_param == "shared_only":
                queryset = queryset.filter(share_with=self.request.chironuser)
            elif state_param == "public_only":
                queryset = queryset.filter(public=True)
            elif state_param == "mine":
                queryset = queryset.filter(creator=self.request.chironuser)
            else:
                raise NotFound(detail="Requested state is unknown")

        # handle search param on name and description
        search_param = self.request.query_params.get("search", None)
        if search_param:
            queryset = queryset.filter(
                Q(name__icontains=search_param) | Q(description__icontains=search_param)
            )

        # if no custom params entered return all content visible to user
        if not state_param and not search_param:
            queryset = queryset.filter(
                Q(public=True)
                | Q(share_with=self.request.chironuser)
                | Q(creator=self.request.chironuser)
            )

        return queryset

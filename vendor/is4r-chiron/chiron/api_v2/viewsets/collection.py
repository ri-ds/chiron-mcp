from chiron import models
from rest_framework import permissions
from chiron.api_v2.permissions import DatasetUrlPermission
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from chiron.api.utils.general import string_to_bool
from chiron import query_definition as qdef
from chiron.api.viewsets.collection import CollectionViewSet


class CollectionViewSetV2(CollectionViewSet):
    """API endpoint that returns Collections. Note that this endpoint is
    read-only and does not allow PUT or POST.

    Query String Parameters:
        - collection: permanent_id for a collection
        - show: "event", only return event based collections
    """

    permission_classes = [permissions.IsAuthenticated, DatasetUrlPermission]
    pagination_class = None

    def get_queryset(self):
        """Get Queryset
        Sets queryset for Concept ViewSet.
        This is where query string parameters are applied.
        :return: Queryset to use for API call
        :rtype: class: django.db.models.query.QuerySet
        """
        # TODO: Add more query string parameters if needed
        chironuser = self.request.chironuser
        # Get initial queryset
        queryset = models.Collection.objects.filter(dataset=chironuser.dataset).order_by("name")
        # Get initial queryset
        # Get query string parameters
        collection_param = self.request.query_params.get("collection", None)
        # Apply filters using query string parameters
        if collection_param:
            selected_collection = queryset.filter(
                permanent_id=str(collection_param).strip()
            ).first()
            queryset = queryset.filter(collection=selected_collection)

        show = self.request.query_params.get("show")
        if show == "event":
            queryset = queryset.filter(event_date_field__isnull=False)

        # Return queryset
        return queryset

    def retrieve(self, request, permanent_id=None, *args, **kwargs):
        """
        :param include_criteria_set_options: include options for modifying a criteria set in the
          cohort definition
        :type include_criteria_set_options: boolean, default=False
        :param include_criteria_set_event_options: include options for modifying a criteria set
          event rule in the cohort definition
        :type include_criteria_set_event_options: boolean, default=False
        :param criteria_set_entry_id: If editing a criteria set in the cohort definition, the
          entry_id of that criteria set. Required if include_criteria_set_options is True or
          include_criteria_set_event_options is True
        :type criteria_set_entry_id: str, optional

        :return: A serialized collection; plus optionally criteria_set_options and
          criteria_set_event_options
        """
        collection = get_object_or_404(self.get_queryset(), permanent_id=permanent_id)
        serializer = self.serializer_class(collection)
        data = serializer.data
        include_options = string_to_bool(request.query_params.get("include_criteria_set_options"))
        include_event_options = string_to_bool(
            request.query_params.get("include_criteria_set_event_options")
        )
        if not include_options and not include_event_options:
            return Response(data)
        cohort_def = qdef.get_active_cohort_def(request)
        entry_id = request.query_params.get("criteria_set_entry_id", None)
        if entry_id is None:
            raise ValueError("criteria_set_entry_id is required")
        if include_options:
            data["criteria_set_options"] = self._get_criteria_set_options(
                collection, cohort_def, entry_id
            )
        if include_event_options:
            data["criteria_set_event_options"] = self._get_criteria_set_event_options(
                request.chironuser, collection, cohort_def, entry_id
            )
        data["criteria_set_entry_id"] = entry_id
        return Response(data)

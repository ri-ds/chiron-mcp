from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework import renderers

from django.shortcuts import get_object_or_404

from chiron import models
from chiron.api import serializers
from chiron.api.utils.general import string_to_bool
from chiron import query_definition as qdef
from chiron.api.renderers import CollectionTemplateRenderer
from chiron.api.permissions import DatasetSelector


class CollectionViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that returns Collections. Note that this endpoint is
    read-only and does not allow PUT or POST.

    Query String Parameters:
        - collection: permanent_id for a collection
        - show: "event", only return event based collections
    """

    permission_classes = [permissions.IsAuthenticated, DatasetSelector]
    serializer_class = serializers.CollectionSerializer
    lookup_field = "permanent_id"
    renderer_classes = [
        renderers.JSONRenderer,  # matches application/json request
        CollectionTemplateRenderer,  # matches text/plain request
        renderers.BrowsableAPIRenderer,  # matches text/html request
    ]

    def get_queryset(self):
        """Get Queryset
        Sets queryset for Concept ViewSet.
        This is where query string parameters are applied.
        :return: Queryset to use for API call
        :rtype: class: django.db.models.query.QuerySet
        """
        # TODO: Add more query string parameters if needed
        # Get initial queryset
        queryset = models.Collection.objects.order_by("name")
        # Get query string parameters
        collection_param = self.request.query_params.get("collection", None)
        # Apply filters using query string parameters
        dataset = None

        if collection_param:
            try:
                dataset = self.request.dataset
                selected_collection = models.Collection.objects.filter(
                    permanent_id=str(collection_param).strip(), dataset=dataset
                ).first()
                queryset = queryset.filter(collection=selected_collection)
            except Exception as e:
                print(e)
                selected_collection = models.Collection.objects.filter(
                    permanent_id=str(collection_param).strip()
                ).first()
                queryset = queryset.filter(collection=selected_collection)

        show = self.request.query_params.get("show")
        if show == "event":
            queryset = queryset.filter(event_date_field__isnull=False)

        # Return queryset
        return queryset

    def retrieve(self, request, permanent_id=None):
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
        try:
            dataset = request.dataset
            collection = models.Collection.objects.get(permanent_id=permanent_id, dataset=dataset)
        except Exception as e:
            print(e)
            collection = get_object_or_404(models.Collection, permanent_id=permanent_id)
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

    def _get_criteria_set_options(self, collection, cohort_def, entry_id):
        """
        :return: A list of dicts representing options for manipulating criteria sets:

          - transformation - the transformation that this option applies to
          - allowed - in the context of the cohort def, can this option be applied?
          - disallowed_reason - if not allowed, why?
          - [various] - all of the other configuration values that can be set for this option
        """
        option = {
            "transformation": "add_criteria_set_count_rule",
            "label": "Count Rule for {} Collection".format(collection.name.title()),
            "allowed": True,
        }
        entry = qdef.lookup_cohort_def_entry(cohort_def, entry_id)
        rel_date_entries = qdef.get_entry_ids_associated_with_relative_date_rule(cohort_def)
        if entry["entry_id"] in rel_date_entries:
            option["allowed"] = False
            option["disallowed_reason"] = (
                "You can't set a custom count rule on events involved in a "
                + "relative date rule."
            )
        else:
            existing_rule = entry.get("subcol_count_restriction", {})
            option["type"] = existing_rule.get("type", "at least")
            option["value"] = existing_rule.get("value", 1)
        option2 = {
            "transformation": "set_criteria_set_alias",
            "label": "Alias for {} Collection".format(collection.name.title()),
            "allowed": True,
            "alias": entry.get("alias", ""),
        }
        return [option, option2]

    def _get_criteria_set_event_options(self, chironuser, collection, cohort_def, entry_id):
        """
        :return: A list of dicts representing options for manipulating a criteria set event rule:

          - option - a unique name for this option
          - transformation - the transformation that this option applies to
          - allowed - in the context of the cohort def, can this option be applied?
          - disallowed_reason - if not allowed, why?
          - (various) - all of the other configuration values that can be set for this option
        """
        response = {}
        event_options = qdef.EventOptionCollection(chironuser, cohort_def, entry_id)
        response["event_options"] = event_options.get_data()
        response["selected_event_option"] = event_options.get_active_option().get_unique_name()
        return response

import json

from django.shortcuts import get_object_or_404
from django.http import StreamingHttpResponse
from django.http import Http404

from rest_framework import viewsets, permissions
from rest_framework.exceptions import NotFound, ParseError
from rest_framework.response import Response
from rest_framework import renderers
from rest_framework.decorators import action

from chiron import models
from chiron import query_definition as qdef
from chiron.api import serializers
from chiron.api.utils.general import convert_to_obj, string_to_bool
from chiron.api.renderers import ConceptTemplateRenderer
from chiron.helpers import make_json_encodable
from chiron.query_engine import get_stattool
from chiron.api.permissions import DatasetSelector
from chiron.api.permissions import SubjectLevelAccess
from chiron.api_v2.permissions import CanViewWorkspacePermission


from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 1000


class ConceptViewSet(viewsets.ModelViewSet):
    """Get information about concepts including statistics and other summary data pulled from the
    dataset. This ModelViewSet is read-only.
    """

    permission_classes = [
        permissions.IsAuthenticated,
        DatasetSelector,
        SubjectLevelAccess,
        CanViewWorkspacePermission,
    ]
    serializer_class = serializers.ConceptSerializer
    renderer_classes = [
        renderers.JSONRenderer,  # matches application/json request
        ConceptTemplateRenderer,  # matches text/plain request
        renderers.BrowsableAPIRenderer,  # matches text/html request
    ]
    lookup_field = "permanent_id"
    pagination_class = StandardResultsSetPagination
    http_method_names = ["head", "get", "put"]

    def get_queryset(self):
        """
        The queryset returned by list() method.

        :return: Queryset to use for API call
        :rtype: class: django.db.models.query.QuerySet
        """
        # TODO: Add more query string parameters if needed
        # Get initial queryset
        queryset = models.Concept.objects.all()
        # Get query string parameters
        collection_param = self.request.query_params.get("collection", None)
        category_param = self.request.query_params.get("category", None)
        search_param = self.request.query_params.get("search", None)
        show_unpublished_param = string_to_bool(
            self.request.query_params.get("show_unpublished", False)
        )

        # get the concept type to display if set
        concept_type = self.request.query_params.get("concept_type")
        # filter further on that concept type
        if not show_unpublished_param:
            queryset = queryset.filter(published=True)
        if concept_type == "cohort":
            queryset = queryset.filter(include_in_cohort_def=True)
        elif concept_type == "table":
            queryset = queryset.filter(include_in_table_def=True)

        if collection_param:
            selected_collection = models.Collection.objects.filter(
                permanent_id=str(collection_param).strip()
            ).first()
            if not selected_collection:
                raise NotFound(detail="Collection with requested ID was not found.")
            queryset = queryset.filter(collection=selected_collection)
        if category_param:
            try:
                selected_category = models.Category.objects.filter(id=int(category_param)).first()
            except ValueError:
                raise ParseError(detail="Category ID must be a valid integer.")
            if not selected_category:
                raise NotFound(detail="Category with requested ID was not found.")
            queryset = queryset.filter(category=selected_category)
        if search_param:
            stat_tool = get_stattool(self.request.chironuser)
            concept_ids = stat_tool.get_concept_search_ids(search_param)
            queryset = queryset.filter(id__in=concept_ids)

        # need to filter the queryset based on user permissions
        allowed_concept_ids = []
        for oConcept in queryset:
            can_view, reason = oConcept.user_can_view_concept_stats(self.request.chironuser)
            if can_view:
                allowed_concept_ids.append(oConcept.id)
        queryset = models.Concept.objects.filter(id__in=allowed_concept_ids)

        # Return queryset
        return queryset

    def list(self, request, *args, **kwargs):
        """
        Retrieve a list of concepts

        :param collection: permanent_id for a collection to filter concepts
        :type collection: string, optional
        :param category: id for a category to filter concepts
        :type category: int, optional
        :param search: search Concepts by name, name plural, and description
        :type search: search Concepts by name, name plural, and description
        :param show_unpublished: set this to "true" to return concepts that are not published
        :type show_unpublished: boolean, default=False
        :param concept_type: filter based on the concept type
        :type concept_type: string, cohort|table, default=None

        :return: serialized list of concepts
        :rtype: list
        """
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, permanent_id=None):
        """
        :param include_statistics: include statistical analysis of concept
        :type include_statistics: boolean, default=False
        :param show_all_data: When calculating statistics, ignore the cohort_def and return stats
          about data for all subjects
        :type show_all_data: boolean, default=False
        :param include_cohort_def_options: include options for creating a cohort def entry
        :type include_cohort_def_options: boolean, default=False
        :param include_table_def_options: include options for creating a table def entry
        :type include_table_def_options: boolean, default=False
        :param cohort_def_entry_id: if editing an existing cohort def entry, the entry_id to use
          whengenerating cohort def options
        :type cohort_def_entry_id: int, optional
        :param table_def_entry_id: if editing an existing table def entry, the entry_id to use when
          generating table def options
        :type table_def_entry_id: int, optional
        :param callback: run callback method for concept
        :type callback: boolean, default=False

        :return: A serialized concept; plus optionally statistics, cohort_def_options, and
          callback_data
        """
        article = get_object_or_404(models.Concept, permanent_id=permanent_id)
        serializer = self.serializer_class(article)
        data = serializer.data
        prefilter_value = request.query_params.get("prefilter_value", None)
        if string_to_bool(request.query_params.get("include_cohort_def_options")):
            data["cohort_def_options"] = self._get_cohort_def_options(
                request, permanent_id, prefilter_value
            )
        if string_to_bool(request.query_params.get("include_table_def_options")):
            data["table_def_options"] = self._get_table_def_options(request, permanent_id)
        if string_to_bool(request.query_params.get("include_statistics")):
            if data["concept_for_prefilter"] and not prefilter_value:
                data["statistics"] = {"error": "You must provide a prefilter value."}
            else:
                data["statistics"] = self._get_concept_statistics(request, permanent_id)
        if string_to_bool(request.query_params.get("callback")):
            if data["concept_for_prefilter"] and not prefilter_value:
                data["callback_data"] = {"error": "You must provide a prefilter value."}
            else:
                data["callback_data"] = self._get_concept_callback_data(request, permanent_id)
        if data["concept_for_prefilter"] and string_to_bool(
            request.query_params.get("include_cohort_def_options")
        ):
            data["concept_for_prefilter"]["cohort_def_options"] = self._get_cohort_def_options(
                request, data["concept_for_prefilter"]["permanent_id"], None
            )
        data["prefilter_value"] = prefilter_value
        return Response(data)

    def update(self, request, permanent_id=None):
        """
        Does the same thing as retrieve() but allows a PUT request for long query parameters.
        """
        article = get_object_or_404(models.Concept, permanent_id=permanent_id)
        serializer = self.serializer_class(article)
        data = serializer.data
        if request.data.get("include_statistics"):
            data["statistics"] = self._get_concept_statistics(request, permanent_id)
        if request.data.get("include_cohort_def_options"):
            prefilter_value = request.data.get("prefilter_value")
            data["cohort_def_options"] = self._get_cohort_def_options(
                request, permanent_id, prefilter_value
            )
        if request.data.get("callback"):
            data["callback_data"] = self._get_concept_callback_data(request, permanent_id)
        return Response(data)

    @action(detail=True, methods=["GET", "POST"], name="cohort def callback")
    def cohort_def_callback(self, request, permanent_id, *args, **kwargs):
        response = self._get_concept_callback_data(request, permanent_id)
        response["is_callback"] = True
        response["permanent_id"] = permanent_id
        return Response(response)

    @action(detail=True, methods=["GET", "POST"], name="cohort def callback streaming")
    def cohort_def_callback_streaming(self, request, permanent_id, *args, **kwargs):
        response = self._get_concept_callback_data_streaming(request, permanent_id)
        # Return response
        return StreamingHttpResponse(response)

    def _get_concept_statistics(self, request, permanent_id):
        oConcept = get_object_or_404(models.Concept, permanent_id=permanent_id)
        can_view, reason = oConcept.user_can_view_concept_stats(request.chironuser)
        if not can_view:
            return {"error": reason}
        # get all of the data from the request
        params = request.query_params
        # use the active snapshot
        cohort_def = qdef.get_active_cohort_def(request)
        if string_to_bool(params.get("show_all_data")):
            cohort_def_for_display = []
        else:
            cohort_def_for_display = cohort_def
        current_chironuser = request.chironuser if hasattr(request, "chironuser") else None
        display_cohort = qdef.Cohort(current_chironuser, cohort_def_for_display)
        # try to find the concept, error out if the concept cannot be found
        processor = oConcept.get_cohort_def_processor(current_chironuser)
        if processor:
            return processor.get_statistics(display_cohort.cohort_def)
        return {}

    def _get_table_def_options(self, request, permanent_id):
        # get all of the data from the request
        params = request.query_params
        existing_entry_id = params.get("table_def_entry_id")
        # use the active snapshot
        table_def = qdef.get_active_table_def(request)
        # also need the cohort def to provide related criteria_set ids
        if "cohort_def" in params:
            cohort_def = convert_to_obj(params["cohort_def"])
        else:
            cohort_def = qdef.get_active_cohort_def(request)
        current_chironuser = request.chironuser if hasattr(request, "chironuser") else None
        table = qdef.Table(current_chironuser, cohort_def, table_def)
        # try to find the concept, error out if the concept cannot be found
        oConcept = get_object_or_404(models.Concept, permanent_id=permanent_id)
        processor = oConcept.get_display_processor(current_chironuser)
        td_entry = {"concept_id": permanent_id}
        if existing_entry_id:
            td_entry = qdef.get_table_def_entry(table.table_def, existing_entry_id)
        if processor:
            processor.set_td_entry(td_entry)
            response = processor.get_form_options(table.table_def)
        else:
            response = {}
        if existing_entry_id:
            response["entry_id"] = existing_entry_id
        response["criteria_set_options"] = qdef.get_all_criteria_set_options_for_collection_id(
            cohort_def, request.chironuser, oConcept.collection.permanent_id
        )
        response["selected_aggregation_criteria_set"] = td_entry.get(
            "aggregation_criteria_set", None
        )
        response["entry_alias"] = td_entry.get("alias", None)
        return response

    def _get_cohort_def_options(self, request, permanent_id, prefilter_value=None):
        # get all of the data from the request
        params = request.query_params
        existing_entry_id = params.get("cohort_def_entry_id")
        # use the active snapshot
        cohort_def = qdef.get_active_cohort_def(request)
        if string_to_bool(params.get("show_all_data")):
            cohort_def_for_display = []
        else:
            cohort_def_for_display = cohort_def
        current_chironuser = request.chironuser if hasattr(request, "chironuser") else None
        cohort = qdef.Cohort(current_chironuser, cohort_def)
        display_cohort = qdef.Cohort(current_chironuser, cohort_def_for_display)
        # try to find the concept, error out if the concept cannot be found
        oConcept = get_object_or_404(models.Concept, permanent_id=permanent_id)
        processor = oConcept.get_cohort_def_processor(
            current_chironuser, prefilter_value=prefilter_value
        )
        cd_entry = None
        if existing_entry_id:
            cd_entry = qdef.lookup_cohort_def_entry(cohort.cohort_def, existing_entry_id)
        if processor:
            response = processor.get_form_options(
                display_cohort.cohort_def, existing_cd_entry=cd_entry
            )
        else:
            response = {}
        if existing_entry_id:
            response["entry_id"] = existing_entry_id
        return response

    def _get_concept_callback_data(self, request, permanent_id):
        """
        Some interactive concept forms need to query additional data from the server after they
        have been loaded. For example, a paginated CohortDefText form needs to run AJAX calls to
        load additional pages.
        """
        params = request.query_params
        cohort_def = qdef.get_active_cohort_def(request)
        if string_to_bool(params.get("show_all_data")):
            cohort_def_for_display = []
        else:
            cohort_def_for_display = cohort_def
        # print([c.permanent_id for c in models.Concept.objects.all()])
        oConcept = get_object_or_404(models.Concept, permanent_id=permanent_id)
        prefilter_value = params.get("prefilter_value", None)
        if not prefilter_value and oConcept.prefilter_required():
            raise Http404("A prefilter value is required for this concept.")
            # BadRequest isn't backwards compatible before Django 3.2
            # raise BadRequest("A prefilter value is required for this concept.")
        current_chironuser = request.chironuser if hasattr(request, "chironuser") else None
        processor = oConcept.get_cohort_def_processor(
            current_chironuser, prefilter_value=prefilter_value
        )
        callback_method = getattr(processor, "form_callback", None)
        if callable(callback_method):
            data = processor.form_callback(request.GET, cohort_def_for_display)
        else:
            # processor doesn't have a form_callback method
            raise Http404("Callback method does not exist or you do not have permission to use it")
        return data

    def _get_concept_callback_data_streaming(self, request, permanent_id):
        """
        Yields streaming callback data, each iteration is separated by string marker '**split**'
        """
        params = request.query_params
        cohort_def = qdef.get_active_cohort_def(request)
        if string_to_bool(params.get("show_all_data")):
            cohort_def_for_display = []
        else:
            cohort_def_for_display = cohort_def
        oConcept = get_object_or_404(models.Concept, permanent_id=permanent_id)
        current_chironuser = request.chironuser if hasattr(request, "chironuser") else None
        processor = oConcept.get_cohort_def_processor(current_chironuser)
        for data in processor.form_callback_streaming(request.GET, cohort_def_for_display):
            data["is_callback"] = True
            data["permanent_id"] = permanent_id
            yield json.dumps(make_json_encodable(data)) + "**split**"

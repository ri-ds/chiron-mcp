from django.db.models import Q

from rest_framework import viewsets, permissions
from rest_framework import renderers
from rest_framework.response import Response

from chiron import models
from chiron.api import serializers
from chiron.api.renderers import CategoryTemplateRenderer
from chiron.api.permissions import DatasetSelector


class ConceptCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Concepts are organized into a hierarchy of categories. This endpoint is used to get lists
    of concepts and categories at a particular position in the hierarchy.  This ModelViewSet is
    read-only.
    """

    permission_classes = [permissions.IsAuthenticated, DatasetSelector]
    serializer_class = serializers.CategorySerializer
    renderer_classes = [
        renderers.JSONRenderer,  # matches application/json request
        CategoryTemplateRenderer,  # matches text/plain request
        renderers.BrowsableAPIRenderer,  # matches text/html request
    ]

    def _filter_concepts_on_user_permissions(self, concepts, chironuser):
        concept_ids = []
        for oConcept in concepts:
            can_view, reason = oConcept.user_can_use_concept_in_table_def(chironuser)
            if can_view:
                concept_ids.append(oConcept.pk)
        return models.Concept.objects.filter(pk__in=concept_ids).order_by("order")

    def _filter_categories_on_user_permissions(self, categories, chironuser):
        category_ids = []
        for oCategory in categories.distinct():
            if oCategory.check_permission_group(chironuser):
                category_ids.append(oCategory.pk)
        return models.Category.objects.filter(pk__in=category_ids).order_by("order")

    def _fetch_concepts_and_categories(self, request, parent_id=None):
        """
        For provided category ID (parent_id), fetches all direct child categories and concepts.
        """
        concept_type = request.query_params.get("concept_type")

        categories = models.Category.objects.accessible(request.dataset)

        # only return category children for specified parent category
        if parent_id is None:
            categories = categories.filter(parent__isnull=True)
        else:
            categories = categories.filter(parent__pk=parent_id)

        # hide a category if it doesn't have at least 1 child concept of right concept_type
        # OR at least 1 child category.
        # This will not cover all cases. It does not check whether the child categories have
        # children, and it does not check that the child concepts are viewable based on the user
        # access level. It would take too much time to check for those uncommon edge cases.
        if concept_type == "cohort":
            categories = categories.filter(
                Q(concepts__include_in_cohort_def=True) | Q(child_set__pk__isnull=False)
            )
        elif concept_type == "table":
            categories = categories.filter(
                Q(concepts__include_in_table_def=True) | Q(child_set__pk__isnull=False)
            )
        elif concept_type == "analysis":
            categories = categories.filter(
                Q(concepts__include_in_analysis_def=True) | Q(child_set__pk__isnull=False)
            )
        else:  # no concept_type specified
            categories = categories.filter(
                Q(concepts__pk__isnull=False) | Q(child_set__pk__isnull=False)
            )

        # last filter on user permissions and so that the order_by clause is used
        categories = self._filter_categories_on_user_permissions(categories, request.chironuser)

        concepts = []
        if parent_id is None:
            concepts = models.Concept.objects.accessible(request.dataset).filter(
                category__isnull=True, published=True
            )
        else:
            concepts = models.Concept.objects.accessible(request.dataset).filter(
                category__pk=parent_id, published=True
            )

        # filter further on that concept type
        if concept_type == "cohort":
            concepts = concepts.filter(include_in_cohort_def=True)
        elif concept_type == "table":
            concepts = concepts.filter(include_in_table_def=True)
        elif concept_type == "analysis":
            concepts = concepts.filter(include_in_analysis_def=True)

        # last filter on user permissions so that the order_by clause is applied
        concepts = self._filter_concepts_on_user_permissions(concepts, request.chironuser)

        # serialize and return
        category_serializer = serializers.CategorySerializer(categories, many=True)
        concept_serializer = serializers.ConceptSerializer(concepts, many=True)
        response = {
            "category_id": "top" if not parent_id else int(parent_id),
            "categories": category_serializer.data,
            "concepts": concept_serializer.data,
        }
        return Response(response)

    def list(self, request, *args, **kwargs):
        """
        Returns all top-level categories and concepts (i.e. categories that don't have parents
        and concepts that don't have a category). Results are filtered based on user permissions.

        :param concept_type: filter based on the concept type
        :type concept_type: string, cohort|table, default=None

        RESPONSE:

        :category_id: "top"
        :categories: (list) all categories without a parent
        :concepts: (list) all concepts without a category
        """
        return self._fetch_concepts_and_categories(request)

    def retrieve(self, request, pk, *args, **kwargs):
        """
        Returns all child categories and concepts of the provided category ID.  Results are
        filtered based on user permissions.

        :param concept_type: filter based on the concept type
        :type concept_type: string, cohort|table, default=None

        RESPONSE:

        :category_id: the provided category ID
        :categories: (list) all direct descendant categories for this category
        :concepts: (list) all concepts belonging to this category
        """
        return self._fetch_concepts_and_categories(request, pk)

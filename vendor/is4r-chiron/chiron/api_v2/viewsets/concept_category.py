from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from chiron.api_v2.permissions import DatasetUrlPermission
from chiron.api.viewsets.concept_category import ConceptCategoryViewSet
from chiron.models import Concept
from chiron.query_engine import get_stattool
from chiron.api import serializers


class ConceptCategoryViewSetV2(ConceptCategoryViewSet):
    """Concepts are organized into a hierarchy of categories. This endpoint is used to get lists
    of concepts and categories at a particular position in the hierarchy.  This ModelViewSet is
    read-only.
    """

    permission_classes = [
        permissions.IsAuthenticated,
        DatasetUrlPermission,
    ]

    @action(detail=False, methods=["GET"], name="Search for Concepts")
    def concept_search(self, request, *args, **kwargs):
        print(request, args, kwargs)
        concept_type = self.request.query_params.get("concept_type")
        search_param = self.request.query_params.get("search")
        qConcept = Concept.objects.all()
        stat_tool = get_stattool(self.request.chironuser)
        concept_ids = stat_tool.get_concept_search_ids(search_param)
        qConcept = qConcept.filter(id__in=concept_ids, published=True)

        # filter further on that concept type
        if concept_type == "cohort":
            qConcept = qConcept.filter(include_in_cohort_def=True)
        elif concept_type == "table":
            qConcept = qConcept.filter(include_in_table_def=True)
        elif concept_type == "analysis":
            qConcept = qConcept.filter(include_in_analysis_def=True)
        concept_serializer = serializers.ConceptSerializer(qConcept, many=True)
        response = {
            "search": str(search_param),
            "concepts": concept_serializer.data,
        }
        return Response(response)

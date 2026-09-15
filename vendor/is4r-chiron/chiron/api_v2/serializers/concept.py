from chiron.api.serializers import CategorySerializer
from rest_framework import serializers
from chiron import models


class ConceptRelatedSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Concept
        fields = [
            "id",
            "permanent_id",
            "name",
            "name_plural",
            "description",
            "get_additional_metadata",
            "order",
            "published",
            "include_in_cohort_def",
            "include_in_table_def",
            "include_in_analysis_def",
            "has_phi",
        ]


class ConceptSerializer(serializers.ModelSerializer):
    """
    Serializer for the Concept model.
    """

    collection = serializers.SlugRelatedField(read_only=True, slug_field="permanent_id")
    collection_name = serializers.SerializerMethodField("get_collection_name", read_only=True)
    collection_name_plural = serializers.SerializerMethodField(
        "get_collection_name_plural", read_only=True
    )
    category_hierarchy = serializers.SerializerMethodField(
        "get_category_hierarchy", read_only=True
    )
    concept_type = serializers.SerializerMethodField("get_concept_type", read_only=True)
    concept_for_prefilter = ConceptRelatedSerializer(read_only=True)

    class Meta:
        model = models.Concept
        # TODO: Re-check which fields are needed in this serializer
        fields = [
            "permanent_id",
            "concept_type",
            "name",
            "get_name_plural",
            "description",
            "get_additional_metadata",
            "collection",
            "collection_name",
            "collection_name_plural",
            "source",
            "concept_for_prefilter",
            "prefilter_mode",
            "category_hierarchy",
            "order",
            "published",
            "include_in_cohort_def",
            "include_in_table_def",
            "include_in_analysis_def",
            "has_phi",
            "pk",
        ]

    def get_category_hierarchy(self, concept):
        categories = concept.get_category_hierarchy()
        return CategorySerializer(categories, many=True).data

    def get_collection_name(self, concept):
        return concept.collection.name

    def get_collection_name_plural(self, concept):
        return concept.collection.get_name_plural()

    def get_concept_type(self, concept):
        try:
            processor = concept.get_cohort_def_processor_without_user()
            return processor.concept_type
        except AttributeError:
            return "unknown"

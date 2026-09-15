import json

from django.contrib.auth import get_user_model

from rest_framework import serializers
from rest_framework.serializers import raise_errors_on_nested_writes
from rest_framework.utils import model_meta

from chiron import models
from chiron.api.utils.general import convert_to_obj
from chiron.query_definition import Cohort


class MeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    is_staff = serializers.BooleanField()
    name = serializers.CharField()
    email = serializers.CharField()
    access_level = serializers.CharField()
    chiron_user_id = serializers.IntegerField()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ["id", "username", "first_name", "last_name", "email"]


class ChironUserSerializer(serializers.ModelSerializer):
    """
    RESPONSE:

    :id: (int) the ChironUser ID
    :user: (dict) The Django User information: username, first_name,
      last_name, email
    :access_level: (str)
    :permission_groups: (list) IDs for permission groups user belongs to
    """

    user = UserSerializer(read_only=True)

    class Meta:
        model = models.ChironUser
        fields = [
            "id",
            "user",
            "access_level",
            "permission_groups",
        ]


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


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for the Category model.
    """

    class Meta:
        model = models.Category
        fields = ["id", "name", "parent_id", "get_level"]
        depth = 1


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


class CollectionSerializer(serializers.ModelSerializer):
    """
    Serializer for the Collection model.
    """

    has_event = serializers.SerializerMethodField(method_name="calculate_has_event")

    class Meta:
        model = models.Collection
        # TODO: Check what fields are needed in this serializer and add them
        fields = [
            "permanent_id",
            "name",
            "get_name_plural",
            "is_root_collection",
            "has_event",
        ]

    def calculate_has_event(self, obj):
        return obj.event_date_field is not None


class ProjectSerializer(serializers.ModelSerializer):
    """
    Serializer for the Project model.
    """

    viewable_report_count = serializers.SerializerMethodField("get_report_count", read_only=True)

    class Meta:
        model = models.Project
        fields = ["id", "name", "viewable_report_count"]

    def get_report_count(self, oProject):
        oChironUser = self.context["request"].chironuser
        return oProject.get_report_count(oChironUser)


class UserCreatedContentSerializer(serializers.ModelSerializer):
    """
    Serializer for Report model.
    """

    creator_name = serializers.SerializerMethodField("get_creator_name", read_only=True)
    project_name = serializers.SerializerMethodField("get_project_name", read_only=True)
    starred = serializers.SerializerMethodField("check_if_starred", read_only=True)
    sharing_description = serializers.SerializerMethodField(
        "get_sharing_description", read_only=True
    )
    share_with = ChironUserSerializer(many=True, read_only=True)

    class Meta:
        model = models.UserCreatedContent
        fields = [
            "id",
            "name",
            "project",
            "project_name",
            "description",
            "creator",
            "created",
            "type",
            "definition",
            "creator_name",
            "public",
            "starred",
            "share_with",
            "sharing_description",
        ]
        read_only_fields = [
            "creator",
            "created",
        ]

    def validate(self, data):
        """Validate

        Additional validation for User Created Content.

        :param data: Input data
        :type data: dict
        :return: Validated data
        :rtype: dict
        """
        if "definition" in data:
            # Special handling for Cohort Defs
            try:
                full_def = convert_to_obj(data["definition"])
            except json.JSONDecodeError:
                full_def = {}
            cohort = Cohort(self.context["request"].chironuser, full_def.get("cohort_def"))
            full_def["cohort_def"] = cohort.cohort_def
            data["definition"] = json.dumps(full_def)

        # force creator to be the requestor
        data["creator_id"] = self.context["request"].chironuser.id
        data["dataset_id"] = self.context["request"].dataset.id

        # Final check for valid Type for User Created Content
        if not any(
            data["type"] in i
            for i in [
                models.UserCreatedContent.Type.COHORT,
                models.UserCreatedContent.Type.TABLE,
            ]
        ):
            raise serializers.ValidationError("Invalid type field for User Created Content.")

        return data

    def get_creator_name(self, usercreatedcontent):
        """Get Creator Name

        Gets name of User Created Content Creator.

        :param usercreatedcontent: UserCreatedContent instance
        :type usercreatedcontent: class: chiron.models.user_models.UserCreatedContent
        :return: UserCreatedContent Creator name
        :rtype: str
        """
        creator_name = usercreatedcontent.creator.get_name()
        return creator_name

    def get_project_name(self, usercreatedcontent):
        """Get Creator Name

        Gets name of User Created Content Creator.

        :param usercreatedcontent: UserCreatedContent instance
        :type usercreatedcontent: class: chiron.models.user_models.UserCreatedContent
        :return: UserCreatedContent Creator name
        :rtype: str
        """
        if not usercreatedcontent.project:
            return ""
        project_name = usercreatedcontent.project.name
        return project_name

    def check_if_starred(self, usercreatedcontent):
        return usercreatedcontent.check_if_starred(self.context["request"].chironuser)

    def get_sharing_description(self, usercreatedcontent):
        return usercreatedcontent.get_sharing_description()

    def update(self, instance, validated_data):
        """Update

        Serializer Update function overridden to allow for sending email notifications
        upon updating.

        :param instance: Model instance
        :type instance: class: chiron.models.user_models.UserCreatedContent
        :param validated_data: Validated data
        :type validated_data: dict
        :return: Model instance
        :type instance: class: chiron.models.user_models.UserCreatedContent
        """
        raise_errors_on_nested_writes("update", self, validated_data)
        info = model_meta.get_field_info(instance)

        # Simply set each attribute on the instance, and then save it.
        # Note that unlike `.create()` we don't need to treat many-to-many
        # relationships as being a special case. During updates we already
        # have an instance pk for the relationships to be associated with.
        m2m_fields = []
        for attr, value in validated_data.items():
            if attr in info.relations and info.relations[attr].to_many:
                m2m_fields.append((attr, value))
            else:
                setattr(instance, attr, value)

        instance.save()

        # Note that many-to-many fields are set after updating instance.
        # Setting m2m fields triggers signals which could potentially change
        # updated instance and we do not want it to collide with .update()
        for attr, value in m2m_fields:
            field = getattr(instance, attr)
            field.set(value)

        return instance

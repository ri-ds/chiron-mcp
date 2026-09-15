from rest_framework import serializers


class AuthUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    isStaff = serializers.BooleanField()
    name = serializers.CharField()
    email = serializers.CharField()


class DatasetSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    unique_id = serializers.CharField()
    description = serializers.CharField(required=False)
    siteTitle = serializers.CharField(required=False)
    lastImport = serializers.CharField(required=False)
    subjectCount = serializers.CharField(required=False)
    accessLevel = serializers.CharField(required=False)
    accessLevelLabel = serializers.CharField(required=False)
    canViewWorkspace = serializers.BooleanField(required=False)
    canViewSubjectDetails = serializers.BooleanField(required=False)
    selectable = serializers.BooleanField(required=False)
    contactEmail = serializers.EmailField(required=False)
    logoUrl = serializers.CharField(required=False)
    chironUserId = serializers.IntegerField(required=False)
    extraHeaderLinks = serializers.JSONField(required=False)


class DatasetListSerializers(serializers.Serializer):
    datasets = DatasetSerializer(many=True)


class AuthSerializer(serializers.Serializer):
    user = AuthUserSerializer()
    chironVersion = serializers.CharField()

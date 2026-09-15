from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from chiron.api.permissions import SubjectLevelAccess
from chiron import models
from chiron.api import serializers
from chiron.api.utils.pagination import LargeResultsSetPagination
from chiron.api.utils.authentication import CsrfExemptSessionAuthentication
from chiron.api.permissions import DatasetSelector


class ProjectViewSet(viewsets.ModelViewSet):
    """API endpoints for defining a project - a named group of reports."""

    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated, DatasetSelector, SubjectLevelAccess]
    serializer_class = serializers.ProjectSerializer
    pagination_class = LargeResultsSetPagination
    queryset = models.Project.objects.all()

    def list(self, request, *args, **kwargs):
        """
        Retrieve a serialized list of projects.

        :return: serialized list of projects
        :rtype: list
        """
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve data about a specific project.

        RESPONSE:

        :id: (int) the Django User ID
        :name: (str) the project name
        :viewable_report_count: (int) How many reports associated with this project can be
          viewed by the current user
        """
        return super().retrieve(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """
        Create a new project.

        :param name: the name of the project to create
        :type name: string
        """
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """
        Edit an existing project.

        :param id: the ID of the project to edit
        :type id: integer
        :param name: the name of the project to create
        :type name: string
        """
        return super().create(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        """
        Delete an existing project.

        :param id: the ID of the project to delete
        :type id: integer
        """
        return super().delete(request, *args, **kwargs)

    def get_serializer_context(self):
        """Get Serializer Context
        Sets context for serializer.
        Values that need to be passed into the serializer can be added here.
        :return: Serializer context
        :rtype: dict
        """
        context = super(ProjectViewSet, self).get_serializer_context()
        context.update({"request": self.request})
        return context

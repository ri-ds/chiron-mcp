from chiron.api_v2.serializers.auth import DatasetListSerializers
from chiron.authorization import get_request_chironuser
from chiron.models.data_definition_models import Dataset
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from chiron.views.views import get_summary_data
from chiron.api_v2.serializers import DatasetSerializer
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from chiron import models


class DatasetViewSetV2(viewsets.ViewSet):
    """
    API endpoint that shows the logged in user's dataset information
    """

    # only need to be logged in to view datasets
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        all_datasets = []

        for d in Dataset.objects.all():
            oChironUser = models.ChironUser.objects.filter(user=request.user, dataset=d).first()
            if oChironUser or d.autocreate_chiron_user:
                d.selectable = True
            else:
                # check whether dataset should be added at all
                if not d.list_visible:
                    continue
                d.selectable = False

            d_object = {
                "id": d.id,
                "name": d.display_name,
                "description": d.description,
                "siteTitle": d.override_site_title,
                "unique_id": d.unique_id,
                "selectable": d.selectable,
                "contactEmail": d.contact_email,
            }
            all_datasets.append(d_object)

        serializer = DatasetListSerializers({"datasets": all_datasets})

        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        # essentially do dataseturlpermissions but for pk
        oDataset = get_object_or_404(models.Dataset.objects, unique_id=pk)
        # get the chironuser
        oChironUser = get_request_chironuser(request, oDataset)

        if not oChironUser:
            raise PermissionDenied("The user doesn't have permission to access this dataset.")

        data = get_summary_data(oChironUser)
        serializer = DatasetSerializer(
            {
                "description": oDataset.description,
                "name": oDataset.display_name,
                "id": oDataset.id,
                "unique_id": oDataset.unique_id,
                "lastImport": data["Date of last import"],
                "subjectCount": data["Total subjects in system"],
                "accessLevelLabel": data["Your Access Level"],
                "accessLevel": oChironUser.access_level,
                "canViewWorkspace": oChironUser.can_view_workspace,
                "canViewSubjectDetails": oChironUser.can_view_subject_details,
                "logoUrl": oDataset.logo_url,
                "chironUserId": oChironUser.pk,
                "extraHeaderLinks": oDataset.extra_header_links,
            }
        )
        return Response(serializer.data)

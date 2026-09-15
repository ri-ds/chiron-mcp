from django.db.models import Q
from django.template.loader import render_to_string
from django.shortcuts import reverse

from rest_framework import viewsets
from rest_framework.exceptions import NotFound
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import renderers
from rest_framework.permissions import IsAuthenticated


from chiron import models, chiron_settings
from chiron.forms import ui_forms
from chiron.api import serializers
from chiron.api.utils.pagination import LargeResultsSetPagination
from chiron.api.utils.authentication import CsrfExemptSessionAuthentication
from chiron import query_definition as qdef
from chiron.api.renderers import ReportsTemplateRenderer
from chiron.api.permissions import DatasetSelector
from chiron.api.utils.report import send_email_report_notification

from ..permissions import UserCreatedContentPermission, SubjectLevelAccess


class ReportViewSet(viewsets.ModelViewSet):
    """API endpoints for defining a report - a results table (cohort def and table def pair) that
    has been named and saved.
    """

    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [
        IsAuthenticated,
        DatasetSelector,
        SubjectLevelAccess,
        UserCreatedContentPermission,
    ]
    serializer_class = serializers.UserCreatedContentSerializer
    pagination_class = LargeResultsSetPagination
    # queryset = models.UserCreatedContent.objects.accessible()
    renderer_classes = [
        renderers.JSONRenderer,  # matches application/json request
        ReportsTemplateRenderer,  # matches text/plain request
        renderers.BrowsableAPIRenderer,  # matches text/html request
    ]

    def list(self, request, *args, **kwargs):
        """
        Retrieve a list of viewable reports (based on the user).

        :param state: additional filtering, "shared_only", "public_only", "mine"
        :type state: string, optional
        :param project_id: filter by report project
        :type project_id: integer, optional
        :param search: search for report using search string
        :type search: string, optional
        :param page_size: page size for response
        :type page_size: int, default=1000, max=10,000

        :return: serialized list of reports
        :rtype: list
        """
        return super().list(request, *args, **kwargs)

    def get_serializer_context(self):
        """Get Serializer Context
        Sets context for serializer.
        Values that need to be passed into the serializer can be added here.
        :return: Serializer context
        :rtype: dict
        """
        context = super(ReportViewSet, self).get_serializer_context()
        context.update({"request": self.request})
        return context

    def get_queryset(self):
        """Get Queryset
        Sets queryset for User Created Content.
        This is where query string parameters are applied.
        Note that any query string parameters added here should be added to the
        User Created Content Viewset class docstring.
        :return: Queryset to use for API call
        :rtype: class: django.db.models.query.QuerySet
        """
        # Get initial queryset

        queryset = self.request.chironuser.get_viewable_reports()

        # handle state params to do some filtering based on value
        state_param = self.request.query_params.get("state")
        if state_param:
            if state_param == "shared_only":
                queryset = queryset.filter(share_with=self.request.chironuser)
            elif state_param == "public_only":
                queryset = queryset.filter(public=True)
            elif state_param == "mine":
                queryset = queryset.filter(creator=self.request.chironuser)
            elif state_param == "starred":
                qStarred = models.ContentFlag.objects.filter(
                    chironuser=self.request.chironuser,
                    flag_type=models.ContentFlag.FlagType.STAR,
                )
                queryset = queryset.filter(contentflag__in=qStarred)
            else:
                raise NotFound(detail="Requested state is unknown")

        project_id = self.request.query_params.get("project_id")
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        # handle search param on name and description
        search_param = self.request.query_params.get("search", None)
        if search_param:
            queryset = queryset.filter(
                Q(name__icontains=search_param) | Q(description__icontains=search_param)
            )

        return queryset

    @action(detail=True, methods=["post"])
    def flag(self, request, pk, *args, **kwargs):
        """
        Add a flag to a report for a user.

        :param chiron_user_id: user to add flag for (default is current user)
        :type chiron_user_id: int, optional
        :param flag_type: type of flag to add (default is ContentFlag.FlagType.STAR)
        :type flag_type: string, optional
        :param add_or_remove: "add" (default) or "remove" the flag
        :type add_or_remove: string, optional

        :return: confirmation message
        :rtype: dict
        """
        oContent = models.UserCreatedContent.objects.get(pk=pk)
        chiron_user_id = request.query_params.get("chiron_user_id")
        if chiron_user_id:
            oChironUser = models.ChironUser.objects.get(pk=chiron_user_id)
        else:
            oChironUser = request.chironuser
        flag_type = self.request.POST.get("flag_type", models.ContentFlag.FlagType.STAR)
        add_or_remove = self.request.POST.get("add_or_remove", "add")
        if add_or_remove == "add":
            oFlag, created = models.ContentFlag.objects.get_or_create(
                content=oContent,
                chironuser=oChironUser,
                flag_type=flag_type,
            )
        else:
            count_deleted, _ = models.ContentFlag.objects.filter(
                content=oContent,
                chironuser=oChironUser,
                flag_type=flag_type,
            ).delete()
        response = {
            "status": "complete",
        }
        return Response(response)

    @action(detail=False, methods=["get", "post"])
    def create_form(self, request, *args, **kwargs):
        """
        Primarily for built-in website. Use GET to retrive HTML snippet of blank form. Use POST
        to submit the form. If validation fails on POST, will return status="incomplete" and
        form HTML with errors.
        """
        fContent = ui_forms.ReportForm(request.chironuser, initial={"dataset": request.dataset})
        if request.method == "POST":
            fContent = ui_forms.ReportForm(
                request.chironuser, request.POST, initial={"dataset": request.dataset}
            )
            if fContent.is_valid():
                oContent = fContent.save(commit=False)
                oContent.type = models.UserCreatedContent.Type.TABLE
                oContent.creator = request.chironuser
                cohort = qdef.Cohort(request.chironuser)
                oContent.set_def_value("cohort_def", cohort.cohort_def)
                table = qdef.Table(request.chironuser)
                oContent.set_def_value("table_def", table.table_def)
                oContent.save()
                fContent.save_m2m2()

                if chiron_settings.CHIRON_EMAIL_NOTIFICATIONS:
                    full_link = request.build_absolute_uri(
                        reverse("chiron:report", args=(oContent.pk,))
                    )
                    for chiron_user in fContent.cleaned_data["share_with"]:
                        send_email_report_notification(chiron_user, oContent, full_link)

                response = {"status": "complete"}
                response["onSuccess"] = "chiron.manager.reportCreated"
                return Response(response)
        context = {
            "fForm": fContent,
            "qReport": models.UserCreatedContent.objects.filter(creator=self.request.chironuser),
        }
        response = {
            "status": "incomplete",
            "title": "Save Current Results View as a Report",
            "html": render_to_string("chiron/reports/save_report.html", context, request=request),
            "onLoad": "attachReportFormEvents",
        }
        return Response(response)

    @action(detail=True, methods=["get", "post"])
    def edit_form(self, request, pk, *args, **kwargs):
        """
        Primarily for built-in website. Use GET to retrive HTML snippet of edit form. Use POST
        to submit the form. If validation fails on POST, will return status="incomplete" and
        form HTML with errors.
        """
        oContent = models.UserCreatedContent.objects.get(pk=pk)
        original_shared_users = list(oContent.share_with.values_list("pk", flat=True))
        fContent = ui_forms.ReportForm(request.chironuser, instance=oContent)
        if request.method == "POST":
            fContent = ui_forms.ReportForm(request.chironuser, request.POST, instance=oContent)
            if fContent.is_valid():
                oContent = fContent.save(commit=False)
                if request.POST.get("overwrite_query_def_with_active", "no") == "yes":
                    cohort = qdef.Cohort(request.chironuser)
                    oContent.set_def_value("cohort_def", cohort.cohort_def)
                    table = qdef.Table(request.chironuser)
                    oContent.set_def_value("table_def", table.table_def)
                oContent.save()
                fContent.save_m2m2()

                if chiron_settings.CHIRON_EMAIL_NOTIFICATIONS:
                    full_link = request.build_absolute_uri(
                        reverse("chiron:report", args=(oContent.pk,))
                    )
                    for chiron_user in fContent.cleaned_data["share_with"]:
                        if chiron_user.pk not in original_shared_users:
                            send_email_report_notification(chiron_user, oContent, full_link)

                response = {"status": "complete"}
                return Response(response)
        overwrite_query_def_with_active = request.GET.get("overwrite_query_def_with_active", False)
        context = {
            "fForm": fContent,
            "oReport": oContent,
            "overwrite_query_def_with_active": overwrite_query_def_with_active,
        }
        response = {
            "status": "incomplete",
            "title": "Edit Report",
            "html": render_to_string("chiron/reports/edit_report.html", context, request=request),
            "onLoad": "attachReportFormEvents",
        }
        return Response(response)

    @action(detail=True, methods=["get", "post"])
    def share_form(self, request, pk, *args, **kwargs):
        oContent = models.UserCreatedContent.objects.get(pk=pk)
        original_shared_users = list(oContent.share_with.values_list("pk", flat=True))
        fContent = ui_forms.ReportSharingForm(oContent.creator, instance=oContent)
        if request.method == "POST":
            fContent = ui_forms.ReportSharingForm(
                oContent.creator, request.POST, instance=oContent
            )
            if fContent.is_valid():
                oContent = fContent.save()

                if chiron_settings.CHIRON_EMAIL_NOTIFICATIONS:
                    full_link = request.build_absolute_uri(
                        reverse("chiron:report", args=(oContent.pk,))
                    )
                    for chiron_user in fContent.cleaned_data["share_with"]:
                        if chiron_user.pk not in original_shared_users:
                            send_email_report_notification(chiron_user, oContent, full_link)

                response = {"status": "complete"}
                return Response(response)
        context = {
            "fForm": fContent,
            "oReport": oContent,
            "full_url": request.build_absolute_uri(reverse("chiron:report", args=(oContent.pk,))),
        }
        response = {
            "status": "incomplete",
            "title": "Share Report",
            "html": render_to_string("chiron/reports/share_report.html", context, request=request),
        }
        return Response(response)

    @action(detail=True, methods=["get", "post"])
    def delete_form(self, request, pk, *args, **kwargs):
        oContent = models.UserCreatedContent.objects.get(pk=pk)
        if request.method == "POST":
            oContent.delete()
            response = {
                "status": "complete",
            }
            return Response(response)
        context = {"oReport": oContent}
        response = {
            "status": "incomplete",
            "title": "Delete Report",
            "html": render_to_string(
                "chiron/reports/delete_report.html", context, request=request
            ),
        }
        return Response(response)

from django.db.models import Q
from django.template.loader import render_to_string
from django.shortcuts import reverse
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
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
from chiron.api.utils.report import send_email_report_notification

from chiron.authorization import get_request_chironuser
from django.http import QueryDict
from django.utils.datastructures import MultiValueDict

from chiron.api.permissions import UserCreatedContentPermission, SubjectLevelAccess
from chiron.api_v2.permissions import DatasetUrlPermission


class ReportViewSetV2(viewsets.ModelViewSet):
    """API endpoints for defining a report - a results table (cohort def and table def pair) that
    has been named and saved.
    """

    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [
        IsAuthenticated,
        DatasetUrlPermission,
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

    @action(detail=False, methods=["get"])
    def get_report(self, request, *args, **kwargs):
        report_id = request.GET.get("report_id")
        oContent = get_object_or_404(self.get_queryset(), pk=report_id)

        # find/create the chironuser for this report and set on the request
        oChironUser = get_request_chironuser(request, oContent.dataset)
        if oChironUser:
            request.chironuser = oChironUser
            request.dataset = oContent.dataset

        # if they're not allowed to view the report then you can finish
        if oContent not in request.chironuser.get_viewable_reports():
            raise PermissionDenied

        cohort = qdef.Cohort(request.chironuser, oContent.get_def_value("cohort_def"))
        table = qdef.Table(
            request.chironuser,
            oContent.get_def_value("cohort_def"),
            oContent.get_def_value("table_def"),
        )

        page = int(request.GET.get("page", 1))

        custom_sort_string = ""
        sort_field = request.GET.get("sort_field", None)
        sort_direction = int(request.GET.get("sort_direction", 1))
        if sort_field:
            # remove sort field if it already exists
            table.table_def["sort"][:] = [
                entry for entry in table.table_def["sort"] if entry["entry_id"] != sort_field
            ]
            table.table_def["sort"].insert(
                0, {"entry_id": sort_field, "direction": sort_direction}
            )
            custom_sort_string = "&sort_field={}&sort_direction={}".format(
                sort_field, sort_direction
            )
        oContentJsonSerializable = {
            "name": oContent.name,
            "creator": str(oContent.creator),
            "created": oContent.created,
            "description": oContent.description,
            "public": oContent.get_sharing_description(),
            "id": oContent.id,
        }
        context = {
            "current_page": "reports",
            "oReport": oContentJsonSerializable,
            "extended_cohort_def": cohort.extended_cohort_def,
            "cohort_description": qdef.describe_cohort_def(cohort.extended_cohort_def),
            "warnings": cohort.warnings,
            "errors": cohort.errors,
            "full_url": request.build_absolute_uri(reverse("chiron:report", args=(oContent.pk,))),
            "extended_table_def": table.extended_table_def,
            "td_warnings": table.warnings,
            "td_errors": table.errors,
            "custom_sort_string": custom_sort_string,
            "cohort_def_interactive": False,
            "page": page,
            "sort_field": sort_field,
            "sort_direction": sort_direction,
        }
        return Response(context)

    @action(detail=False, methods=["get"])
    def viewable_reports(self, request, *args, **kwargs):
        qReport = self.get_queryset()
        custom_report_categories = []
        qStarred = models.ContentFlag.objects.filter(
            chironuser=request.chironuser,
            flag_type=models.ContentFlag.FlagType.STAR,
        )
        count = qReport.filter(contentflag__in=qStarred).count()
        custom_report_categories.append(
            {"label": "All Reports", "state": "all", "count": qReport.count()}
        )
        if count:
            custom_report_categories.append(
                {"label": "Starred", "state": "starred", "count": count}
            )
        count = qReport.filter(creator=request.chironuser).count()
        if count:
            custom_report_categories.append(
                {"label": "My Reports", "state": "mine", "count": count}
            )

        qProject = models.Project.objects.filter(dataset=request.chironuser.dataset)
        viewProjects = []
        for oProject in qProject:
            oProject.report_count = oProject.get_report_count(request.chironuser)
            viewProjects.append(
                {
                    "label": oProject.name,
                    "pk": oProject.pk,
                    "state": "",
                    "count": oProject.report_count,
                }
            )
        context = {
            "current_page": "reports",
            "qProject": viewProjects,
            "custom_report_categories": custom_report_categories,
        }
        return Response(context)

    def get_serializer_context(self):
        """Get Serializer Context
        Sets context for serializer.
        Values that need to be passed into the serializer can be added here.
        :return: Serializer context
        :rtype: dict
        """
        context = super(ReportViewSetV2, self).get_serializer_context()
        context.update({"request": self.request})
        return context

    def get_queryset(
        self,
    ):
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

    def _dict_to_querydict(self, dictionary):
        qdict = QueryDict("", mutable=True)
        for key, value in dictionary.items():
            d = {key: value}
            qdict.update(MultiValueDict(d) if isinstance(value, list) else d)
        return qdict

    def _format_user_content(self, oContent):
        return {
            "name": oContent.name,
            "creator": str(oContent.creator),
            "created": oContent.created,
            "description": oContent.description,
            "id": oContent.id,
            "project": str(oContent.project),
            "project_id": oContent.project.pk if oContent.project is not None else None,
            "public": oContent.public,
        }

    def _format_shared_options(self, oContent):
        # make our filled out own form data here
        share_checked = list(oContent.share_with.all())
        # exclude sharing with owner
        qChironUser = models.ChironUser.objects.exclude(id=oContent.creator.id)
        # only share with ChironUsers associated with this dataset
        qChironUser = qChironUser.filter(dataset=oContent.creator.dataset)
        # exclude chiron users who only have aggregated access
        qChironUser = qChironUser.exclude(access_level=models.ChironUser.AccessLevel.AGG)
        share_options = list(qChironUser)
        # create checked map to users
        share_checked_data = list(
            map(
                lambda user: {
                    "username": str(user),
                    "user_id": user.id,
                    "checked": user in share_checked,
                },
                share_options,
            )
        )
        return share_checked_data

    def _format_project_select(self, fContent):
        # handle project selection
        projects = [{"label": fContent.fields["project"].empty_label, "value": -1}]
        for q in fContent.fields["project"].queryset:
            projects.append({"label": str(q), "value": q.pk})
        return projects

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

        oContent = get_object_or_404(self.get_queryset(), pk=pk)
        chiron_user_id = request.query_params.get("chiron_user_id")
        if chiron_user_id:
            oChironUser = models.ChironUser.objects.get(pk=chiron_user_id)
        else:
            oChironUser = request.chironuser
        flag_type = self.request.POST.get("flag_type", models.ContentFlag.FlagType.STAR)
        add_or_remove = self.request.data.get("add_or_remove", "add")

        if add_or_remove == "add":
            models.ContentFlag.objects.get_or_create(
                content=oContent,
                chironuser=oChironUser,
                flag_type=flag_type,
            )
        else:
            models.ContentFlag.objects.filter(
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
            qDict = self._dict_to_querydict(request.data)
            fContent = ui_forms.ReportForm(
                request.chironuser, qDict, initial={"dataset": request.dataset}
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
                        request.build_absolute_uri(f"/{request.dataset}/reports/{oContent.pk}/")
                    )
                    for chiron_user in fContent.cleaned_data["share_with"]:
                        send_email_report_notification(chiron_user, oContent, full_link)

                response = {"status": "complete", "errors": [fContent.errors.as_text()]}
                response["onSuccess"] = "chiron.manager.reportCreated"
                return Response(response)

        oReports = self.get_queryset().filter(creator=self.request.chironuser)
        reports = [{"label": "---select a report---", "value": -1}]
        for r in oReports:
            reports.append({"label": str(r), "value": r.pk})

        response = {
            "status": "incomplete",
            "title": "Save Current Results View as a Report",
            "errors": [fContent.errors.as_text()],
            "data": {
                "fForm": {
                    "shared_options": list(
                        map(
                            lambda user: {
                                "username": str(user),
                                "user_id": user.id,
                                "checked": False,
                            },
                            fContent.fields["share_with"].queryset,
                        )
                    ),
                    "project_selection": self._format_project_select(fContent),
                },
                "oReports": reports,
            },
        }
        return Response(response)

    @action(detail=True, methods=["get", "post"])
    def edit_form(self, request, pk, *args, **kwargs):
        """
        Primarily for built-in website. Use GET to retrive HTML snippet of edit form. Use POST
        to submit the form. If validation fails on POST, will return status="incomplete" and
        form HTML with errors.
        """
        oContent = get_object_or_404(self.get_queryset(), pk=pk)
        original_shared_users = list(oContent.share_with.values_list("pk", flat=True))
        fContent = ui_forms.ReportForm(request.chironuser, instance=oContent)
        if request.method == "POST":
            qDict = self._dict_to_querydict(request.data)
            fContent = ui_forms.ReportForm(request.chironuser, qDict, instance=oContent)
            if fContent.is_valid():
                oContent = fContent.save(commit=False)
                if qDict.get("overwrite_query_def_with_active") == "yes":
                    cohort = qdef.Cohort(request.chironuser)
                    oContent.set_def_value("cohort_def", cohort.cohort_def)
                    table = qdef.Table(request.chironuser)
                    oContent.set_def_value("table_def", table.table_def)
                oContent.save()
                fContent.save_m2m2()

                if chiron_settings.CHIRON_EMAIL_NOTIFICATIONS:
                    full_link = request.build_absolute_uri(
                        request.build_absolute_uri(f"/{request.dataset}/reports/{oContent.pk}/")
                    )
                    for chiron_user in fContent.cleaned_data["share_with"]:
                        if chiron_user.pk not in original_shared_users:
                            send_email_report_notification(chiron_user, oContent, full_link)

                response = {
                    "status": "complete",
                    "errors": [fContent.errors.as_text()],
                }
                return Response(response)
        overwrite_query_def_with_active = request.GET.get("overwrite_query_def_with_active", False)
        output_type = request.GET.get("output_type")
        if output_type == "json":
            response = {
                "status": "incomplete",
                "title": "Edit Report",
                "errors": [fContent.errors.as_text()],
                "data": {
                    "fForm": {
                        "shared_options": self._format_shared_options(oContent),
                        "project_selection": self._format_project_select(fContent),
                    },
                    "oReport": self._format_user_content(oContent),
                    "overwrite_query_def_with_active": overwrite_query_def_with_active,
                },
            }
        else:
            context = {
                "fForm": fContent,
                "oReport": oContent,
                "overwrite_query_def_with_active": overwrite_query_def_with_active,
            }
            response = {
                "status": "incomplete",
                "title": "Edit Report",
                "html": render_to_string(
                    "chiron/reports/edit_report.html", context, request=request
                ),
                "onLoad": "attachReportFormEvents",
            }
        return Response(response)

    @action(detail=True, methods=["get", "post"])
    def share_form(self, request, pk, *args, **kwargs):
        oContent = get_object_or_404(self.get_queryset(), pk=pk)
        original_shared_users = list(oContent.share_with.values_list("pk", flat=True))
        fContent = ui_forms.ReportSharingForm(oContent.creator, instance=oContent)
        if request.method == "POST":
            share_with = {"share_with": request.data.get("share_with")}
            qDict = self._dict_to_querydict(share_with)
            fContent = ui_forms.ReportSharingForm(oContent.creator, qDict, instance=oContent)

            if fContent.is_valid():
                fContent.save()

                if chiron_settings.CHIRON_EMAIL_NOTIFICATIONS:
                    full_link = request.build_absolute_uri(
                        request.build_absolute_uri(f"/{request.dataset}/reports/{oContent.pk}/")
                    )
                    for chiron_user in fContent.cleaned_data["share_with"]:
                        if chiron_user.pk not in original_shared_users:
                            send_email_report_notification(chiron_user, oContent, full_link)

                response = {"status": "complete", "errors": [fContent.errors.as_text()]}
                return Response(response)
            else:
                return Response(
                    {"status": "Data not valid", "errors": [fContent.errors.as_text()]}
                )

        output_type = request.GET.get("output_type")
        # need to decouple orm logic from view
        if output_type == "json":
            # need to actually make new full url, get it in ui, this only works in local for now
            response = {
                "status": "incomplete",
                "title": "Share Report",
                "errors": [fContent.errors.as_text()],
                "data": {
                    "fForm": {
                        "shared_options": self._format_shared_options(oContent),
                    },
                    "oReport": self._format_user_content(oContent),
                    "full_url": request.build_absolute_uri(
                        reverse("chiron:report", args=(oContent.pk,))
                    ).replace("127.0.0.1:8000", "localhost:3000"),
                },
            }

        else:
            context = {
                "fForm": fContent,
                "oReport": oContent,
                "full_url": request.build_absolute_uri(
                    reverse("chiron:report", args=(oContent.pk,))
                ),
            }
            response = {
                "status": "incomplete",
                "title": "Share Report",
                "data": render_to_string(
                    "chiron/reports/share_report.html", context, request=request
                ),
            }
        return Response(response)

    @action(detail=True, methods=["get", "post"])
    def delete_form(self, request, pk, *args, **kwargs):
        oContent = get_object_or_404(self.get_queryset(), pk=pk)
        if request.method == "POST":
            oContent.delete()
            response = {"status": "complete", "errors": [""]}
            return Response(response)
        context = {"oReport": str(oContent)}
        response = {
            "status": "incomplete",
            "title": "Delete Report",
            "errors": [""],
            "data": context,
        }
        return Response(response)

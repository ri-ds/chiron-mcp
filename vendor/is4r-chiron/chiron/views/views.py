import datetime
from collections import OrderedDict

from django.contrib.auth.decorators import login_required
from django.contrib.humanize.templatetags.humanize import intcomma
from django.core.exceptions import PermissionDenied

# from bson.errors import InvalidId
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.template.loader import render_to_string

# from chiron.paginator import MongoPaginator
from chiron import chiron_settings, models
from chiron import query_definition as qdef
from chiron.authorization import (
    can_view_workspace,
    dataset_selector,
    get_request_chironuser,
    request_passes_test,
)
from chiron.models import SystemChironUser
from chiron.query_engine import get_querytool
from chiron.utilities import get_object_from_python_path


def get_summary_data(chironuser):
    response = OrderedDict()
    # get date of last import
    oLog = models.EtlLog.get_latest_record(chironuser.dataset)
    response["Date of last import"] = "Unknown"
    if oLog:
        response["Date of last import"] = oLog.start_date.strftime("%m/%d/%Y")
    # get total number of subjects in system (independent of user permissions)
    system_user = SystemChironUser(chironuser.dataset)
    querytool = get_querytool(system_user, cohort_def=[])
    subject_count = querytool.get_cohort_count()
    response["Total subjects in system"] = intcomma(subject_count)

    if models.PermissionGroup.dataset_uses_permission_groups(chironuser.dataset):
        # get number of subjects this user can see
        querytool = get_querytool(chironuser, cohort_def=[])
        subject_count = querytool.get_cohort_count()
        response["Subjects you can view"] = intcomma(subject_count)
        # get info about this user's permissions
        your_groups = chironuser.list_permission_groups(pretty=True)
        response["Your Permission Group(s)"] = your_groups

    response["Your Access Level"] = chironuser.get_access_level_display()
    return response


def get_data_summary_string(request):
    context = {
        "summary_data": get_summary_data(request.chironuser),
    }
    return render_to_string("chiron/snippets/data_summary.html", context)


@login_required
@dataset_selector
def home(request):
    data_summary_function_path = chiron_settings.CHIRON_DATA_SUMMARY_FUNCTION_PATH
    if request.dataset and request.dataset.override_data_summary_function_path:
        data_summary_function_path = request.dataset.override_data_summary_function_path
    data_summary_function = get_object_from_python_path(data_summary_function_path)
    try:
        summary_string = data_summary_function(request)
    except Exception as e:
        print("error generating data summary: {}".format(e))
        summary_string = (
            '<strong class="text-danger">There was an error generating the data summary.</strong>'
        )

    # need info to check if they can select other datasets
    qDataset = models.Dataset.objects.all()

    context = {
        "current_page": "home",
        "data_summary_string": summary_string,
        "qDataset": qDataset,
    }

    return render(request, "chiron/home.html", context)


@login_required
def select_dataset(request):
    if request.method == "POST":
        dataset_id = request.POST.get("dataset_id")
        oDataset = models.Dataset.objects.get(pk=dataset_id)
        request.session["dataset_id"] = dataset_id
        return redirect("chiron:workspace")
    qDataset = models.Dataset.objects.all()
    # check which datasets they can view
    for oDataset in qDataset:
        oChironUser = models.ChironUser.objects.filter(user=request.user, dataset=oDataset).first()
        if oChironUser or oDataset.autocreate_chiron_user:
            oDataset.selectable = True
        else:
            oDataset.selectable = False
    context = {"qDataset": qDataset}
    return render(request, "chiron/select_dataset.html", context)


@login_required
@dataset_selector
def reports(request):
    qReport = request.chironuser.get_viewable_reports()
    custom_report_categories = []
    qStarred = models.ContentFlag.objects.filter(
        chironuser=request.chironuser,
        flag_type=models.ContentFlag.FlagType.STAR,
    )
    count = qReport.filter(contentflag__in=qStarred).count()
    if count:
        custom_report_categories.append({"label": "Starred", "state": "starred", "count": count})
    custom_report_categories.append(
        {"label": "All Reports", "state": None, "count": qReport.count()}
    )
    count = qReport.filter(creator=request.chironuser).count()
    if count:
        custom_report_categories.append({"label": "My Reports", "state": "mine", "count": count})

    qProject = models.Project.objects.filter(dataset=request.dataset)
    for oProject in qProject:
        oProject.report_count = oProject.get_report_count(request.chironuser)
    context = {
        "current_page": "reports",
        "qProject": qProject,
        "custom_report_categories": custom_report_categories,
    }
    return render(request, "chiron/reports.html", context)


@login_required
def report(request, report_id):
    oContent = get_object_or_404(models.UserCreatedContent, pk=report_id)
    # find/create the chironuser for this report and set on the request
    oChironUser = get_request_chironuser(request, oContent.dataset)
    if oChironUser:
        request.chironuser = oChironUser
        request.dataset = oContent.dataset

    # if they're not allowed to view the report then you can finish
    if oContent not in request.chironuser.get_viewable_reports():
        raise PermissionDenied

    # go ahead and update their session dataset so that subsequent API requests will use the
    # correct dataset
    request.session["dataset_id"] = request.dataset.id

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
        table.table_def["sort"].insert(0, {"entry_id": sort_field, "direction": sort_direction})
        custom_sort_string = "&sort_field={}&sort_direction={}".format(sort_field, sort_direction)

    context = {
        "current_page": "reports",
        "oReport": oContent,
        "extended_cohort_def": cohort.extended_cohort_def,
        "cohort_description": qdef.describe_cohort_def(cohort.extended_cohort_def),
        "warnings": cohort.warnings,
        "errors": cohort.errors,
        "full_url": request.build_absolute_uri(reverse("chiron:report", args=(oContent.pk,))),
        "extended_table_def": table.extended_table_def,
        "td_warnings": table.warnings,
        "td_errors": table.errors,
        # "display_table": display_table,
        # "sort": table_def["sort"][0] if len(table_def["sort"]) > 0 else None,
        # "patient_count": patient_count,
        # "paginator": paginator,
        "custom_sort_string": custom_sort_string,
        "cohort_def_interactive": False,
        "page": page,
        "sort_field": sort_field,
        "sort_direction": sort_direction,
    }
    return render(request, "chiron/report.html", context)


@login_required
@dataset_selector
@request_passes_test(can_view_workspace, redirect_field_name=None)
def workspace(request):
    content_id = request.session.get("active_cohort_id")
    oContent = get_object_or_404(models.UserCreatedContent, pk=content_id) if content_id else None
    context = {
        "oContent": oContent,
        "data_view_mode": request.session.get("data_view_mode", "all"),
    }
    return render(request, "chiron/workspace.html", context)


def unix_time_millis(dt):
    epoch = datetime.datetime.fromtimestamp(0, datetime.UTC)
    return (dt - epoch).total_seconds() * 1000.0


def update_timeline_for_subdoc(chironuser, timeline, subdoc, oCollection, collection_index):
    if oCollection.permanent_id not in timeline:
        timeline[oCollection.permanent_id] = {}
    event_date = subdoc.get(oCollection.event_date_field.permanent_id, None)
    if event_date and event_date not in timeline[oCollection.permanent_id].keys():
        event_date_utc = int(unix_time_millis(event_date))
        # set event end date in utc millisecond format
        event_end_date_utc = event_date_utc + (1000 * 60 * 60 * 23)
        if oCollection.event_end_date_field:
            event_end_date = subdoc.get(oCollection.event_end_date_field.permanent_id, None)
            if event_end_date:
                event_end_date_utc = int(unix_time_millis(event_end_date)) + (1000 * 60 * 60 * 23)

        timeline[oCollection.permanent_id][event_date] = {
            "x": event_date_utc,
            "x2": event_end_date_utc,
            "y": collection_index,
            "collection_name": oCollection.name,
            "collection_name_plural": oCollection.get_name_plural(),
        }
        event_name = None
        if oCollection.event_name_field:
            display_processor = oCollection.event_name_field.get_display_processor(chironuser)
            event_name = display_processor.display_function(
                subdoc.get(oCollection.event_name_field.permanent_id, None), "json"
            )
            timeline[oCollection.permanent_id][event_date]["tooltip_data"] = {event_name: 1}
    elif event_date:
        event_name = None
        if oCollection.event_name_field:
            display_processor = oCollection.event_name_field.get_display_processor(chironuser)
            event_name = display_processor.display_function(
                subdoc.get(oCollection.event_name_field.permanent_id, None), "json"
            )
            if event_name in timeline[oCollection.permanent_id][event_date]["tooltip_data"]:
                timeline[oCollection.permanent_id][event_date]["tooltip_data"][event_name] += 1
            else:
                timeline[oCollection.permanent_id][event_date]["tooltip_data"][event_name] = 1

    return timeline


def process_timeline_for_highcharts(timeline):
    output = []
    for collection_id, entry_dict in timeline.items():
        for entry in entry_dict.values():
            tooltip_data = entry.get("tooltip_data", {})
            if len(tooltip_data) == 0:
                tooltip = "<strong>{}</strong> ".format(entry["collection_name"].title())
            elif len(tooltip_data) == 1 and list(tooltip_data.values()) == [1]:
                tooltip = "<strong>{}:</strong> ".format(entry["collection_name"].title())
            else:
                tooltip = "<strong>{}:</strong> ".format(entry["collection_name_plural"].title())
            event_name_list = []
            for event_name, count in tooltip_data.items():
                if count == 1:
                    event_name_list.append("{}".format(event_name))
                else:
                    event_name_list.append("{} ({})".format(event_name, count))
            event_name_list.sort()
            tooltip += "<br>" + "<br>".join(event_name_list)
            output.append(
                {
                    "x": entry["x"],
                    "x2": entry["x2"],
                    "y": entry["y"],
                    "tooltip": tooltip,
                    "color": "rgba(41, 171, 224, 0.3)",
                    "borderColor": "#325d88",
                }
            )
    return output

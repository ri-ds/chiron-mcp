import json

# import pprint

from django.shortcuts import render, redirect, reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Q
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404

from chiron.authorization import user_is_staff, dataset_selector
from chiron import helpers
from chiron import query_definition as qdef
from chiron import models
from chiron.data_dictionary.visualize_schema import VisSchema
from chiron.data_dictionary.validate import validate_data_dictionary


@login_required
@dataset_selector
@user_passes_test(user_is_staff, redirect_field_name=None)
def query_troubleshooting(request):
    """
    This is the landing page for a collection of query troubleshooting views. It shows the
    relevant active query definitions and the full data processing pipeline for several
    types of queries run on the site.
    """
    cd_validated = qdef.clean_active_cohort_def(request.chironuser, include_metadata=True)
    for key, value in cd_validated.items():
        json_val = helpers.make_json_encodable(value)
        cd_validated[key] = (json.dumps(json_val, indent=4),)
    td_validated = qdef.clean_active_table_def(request.chironuser, include_metadata=True)
    for key, value in td_validated.items():
        json_val = helpers.make_json_encodable(value)
        td_validated[key] = (json.dumps(json_val, indent=4),)
    ad_validated = qdef.clean_active_analysis_def(request.chironuser, include_metadata=True)
    for key, value in ad_validated.items():
        json_val = helpers.make_json_encodable(value)
        ad_validated[key] = (json.dumps(json_val, indent=4),)
    context = {
        "query_type": "",
        "cd_validated": cd_validated,
        "td_validated": td_validated,
        "ad_validated": ad_validated,
    }
    return render(request, "chiron/backend/query_troubleshooting.html", context)


@login_required
@dataset_selector
@user_passes_test(user_is_staff, redirect_field_name=None)
def view_schema(request):
    """ """
    selected_collections = []
    show_related = False
    if request.method == "POST":
        show_related = True if request.POST.get("show_related") else False
        selected_collections = list(request.POST.getlist("subcollections"))
    qCollection = request.dataset.subcollections()
    schema = VisSchema(request.dataset)
    for collection_id in selected_collections:
        schema.add_subcollection(collection_id, include_related=show_related)
    schema.add_all_missing_subrelationships()
    validation_errors = validate_data_dictionary(request.dataset)
    context = {
        "qCollection": qCollection,
        "selected_collections": selected_collections,
        "show_related": show_related,
        "diagram": schema.get_mermaid_diagram(),
        "validation_errors": validation_errors,
    }
    return render(request, "chiron/backend/view_schema.html", context)


@login_required
@dataset_selector
@user_passes_test(user_is_staff, redirect_field_name=None)
def etl_logs(request):
    """
    Each time the ETL process is run (`python manage.py chiron_run_etl`), log records are created
    and listed here. You can click on a log record to drill down to get more details.

    This is a great place to troubleshoot problems with how your data is loading.

    There are a couple customization options that will affect what information is collected
    during the etl:

    .. code-block:: bash

        # Don't track this ETL in the log
        python manage.py chiron_run_etl --no-log

        # Collects extensive information about how each record is loaded, allowing much more
        # detailed drill-down. On large systems, this shouldn't be set every time because it can
        # result in a large number of log records.
        python manage.py chiron_run_etl --track-subject-matching

    """
    qLog = models.EtlLog.objects.all()
    paginator = Paginator(qLog, 10)
    page_number = request.GET.get("page", 1)
    context = {"pLog": paginator.get_page(page_number)}
    return render(request, "chiron/backend/etl_logs.html", context)


@login_required
@dataset_selector
@user_passes_test(user_is_staff, redirect_field_name=None)
def etl_log_details(request, log_id):
    """The details view for an ETL run"""
    oLog = get_object_or_404(models.EtlLog, pk=log_id)
    context = {"oLog": oLog}
    return render(request, "chiron/backend/etl_log_details.html", context)


@login_required
@dataset_selector
@user_passes_test(user_is_staff, redirect_field_name=None)
def source_data_issues(request, source_log_id):
    """Info about an ETL run for a specific source"""
    oSourceLog = get_object_or_404(models.SourceEtlLog, pk=source_log_id)
    context = {
        "oLog": oSourceLog.etl_log,
        "oSourceLog": oSourceLog,
    }
    return render(request, "chiron/backend/source_data_issues.html", context)


@login_required
@dataset_selector
@user_passes_test(user_is_staff, redirect_field_name=None)
def source_record_subject_matching(request, source_log_id):
    """Info about an ETL run for a specific source"""
    oSourceLog = get_object_or_404(models.SourceEtlLog, pk=source_log_id)
    qRecordLog = oSourceLog.sourcerecordetllog_set.all()
    show_created = request.GET.get("created", None)
    if show_created == "yes":
        qRecordLog = qRecordLog.filter(subject_created=True)
    if show_created == "no":
        qRecordLog = qRecordLog.filter(subject_created=False)
    paginator = Paginator(qRecordLog, 100)
    page_number = request.GET.get("page", 1)
    context = {
        "oLog": oSourceLog.etl_log,
        "oSourceLog": oSourceLog,
        "pRecordLog": paginator.get_page(page_number),
    }
    return render(request, "chiron/backend/source_record_subject_matching.html", context)


@login_required
@dataset_selector
@user_passes_test(user_is_staff, redirect_field_name=None)
def record_logs_for_subject(request, log_id, subject_id):
    """Info about an ETL run for a specific subject"""
    oLog = get_object_or_404(models.EtlLog, pk=log_id)
    qRecordLog = models.SourceRecordEtlLog.objects.filter(
        source_log__etl_log=oLog, subject_id=subject_id
    )
    show_created = request.GET.get("created", None)
    if show_created == "yes":
        qRecordLog = qRecordLog.filter(subject_created=True)
    if show_created == "no":
        qRecordLog = qRecordLog.filter(subject_created=False)
    paginator = Paginator(qRecordLog, 100)
    page_number = request.GET.get("page", 1)
    context = {
        "oLog": oLog,
        "subject_id": subject_id,
        "pRecordLog": paginator.get_page(page_number),
    }
    return render(request, "chiron/backend/record_logs_for_subject.html", context)


@login_required
@dataset_selector
@user_passes_test(user_is_staff, redirect_field_name=None)
def data_dictionary(request):
    """Metadata about published concepts"""
    # TODO: This view is broken and is currently hidden in UI.
    qConcept = models.Concept.objects.filter(published=True).filter(
        Q(include_in_cohort_def=True) | Q(include_in_table_def=True)
    )
    # append summary statistics
    i = 1
    for oConcept in qConcept:
        oConcept.summary_statistics = oConcept.summarize(request.chironuser)
        oConcept.data_type = oConcept.get_data_type(request.chironuser)
        # print(i)
        i += 1
    context = {"qConcept": qConcept}
    return render(request, "chiron/backend/data_dictionary.html", context)


@login_required
@dataset_selector
def stop_viewing_as_user(request):
    """
    This view can't be limited to staff, because it needs to be accessible by the override user.
    """
    request.session["override_user_id"] = None
    return redirect(reverse("chiron:workspace"))


@login_required
@dataset_selector
@user_passes_test(user_is_staff, redirect_field_name=None)
def user_report(request):
    """
    An admin view that gives information about data access permissions and activity of each user.

    If the `ViewSiteAsOtherUser` middleware is installed, it will also allow you to temporarily
    log in as another user to test what the Chiron site looks like for them.
    """
    if request.method == "POST":
        override_user_id = int(request.POST.get("override_user_id", None))
        if override_user_id:
            request.session["override_user_id"] = int(override_user_id)
            return redirect(reverse("chiron:workspace"))
    qChironUser = models.ChironUser.objects.all().order_by("-user__last_login")
    context = {
        "qChironUser": qChironUser,
    }
    return render(request, "chiron/backend/user_report.html", context)

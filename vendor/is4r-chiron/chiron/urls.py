from django.urls import path, include

from .views import views
from .views import views_backend as vb
from .views import views_ajax_concepts as vc
from .views import views_ajax_table_def as vt

urlpatterns = [
    path(
        "ajax/set_data_view_mode",
        vc.ajax_set_data_view_mode,
        name="ajax_set_data_view_mode",
    ),
    path(
        "ajax/get_view_mode_selector",
        vc.ajax_view_mode_widget,
        name="ajax_view_mode_widget",
    ),
    path(
        "ajax/export_data/get_td_resort_form",
        vt.ajax_get_td_resort_form,
        name="ajax_get_td_resort_form",
    ),
    path(
        "ajax/export_data/get_add_id_field_form",
        vt.ajax_get_add_id_field_form,
        name="ajax_get_add_id_field_form",
    ),
    # path(
    #     "ajax/export_data/get_td_entry_form",
    #     vt.ajax_get_td_entry_form,
    #     name="ajax_get_td_entry_form",
    # ),
    path("workspace", views.workspace, name="workspace"),
    path("backend/data_dictionary", vb.data_dictionary, name="data_dictionary"),
    path("backend/etl_logs/<int:log_id>", vb.etl_log_details, name="etl_log_details"),
    path("backend/etl_logs", vb.etl_logs, name="etl_logs"),
    path(
        "backend/source_logs/<int:source_log_id>/data_issues",
        vb.source_data_issues,
        name="source_data_issues",
    ),
    path(
        "backend/source_logs/<int:source_log_id>/subject_matching",
        vb.source_record_subject_matching,
        name="source_record_subject_matching",
    ),
    path(
        "backend/etl_logs/<int:log_id>/subject/<str:subject_id>",
        vb.record_logs_for_subject,
        name="record_logs_for_subject",
    ),
    path(
        "backend/query_troubleshooting",
        vb.query_troubleshooting,
        name="query_troubleshooting",
    ),
    # path(
    #     "backend/query_troubleshooting/results_table",
    #     vb.query_troubleshooting_results_table,
    #     name="query_troubleshooting_results_table",
    # ),
    # path(
    #     "backend/query_troubleshooting/cohort_count",
    #     vb.query_troubleshooting_cohort_count,
    #     name="query_troubleshooting_cohort_count",
    # ),
    # path(
    #     "backend/query_troubleshooting/analysis_output",
    #     vb.query_troubleshooting_analysis_output,
    #     name="query_troubleshooting_analysis_output",
    # ),
    path(
        "backend/user_report",
        vb.user_report,
        name="user_report",
    ),
    path(
        "backend/stop_viewing_as_user",
        vb.stop_viewing_as_user,
        name="stop_viewing_as_user",
    ),
    path(
        "backend/view_schema",
        vb.view_schema,
        name="view_schema",
    ),
    path("report/<int:report_id>", views.report, name="report"),
    path("reports", views.reports, name="reports"),
    # path(
    #     "single_subject_timeline",
    #     views.single_subject_timeline,
    #     name="single_subject_timeline",
    # ),
    # path(
    #     "single_subject/<str:collection_name>",
    #     views.single_subject,
    #     name="single_subject",
    # ),
    # path("single_subject", views.single_subject, name="single_subject"),
    path("api/", include("chiron.api.urls", "api")),
    path("api/v2/", include("chiron.api_v2.urls", "apiv2")),
    path("select_dataset", views.select_dataset, name="select_dataset"),
    path("", views.home, name="home"),
]

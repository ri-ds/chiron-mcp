import csv
from datetime import datetime
import time

from django.http import HttpResponse
from django.core.exceptions import PermissionDenied

from chiron import chiron_settings, helpers
from chiron import query_definition as qdef
from chiron.query_engine import get_querytool
from chiron.paginator import ReportPaginator


def get_paginated_preview(cohort_def, table_def, chironuser, query_params):
    response = {}
    page_number = int(query_params.get("page", 1))
    records_per_page = int(query_params.get("records_per_page", 10))
    output_type = query_params.get("output_type", "json")
    cohort = qdef.Cohort(chironuser, cohort_def)
    table = qdef.Table(chironuser, cohort_def, table_def)
    paginator = ReportPaginator(records_per_page, page_number)
    paginator.set_collection_count(0)
    response["warnings"] = cohort.warnings + table.warnings
    response["errors"] = cohort.errors + table.errors
    # if there are any errors with the cohort def, the preview can't be generated
    if response["errors"]:
        response["extended_table_def"] = table.extended_table_def
        response["preview_failed"] = True
    else:
        # generate the dataset
        start_time = time.time()
        querytool = get_querytool(chironuser, cohort.cohort_def, table.table_def)
        cohort, subject_count, collection_count = querytool.get_report_preview(
            skip=paginator.get_skip_value(), output_type=output_type, limit=paginator.limit
        )
        helpers.print_query_info("new method seconds", time.time() - start_time)
        paginator.set_collection_count(collection_count)
        response["record_count"] = paginator.collection_count
        response["subject_count"] = subject_count
        response["paginator"] = paginator.json()
        response["extended_table_def"] = table.extended_table_def
        response["data"] = cohort
        if chiron_settings.CHIRON_GET_QUERY_PERFORMANCE:
            response["perf"] = querytool.time_analysis
            response["cache_mode"] = querytool.cache_mode
    return response


def get_paginated_preview_metadata(cohort_def, table_def, chironuser, query_params):
    """
    Similar to get_paginated_preview but returns only metadata about a preview,
    not the actual data, so on slow queries it will run much faster.
    """
    response = {}
    cohort = qdef.Cohort(chironuser, cohort_def)
    table = qdef.Table(chironuser, cohort_def, table_def)
    response["warnings"] = cohort.warnings + table.warnings
    response["errors"] = cohort.errors + table.errors
    response["extended_table_def"] = table.extended_table_def
    # if there are any errors with the cohort def, the preview can't be generated
    if response["errors"]:
        response["preview_failed"] = True
    else:
        response["pipeline"] = "no longer using mongo to generate report"
    return response


def generate_cohort_csv(cohort_def, table_def, chironuser, file_name=None):
    """Generate Cohort CSV

    Generate CSV from a given Cohort definition.

    TODO: Update these parameters after implementation.
    :param cohort_def: Cohort Def
    :type cohort_def: str
    :param table_def: Table Def
    :type table_def: str
    :param request: Django HTTP Request
    :type request: class: django.http.request.HttpRequest
    :return:
    :rtype:
    """
    # TODO: Troubleshoot this function (copied from chiron/views/view_exports.py)
    cohort = qdef.Cohort(chironuser, cohort_def)
    if cohort.errors:
        raise PermissionDenied("This dataset can't be exported until errors are resolved.")
    table = qdef.Table(chironuser, cohort_def, table_def)
    if not file_name:
        file_name = "results" + datetime.now().strftime("_%Y-%m-%d")
    querytool = get_querytool(chironuser, cohort.cohort_def, table.table_def)
    dataset = querytool.get_full_report(output_type="csv")
    header_names = []
    for entry in table.extended_table_def.get("fields"):
        if not entry.get("has_errors", False):
            header_name = entry.get("alias")
            if not header_name:
                header_name = entry["label"]
            header_names.append(header_name)
    table_name = "results"
    table_name += datetime.now().strftime("_%Y-%m-%d")
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="{}.csv"'.format(file_name)
    writer = csv.writer(response)
    writer.writerow(header_names)
    for row in dataset:
        writer.writerow(row)
    return response


def generate_pivottable_csv(cohort_def, analysis_def, chironuser, file_name=None):
    """Generate Cohort CSV

    Generate CSV from a given Cohort definition.

    TODO: Update these parameters after implementation.
    :param cohort_def: Cohort Def
    :type cohort_def: str
    :param table_def: Table Def
    :type table_def: str
    :param request: Django HTTP Request
    :type request: class: django.http.request.HttpRequest
    :return:
    :rtype:
    """
    # TODO: Troubleshoot this function (copied from chiron/views/view_exports.py)
    cd_validate = qdef.clean_cohort_def(cohort_def, chironuser, include_metadata=True)
    if cd_validate["errors"]:
        raise PermissionDenied("This dataset can't be exported until errors are resolved.")
    if not file_name:
        file_name = "results" + datetime.now().strftime("_%Y-%m-%d")
    querytool = get_querytool(chironuser, cd_validate["cohort_def"])
    analysis = qdef.Analysis(chironuser, analysis_def)
    dataset = querytool.run_analysis(analysis).to_csv()
    table_name = "results"
    table_name += datetime.now().strftime("_%Y-%m-%d")
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="{}.csv"'.format(file_name)
    # TODO: find a more efficient way to write csv string "dataset" to csv file
    writer = csv.writer(response)
    for row in dataset.split("\n"):
        row_list = row.split(",")
        writer.writerow(row_list)
    return response


def generate_cohort_json(cohort_def, table_def, chironuser, output_type):
    cohort = qdef.Cohort(chironuser, cohort_def)
    if cohort.errors:
        raise PermissionDenied("This dataset can't be exported until errors are resolved.")
    table = qdef.Table(chironuser, cohort_def, table_def)

    # create header row
    header_names = []
    for entry in table.extended_table_def.get("fields"):
        if not entry.get("has_errors", False):
            header_name = entry.get("alias")
            if not header_name:
                header_name = entry["label"]
            header_names.append(header_name)
    querytool = get_querytool(chironuser, cohort.cohort_def, table.table_def)
    data = querytool.get_full_report(output_type=output_type)
    response = {
        "header": header_names,
        "records": data,
    }

    if chiron_settings.CHIRON_GET_QUERY_PERFORMANCE:
        response["perf"] = querytool.time_analysis
        response["cache_mode"] = querytool.cache_mode

    return response

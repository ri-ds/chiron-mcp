from datetime import datetime

from django.core.management.base import BaseCommand

from chiron import models
from chiron.helpers import dataset_command_line_selection
from chiron.api.utils.export import get_paginated_preview


class Command(BaseCommand):
    """Verifies that all saved reports are working and returning data.

    Results of check will be printed to stdout.
    """

    help = "Verifies that all saved reports are working and returning data."

    def print_out(self, *args):
        """A wrapper for self.stdout.write() that converts anything into a string"""
        strings = []
        for arg in args:
            strings.append(str(arg))
        self.stdout.write(",".join(strings))

    def print_err(self, *args):
        """A wrapper for self.stderr.write() that converts anything into a string"""
        strings = []
        for arg in args:
            strings.append(str(arg))
        self.stderr.write(",".join(strings))

    def add_arguments(self, parser):
        parser.add_argument(
            "dataset_id",
            nargs="?",
            default="no_selection",
            help="The dataset id, or 'all' to run all, or leave blank to select from a list",
        )

    def handle(self, *args, **options):
        # determine the dataset to check
        qDataset = models.Dataset.objects.all()
        dataset_id = options["dataset_id"]
        dataset_id = dataset_command_line_selection(qDataset, dataset_id, allow_all=True)
        if dataset_id == "all":
            qDataset = models.Dataset.objects.all()
        else:
            qDataset = models.Dataset.objects.filter(pk=dataset_id)

        # to save time, we will just get the first 10 records from each report
        params = {"page": 1, "records_per_page": 10, "output_type": "json"}

        # run reports
        report_analysis = []
        for oDataset in qDataset:
            qReport = models.UserCreatedContent.objects.filter(dataset=oDataset)
            for oReport in qReport:
                start_time = datetime.now()
                chironuser = oReport.creator
                input_cohort_def = oReport.get_def_value("cohort_def")
                input_table_def = oReport.get_def_value("table_def")

                response = get_paginated_preview(
                    input_cohort_def, input_table_def, chironuser, params
                )
                end_time = datetime.now()
                print(oReport.id, oReport, "time to get preview:", end_time - start_time)
                preview_failed = response.get("preview_failed", False)
                if preview_failed:
                    warnings = response.get("warnings", [])
                    errors = response.get("errors", [])
                else:
                    errors = response.get("errors", [])  # I think this should always be empty
                    warnings = response.get("warnings", [])
                    if response["record_count"] == 0:
                        warnings.append("zero records were returned")
                if warnings or errors or preview_failed:
                    report_analysis.append(
                        {
                            "report_id": oReport.id,
                            "report": str(oReport),
                            "preview_failed": preview_failed,
                            "warnings": warnings,
                            "errors": errors,
                        }
                    )

        for entry in report_analysis:
            report_str = f'{entry["report_id"]} "{entry["report"]}"'
            if entry["preview_failed"]:
                self.print_out(f"report {report_str} failed to run:")
            else:
                self.print_out(f"report {report_str} ran successfully but had warnings:")
            for error in entry["errors"]:
                print(f"  -  ERROR: {error}")
            for warning in entry["warnings"]:
                print(f"  -  WARNING: {warning}")

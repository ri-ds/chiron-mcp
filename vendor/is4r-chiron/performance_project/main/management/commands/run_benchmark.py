import sys
import json
from typing import OrderedDict
import requests

from django.core.management.base import BaseCommand, CommandParser
from chiron import chiron_settings

from chiron.models import UserCreatedContent

PRINT_FMT = "{:<50} {:<25} {:<25} {:<25}"


class Command(BaseCommand):
    help = "Benchmarks Chiron for testing purposes"
    iterations = 1
    session = None
    prefix = ""
    user = None
    patient_ids = []
    debug = False

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("endpoint", type=str, help="The base endpoint to point towards")
        parser.add_argument("-i", type=int, help="Number of iterations for timing")
        parser.add_argument(
            "--format",
            type=str,
            help="Output results in specific format (json, csv, table)",
        )

    def _login(self, user="admin"):
        """
        Standard Django login
        TODO: might want to support more login options or have performance tests run from the
          Chiron admin views within the website.
        """
        self.session = requests.Session()
        csrf_req = self.session.get(f"{self.prefix}/accounts/login/")
        token = csrf_req.cookies["csrftoken"]
        response = self.session.post(
            f"{self.prefix}/accounts/login/",
            data={"csrfmiddlewaretoken": token, "username": user, "password": "demo1234"},
            cookies=csrf_req.cookies,
        )
        self.cookies = response.cookies

    def handle(self, *args, **options):
        self.prefix = options.get("endpoint")
        self.iterations = 1 if not options.get("i") else options.get("i")
        self.results = {}
        self._login("admin")
        self.session.headers.update({"Content-Type": "application/json"})
        print("Running Benchmarks:", file=sys.stderr)
        use_caches = "Yes" if chiron_settings.CHIRON_USE_CACHES else "No"
        performance_logging = "Yes" if chiron_settings.CHIRON_GET_QUERY_PERFORMANCE else "No"
        print(f"  Using caching: {use_caches}", file=sys.stderr)
        print(f"  Using performance logging: {performance_logging}", file=sys.stderr)
        self.results["whoami"] = self.time_request("GET", "/api/me/")
        self.time_concept_stats()
        self.time_reports()
        print("Done.", file=sys.stderr)

        self._format_output(options.get("format"))

    def time_concept_stats(self):
        """
        Times getting statistics on specific concepts
        """
        concept_stats = {
            "stat text": "med_order_id",
            "stat date": "med_start",
            "stat boolean": "currently_taking",
            "stat float": "med_dose",
            "stat category": "med_units",
        }
        for test_name, concept_id in concept_stats.items():
            print(f"  Running statistics on {concept_id} ({test_name})", file=sys.stderr)
            self.results[test_name] = self.time_request(
                "GET", f"/api/concepts/{concept_id}/cohort_def_callback/"
            )

    def time_reports(self):
        """
        Runs saved reports in performance_project.
        """
        report_groups_to_run = ["Group A", "Group B", "Group C", "Group D"]
        # some reports are too slow, ignoring for now, can hopefully incorporate in the future
        # with improvements to the query engine
        ignore_report_ids = [19, 16, 15]
        for group_name in report_groups_to_run:
            qReport = UserCreatedContent.objects.filter(
                project__name__startswith=group_name
            ).exclude(id__in=ignore_report_ids)
            for oReport in qReport:
                print(f"  Timing report preview {oReport.name}", file=sys.stderr)
                self.results[f"{oReport.name.replace(',', ';')} (preview)"] = self.time_request(
                    "GET", f"/api/report_tools/{oReport.id}/preview/"
                )
                if self.debug:
                    print(
                        json.dumps(
                            self.results[f"{oReport.name.replace(',', ';')} (preview)"], indent=2
                        ),
                        file=sys.stderr,
                    )
                print(f"  Timing report export (json) {oReport.name}", file=sys.stderr)
                self.results[f"{oReport.name.replace(',', ';')} (json)"] = self.time_request(
                    "GET", f"/api/report_tools/{oReport.id}/export_json/"
                )
                if self.debug:
                    print(
                        json.dumps(
                            self.results[f"{oReport.name.replace(',', ';')} (json)"], indent=2
                        ),
                        file=sys.stderr,
                    )

    def time_request(self, method, url, data=None):
        final_url = f"{self.prefix}{url}"
        total = 0
        min = 99
        max = 0
        stages = OrderedDict()
        for i in range(self.iterations):
            response = self.session.request(method, final_url, data=data, cookies=self.cookies)
            if response.status_code >= 400:
                return str(response.content).split("\\n")

            data = response.json()
            if data.get("perf"):
                perf = response.json().get("perf")
                for key in perf.keys():
                    if not stages.get(key):
                        stages[key] = {"avg": 0.0, "min": 99.0, "max": 0.0, "total": 0.0}

                    perf_value = float(perf[key].replace(" seconds", ""))
                    if perf_value < stages[key]["min"]:
                        stages[key]["min"] = perf_value

                    if perf_value > stages[key]["max"]:
                        stages[key]["max"] = perf_value

                    stages[key]["total"] += perf_value
                    stages[key]["avg"] = stages[key]["total"] / (i + 1)

            time = response.elapsed.total_seconds()
            total += time

            if time < min:
                min = time

            if time > max:
                max = time

        return {
            "avg": total / (i + 1),
            "max": max,
            "min": min,
        } | stages

    def _format_output(self, format=None):
        if format == "json":
            print(json.dumps(self.results, indent=4))
            return

        headers = ["name", "avg", "max", "min"]
        added_subkeys = ["name", "avg", "max", "min"]

        # fetch all possible headers for data
        for key in self.results.keys():
            for subkey in self.results.get(key).keys():
                if subkey not in added_subkeys:
                    headers.append(f"{subkey}_avg")
                    headers.append(f"{subkey}_max")
                    headers.append(f"{subkey}_min")
                    added_subkeys.append(subkey)

        print(",".join(headers))
        for key in self.results.keys():
            data = [
                key,
                str(self.results.get(key).get("avg")),
                str(self.results.get(key).get("max")),
                str(self.results.get(key).get("min")),
            ]

            for header in headers[4:]:
                parts = header.split("_")
                header_key = "_".join(parts[:-1])
                header_value_key = parts[-1]
                if self.results.get(key).get(header_key):
                    data.append(str(self.results.get(key).get(header_key).get(header_value_key)))
                else:
                    data.append("N/A")

            print(",".join(data))

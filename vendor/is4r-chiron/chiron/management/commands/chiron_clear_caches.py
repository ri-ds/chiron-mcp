import sys
from django.core.management.base import BaseCommand

from chiron.models import Dataset
from chiron.helpers import dataset_command_line_selection
from chiron.cache.cache_utils import clear_cached_data
from chiron import chiron_settings


class Command(BaseCommand):
    """
    Clears both caches of subject data (CachedConceptStats and CachedCohort). Will prompt for
    a dataset or select "all" to clear caches for all datasets.

    NOTE: These caches are already cleared for a dataset every time chiron_run_etl is executed.
    """

    help = "Clears all caches of calculated patient data."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def print_out(self, *args, **kwargs):
        """A wrapper for self.stdout.write() that converts anything into a string"""
        strings = []
        for arg in args:
            strings.append(str(arg))
        output = ",".join(strings)
        self.stdout.write(output)

    def print_err(self, *args, **kwargs):
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
            help="The dataset_id, or leave blank to select from a list",
        )
        parser.add_argument("-s", "--source")

    def handle(self, *args, **options):
        qDataset = Dataset.objects.all()
        dataset_id = options["dataset_id"]
        dataset_id = dataset_command_line_selection(qDataset, dataset_id, allow_all=True)
        if dataset_id == "all":
            oDataset = None
        else:
            oDataset = Dataset.objects.get(pk=dataset_id)

        if not chiron_settings.CHIRON_USE_CACHES:
            self.print_out(
                "WARNING: CHIRON_USE_CACHES is currently set to False for this project. "
                "No cached data will be cleared."
            )
            sys.exit(0)

        clear_cached_data(oDataset)
        self.print_out("Cached data has been cleared.")

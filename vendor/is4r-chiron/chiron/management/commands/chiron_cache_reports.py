from django.core.management.base import BaseCommand  # CommandError

from chiron.models import Dataset
from chiron.helpers import dataset_command_line_selection
from chiron.cache.cache_utils import cache_reports
from chiron import chiron_settings


class Command(BaseCommand):
    """
    Creates cache entries in CachedCohort for every saved report.

    When using permission groups - If the report is not shared or shared with everyone, will
    create a cache entry specific to the permission group settings of the owner. If the report is
    shared with specific users, will create caches for any permission group settings for
    those users as well.
    """

    help = "Updates caches using existing data."

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

    def handle(self, *args, **options):
        qDataset = Dataset.objects.all()
        dataset_id = options["dataset_id"]
        dataset_id = dataset_command_line_selection(qDataset, dataset_id, allow_all=True)
        if dataset_id == "all":
            oDataset = None
        else:
            oDataset = Dataset.objects.get(pk=dataset_id)

        if not chiron_settings.CHIRON_USE_CACHES:
            self.print_err("ERROR: CHIRON_USE_CACHES is currently set to False for this project.")
            self.print_err("This setting must be set to True before caches can be updated.")
            self.print_err("No action was taken.")
            return
        cache_reports(oDataset)
        self.print_out("Caches have been updated.")

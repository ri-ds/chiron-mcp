from django.core.management.base import BaseCommand  # CommandError

from chiron.models import Dataset
from chiron.helpers import dataset_command_line_selection, get_all_collections_from_source_name
from chiron.cache.cache_utils import cache_concepts
from chiron import chiron_settings


class Command(BaseCommand):
    """
    Loops through all of the current published concepts and caches the stats for an empty cohort
    def.

    If using permission groups, will create concept cache entries for every
    combination of permission groups that actually exists for at least one ChironUser. Does not
    do permission group combos that don't currently exist for any users (which would require 2^n
    cache entries where n = count of permission groups)
    """

    help = "Primes the cache for all of the published concepts."

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
            self.print_err("ERROR: CHIRON_USE_CACHES is currently set to False for this project.")
            self.print_err("This setting must be set to True before caches can be updated.")
            self.print_err("No action was taken.")
            return

        self.print_out("Starting to cache all published concepts.")
        collections = get_all_collections_from_source_name(oDataset, options.get("source"))
        cache_concepts(oDataset, collections)
        self.print_out("All published concepts have been cached.")

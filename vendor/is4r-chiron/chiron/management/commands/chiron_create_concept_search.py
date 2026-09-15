from django.core.management.base import BaseCommand  # CommandError

from chiron.etl import ChironEtl
from chiron.models import Dataset
from chiron.helpers import dataset_command_line_selection


class Command(BaseCommand):
    """
    Creates the collection used to search for concepts by keywords for a dataset. If there are
    multiple datasets, will prompt you to select a dataset.

    This action is also run as a part of `chiron_run_etl`.
    """

    help = "Creates the collection used to search for concepts by keywords."

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
        dataset_id = dataset_command_line_selection(qDataset, dataset_id, allow_all=False)

        # Recreate the concept search collection
        # Does not use the staging schema
        etl = ChironEtl(dataset_id, use_staging=False)
        etl.create_concept_search_collection()
        self.print_out("Concept search has been created.")

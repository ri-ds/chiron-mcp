from django.core.management.base import BaseCommand  # CommandError

from chiron.etl import ChironEtl
from chiron.models import Dataset
from chiron.helpers import dataset_command_line_selection


class Command(BaseCommand):
    """
    Copies permission groups to subcollections for a dataset. If there are multiple
    datasets, will prompt you to select a dataset.

    This action is also run as a part of `chiron_run_etl`.
    """

    help = "Copies permission groups to subcollections"

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

        etl = ChironEtl(dataset_id)
        etl.use_staging = False
        etl.finalize_data()
        self.print_out("Permission groups copied.")

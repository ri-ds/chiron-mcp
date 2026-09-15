from django.core.management.base import BaseCommand

from chiron.etl import ChironEtl
from chiron.helpers import dataset_command_line_selection
from chiron.models import Dataset


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "dataset_id",
            nargs="?",
            default="no_selection",
            help="The dataset_id, or 'all' to run all, or leave blank to select from a list",
        )

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

    def handle(self, *args, **options):
        qDataset = Dataset.objects.all()
        dataset_id = options["dataset_id"]
        dataset_id = dataset_command_line_selection(qDataset, dataset_id, allow_all=True)
        self.print_out("chiron run etl")

        if dataset_id != "all":
            oDataset = Dataset.objects.get(id=dataset_id)
            qDataset = [oDataset]

        for oDataset in qDataset:
            etl = ChironEtl(oDataset.id, use_staging=False)
            etl.create_indexes()

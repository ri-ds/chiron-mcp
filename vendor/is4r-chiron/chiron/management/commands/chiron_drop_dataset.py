from django.core.management.base import BaseCommand  # CommandError

from chiron.helpers import dataset_command_line_selection
from chiron import models
from chiron.data_dictionary.drop_dataset import drop_dataset


class Command(BaseCommand):
    """
    Drops a single dataset and all related data from the data dictionary. The easiest way to use
    is to run with no arguments and select the dataset when prompted.
    """

    help = "Drops a single dataset and all related data from the data dictionary."

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
            help="The dataset (either Dataset.id integer or Dataset.unique_id slug), or 'all' "
            "to run all, or leave blank to select from a list",
        )

    def handle(self, *args, **options):
        qDataset = models.Dataset.objects.all()
        if qDataset.count() < 2:
            self.print_out("You can only use this command on systems with multiple datasets.")
            self.print_out("No changes were made")
            return
        dataset_id = options["dataset_id"]
        dataset_id = dataset_command_line_selection(qDataset, dataset_id, allow_all=False)
        oDataset = models.Dataset.objects.get(id=dataset_id)
        dataset_unique_id = oDataset.unique_id
        self.print_out(f"dropping the selected dataset '{dataset_unique_id}'")

        drop_dataset(oDataset)

        self.print_out(
            f"The dataset '{dataset_unique_id}' has been removed from the data dictionary"
        )

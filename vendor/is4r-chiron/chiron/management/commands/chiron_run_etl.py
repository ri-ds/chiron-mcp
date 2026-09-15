from django.core.management.base import BaseCommand  # CommandError

from chiron.etl import ChironEtl
from chiron.helpers import dataset_command_line_selection
from chiron.models import Dataset, Source
from chiron.data_dictionary.validate import validate_data_dictionary


class Command(BaseCommand):
    """
    Full truncate and reload of a dataset from sources. If there are multiple
    datasets, will prompt you to select a dataset.

    You can run a single source but it doesn't work correctly in all situations, so not
    appropriate for production:

    .. code-block:: bash

        python manage.py chiron_run_etl --source=[source name]

    :--no-log:                  default=False, don't add record of this to EtlLog table
    :--abbreviated:             default=False, run subset of the ETL, see chiron settings for
      configuration options
    :--source:                  default=None, run only a single source, see chiron settings for
      configuration options
    :--track-subject-matching:  default=False, Print and log detailed info about how subjects were
      matched for each record.
    """

    help = "Uses the Chiron data dictionary to populate a research data database."

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
            help="The dataset_id, or 'all' to run all, or leave blank to select from a list",
        )
        parser.add_argument("-s", "--source")
        parser.add_argument(
            "--force",
            action="store_true",
            help="When using --source this will force apply the loading of data",
        )
        parser.add_argument(
            "--no-log",
            action="store_true",
            help="Don't create a log entry in EtlLog database table.",
        )
        parser.add_argument(
            "--track-subject-matching",
            action="store_true",
            help="Print and log detailed info about how subjects were matched for each record.",
        )
        parser.add_argument(
            "--abbreviated",
            action="store_true",
            help="Only load a subset of the data in the ETL run.",
        )
        parser.add_argument(
            "--ignore-validation-errors",
            action="store_true",
            help="If the system finds a problem with your data dict setup, run anyway.",
        )

    def handle(self, *args, **options):
        qDataset = Dataset.objects.all()
        dataset_id = options["dataset_id"]
        dataset_id = dataset_command_line_selection(qDataset, dataset_id, allow_all=True)
        self.print_out("chiron run etl")
        create_log = False if options["no_log"] else True
        notification_count = 1000
        track_subject_matching = True if options["track_subject_matching"] else False
        source = options.get("source")
        force = options.get("force", False)
        abbreviated = True if options["abbreviated"] else False
        ignore_validation_errors = True if options["ignore_validation_errors"] else False

        if dataset_id != "all":
            oDataset = Dataset.objects.get(id=dataset_id)
            qDataset = [oDataset]

        has_source_name_error = False
        if source:
            source_count = Source.objects.filter(name=source).count()
            if source_count > 1:
                print("The source name {} is associated with more than one source.".format(source))
                has_source_name_error = True
            elif source_count == 0:
                print("The source name {} doesn't exist.".format(source))
                has_source_name_error = True
            elif dataset_id == "all":
                print("Please select the appropriate dataset for source {}.".format(source))
                print("It's used to verify that you are using the intended source.")
                has_source_name_error = True

            # need to check if the dataset contains the provided soruce
            source_obj = Source.objects.get(name=source)
            if source_obj.collection.dataset.id != int(dataset_id):
                print(
                    "The source {} is in dataset {} ({}), not dataset {}.".format(
                        source,
                        source_obj.collection.dataset.id,
                        source_obj.collection.dataset.display_name,
                        dataset_id,
                    )
                )
                has_source_name_error = True
        if has_source_name_error:
            print("Nothing was run.")
            return

        for oDataset in qDataset:
            validation_errors = validate_data_dictionary(oDataset)
            if validation_errors:
                for message in validation_errors:
                    print("validation error: ", message)
                if not ignore_validation_errors:
                    print("ETL was not run because of data dictionary validation errors.")
                    print("To run anyway, rerun with argument --ignore-validation-errors")
                    return

        for oDataset in qDataset:
            etl = ChironEtl(
                oDataset.id,
                notification_count,
                create_log,
                source,
                track_subject_matching,
                abbreviated,
                force_single_source=force,
            )
            etl.run()

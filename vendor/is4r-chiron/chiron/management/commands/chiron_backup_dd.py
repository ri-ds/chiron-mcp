from django.core.management.base import BaseCommand
from django.core.management import call_command

from chiron.helpers import prepare_backup_file_path


class Command(BaseCommand):
    """
    Backs up the chiron data dictionary to the directory specified in
    `chiron_settings.CHIRON_DATA_DICT_BACKUP_DIR` with name full_dd_backup.json.

    PermissionGroups are included in the backup, but User and ChironUser (user permission
    settings) models are not. Log and cache models are also not backed up.
    """

    help = "Backs up the chiron data dictionary."

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
            "--backup-dir",
            # default="no_selection",
            help="Specify the dir loc of your `full_dd.json` file if different from "
            "settings.CHIRON_DATA_DICT_BACKUP_DIR",
        )

    def handle(self, *args, **options):
        # prepare filepath
        filename = "full_dd.json"
        filepath, file_exists = prepare_backup_file_path(filename, options.get("backup_dir"))

        # create a backup of all Collection, Category, Concept, Source,
        # AutocreatedFields
        call_command(
            "dumpdata",
            "chiron.Dataset",
            "chiron.PermissionGroup",
            "chiron.DefaultPermissionGroup",
            "chiron.Processor",
            "chiron.ConceptHandler",
            "chiron.Collection",
            "chiron.CollectionRelationship",
            "chiron.Source",
            "chiron.Category",
            "chiron.Concept",
            "chiron.DefaultTableDefConcept",
            "chiron.ConceptHandlerArg",
            "chiron.SourceProcessorArg",
            "chiron.SourceSourceDependency",
            "chiron.ConceptConceptDependency",
            "chiron.ConceptSourceDependency",
            "chiron.AutocreatedField",
            indent=4,
            output=filepath,
        )
        self.print_out(f"Your backup has been saved to `{filepath}`")

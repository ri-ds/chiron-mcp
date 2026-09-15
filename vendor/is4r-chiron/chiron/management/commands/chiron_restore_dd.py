from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import transaction

from chiron import models
from chiron.data_dictionary.preserve_permission_groups import PreservePermissionGroups
from chiron.helpers import prepare_backup_file_path


class Command(BaseCommand):
    """
    Truncates and reloads a data dictionary fixture that was backed up using the `chiron_backup_dd`
    command. It will look for the fixture named `full_dd.json` in
    `chiron_settings.CHIRON_DATA_DICT_BACKUP_DIR` (default is `chiron_config/backups`).

    Links between ChironUser and PermissionGroup will be preserved as long the updated data
    dictionary contains a permission group with the same name.
    """

    help = "Reloads the data dictionary from a Django fixture"

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
            help="Specify the dir loc of your file if different from "
            "settings.CHIRON_DATA_DICT_BACKUP_DIR",
        )

    def handle(self, *args, **options):
        filepath, file_exists = prepare_backup_file_path("full_dd.json", options.get("backup_dir"))

        # need to save and later restore fk links between ChironUser and PermissionGroup
        preserve_pg = PreservePermissionGroups()
        preserve_pg.backup_to_memory()

        with transaction.atomic():
            # clear out the existing data dict
            models.DefaultPermissionGroup.objects.all().delete()
            models.DefaultTableDefConcept.objects.all().delete()
            models.PermissionGroup.objects.all().delete()
            models.AutocreatedField.objects.all().delete()
            models.CollectionRelationship.objects.all().delete()
            models.SourceSourceDependency.objects.all().delete()
            models.ConceptConceptDependency.objects.all().delete()
            models.ConceptSourceDependency.objects.all().delete()
            models.Concept.objects.all().delete()
            models.Category.objects.all().delete()
            models.Source.objects.all().delete()
            models.Collection.objects.all().delete()
            models.SourceProcessorArg.objects.all().delete()
            models.ConceptHandlerArg.objects.all().delete()
            models.Processor.objects.all().delete()
            models.ConceptHandler.objects.all().delete()
            call_command(
                "loaddata",
                filepath,
            )

            # recreate links between chironuser and permission groups
            if preserve_pg.permission_groups_found():
                preserve_pg.restore_to_database()

            # in case the data dict has changed significantly, get rid of snapshots in order to
            # reduce risk of broken references
            models.CohortDefSnapshot.objects.all().delete()
            models.TableDefSnapshot.objects.all().delete()
            models.AnalysisDefSnapshot.objects.all().delete()
        self.print_out("Process complete.")

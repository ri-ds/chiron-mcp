from django.core.management.base import BaseCommand
from django.core.management import call_command
from main.utils import setup_default_chironuser_permission_groups
from django.conf import settings

import os


class Command(BaseCommand):
    # provide some help text
    help = "Sets/Resets demo database with data dictionary and two users."

    # add optional command line arguments
    def add_arguments(self, parser):
        pass

    # this will be executed when the command is called
    def handle(self, *args, **options):
        # Sometimes trying to programatically remove the old database generates an error
        # saying the file is already in use. So instead I ask the user to remove manually.
        if settings.DATABASES["default"].get("engine", "") == "django.db.backends.sqlite3":
            if os.path.isfile("db.sqlite3") and os.path.getsize("db.sqlite3") != 0:
                print("First delete the existing database at db.sqlite3, then run this command.")
                return

        self.stdout.write("*** Creating database ************************************************")
        call_command("migrate")

        if "ontologies" in settings.INSTALLED_APPS:
            call_command("ontology_load", o=["source_data/ontology_source/fyler_test.json"])

        self.stdout.write("*** Restoring the Chiron data dictionary *****************************")
        call_command("loaddata", "patient_model_data.json")
        call_command("chiron_restore_dd")

        self.stdout.write("*** Creating users ***************************************************")
        call_command("loaddata", "test_project.json")

        # add user permission groups
        setup_default_chironuser_permission_groups()

        self.stdout.write("*** Loading patient data *****************************")
        call_command("chiron_run_etl", "all")

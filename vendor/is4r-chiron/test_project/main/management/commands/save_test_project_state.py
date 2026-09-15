from django.core.management.base import BaseCommand
from django.core.management import call_command

from chiron.models import ChironUser, Dataset

from main.utils import setup_default_chironuser_permission_groups


class Command(BaseCommand):
    # provide some help text
    help = "Sets/Resets demo database with data dictionary and two users."

    # add optional command line arguments
    def add_arguments(self, parser):
        pass

    # this will be executed when the command is called
    def handle(self, *args, **options):
        self.stdout.write("*** Save data for Django models used as source data*****************")

        # The Django app patient_models has models with dummy data  that are used to
        # populate dataset3 during the ETL. We want to back up that that data into a fixture,
        # this should capture any changes that have been made.
        call_command(
            "dumpdata",
            "patient_models",
            indent=4,
            output="patient_model_data.json",
        )

        self.stdout.write("*** Saving the Chiron data dictionary *****************************")

        # We currently have 3 stored datasets used for tests.
        # This will erase any other datasets and then backup those 3 to a fixture.
        dataset_names = ["dataset1_stored", "dataset2_stored", "dataset3_stored"]
        qDataset = Dataset.objects.all().exclude(unique_id__in=dataset_names)
        for oDataset in qDataset:
            call_command("chiron_drop_dataset", oDataset.unique_id)
        # save datasets
        call_command("chiron_backup_dd")

        self.stdout.write("*** Saving Users and UserCreatedContent *****************************")

        # need to erase permission groups to prevent key error when reloading
        ChironUser.permission_groups.through.objects.all().delete()

        call_command(
            "dumpdata",
            "auth.user",
            "chiron.ChironUser",
            "chiron.Project",
            "chiron.UserCreatedContent",
            "chiron.ContentSharing",
            "chiron.ContentFlag",
            indent=4,
            output="test_project.json",
        )

        # restore user permission groups
        setup_default_chironuser_permission_groups()

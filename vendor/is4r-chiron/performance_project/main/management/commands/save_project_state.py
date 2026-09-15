from django.core.management.base import BaseCommand
from django.core.management import call_command

from chiron.models import ChironUser


class Command(BaseCommand):
    # provide some help text
    help = "Sets/Resets demo database with data dictionary and two users."

    # add optional command line arguments
    def add_arguments(self, parser):
        pass

    # this will be executed when the command is called
    def handle(self, *args, **options):
        self.stdout.write("*** Saving the Chiron data dictionary *****************************")
        call_command("chiron_backup_dd")

        self.stdout.write("*** Saving Users and UserCreatedContent *****************************")

        # need to erase permission groups to prevent key error when reloading
        ChironUser.permission_groups.through.objects.all().delete()

        call_command(
            "dumpdata",
            "auth.user",
            "chiron.ChironUser",
            "chiron.UserCreatedContent",
            "chiron.Project",
            "chiron.ContentSharing",
            "chiron.ContentFlag",
            indent=4,
            output="performance_project.json",
        )

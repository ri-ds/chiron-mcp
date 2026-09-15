import os

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings


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

        self.stdout.write("*** Creating database **********************************************")
        call_command("migrate")

        self.stdout.write("*** Creating users *************************************************")
        # User = get_user_model()
        # user = User.objects.create_user(username='admin', password='demo1234')
        # user.is_superuser = True
        # user.is_staff = True
        # user.save()
        # user = User.objects.create_user(username='demouser', password='demo1234')
        # user.save()
        call_command("loaddata", "performance_project.json")

        self.stdout.write("*** Restoring the Chiron data dictionary ***************************")
        call_command("chiron_restore_dd")

        print("The project state was restored. Next run `chiron_run_etl` to load data.")

import random
import string

from django.core.management.base import BaseCommand

from chiron import models


def slug_to_name(slug):
    response = slug.replace("-", " ").replace("_", " ")
    return response


def random_string(stringLength=10):
    """Generate a random string of fixed length"""
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(stringLength))


class Command(BaseCommand):
    help = "Populates tables for schema (Instrument and Event) but not Field definitions"

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
        pass

    def handle(self, *args, **options):
        models.Concept.objects.all().delete()
        models.Category.objects.all().delete()
        models.Source.objects.all().delete()
        models.Collection.objects.all().delete()
        models.AutocreatedField.objects.all().delete()

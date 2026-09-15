from django.core.management.base import BaseCommand

from chiron import models


class Command(BaseCommand):
    """
    Postgres has a maximum object name length of 63 characters. Names of postgres objects are
    derived from Collection.permanent_id and Concept.permanent_id which have much higher length
    limits. Long permanent IDs will cause the database to throw an error.

    In the future, we will likely shorten the maximum allowed length of permanent_ids and
    add a tool for automatically shortening ones that are too long. For now, this method can
    be used to generate a list of IDs that are too long for manual correction.

    The current limit is 59 characters for concepts and 63 characters for collections.
    """

    help = "Prints a list of collection and concept permanent IDs that are too long for Postgres"

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
        # list long collection IDs
        long_collection_ids = []
        for oCollection in models.Collection.objects.all():
            collection_id = oCollection.permanent_id
            if len(collection_id) > 63:
                long_collection_ids.append(collection_id)
        if not long_collection_ids:
            self.print_out("All your collection permanent_ids are short enough for Postgres.")
        else:
            self.print_out("The following collection permanent_ids exceed the limit of 63 chars:")
            for name in long_collection_ids:
                print("- " + name)

        # list long concept IDs
        long_concept_ids = []
        for oConcept in models.Concept.objects.all():
            concept_id = oConcept.permanent_id
            if len(concept_id) > 59:
                long_concept_ids.append(concept_id)
        if not long_concept_ids:
            self.print_out("All your concept permanent_ids are short enough for Postgres.")
        else:
            self.print_out("The following concept permanent_ids exceed the limit of 59 chars:")
            for name in long_concept_ids:
                print("- " + name)

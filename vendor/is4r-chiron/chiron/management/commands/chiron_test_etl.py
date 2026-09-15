from django.core.management.base import BaseCommand

from chiron.models import Concept


class Command(BaseCommand):
    """
    Check if the ETL is working for a single concept. Will run the corresponding source
    and output each value type and value to stdout. Does not modify the database.

    .. code-block:: bash

        python manage.py chiron_test_etl [concept permanent_id]

    """

    help = "Check if the ETL is working for a single concept"

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
        parser.add_argument("concept_id")

    def handle(self, *args, **options):
        concept_id = options["concept_id"]
        try:
            oConcept = Concept.objects.get(id=concept_id)
        except Exception:
            oConcept = Concept.objects.get(permanent_id=concept_id)
        oSource = oConcept.source
        source_processor = oSource.get_processor()
        etl_processor = oConcept.get_etl_processor()
        count = 0
        count_non_null = 0
        for record in source_processor.get_source():
            val = etl_processor.pull_concept_value_from_record(record)
            if val is not None:
                print(type(val), val)
            count += 1
            if val is not None:
                count_non_null += 1
        print("final count of records returned (including None): ", count)
        print("final count of non-null records returned: ", count_non_null)

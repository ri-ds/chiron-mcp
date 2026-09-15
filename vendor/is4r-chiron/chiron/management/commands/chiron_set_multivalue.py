from sqlalchemy import select

from django.core.management.base import BaseCommand

from chiron import models
from chiron.helpers import dataset_command_line_selection
from chiron.query_engine.postgres.database import (
    generate_sql_alchemy_lookup_table_for_concept,
    get_sql_alchemy_db_engine,
)


class Command(BaseCommand):
    """Sets multivalue fields based on what seems necessary with current loaded data.

    A concept can be overloaded, meaning multiple values can be stored in a single record. This
    was accomplished in MongoDB using array values, and it's accomplished in Postgres using
    lookup tables. Overloaded concepts must be flagged as "multivalue".

    Having all concepts flagged as multivalue is inefficient - it's better to only flag concepts
    that might actually be overloaded. This command looks at the actual data being stored in
    all multivalue=True concepts, and if there are no overloaded values, converts to
    multivalue=False.

    Note, you should have all the real data loaded before doing this check. And it still is only
    based on current data, it can't anticipate how data for a concept might change in the future.
    """

    help = "Checks if unwound fields seem necessary based on current loaded data."

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
            "dataset_id",
            nargs="?",
            default="no_selection",
            help="The dataset id, or 'all' to run all, or leave blank to select from a list",
        )

    def handle(self, *args, **options):
        # determine the dataset to check
        qDataset = models.Dataset.objects.all()
        dataset_id = options["dataset_id"]
        dataset_id = dataset_command_line_selection(qDataset, dataset_id, allow_all=True)
        if dataset_id == "all":
            qDataset = models.Dataset.objects.all()
        else:
            qDataset = models.Dataset.objects.filter(pk=dataset_id)

        count_unchanged = 0
        count_changed = 0

        for oDataset in qDataset:
            qConcept = models.Concept.objects.filter(
                collection__dataset=oDataset, multivalue=True, published=True
            )
            for oConcept in qConcept:
                table = generate_sql_alchemy_lookup_table_for_concept(oConcept)
                stmt_count_records = select(table.c._collection_id)
                stmt_count_distinct = stmt_count_records.distinct()
                with get_sql_alchemy_db_engine(oDataset).connect() as conn:
                    count_records = conn.execute(stmt_count_records).rowcount
                    count_distinct = conn.execute(stmt_count_distinct).rowcount
                if count_records == count_distinct and count_records > 0:
                    print("**NOT MULTIVALUE**", oConcept)
                    oConcept.multivalue = False
                    oConcept.save()
                    count_changed += 1
                else:
                    print("MULTIVALUE", oConcept)
                    count_unchanged += 1
            print("count changed", count_changed)
            print("count unchanged", count_unchanged)

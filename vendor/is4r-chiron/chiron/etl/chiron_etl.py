import datetime
import math
import sys

from django.utils.html import strip_tags
from django.db import connections

from chiron.helpers import get_all_collections_from_source_name, get_all_related_sources
from chiron.models import Concept, Dataset
from chiron import chiron_settings
from chiron.cache import cache_utils

from chiron.etl.populate_subcollection import populate_subcollection
from chiron.etl.populate_subject_collection import populate_subject_collection
from chiron.etl.logger import Logger
from chiron.query_engine import get_db_writer


def sizeof_fmt(num, suffix="B"):
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, "Yi", suffix)


class ChironEtl:
    """
    Loads data from sources into the Chiron database and other methods related to preparing
    a Chiron database.
    """

    def __init__(
        self,
        dataset_id,
        notification_count=1000,
        create_log=True,
        source=None,
        track_subject_matching=False,
        abbreviated=False,
        refresh_database_connections=True,
        use_staging=None,
        force_single_source=False,
    ):
        self.dataset = Dataset.objects.get(pk=dataset_id)
        self.notification_count = notification_count  # notify status every x records
        self.logger = Logger(self.dataset, track_subject_matching) if create_log else None
        self.create_log = create_log
        self.abbreviated = abbreviated
        self.source = source  # single source name or set to none to load all sources
        self.force_single_source = force_single_source
        self.use_staging = chiron_settings.CHIRON_USE_STAGING_DURING_ETL
        # refresh connections after each source loaded to prevent database connection timeout error
        self.refresh_database_connections = refresh_database_connections
        # if use_staging is set, override the default setting
        if use_staging is not None:
            self.use_staging = use_staging

    def print_out(self, *args, **kwargs):
        """A wrapper for print that also saves to self.log_comments"""
        strings = []
        for arg in args:
            strings.append(str(arg))
        output = ",".join(strings)
        if kwargs.get("log") and self.logger:
            self.logger.add_log_comment(output)
        print(output, end=kwargs.get("end"))

    def run(self):
        """
        Runs the Chiron ETL process
        """
        if self.logger:
            self.logger.start_etl_log(self.use_staging, self.abbreviated)
        writer = get_db_writer(self.dataset, self.use_staging)

        self.print_out(
            "Deleting existing data"
            " (if using staging, does not delete anything from live database)"
        )

        self.print_out("Preparing database for ETL")
        sources = get_all_related_sources(self.dataset, self.source)
        if self.source and not self.force_single_source:
            print("Would reload the following sources:")
            print("  ", "\n   ".join([s.name for s in sources]))
            print("To reload these sources, use the --force flag")
            sys.exit(1)

        # if not using a staging schema, clear cached data right before clearing research data
        if not self.use_staging:
            self.clear_cached_data()

        # prepare the database to load new data
        writer.initialize_database(self.source, sources=sources)

        # load each source
        for source in sources:
            self.load_source(source)

        self.print_out("###################################################################")
        self.print_out("Source data has finished loading - finishing up")

        # perform any final actions on newly-loaded data needed to prepare it for use
        self.print_out("Making final updates to the data")
        self.refresh_django_database_conections()
        self.finalize_data()

        # make sure indexes are all set up, even after staging move
        self.print_out("Setting up database indexes")
        self.refresh_django_database_conections()
        self.create_indexes()

        # refresh the concept search collection
        if chiron_settings.CHIRON_REQUIRE_SUCCESSFUL_CONCEPT_SEARCH_UPDATE:
            self.print_out("Refreshing the concept search collection")
            self.refresh_django_database_conections()
            self.create_concept_search_collection()

        # if using a staging schema, clear cached data right before making staging data live
        if self.use_staging:
            self.clear_cached_data()

        # clean up unused tables in the database, rename staging tables if appropriate
        self.print_out(
            "Making final updates to the database  (If using staging,"
            " this step will replace the live database with your staging database)"
        )
        self.refresh_django_database_conections()
        writer.finalize_database()

        # after finalizing the database, we are finished with any staging database
        self.use_staging = False

        # finish log record
        self.print_out("Finishing final ETL log entry")
        self.refresh_django_database_conections()
        if self.logger:
            self.logger.finalize_etl_log()

        # refresh the concept search collection after log finish if fail is OK
        if not chiron_settings.CHIRON_REQUIRE_SUCCESSFUL_CONCEPT_SEARCH_UPDATE:
            self.print_out("Refreshing the concept search collection")
            self.refresh_django_database_conections()
            self.create_concept_search_collection()

        # repopulate cached data
        self.print_out("Refreshing caches if applicable")
        self.refresh_django_database_conections()
        if chiron_settings.CHIRON_USE_CACHES:
            cache_utils.cache_reports(self.dataset)
            collections = get_all_collections_from_source_name(self.dataset, self.source)
            cache_utils.cache_concepts(self.dataset, collections)

    def clear_cached_data(self):
        self.print_out("Clearing stale caches")
        self.refresh_django_database_conections()
        cache_utils.clear_cached_data(self.dataset)

    def finalize_data(self):
        """
        Database-specific actions that should be performed after the database has loaded.
        """
        writer = get_db_writer(self.dataset, self.use_staging)
        writer.finalize_data()

    def create_indexes(self, only_text=False):
        writer = get_db_writer(self.dataset, self.use_staging)
        writer.create_indexes(only_text)

    def create_ngram_array(self, concept):
        ngram_results = []
        for word in concept.split(" "):
            if len(word) <= 2:
                continue
            first_three_characters = word[:3]
            ngram_results.append(first_three_characters)
            rest_of_the_characters = word[3:]
            ngram_results += [
                first_three_characters + rest_of_the_characters[: i + 1]
                for i in range(len(rest_of_the_characters))
            ]
        return ngram_results

    def create_concept_search_collection(self):
        """
        Creates the data table that will be used to search for concepts.
        """
        # drop/create table
        writer = get_db_writer(self.dataset, self.use_staging)
        writer.recreate_concept_search_table()

        queryset = Concept.objects.accessible(self.dataset).exclude(concept_handler__isnull=True)
        total_count = queryset.count()

        i = 0
        for concept in queryset:
            cohort_def_processor = concept.get_cohort_def_processor_without_user()
            if not cohort_def_processor:
                continue

            # get category names
            categories = []
            category_objects = concept.get_category_hierarchy()
            for category in category_objects:
                categories.append(category.name)

            try:
                # insert data into table
                writer.insert_one_concept_search_row(
                    {
                        "concept_id": concept.id,
                        "concept_name": concept.name,
                        "concept_description": strip_tags(concept.description),
                        "categories": "; ".join(categories),
                        # full text indexing must be used to handle the large text/ontology
                        # fields, It's not just as easy as enabling that feature
                        "other_search_terms": (
                            cohort_def_processor.get_concept_search_terms()
                            if cohort_def_processor.concept_type not in ["text", "ontology"]
                            else ""
                        ),
                        "ngram_search": "; ".join(self.create_ngram_array(concept.name)),
                    }
                )
            except Exception as e:
                print(f"Could not create search for {concept.name}")
                print(e)

            i += 1
            print(f"Progress: {str(i)}/{str(total_count)}", end="\r", flush=True)

    def load_source(self, oSource):
        """
        Loads all the data from a single Source into the Chiron database
        """
        # track progress
        collection_load_start = datetime.datetime.now()
        subject_writer = get_db_writer(self.dataset, self.use_staging)
        start_subject_count = subject_writer.get_collection_stats()["subject_count"]

        # print at start
        self.print_out(" ")
        self.print_out(
            "### Starting source {} ({}) #################################".format(
                oSource.name, collection_load_start
            ),
            log=True,
        )

        # load data
        if oSource.collection.is_root_collection:
            self.print_out("loading into the subject (root) collection", log=True)
            source_record_count = populate_subject_collection(
                oSource=oSource,
                writer=subject_writer,
                notify_count=self.notification_count,
                logger=self.logger,
                abbreviated=self.abbreviated,
                db_refresh_func=self.refresh_django_database_conections,
            )
        else:
            subcol_name = oSource.collection.name
            self.print_out("loading into the {} subcollection".format(subcol_name), log=True)
            writer = get_db_writer(self.dataset, self.use_staging, oSource.collection)
            source_record_count = populate_subcollection(
                oSource=oSource,
                writer=writer,
                notify_count=self.notification_count,
                logger=self.logger,
                abbreviated=self.abbreviated,
                db_refresh_func=self.refresh_django_database_conections,
            )

        # track progress
        end_subject_count = subject_writer.get_collection_stats()["subject_count"]
        collection_load_finish = datetime.datetime.now()
        collection_load_duration_s = (
            collection_load_finish - collection_load_start
        ).total_seconds()
        stats = subject_writer.get_collection_stats()

        # print summary of data load
        self.print_out("Source records read: {}".format(source_record_count), log=True)
        if end_subject_count != start_subject_count:
            self.print_out(
                "subject (root) collection count changed from {} to {}".format(
                    start_subject_count, end_subject_count
                ),
                log=True,
            )

        self.print_out(
            "load time = {} min {} sec".format(
                math.floor(collection_load_duration_s / 60),
                round(collection_load_duration_s % 60),
            ),
            log=True,
        )
        self.print_out(
            "avg doc size: {}; max doc size: {} (id: {})".format(
                sizeof_fmt(stats["avg_doc_size"]),
                sizeof_fmt(stats["max_doc_size"]),
                stats["max_doc_id"],
            ),
            log=True,
        )
        self.refresh_django_database_conections()

    def refresh_django_database_conections(self):
        """
        For long ETL processes, database connections might time out if inactive for too long.
        This will refresh connections for all databases defined in Django settings. It should be
        run after each long step where a timeout might occur.
        """
        if self.refresh_database_connections:
            for conn_name in connections:
                connection = connections[conn_name]
                connection.connect()

import os
import random
import string
import sys

from sqlalchemy import MetaData, select, text
from sqlalchemy.exc import ProgrammingError

from chiron import chiron_settings
from chiron.models import Concept, Source
from chiron.query_engine.abstract_db_writer import DbWriter
from chiron.query_engine.postgres import database
from chiron.query_engine.postgres.bulk_inserter import BulkInserter

# get the path to the directory this file is in
__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


class DbWriterPostgres(DbWriter):
    """Handles interaction with the Chiron database during the ETL process.

    Has methods involved in preparing the database for the ETL, adding data to the database,
    checking the status of data in the database, and any finishing steps for the database after
    the ETL.

    :param oDataset: The Chiron dataset that will be written
    :type oDataset: model object
    :param use_staging: Whether a separate staging database should be used
    :type use_staging: bool
    :param oCollection: The Chiron collection to work with, can leave null if working with the
      subject collection or if not using relevant methods
    :type oCollection: model object
    """

    def __init__(self, oDataset, use_staging, oCollection=None):
        super().__init__(oDataset, use_staging, oCollection=oCollection)
        self.engine = database.refresh_sql_alchemy_db_engine(self.dataset, self.use_staging)
        metadata_obj = MetaData()
        self.subject_collection = oDataset.root_collection
        self.bulk_inserter = BulkInserter(
            self.engine, metadata_obj, self.subject_collection, self.collection
        )

    def refresh_engine(self):
        self.engine = database.refresh_sql_alchemy_db_engine(self.dataset, self.use_staging)
        self.bulk_inserter.engine = self.engine

    def initialize_database(self, source, sources=[]):
        """Prepare the database for a new data load.

        In postgres, this (drops and) creates the schema and runs all the DDL commands.

        :param source: The single source to load
        :param sources: The sources to load data from, or empty list to load all sources
        :return:
        """
        # if no sources are passed in do a full reset otherwise no
        full_reset = source is None
        schema_name = database.get_schema_name_for_dataset(self.dataset, self.use_staging)
        if not full_reset:
            collections = set([])
            for db_source in sources:
                collections.add(db_source.collection)

            for collection in collections:
                # if the root collection is being reloaded then do a full reset
                if collection.is_root_collection:
                    full_reset = True
                    break
                else:
                    # reloading a single collection, cannot use staging
                    self.use_staging = False
                    print("Not using staging for partial collection reload")

                    # get collection to truncate and truncate the table
                    with self.engine.connect() as conn:
                        print("starting collection truncate:", collection.name)
                        sql = f'TRUNCATE TABLE "{schema_name}".{collection.permanent_id} RESTART IDENTITY'
                        conn.execute(text(sql))
                        conn.commit()
                        print("ending collection truncate")

        if full_reset:
            # reloading full datasset
            # drop and recreate schema
            with self.engine.connect() as conn:
                print("starting schema reset")
                sql = f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'
                conn.execute(text(sql))
                conn.commit()
                sql = f'CREATE SCHEMA "{schema_name}"'
                conn.execute(text(sql))
                conn.commit()
                print("ending schema reset")

            # set up custom functions
            with open(os.path.join(__location__, "custom_functions.sql"), "r") as file:
                custom_function_sql = file.read()

            # write the custom functions to the database
            with self.engine.connect() as conn:
                conn.execute(text(custom_function_sql))
                conn.commit()

            # re-create all the collections needed for the dataset
            metadata_obj = MetaData()
            for oCollection in self.dataset.collection_set.all():
                if oCollection.is_root_collection:
                    database.generate_sql_alchemy_table_for_subject_collection(
                        self.subject_collection, metadata_obj
                    )
                else:
                    database.generate_sql_alchemy_table_for_subcollection(
                        oCollection, metadata_obj
                    )
                database.generate_sql_alchemy_lookup_tables_for_collection(
                    oCollection, metadata_obj
                )
            database.generate_sql_alchemy_table_for_subject_identification(
                self.subject_collection, metadata_obj
            )
            database.generate_sql_alchemy_table_for_concept_search(metadata_obj)
            metadata_obj.create_all(self.engine)

    def finalize_database(self):
        if not self.use_staging:
            return
        staging_schema_name = database.get_schema_name_for_dataset(self.dataset, use_staging=True)
        prod_schema_name = database.get_schema_name_for_dataset(self.dataset, use_staging=False)
        # Make sure all other db connections are closed - any open connections will block
        # the DROP statement.
        self.engine = None
        self.bulk_inserter.engine = None
        database.dispose_of_all_db_engines()
        self.engine = database.refresh_sql_alchemy_db_engine(self.dataset, self.use_staging)
        self.bulk_inserter.engine = self.engine
        with self.engine.connect() as conn:
            if chiron_settings.CHIRON_KEEP_DATABASE_BACKUP:
                print("backing up old prod schema and moving staging schema to replace it")
                backup_schema_name = f"{prod_schema_name}_backup"
                sql = f'DROP SCHEMA IF EXISTS "{backup_schema_name}" CASCADE'
                conn.execute(text(sql))
                conn.commit()
                sql = f'ALTER SCHEMA "{prod_schema_name}" RENAME TO "{backup_schema_name}"'
                try:
                    conn.execute(text(sql))
                except ProgrammingError:
                    # will fail if there is no pre-existing database to backup
                    pass
                conn.commit()
            else:
                print("deleting prod schema and moving staging schema to replace it")
                sql = f'DROP SCHEMA IF EXISTS "{prod_schema_name}" CASCADE'
                conn.execute(text(sql))
                conn.commit()
            sql = f'ALTER SCHEMA "{staging_schema_name}" RENAME TO "{prod_schema_name}"'
            conn.execute(text(sql))
            conn.commit()
            print("staging schema move complete")

    def delete_existing_data(self, source=None):
        """Delete all research data for specified sources.

        This has not been implemented yet. The initialize_database() method drops and recreates
        the schema, so that will erase all data.

        :param source:
        :return: a Django queryset of sources that were deleted.
        """
        sources = Source.objects.filter(exclude_from_etl=False, collection__dataset=self.dataset)
        if source:
            # include all sources that match the given sources collection
            try:
                source_obj = Source.objects.get(name=source, collection__dataset=self.dataset)
            except Source.DoesNotExist:
                print(f"Source {source} not found in dataset {self.dataset}")
                sys.exit(1)

            # if we are reloading the root_collection then return all
            if source_obj.collection.is_root_collection:
                return sources

            # else get all sources for the collection
            sources = sources.filter(collection=source_obj.collection)
        return sources.order_by("execution_order")

    def insert_one_subject(self, record, alt_subject_ids):
        """Inserts one subject record with provided data.

        :param record: The subject data to be loaded where keys are concept permanent IDs and
          values are the values to be stored
        :type record: dict
        :param subject_ids: Any alternative subject IDs to store where keys are the name of the
          subject ID (ex. "mrn") and values are the ID values for this subject.
        :type subject_ids: dict
        :return: The subject ID of the created subject
        :rtype: various (string, int, object_id, etc.)
        """
        if not record.get("_id"):
            subject_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=20))
            record["_id"] = subject_id
            record["_subject_id"] = subject_id
        if not record.get("_subject_id"):
            record["_subject_id"] = record["_id"]
        subject_id = self.bulk_inserter.insert_subject(record, alt_subject_ids)
        return subject_id

    def insert_empty_subject(self, alt_subject_ids):
        """Inserts a new subject with no data other than an ID and optional alternative IDs.

        This is used when loading a subcollection for a subject that doesn't exist yet.

        :param alt_subject_ids: Any alternative subject IDs to store where keys are the name of the
          subject ID (ex. "mrn") and values are the ID values for this subject.
        :type alt_subject_ids: dict
        :return: The subject ID of the created subject
        :rtype: various (string, int, object_id, etc.)
        """
        subject_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=20))
        empty_record = {"_id": subject_id, "_subject_id": subject_id}
        subject_id = self.bulk_inserter.insert_subject(empty_record, alt_subject_ids)
        return subject_id

    def insert_one_subcollection(self, record, collection_id, subject_ids):
        """Inserts one subcollection record with provided data.

        :param record: The data to be loaded where keys are concept permanent IDs and
          values are the values to be stored
        :type record: dict
        :param collection_id: The ID of the collection, or None to autocreate collection ID,
          or False to skip this subcollection
        :type collection_id: various
        :param subject_ids: The ID or array of IDs for subject(s) that this subcollection should
          be associated with
        :type subject_ids: various
        :return: The ID of the created collection
        :rtype: various (usually string or int)
        """
        if collection_id is False:
            return 0
        if not record:
            return 0
        if collection_id is None:
            collection_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=20))
        record["_id"] = collection_id
        record["_subject_id"] = subject_ids[0]
        collection_id = self.bulk_inserter.insert_subcollection(record, collection_id, subject_ids)
        return collection_id

    def _get_subject_id_from_match_rule(self, match_rule):
        if "_id" in match_rule:
            return match_rule["_id"]
        for id_name, id_value in match_rule.items():
            id_value = str(id_value)
            subject_id = self.bulk_inserter.subject_lookup.get(id_name, {}).get(id_value)
            if subject_id:
                return subject_id
        return None

    def update_one_subject(self, match_rule, record, alt_subject_ids=None):
        """Updates one subject record identifed by provided match rule with provided data.

        :param match_rule: The definition of the subject(s) to update where the key is the
          subject field name to match (all specified fields must match)
        :type match_rule: dict
        :param record: The subject data to be loaded where keys are concept permanent IDs and
          values are the values to be stored
        :type record: dict
        :param alt_subject_ids: Any alternative subject IDs to store where keys are the name of the
          subject ID (ex. "mrn") and values are the ID values for this subject.
        :type alt_subject_ids: dict
        :return: The count of subjects that were updated
        :rtype: int
        """
        subject_id = self._get_subject_id_from_match_rule(match_rule)
        if not subject_id:
            return 0
        rowcount = self.bulk_inserter.update_subject(record, subject_id, alt_subject_ids)
        return rowcount

    def update_one_subcollection(self, record, collection_id, subject_ids):
        """Updates one subcollection record identifed by provided collection_id.

        :param record: The subcollection data to be loaded where keys are concept permanent IDs and
          values are the values to be stored
        :type record: dict
        :param collection_id: The ID of the collection, or None to autocreate collection ID,
          or False to skip this subcollection
        :type collection_id: various
        """
        if collection_id is False or collection_id is None:
            return 0
        if not record:
            return 0
        rowcount = self.bulk_inserter.update_subcollection(record, collection_id, subject_ids)
        return rowcount

    def find_subjects(self, match_rule, set_alt_ids=None):
        """Finds (and optionally updates IDs for) subjects matching the match_rule

        If a value is provided for set_alt_ids, will also write to the database to add any
        new alt subject IDs.

        :param match_rule: The definition of the subject(s) to update where the key is the
          subject field name to match (all specified fields must match)
        :type match_rule: dict
        :param set_alt_ids: Any alternative subject IDs to store where keys are the name of the
          subject ID (ex. "mrn") and values are the ID values for this subject.
        :type set_alt_ids: dict
        :return: list of subject IDs and dict of dicts with subject_id:alt_ids_dict
        :rtype: tuple with 1 array and 1 dict
        """
        subject_ids = []
        alt_ids = {}
        # TODO: what if multiple match rules, should that be allowed?
        if "_id" in match_rule:
            subject_ids.append(match_rule["_id"])
        else:
            subject_id = self._get_subject_id_from_match_rule(match_rule)
            if subject_id:
                subject_ids.append(subject_id)
        if set_alt_ids:
            for subject_id in subject_ids:
                self.bulk_inserter._add_alt_subject_ids(subject_id, set_alt_ids)
        return subject_ids, alt_ids

    def find_one_subject(self, match_rule):
        """
        Looks up record and gets the autocreated subject ID and list of all source subject IDs
        """
        subject_id = self._get_subject_id_from_match_rule(match_rule)
        # TODO: should also return list of source_subject_ids
        return subject_id, {}

    def count_subject_records(self):
        """Returns the current count of subject records"""
        stmt = select(self.bulk_inserter.subject_table)
        count = 0
        with self.engine.begin() as conn:
            result = conn.execute(stmt)
            for row in result:
                count += 1
        return count

    def count_subcollection_records(self):
        """Returns the current count of subcollection records (self.collection must be defined)"""
        stmt = select(self.bulk_inserter.table)
        count = 0
        with self.engine.begin() as conn:
            result = conn.execute(stmt)
            for row in result:
                count += 1
        return count

    def get_collection_stats(self):
        """Gets statistics about all collections.

        TODO: this might be too specific to MongoDB. We might want to modify our code so that
          this can return null values for irrelevant stats or a different set of stats.

        :return: subject_count, avg_doc_size, max_doc_size, max_doc_id
        :rtype: dict
        """
        return {
            "subject_count": 0,
            "avg_doc_size": 0,
            "max_doc_size": 0,
            "max_doc_id": 0,
        }

    def finalize_subject_collection(self):
        """Performs any final steps to finish loading a source to the subject collection."""
        self.bulk_inserter.finalize_populate_subject_collection()

    def finalize_subcollection(self):
        """Performs any final steps to finish loading a source to a subcollection."""
        self.bulk_inserter.finalize_populate_subcollection()

    def recreate_concept_search_table(self):
        # drop the table
        schema_name = database.get_schema_name_for_dataset(
            self.dataset, use_staging=self.use_staging
        )
        with self.engine.connect() as conn:
            sql = f'DROP TABLE IF EXISTS "{schema_name}".concept_search'
            conn.execute(text(sql))
            # sql = "CREATE OR REPLACE FUNCTION fti() RETURNS opaque AS 'fti.so' LANGUAGE 'C'"
            # conn.execute(text(sql))
            conn.commit()

        # re-create the table
        metadata_obj = MetaData()
        database.generate_sql_alchemy_table_for_concept_search(metadata_obj)
        metadata_obj.create_all(self.engine)

    def insert_one_concept_search_row(self, data):
        schema_name = database.get_schema_name_for_dataset(self.dataset, self.use_staging)
        with self.engine.connect() as conn:
            sql = f"""
                INSERT INTO "{schema_name}".concept_search(
                    concept_id,
                    concept_name,
                    concept_description,
                    categories,
                    other_search_terms,
                    ngram_search
                ) VALUES(
                    :concept_id,
                    :concept_name,
                    :concept_description,
                    :categories,
                    :other_search_terms,
                    :ngram_search
                )
            """
            conn.execute(text(sql), data)
            conn.commit()

    def create_indexes(self, only_text=False):
        """
        Creates all indexes needed for live database
        """
        # create indexes for all concepts
        schema_name = database.get_schema_name_for_dataset(self.dataset, self.use_staging)
        with self.engine.connect() as conn:
            concepts = Concept.objects.filter(published=True, collection__dataset=self.dataset)
            total = concepts.count()
            i = 0
            for oConcept in concepts:
                i += 1
                print(f"Progress: {str(i)}/{str(total)}", end="\r")
                concept_handler = oConcept._instantiate_concept_handler(chironuser=None)
                if only_text:
                    data_type = concept_handler.get_stored_data_type()
                    if data_type != "text":
                        continue

                index_name = f"idx_{oConcept.permanent_id}"
                table_name = (
                    f"lkp_{oConcept.permanent_id}"
                    if oConcept.multivalue
                    else oConcept.collection.permanent_id
                )

                sql_list = []

                sql_list.append(
                    f"""
                    CREATE INDEX IF NOT EXISTS {index_name}
                        ON "{schema_name}"."{table_name}"
                        ("{oConcept.permanent_id}")
                """
                )

                # create indexes for subfields also if this is a complex datatype
                data_type = concept_handler.get_stored_data_type()
                if isinstance(data_type, dict):
                    for subfield in data_type.keys():
                        field_name = f"{oConcept.permanent_id}__{subfield}"
                        index_name = f"idx_{field_name}"
                        sql_list.append(
                            f"""
                                CREATE INDEX IF NOT EXISTS {index_name}
                                    ON "{schema_name}"."{table_name}"
                                    ("{field_name}")
                            """
                        )

                try:
                    for sql in sql_list:
                        conn.execute(text(sql))
                except Exception as e:
                    print(
                        f"Warning: Could not create index on {table_name}.{oConcept.permanent_id}"
                    )
                    print(e)
                    sys.exit(1)

            print("Committing indexes")
            conn.commit()
            print("Done.")

import json

from sqlalchemy import insert, update, select, func
from sqlalchemy.exc import ProgrammingError

from chiron import chiron_settings
from chiron.query_engine.postgres import database


class BulkInserter:
    """Contains methods for efficiently writing research data to Postgres.

    This class is used to speed up operations from DbWriterPostgres by storing db operations
    in queues and running in batches.

    :param engine: The SQL alchemy engine to use
    :param metadata_obj: The SQL alchemy metadata object to use
    :param subject_collection: The Django model object for the subject collection
    :param subcollection: Optionally the Django model object for the subcollection.
    """

    def __init__(self, engine, metadata_obj, subject_collection, subcollection=None):
        self.engine = engine
        self.metadata_obj = metadata_obj
        self.subject_collection = subject_collection
        self.subcollection = subcollection
        self.subject_insert_queue = []
        self.subject_lookup_insert_queue = {}
        self.subcollection_lookup_insert_queue = {}
        self.subcollection_insert_queue = []
        self.m2m_table_insert_queue = []
        self.alt_subject_id_insert_queue = []
        self.alt_subject_id_update_queue = []
        self.subject_lookup_concept_mapping = database.get_lookup_concept_mapping(
            self.subject_collection
        )
        self.subject_id_table = database.generate_sql_alchemy_table_for_subject_identification(
            self.subject_collection
        )
        self._generate_subject_lookup_dict()
        if subcollection:
            (
                self.table,
                self.m2m_table,
            ) = database.generate_sql_alchemy_table_for_subcollection(subcollection, metadata_obj)
            self.subcollection_lookup_tables = (
                database.generate_sql_alchemy_lookup_tables_for_collection(
                    subcollection, metadata_obj
                )
            )
            self.subcollection_lookup_concept_mapping = database.get_lookup_concept_mapping(
                self.subcollection
            )
        self.subject_table = database.generate_sql_alchemy_table_for_subject_collection(
            self.subject_collection, metadata_obj
        )
        self.subject_lookup_tables = database.generate_sql_alchemy_lookup_tables_for_collection(
            self.subject_collection, metadata_obj
        )
        self.subject_id_table = database.generate_sql_alchemy_table_for_subject_identification(
            self.subject_collection
        )

    def insert_subject(self, record, alt_subject_ids):
        """Insert one subject record into the database.

        :param dict record: The subject data to load as concept_id/value pairs
        :param dict alt_subject_ids: And alternative subject IDs to include.
        :return: the record ID for the created subject
        """
        new_record = {}
        for key, value in record.items():
            new_record = self.add_value_to_subject_record(new_record, record["_id"], key, value)
        self.subject_insert_queue.append(new_record)
        self._add_alt_subject_ids(new_record["_id"], alt_subject_ids)
        if len(self.subject_insert_queue) > chiron_settings.CHIRON_BULK_INSERT_BATCH_SIZE:
            self.finalize_populate_subject_collection()
        return record["_id"]

    def insert_m2m_subcollection(self, record, collection_id, subject_ids):
        """Insert one subcollection record that is M2M with subjects.

        Note: you can just call insert_subcollection() and this will automatically be used
        when appropriate.

        :param dict record: The collection data to load as concept_id/value pairs
        :param str collection_id: The ID for this collection record.
        :param list subject_ids: An array of all subject_ids associated with this record.
        :return: the collection ID
        """
        new_record = {
            "_id": record["_id"],
        }
        for key, value in record.items():
            new_record = self.add_value_to_subcollection_record(
                new_record, collection_id, key, value
            )
        self.subcollection_insert_queue.append(new_record)
        for subject_id in subject_ids:
            self.m2m_table_insert_queue.append(
                {
                    "_subject_id": subject_id,
                    "_collection_id": collection_id,
                }
            )
        if len(self.subcollection_insert_queue) > chiron_settings.CHIRON_BULK_INSERT_BATCH_SIZE:
            self.finalize_populate_subcollection()
        return new_record["_id"]

    def insert_subcollection(self, record, collection_id, subject_ids):
        """Insert one subcollection record.

        :param dict record: The collection data to load as concept_id/value pairs
        :param str collection_id: The ID for this collection record.
        :param list subject_ids: An array of all subject_ids associated with this record.
          Typically this will be 1 but M2M subcollections can be associated with multiple subjects.
        :return: the collection ID
        """
        if self.subcollection.many_to_many_with_subject:
            return self.insert_m2m_subcollection(record, collection_id, subject_ids)
        # subject_id = subject_ids[0]
        new_record = {
            "_id": record["_id"],
            "_subject_id": record["_subject_id"],
        }
        for key, value in record.items():
            new_record = self.add_value_to_subcollection_record(
                new_record, collection_id, key, value
            )
        self.subcollection_insert_queue.append(new_record)
        if len(self.subcollection_insert_queue) > chiron_settings.CHIRON_BULK_INSERT_BATCH_SIZE:
            self.finalize_populate_subcollection()
        return new_record["_id"]

    def update_subject(self, record, subject_id, alt_subject_ids):
        """Apply updates to an existing subject record.

        :param dict record: The collection data to modify as concept_id/value pairs
        :param str subject_id:
        :param dict alt_subject_ids:
        :return: The number of records affected
        """
        # this only gets called when subject exists, so shouldn't need to check that
        # multivalue output gets multiple columns in database table
        new_record = {}
        rowcount = 1
        for key, value in record.items():
            new_record = self.add_value_to_subject_record(new_record, subject_id, key, value)
        if new_record:
            # TODO: this is slow, would be better to do a bulk update, but do I need rowcount?
            stmt = (
                update(self.subject_table).filter_by(_subject_id=subject_id).values(**new_record)
            )
            with self.engine.begin() as conn:
                result = conn.execute(stmt)
            rowcount = result.rowcount
        if alt_subject_ids:
            self._add_alt_subject_ids(subject_id, alt_subject_ids)
        # sometimes there might be no data to load in collection but may have loaded data
        # already in lookup tables
        return rowcount

    def update_subcollection(self, record, collection_id, subject_ids):
        """Apply updates to an existing collection record.

        :param dict record: The collection data to modify as concept_id/value pairs
        :param collection_id:
        :param subject_ids:
        :return: The number of records affected
        """
        if not collection_id:
            return 0
        stmt = select(func.count(self.table.c._id)).where(self.table.c._id == str(collection_id))
        with self.engine.begin() as conn:
            rowcount = conn.execute(stmt).first()[0]
        if rowcount == 0:
            return 0
        new_record = {}
        for key, value in record.items():
            new_record = self.add_value_to_subcollection_record(
                new_record, collection_id, key, value
            )
        if new_record:
            stmt = (
                update(self.table)
                .where(self.table.c._id == str(collection_id))
                .values(**new_record)
            )
            with self.engine.begin() as conn:
                result = conn.execute(stmt)
            # TODO: load alt subject IDs
            return result.rowcount
        # sometimes there might be no data to load in collection but may have loaded data
        # already in lookup tables
        return 1

    def finalize_populate_subject_collection(self):
        """Runs batch updates/inserts of everything in the queues related to subjects.

        :return:
        """
        # update subject table
        if self.subject_insert_queue:
            with self.engine.begin() as conn:
                data = self._make_dicts_the_same(self.subject_insert_queue)
                conn.execute(insert(self.subject_table), data)
        # update subject alt ids table
        if self.alt_subject_id_insert_queue:
            with self.engine.begin() as conn:
                conn.execute(insert(self.subject_id_table), self.alt_subject_id_insert_queue)
        if self.alt_subject_id_update_queue:
            with self.engine.begin() as conn:
                for entry in self.alt_subject_id_update_queue:
                    # print("updates", entry)
                    pass
        # update lookup tables
        if self.subject_lookup_insert_queue:
            with self.engine.begin() as conn:
                for concept_id, insert_data in self.subject_lookup_insert_queue.items():
                    lookup_table = self.subject_lookup_tables[concept_id]
                    conn.execute(insert(lookup_table), insert_data)
        # reset all queues
        self.subject_insert_queue = []
        self.alt_subject_id_insert_queue = []
        self.alt_subject_id_update_queue = []
        self.subject_lookup_insert_queue = {}

    def finalize_populate_subcollection(self):
        """Runs batch updates/inserts of everything in the queues related to a subcollection.

        :return:
        """
        # make sure the subject collection is up to date first (avoids missing FK issues)
        self.finalize_populate_subject_collection()
        if self.subcollection_insert_queue:
            with self.engine.begin() as conn:
                data = self._make_dicts_the_same(self.subcollection_insert_queue)
                conn.execute(insert(self.table), data)
        if self.subcollection_lookup_insert_queue:
            with self.engine.begin() as conn:
                for (
                    concept_id,
                    insert_data,
                ) in self.subcollection_lookup_insert_queue.items():
                    lookup_table = self.subcollection_lookup_tables[concept_id]
                    conn.execute(insert(lookup_table), insert_data)
        if self.m2m_table_insert_queue:
            with self.engine.begin() as conn:
                conn.execute(insert(self.m2m_table), self.m2m_table_insert_queue)
        self.subcollection_insert_queue = []
        self.subcollection_lookup_insert_queue = {}
        self.m2m_table_insert_queue = []

    def _add_alt_subject_ids(self, subject_id, alt_subject_ids):
        if not alt_subject_ids:
            return
        for id_name, id_value in alt_subject_ids.items():
            id_value = str(id_value)
            if self.subject_lookup.get(id_name) is None:
                self.subject_lookup[id_name] = {}
            if self.subject_lookup[id_name].get(id_value) is None:
                self.alt_subject_id_insert_queue.append(
                    {
                        "_subject_id": subject_id,
                        "id_name": id_name,
                        "id_value": id_value,
                    }
                )
                self.subject_lookup[id_name][id_value] = subject_id
            elif self.subject_lookup[id_name][id_value]:
                self.alt_subject_id_update_queue.append(
                    {
                        "_subject_id": subject_id,
                        "id_name": id_name,
                        "id_value": id_value,
                    }
                )
                self.subject_lookup[id_name][id_value] = subject_id

    def add_value_to_subject_record(self, record, subject_id, concept_id, value):
        if self.subject_lookup_concept_mapping.get(concept_id) is not None:
            self.add_to_lookup_queue(self.subject_collection, subject_id, concept_id, value)
            # complex values are stored in more than one field
        elif isinstance(value, dict):
            x = self._map_complex_value(concept_id, value)
            record = {**record, **x}
            # standard values
        else:
            record[concept_id] = value
        return record

    def add_value_to_subcollection_record(self, record, collection_id, concept_id, value):
        if self.subcollection_lookup_concept_mapping.get(concept_id) is not None:
            self.add_to_lookup_queue(self.subcollection, collection_id, concept_id, value)
        # complex values are stored in more than one field
        elif isinstance(value, dict):
            x = self._map_complex_value(concept_id, value)
            record = {**record, **x}
        # standard values
        else:
            record[concept_id] = value
        return record

    def add_to_lookup_queue(self, oCollection, collection_id, concept_name, values):
        if not isinstance(values, list):
            values = [values]
        if oCollection.is_root_collection:
            queue = self.subject_lookup_insert_queue
        else:
            queue = self.subcollection_lookup_insert_queue
        if queue.get(concept_name) is None:
            queue[concept_name] = []
        insert_data_base = {
            "_collection_id": collection_id,
        }
        for value in values:
            if isinstance(value, dict):
                x = self._map_complex_value(concept_name, value)
                new_record = {**insert_data_base, **x}
            else:
                new_record = {**insert_data_base}
                new_record[concept_name] = value
            queue[concept_name].append(new_record)

    def _make_dicts_the_same(self, insert_list):
        """For bulk inserts, all dicts must have same set of keys."""
        # TODO: it might be better to handle this when the dicts are generated
        keys = set()
        response = []
        for entry in insert_list:
            keys.update(entry.keys())
        for entry in insert_list:
            for key in keys:
                # .get defaults to None if doesn't exist
                # so just try to .get it
                entry[key] = entry.get(key)
            response.append(entry)
        return response

    def _map_complex_value(self, concept_id, value):
        response = {}
        for subcolumn, subvalue in value.items():
            response[f"{concept_id}__{subcolumn}"] = subvalue
        response[concept_id] = json.dumps(value)
        return response

    def _generate_subject_lookup_dict(self):
        """will be a nested dict, first key is id name, second key is id value, value
        is subject_id in database"""
        self.subject_lookup = {}
        try:
            stmt = select(self.subject_id_table)
            with self.engine.connect() as conn:
                result = conn.execute(stmt)
                for row in result:
                    subject_id = row[1]
                    id_name = row[2]
                    id_value = row[3]
                    if self.subject_lookup.get(id_name) is None:
                        self.subject_lookup[id_name] = {}
                    self.subject_lookup[id_name][id_value] = subject_id
        except ProgrammingError:
            # ignore this whole step if the table doesn't exist yet
            pass

import sys

from sqlalchemy import create_engine
from sqlalchemy import MetaData, Table, Column, ForeignKey, Identity
from sqlalchemy import Integer, String, Date, Text, Float, Boolean, BigInteger
from sqlalchemy.dialects import postgresql
from django.core.management import get_commands

from chiron import chiron_settings
from chiron.models import CollectionRelationship


# will allow only one singeton engine for each schema name
singleton_engines = {}
# Engines can actually be replaced, which helps avoid timeout errors. But we don't destroy the
# angines (and their db connections) right away since they might be in used somewhere else in the
# code. Instead, we append them to this list. This maintains a reference to them in case
# we do want to eventually destroy them.
discontinued_engines = []

# keep a list of chiron management commands to allow custom handling based on context
chiron_commands = [command[0] for command in get_commands().items() if command[1] == "chiron"]


def get_schema_name_for_dataset(oDataset, use_staging=False):
    """Get the postgres schema where the specified dataset will be stored.

    :param obj oDataset: Django model object
    :return: schema name
    :rtype: str
    """
    schema_name = oDataset.get_actual_database_name()
    if use_staging:
        schema_name = f"{schema_name}_staging"
    return schema_name


def get_connection_settings(oDataset, use_staging):
    """Returns custom setting values for the db connection based on context."""
    # limit the pool size to 1 if we're running any chiron management command
    using_mgmt_command = any(x in sys.argv for x in chiron_commands)
    if using_mgmt_command:
        limit_pool = True
        addl_options = chiron_settings.CHIRON_PG_CONN_OPTIONS_MGMT
    else:
        limit_pool = False
        addl_options = chiron_settings.CHIRON_PG_CONN_OPTIONS_SITE
    pool_size = 1 if limit_pool else 5
    # max overflow is always 10
    max_overflow = 10
    # options_str will include the schema and any other custom settings
    # from CHIRON_PG_CONN_OPTIONS_MGMT or CHIRON_PG_CONN_OPTIONS_SITE
    schema_name = get_schema_name_for_dataset(oDataset, use_staging)
    options_str = "-csearch_path={}".format(schema_name)
    for key, val in addl_options.items():
        options_str += " --{}={}".format(key, str(val))
    return options_str, pool_size, max_overflow


def get_sql_alchemy_db_engine(oDataset, use_staging=False):
    """Get the SQL Alchemy db engine for the specified dataset.

    :param obj oDataset: Django model object
    :return: SLQ alchemy engine
    """
    schema_name = get_schema_name_for_dataset(oDataset, use_staging)
    if schema_name not in singleton_engines:
        options_str, pool_size, max_overflow = get_connection_settings(oDataset, use_staging)
        singleton_engines[schema_name] = create_engine(
            chiron_settings.CHIRON_SQL_ALCHEMY_CONNECTION_STRING,
            connect_args={"options": options_str},
            pool_size=pool_size,
            max_overflow=max_overflow,
        )
    return singleton_engines[schema_name]


def refresh_sql_alchemy_db_engine(oDataset, use_staging=False):
    """Refresh the SQL Alchemy db engine for the specified dataset.

    A refresh would be run to avoid a database connection timeout. This is useful
    on very long processes where some db connections might sit inactive for a while.

    :param obj oDataset: Django model object
    :param bool use_staging: Use the staging schema for this database connection
    :return: SLQ alchemy engine
    """
    schema_name = get_schema_name_for_dataset(oDataset, use_staging)
    options_str, pool_size, max_overflow = get_connection_settings(oDataset, use_staging)
    singleton_engines[schema_name] = create_engine(
        chiron_settings.CHIRON_SQL_ALCHEMY_CONNECTION_STRING,
        connect_args={"options": options_str},
        pool_size=pool_size,
        max_overflow=max_overflow,
    )
    return singleton_engines[schema_name]


def dispose_of_all_db_engines():
    """Dispose of all SQL Alchemy engines that were created.

    This will close any SQL Alchemy connections that we made to the database.
    It is useful when we want to drop a database, because open connections will
    block that action.
    """
    for engine in discontinued_engines:
        engine.dispose()
    for engine in singleton_engines.values():
        engine.dispose()


def get_sql_alchemy_column_data_type(data_type):
    """Get a SQl Alchemy datatype object for the specified data type.

    For varchar, pass a tuple with the max length like ("varchar", 20).

    :param str data_type: The type of data ("date", "integer", etc.).
    :return: SQl Alchemy datatype object
    """
    if isinstance(data_type, tuple) and data_type[0] == "array":
        inner_type = get_sql_alchemy_column_data_type(data_type[1])
        return postgresql.ARRAY(inner_type, dimensions=1)
    if isinstance(data_type, tuple) and data_type[0] == "varchar":
        return String(data_type[1])
    if data_type == "date":
        return Date
    if data_type == "integer":
        return BigInteger
    if data_type == "float":
        return Float
    if data_type == "boolean":
        return Boolean
    return Text


def generate_sql_alchemy_table_for_subject_collection(
    oCollection, metadata_obj=None, relevant_concept_ids=None
):
    """Get a SQL Alchemy table for subject data.

    The relevant_concept_ids list can be used to filter the columns to include in the SQL
    Alchemy table object. This is for performance, since creating a wide SQL Alchemy table can
    take a while.

    :param obj oCollection: the Django model object for the subject collection
    :param obj metadata_obj: Optionally specify a SQL Alchemy metadata_obj to use.
    :param list relevant_concept_ids: A list of concept ID strings that might be referenced by
      this query, or None to include all columns.
    :return: SQL alchemy table object for the subject table
    """
    # create the sql alchemy table
    if not metadata_obj:
        metadata_obj = MetaData()
    subject_table = Table(
        oCollection.permanent_id,
        metadata_obj,
        Column("_id", String(120), primary_key=True),
        Column("_subject_id", String(120), nullable=False, index=True),
        # Column("id", String(120), nullable=True, index=True),
    )
    # append a column for each concept
    qConcept = oCollection.concept_set.filter(published=True, multivalue=False)
    if relevant_concept_ids is not None:
        if oCollection.event_date_field:
            relevant_concept_ids.append(oCollection.event_date_field.permanent_id)
        if oCollection.event_end_date_field:
            relevant_concept_ids.append(oCollection.event_end_date_field.permanent_id)
        qConcept = qConcept.filter(permanent_id__in=relevant_concept_ids)
    for oConcept in qConcept:
        concept_handler = oConcept._instantiate_concept_handler(chironuser=None)
        data_type = concept_handler.get_stored_data_type()
        if isinstance(data_type, dict):
            column = Column(
                oConcept.permanent_id,
                Text,
            )
            subject_table.append_column(column)
            for subcolumn, sub_data_type in data_type.items():
                column = Column(
                    f"{oConcept.permanent_id}__{subcolumn}",
                    get_sql_alchemy_column_data_type(sub_data_type),
                )
                subject_table.append_column(column)
        else:
            column = Column(
                oConcept.permanent_id,
                get_sql_alchemy_column_data_type(data_type),
            )
            subject_table.append_column(column)

    return subject_table


def generate_sql_alchemy_table_for_subject_identification(oCollection, metadata_obj=None):
    """Get a SQL Alchemy table for subject ID data.

    The Subject ID data is stored in a separate table because there can be multiple values
    for a subject.

    :param obj oCollection: the Django model object for the subject collection
    :param obj metadata_obj: Optionally specify a SQL Alchemy metadata_obj to use.
    :return: SQL alchemy table object for the subject ID table
    """
    if not metadata_obj:
        metadata_obj = MetaData()
    subject_pk = f"{oCollection.permanent_id}._id"
    subject_identification_table = Table(
        "subject_identification",
        metadata_obj,
        Column("_id", Integer, Identity(start=42, cycle=True), primary_key=True),
        Column(
            "_subject_id", ForeignKey(subject_pk, ondelete="CASCADE"), nullable=False, index=True
        ),
        Column("id_name", String(60), nullable=True, index=True),
        Column("id_value", String(120), nullable=True, index=True),
    )
    return subject_identification_table


def generate_sql_alchemy_lookup_table_for_concept(oConcept, metadata_obj=None):
    """Get a SQL Alchemy lookup table for a concept.

    Lookup tables are used when a collection record can have multiple values for the same
    concept. For example, an encounter collection with reason for visit where multiple reasons
    could be provided.

    :param obj oConcept: the Django model object for the concept
    :param obj metadata_obj: Optionally specify a SQL Alchemy metadata_obj to use.
    :return: SQL alchemy table object for the concept lookup table
    """
    if not metadata_obj:
        metadata_obj = MetaData()
    concept_handler = oConcept._instantiate_concept_handler(chironuser=None)
    data_type = concept_handler.get_stored_data_type()
    table_name = f"lkp_{oConcept.permanent_id}"
    parent_table_name = f"{oConcept.collection.permanent_id}._id"
    table = Table(
        table_name,
        metadata_obj,
        Column(
            "_id",
            Integer,
            Identity(start=1, cycle=True),
            primary_key=True,
        ),
        Column(
            "_collection_id",
            ForeignKey(parent_table_name, ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    if isinstance(data_type, dict):
        column = Column(
            oConcept.permanent_id,
            Text,
        )
        table.append_column(column)
        for subcolumn, sub_data_type in data_type.items():
            column = Column(
                f"{oConcept.permanent_id}__{subcolumn}",
                get_sql_alchemy_column_data_type(sub_data_type),
            )
            table.append_column(column)
    else:
        column = Column(
            oConcept.permanent_id,
            get_sql_alchemy_column_data_type(data_type),
        )
        table.append_column(column)
    return table


def generate_sql_alchemy_lookup_tables_for_collection(oCollection, metadata_obj=None):
    """Get all SQL Alchemy lookup tables for a collection.

    Any concepts that are multivalue need to allow multiple values per record. In postgres, this is
    accomplished using a lookup table. Each concept will get its own lookup table instead of
    getting a field in the collection table.

    :param obj oCollection: the Django model object for the collection
    :param obj metadata_obj: Optionally specify a SQL Alchemy metadata_obj to use.
    :return: list of SQL alchemy table objects
    """
    if not metadata_obj:
        metadata_obj = MetaData()
    tables = {}
    for oConcept in oCollection.concept_set.filter(published=True, multivalue=True):
        table = generate_sql_alchemy_lookup_table_for_concept(oConcept, metadata_obj)
        tables[oConcept.permanent_id] = table
    return tables


def get_lookup_concept_mapping(oCollection):
    """Get a dict with the names of all lookup tables associated with a collection.

    :param obj oCollection: the Django model object for the collection
    :return: A dictionary with key = concept ID and value = lookup table name
    """
    mapping = {}
    for oConcept in oCollection.concept_set.filter(published=True, multivalue=True):
        table_name = f"lkp_{oConcept.permanent_id}"
        mapping[oConcept.permanent_id] = table_name
    return mapping


def generate_m2m_table_for_m2m_subcollection(oCollection, metadata_obj=None):
    """Get the table that makes a subcollection M2M with a subject.

    The is for the table that goes inbetween a subcollection table and a subject table.
    This table is also returned from generate_sql_alchemy_table_for_subcollection(), so
    you are not likely to have to call this function directly.

    :param obj oCollection: the Django model object for the collection
    :param obj metadata_obj: Optionally specify a SQL Alchemy metadata_obj to use.
    :rtype: The M2M table that links an M2M subcollection to the subject.
    """
    if not oCollection.many_to_many_with_subject:
        return None
    if not metadata_obj:
        metadata_obj = MetaData()
    subject_collection = oCollection.dataset.root_collection
    subject_pk = f"{subject_collection.permanent_id}._id"
    subcollection_pk = f"{oCollection.permanent_id}._id"
    table = Table(
        f"m2m_subject_{oCollection.permanent_id}",
        metadata_obj,
        Column(
            "_id",
            Integer,
            Identity(start=1, cycle=True),
            primary_key=True,
        ),
        Column(
            "_subject_id", ForeignKey(subject_pk, ondelete="CASCADE"), nullable=False, index=True
        ),
        Column(
            "_collection_id",
            ForeignKey(subcollection_pk, ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    return table


def generate_sql_alchemy_table_for_subcollection(
    oCollection, metadata_obj=None, relevant_concept_ids=None
):
    """Get a SQL Alchemy table for a subollection.

    The relevant_concept_ids list can be used to filter the columns to include in the SQL
    Alchemy table object. This is for performance, since creating a wide SQL Alchemy table can
    take a while.

    :param obj oCollection: the Django model object for the collection
    :param obj metadata_obj: Optionally specify a SQL Alchemy metadata_obj to use.
    :param list relevant_concept_ids: A list of concept ID strings that might be referenced by
      this query, or None to include all columns.
    :return: SQL alchemy table object for the table
    :rtype: tuple with subcollection table and optionally a M2M table that links the
      subcollection to the subject. If not M2M, this second value will be None.
    """
    # create the sql alchemy table, returns (table, m2m_table) where m2m_table might be None
    if not metadata_obj:
        metadata_obj = MetaData()
    subject_collection = oCollection.dataset.root_collection
    subject_pk = f"{subject_collection.permanent_id}._id"
    table = Table(
        oCollection.permanent_id,
        metadata_obj,
        Column("_id", String(120), primary_key=True),
    )
    if oCollection.many_to_many_with_subject:
        m2m_table = generate_m2m_table_for_m2m_subcollection(oCollection, metadata_obj)
    else:
        m2m_table = None
        column = Column(
            "_subject_id", ForeignKey(subject_pk, ondelete="CASCADE"), nullable=False, index=True
        )
        table.append_column(column)
    # append a column for each concept that isn't multivalue
    qConcept = oCollection.concept_set.filter(published=True, multivalue=False)
    if relevant_concept_ids is not None:
        if oCollection.event_id_field:
            relevant_concept_ids.append(oCollection.event_id_field.permanent_id)
        if oCollection.event_date_field:
            relevant_concept_ids.append(oCollection.event_date_field.permanent_id)
        if oCollection.event_end_date_field:
            relevant_concept_ids.append(oCollection.event_end_date_field.permanent_id)
        for oRel in CollectionRelationship.objects.filter(pk_concept__collection=oCollection):
            relevant_concept_ids.append(oRel.pk_concept.permanent_id)
        for oRel in CollectionRelationship.objects.filter(fk_concept__collection=oCollection):
            relevant_concept_ids.append(oRel.fk_concept.permanent_id)
        qConcept = qConcept.filter(permanent_id__in=relevant_concept_ids)
    for oConcept in qConcept:
        concept_handler = oConcept._instantiate_concept_handler(chironuser=None)
        data_type = concept_handler.get_stored_data_type()
        if isinstance(data_type, dict):
            column = Column(
                oConcept.permanent_id,
                Text,
                index=True,
            )
            table.append_column(column)
            for subcolumn, sub_data_type in data_type.items():
                column = Column(
                    f"{oConcept.permanent_id}__{subcolumn}",
                    get_sql_alchemy_column_data_type(sub_data_type),
                )
                table.append_column(column)
        else:
            column = Column(
                oConcept.permanent_id,
                get_sql_alchemy_column_data_type(data_type),
            )
            table.append_column(column)

    return table, m2m_table


def generate_sql_alchemy_table_for_concept_search(metadata_obj=None):
    if not metadata_obj:
        metadata_obj = MetaData()
    concept_search_table = Table(
        "concept_search",
        metadata_obj,
        Column("id", Integer, Identity(start=1, cycle=True), primary_key=True),
        Column(
            "concept_id",
            Text(),
            nullable=False,
        ),
        Column("concept_name", Text(), index=True),
        Column("concept_description", Text(), index=True),
        Column("categories", Text(), index=True),
        Column("other_search_terms", Text(), index=True),
        Column("ngram_search", Text(), index=True),
    )

    return concept_search_table

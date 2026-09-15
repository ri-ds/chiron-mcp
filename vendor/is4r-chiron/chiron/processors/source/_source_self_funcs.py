from sqlalchemy import select, func

from chiron.query_engine.postgres import database
from chiron.models import Collection


def get_subjects(oDataset, use_staging):
    """
    Yields a list of subject records. These are structured to match the old
    MongoDB subject documents (to preserve backwards compatibility).
    """
    oSubject = oDataset.root_collection
    engine = database.refresh_sql_alchemy_db_engine(oDataset, use_staging)
    subject_table = database.generate_sql_alchemy_table_for_subject_collection(oSubject)
    alt_ids_table = database.generate_sql_alchemy_table_for_subject_identification(oSubject)
    fields = _get_all_fields_for_collection(oSubject, subject_table)
    stmt = select(*fields)
    with engine.begin() as conn:
        result = conn.execute(stmt)
    with engine.begin() as conn:
        for row in result.mappings():
            dict_row = dict(row)
            # need to append subject IDs using format matching old mongodb structure
            stmt2 = select(alt_ids_table.c.id_name, alt_ids_table.c.id_value)
            stmt2 = stmt2.select_from(alt_ids_table)
            stmt2 = stmt2.where(alt_ids_table.c._subject_id == dict_row["_subject_id"])
            result2 = conn.execute(stmt2)
            dict_row["_ids"] = {}
            for row2 in result2:
                dict_row["_ids"][row2[0]] = row2[1]
            yield dict_row


def get_subjects_with_subcollection_data(
    oDataset, subcollection_id, use_staging, sort_concept_id=None
):
    """
    Yields a list of doc/subdocs dicts where doc is one subject document and subdocs is all
    subcollection documents associated with that subject
    """
    oCollection = Collection.objects.get(dataset=oDataset, permanent_id=subcollection_id)
    table, m2m_table = database.generate_sql_alchemy_table_for_subcollection(oCollection)
    subcol_fields = _get_all_fields_for_collection(oCollection, table)
    base_subcol_stmt = select(*subcol_fields)
    engine = database.refresh_sql_alchemy_db_engine(oDataset, use_staging)
    with engine.begin() as conn:
        for subject_doc in get_subjects(oDataset, use_staging):
            response = {"doc": subject_doc}
            subcol_stmt = base_subcol_stmt.where(table.c._subject_id == subject_doc["_subject_id"])
            if sort_concept_id:
                subcol_stmt = subcol_stmt.order_by(sort_concept_id)
            result = conn.execute(subcol_stmt)
            if result.rowcount > 0:
                subdocs = result.mappings()
                response["subdocs"] = subdocs
                yield response


def get_subdocuments(oCollection, use_staging, include_related_subdocs=False):
    """
    Yields a list of subcollection records. These are structured to match the
    old MongoDB subcollection documents (to preserve backwards compatibility).
    """
    # actually will iterate subjects instead of subdocs
    records = get_subjects_with_subcollection_data(
        oCollection.dataset, oCollection.permanent_id, use_staging
    )
    for record in records:
        try:
            for subdoc in record["subdocs"]:
                if include_related_subdocs:
                    yield {
                        "doc": record["doc"],
                        "subdoc": subdoc,
                        "subdocs": record["subdocs"],
                    }
                else:
                    yield {
                        "doc": record["doc"],
                        "subdoc": subdoc,
                    }
        except AttributeError:
            # Sometimes get error "'NoneType' object has no attribute 'fetchone'".
            # It seems to be trying to continue past the end of the record["subdocs"]
            # MappingResult iterable.
            # I don't understand why it does this (sql alchemy bug) but it shouldn't cause any
            # problems to simply ignore the error and continue.
            pass
    return None


def _get_all_fields_for_collection(oCollection, collection_table):
    fields = [collection_table.c._id, collection_table.c._subject_id]
    for oConcept in oCollection.concept_set.filter(published=True):
        if oConcept.multivalue:
            # TODO: what about complex data types?
            lookup_table = database.generate_sql_alchemy_lookup_table_for_concept(oConcept)
            field = getattr(lookup_table.c, oConcept.permanent_id)
            subq = (
                select(func.json_agg(field))
                .where(lookup_table.c._collection_id == collection_table.c._id)
                .scalar_subquery()
            )
            fields.append(subq.label(oConcept.permanent_id))
        else:
            # TODO: what about complex data types?
            field = getattr(collection_table.c, oConcept.permanent_id)
            fields.append(field)
    return fields

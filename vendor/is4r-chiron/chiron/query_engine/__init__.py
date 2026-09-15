from chiron.query_engine.postgres.querytool import QueryToolPostgres
from chiron.query_engine.postgres.stattool import StatToolPostgres
from chiron.query_engine.postgres.db_writer import DbWriterPostgres


def get_querytool(
    chironuser,
    cohort_def,
    table_def=None,
    analyze_performance=True,
    analyze_data=False,
    cache_mode="rw",
):
    """A factory function to get a QueryTool object.

    Currently the only option is QueryToolPostgres.

    :param chironuser:
    :param cohort_def:
    :param table_def:
    :param analyze_performance:
    :param analyze_data:
    :param cache_mode:
    :return:
    """
    return QueryToolPostgres(
        chironuser, cohort_def, table_def, analyze_performance, analyze_data, cache_mode
    )


def get_stattool(
    chironuser,
    cohort_def=None,
    concept=None,
    collection_prefilters=None,
    analyze_performance=True,
    analyze_data=False,
):
    """A factory function to get a StatTool object.

    Currently the only option is StatToolPostgres.

    :param chironuser:
    :param cohort_def:
    :param concept:
    :param collection_prefilters:
    :param analyze_performance:
    :param analyze_data:
    :return:
    """
    return StatToolPostgres(
        chironuser, cohort_def, concept, collection_prefilters, analyze_performance, analyze_data
    )


def get_db_writer(oDataset, use_staging, oCollection=None):
    """A factory function to get a DbWriter object.

    Currently the only option is DbWriterPostgres.

    :param oDataset:
    :param use_staging:
    :param oCollection:
    :return:
    """
    return DbWriterPostgres(oDataset, use_staging, oCollection)

from chiron.query_engine.postgres.sql_alchemy_queries.aggregation.average import PgAggAverage
from chiron.query_engine.postgres.sql_alchemy_queries.aggregation.sum import PgAggSum
from chiron.query_engine.postgres.sql_alchemy_queries.aggregation.count_all import PgAggCountAll
from chiron.query_engine.postgres.sql_alchemy_queries.aggregation.count_distinct import (
    PgAggCountDistinct,
)
from chiron.query_engine.postgres.sql_alchemy_queries.aggregation.earliest import PgAggEarliest
from chiron.query_engine.postgres.sql_alchemy_queries.aggregation.has_value import PgAggHasValue
from chiron.query_engine.postgres.sql_alchemy_queries.aggregation.has_value_text import (
    PgAggHasValueText,
)
from chiron.query_engine.postgres.sql_alchemy_queries.aggregation.latest import PgAggLatest
from chiron.query_engine.postgres.sql_alchemy_queries.aggregation.list_all import PgAggListAll
from chiron.query_engine.postgres.sql_alchemy_queries.aggregation.list_distinct import (
    PgAggListDistinct,
)
from chiron.query_engine.postgres.sql_alchemy_queries.aggregation.max import PgAggMax
from chiron.query_engine.postgres.sql_alchemy_queries.aggregation.max_date import PgAggMaxDate
from chiron.query_engine.postgres.sql_alchemy_queries.aggregation.median import PgAggMedian
from chiron.query_engine.postgres.sql_alchemy_queries.aggregation.min import PgAggMin
from chiron.query_engine.postgres.sql_alchemy_queries.aggregation.min_date import PgAggMinDate
from chiron.query_engine.postgres.sql_alchemy_queries.aggregation.most_frequent import (
    PgAggMostFrequent,
)
from chiron.query_engine.postgres.sql_alchemy_queries.aggregation.std_dev import PgAggStdDev


def get_postgres_aggregator(chironuser, field):
    method_lookup = {
        "sum": PgAggSum,
        "min": PgAggMin,
        "max": PgAggMax,
        "min_date": PgAggMinDate,
        "max_date": PgAggMaxDate,
        "count_distinct": PgAggCountDistinct,
        "list_distinct": PgAggListDistinct,
        "earliest": PgAggEarliest,
        "latest": PgAggLatest,
        "has_value": PgAggHasValue,
        "has_value_text": PgAggHasValueText,
        "average": PgAggAverage,
        "count_all": PgAggCountAll,
        "list_all": PgAggListAll,
        "median": PgAggMedian,
        "most_frequent": PgAggMostFrequent,
        "std_dev": PgAggStdDev,
    }
    agg_method = field["aggregation_method"]
    klass = method_lookup[agg_method]
    return klass(chironuser, field)

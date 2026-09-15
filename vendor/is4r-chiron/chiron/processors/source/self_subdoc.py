from chiron.processors.abstract import SourceProcessor, StandardLoadMixin
from chiron import chiron_settings
from chiron.processors.source._source_self_funcs import get_subdocuments


class SourceSelfSubdoc(StandardLoadMixin, SourceProcessor):
    """
    SourceSelfSubdoc for systems using RDBMS instead of Mongodb
    """

    def __init__(
        self,
        oSource,
        include_related_subdocs=False,
    ):
        super().__init__(oSource)
        self.source = oSource
        self.include_related_subdocs = include_related_subdocs

    def get_source(self):
        use_staging = chiron_settings.CHIRON_USE_STAGING_DURING_ETL
        iterator = get_subdocuments(
            self.source.collection, use_staging, self.include_related_subdocs
        )
        return iterator

    def check_source_format(self):
        return "chiron subcollection"

    def get_subject_match_def(self, record):
        subject_match_def = {
            "match_rule": {"_id": record["doc"]["_id"]},
        }
        return subject_match_def

    def get_subject_id_fields_used_for_matching(self):
        """
        Matching is done using the root _id for the record, so we just say None for
        matching
        """
        return None

    def get_subject_id_fields_added(self):
        return None

    def get_collection_id(self, record):
        return record["subdoc"]["_id"]

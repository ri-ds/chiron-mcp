from chiron.processors.abstract import SourceProcessor, StandardLoadMixin
from chiron import chiron_settings
from chiron.processors.source._source_self_funcs import get_subjects


class SourceSelf(StandardLoadMixin, SourceProcessor):
    """
    Pulls all records from the Chiron research database itself.
    Useful for generating calculated fields on existing records.
    Needs to be run later in execution order, when all the input fields
    it depends on have already been loaded.
    """

    def get_source(self):
        oDataset = self.source.collection.dataset
        use_staging = chiron_settings.CHIRON_USE_STAGING_DURING_ETL
        return get_subjects(oDataset, use_staging)

    def check_source_format(self):
        return "chiron subject collection"

    def get_subject_match_def(self, record):
        subject_match_def = {
            "match_rule": {"_id": record["_id"]},
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
        return record["_id"]

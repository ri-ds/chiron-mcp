from chiron.processors.abstract import EtlProcessor
from chiron.processors.etl.clean_value import SimpleClean


class EtlChironSubjectId(EtlProcessor):
    """
    During the ETL, Chiron collects subject IDs in the subject collection "_ids" field. The
    purpose of subject IDs is to match source records to existing subjects as they are loaded.
    But sometimes, you may also want to expose a subject ID field to your users. This ETL
    processor allows you to do that by copying a subject ID into a concept.

    This should be run with SourceSelf at or near the end of your ETL - after all the subject IDs
    have been loaded.

    :param subject_id_name: the key value for the field you want
    :type subject_id_name: str
    :param cast_to_type: the Django field name
    :type cast_to_type: str, optional (int, float, string, date)
    :param ignore_casting_errors: If cast_to_type fails, returns None instead of throwing an error
    :type ignore_casting_errors: boolean, optional (default=False)
    """

    def __init__(
        self,
        oConcept,
        subject_id_name,
        cast_to_type=None,
        ignore_casting_errors=False,
    ):
        super().__init__(oConcept)
        self.concept = oConcept
        self.warnings = []
        self.subject_id_name = subject_id_name
        self.cast_to_type = cast_to_type  # int, float, str, date
        self.ignore_casting_errors = ignore_casting_errors
        self.data_cleaner = SimpleClean(self.cast_to_type)

    def pull_concept_value_from_record(self, doc):
        """
        Retrieves value `self.field_name` from the "_ids" field in a record.
        """
        value = doc.get("_ids", {}).get(self.subject_id_name, None)
        # if key missing from dict, return None
        if value is None:
            self._add_warning(
                value, f"subject ID `_ids.{self.subject_id_name}` was not defined in the doc"
            )
            return None

        # clean value(s) and get any data warnings
        cleaned_val = self.data_cleaner.clean(value)
        for inval, warning in self.data_cleaner.get_warnings():
            self._add_warning(inval, warning)

        return cleaned_val

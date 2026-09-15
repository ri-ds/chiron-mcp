from chiron.processors.abstract import EtlProcessor
from chiron.processors.etl.clean_value import SimpleClean, CurrentAgeClean
from chiron.processors.utils import DjangoModelObjectValueRetriever


class EtlDjangoField(EtlProcessor):
    """
    Use with a source of Django models. Will pull a single field value from each
    model object.

    :param django_field: full path name from the source model to the Django field
    :type django_field: str
    :param cast_to_type: the Django field name
    :type cast_to_type: str, optional (int, float, string, date)
    :param ignore_casting_errors: If cast_to_type fails, returns None instead of throwing an error
    :type ignore_casting_errors: boolean, optional (default=False)
    :param ignore_model_mismatch: returns None instead of error if specified model or field don't
      exist
    :type ignore_model_mismatch: boolean, optional (default=False)
    """

    def __init__(
        self,
        oConcept,
        django_field,
        cast_to_type=None,
        ignore_casting_errors=False,
        ignore_model_mismatch=False,
    ):
        super().__init__(oConcept)
        self.concept = oConcept
        self.warnings = []
        self.full_field_name = django_field
        self.cast_to_type = cast_to_type  # int, float, str, date
        self.ignore_casting_errors = ignore_casting_errors
        self.ignore_model_mismatch = bool(ignore_model_mismatch)
        if self.cast_to_type == "current_age":
            self.data_cleaner = CurrentAgeClean()
        else:
            self.data_cleaner = SimpleClean(self.cast_to_type)
        self.retriever = DjangoModelObjectValueRetriever(
            self.full_field_name, ignore_model_mismatch=self.ignore_model_mismatch
        )

    def pull_concept_value_from_record(self, oRecord):
        """
        Reads a single record and returns the final value to store in the research database
        """
        # use the retriever to get the field value(s)
        raw = self.retriever(oRecord)
        if raw == "***missing***":
            self._add_warning(
                None, f"field {self.full_field_name} was not defined in the model object"
            )
            raw = None
        # clean value(s) and get any data warnings
        cleaned_val = self.data_cleaner.clean(raw)
        for inval, warning in self.data_cleaner.get_warnings():
            self._add_warning(inval, warning)
        return cleaned_val

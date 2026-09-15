from chiron.processors.abstract import EtlProcessor
from chiron.processors.etl.clean_value import SimpleClean, CurrentAgeClean


class EtlPythonDictItem(EtlProcessor):
    """
    Use with a source that returns a Python dictionary.

    :param field_name: the key value for the field you want
    :type field_name: str
    :param cast_to_type: the Django field name
    :type cast_to_type: str, optional (int, float, string, date)
    :param ignore_casting_errors: If cast_to_type fails, returns None instead of throwing an error
    :type ignore_casting_errors: boolean, optional (default=False)
    :param convert_list_to_set: if field has a list of multiple values, only get distinct set
    :type convert_list_to_set: boolean, optional (default=True)
    :param string_val_separator: if field has a list of multiple values, only get distinct set
    :type string_val_separator: string, optional (default=None)
    """

    def __init__(
        self,
        oConcept,
        field_name,
        cast_to_type=None,
        ignore_casting_errors=False,
        convert_list_to_set=True,
        string_val_separator=None,
    ):
        super().__init__(oConcept)
        self.concept = oConcept
        self.warnings = []
        self.field_name = field_name
        self.cast_to_type = cast_to_type  # int, float, str, date
        self.ignore_casting_errors = ignore_casting_errors
        self.convert_list_to_set = convert_list_to_set
        self.string_val_separator = string_val_separator
        if self.cast_to_type == "current_age":
            self.data_cleaner = CurrentAgeClean(self.convert_list_to_set)
        else:
            self.data_cleaner = SimpleClean(self.cast_to_type, self.convert_list_to_set)

    def pull_concept_value_from_record(self, record):
        """
        Retrieves value `self.field_name` from provided dict `record` and converts to the value to
        store in the research database.
        """
        # if key missing from dict, return None
        if self.field_name not in record:
            self._add_warning(None, f"field {self.field_name} was not defined in the record dict")
            return None

        # get value(s)
        raw = record[self.field_name]
        if self.string_val_separator and isinstance(raw, str):
            raw = raw.split(self.string_val_separator)

        # clean value(s) and get any data warnings
        cleaned_val = self.data_cleaner.clean(raw)
        for inval, warning in self.data_cleaner.get_warnings():
            self._add_warning(inval, warning)

        return cleaned_val

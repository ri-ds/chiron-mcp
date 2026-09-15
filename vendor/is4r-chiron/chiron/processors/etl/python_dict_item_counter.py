from chiron.processors.abstract import EtlProcessor


class EtlPythonDictItemCounter(EtlProcessor):
    """
    Retrieves an item (usually a sequence) from a python dict and returns
    the length of the item as an integer.
    If field is not a sequence or collection, will return 1 if field evaluates to
    true and 0 if sequence evaluates to False.
    By default, a string value returns 1 instead of len(str). Pass
    treat_string_as_sequence=True to override.

    :param field_name: the key value for the field you want
    :type field_name: str
    :param treat_string_as_sequence: if string, return string length instead of 1
    :type treat_string_as_sequence: boolean, optional (default=False)
    """

    def __init__(self, oConcept, field_name, treat_string_as_sequence=False):
        super().__init__(oConcept)
        self.concept = oConcept
        self.field_name = field_name
        self.treat_string_as_sequence = treat_string_as_sequence

    def pull_concept_value_from_record(self, record):
        if self.field_name not in record:
            return 0
        raw = record[self.field_name]
        if isinstance(raw, str) and not self.treat_string_as_sequence:
            return 1 if raw else 0
        try:
            response = len(raw)
            return response
        except TypeError:
            return 1 if raw else 0

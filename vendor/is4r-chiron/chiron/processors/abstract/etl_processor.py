from abc import ABCMeta, abstractmethod


class EtlProcessor:
    """
    An ETL Processor is for a concept. During the ETL, the ETLProcessor gets
    a record from the source and returns the value to store for this concept in
    the research database.

    It is associated with a Concept in the data dictionary using the ``Concept.etl_processor``
    field.
    """

    __metaclass__ = ABCMeta

    def __init__(self, oConcept):
        self.concept = oConcept
        # Warnings about any issues while cleaning values (ex. whitespace was stripped)
        self.warnings = []

    @abstractmethod
    def pull_concept_value_from_record(self, record):
        """
        Retrieves or calculates the value to store in the research database from a source record.

        :param record: a single entry returned by ``Source.get_source()``
        :type record: various
        :return: the value to store in the research database
        :rtype: various
        """
        pass

    def pull_concept_value_from_record_with_warnings(self, record):
        """
        Wrapper for `pull_concept_value_from_record()`. For custom ETL processors, you shouldn't
        need to modify this method.

        If the system is logging warnings about data issues, this method will be called instead
        of pull_concept_value_from_record.
        """
        # reset warnings to remove any previous values
        self.warnings = []
        val = self.pull_concept_value_from_record(record)
        return val, self.warnings

    def _add_warning(self, value, warning):
        """
        Pass the relevant input value and the warning about it
        """
        self.warnings.append((value, warning))

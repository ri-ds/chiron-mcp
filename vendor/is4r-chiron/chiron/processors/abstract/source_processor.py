from abc import ABCMeta, abstractmethod
from datetime import datetime


class StandardLoadMixin:
    """
    Retrieves an entire source as an iterable and processes/loads
    to the research database one record at a time.
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def get_source(self):
        """
        Returns the entire source dataset as an iterable. Each entry in this iterable should
        corresponds to the associated ``Collection``. For example, a source data collection
        associated with a "sample" collection should return an iterable of samples.

        :return: an iterable dataset
        :rtype: various
        """
        raise NotImplementedError

    def check_source_format(self):
        """
        What is the format of the source iterable that gets returned

        The method get_source() must return an iterable, but that is the only restriction. This
        method can be used to describe that iterable. This allows code that uses source data to
        know what it's getting and modify its behavior accordingly.

        ex. "list of dicts", "queryset", "chiron subject collection"
        """
        return None

    @abstractmethod
    def get_subject_match_def(self, record):
        """
        Returns rules as a Python dict about how associate a new record with the correct
        subject in the research database.

        SPECIAL VALUES YOU CAN RETURN:

        If a simple ID value (string, integer):

        .. code-block:: python

            {
                "match_rule" : {"_ids.id" : value},
                "add_ids" : {"id" : value},
                "if_no_match" : "create",
            }

        If None, a new subject record will be created:

        .. code-block:: python

            {
                "match_rule" : {},
                "add_ids" : {},
                "if_no_match" : "create",
            }

        If False, the record will be skipped:

        .. code-block:: python

            {
                "match_rule" : {},
                "add_ids" : {},
                "if_no_match" : "skip",
            }

        Finally, there may be instances where a source record needs to be associated
        with multiple subjects (ex. m2m relationships). To do this, you can return a list of match
        definitions (or special values) and the ETL loaded will use all of them.

        :return: the match_def
        :rtype: python dict, str, integer, None, False, python list
        """
        raise NotImplementedError

    def get_subject_id_fields_used_for_matching(self):
        """
        Returns the names of any subject ID fields used to match records from this source
        to the correct subject. This is not required but can be useful for troubleshooting
        subject matching issues on datasets with many sources.

        :return: subject_id_fields
        :rtype: string, list of strings, or None
        """
        return None

    def get_subject_id_fields_added(self):
        """
        Returns the names of any subject ID fields added to Chiron _ids when these subjects
        are loaded. This is not required but can be useful for troubleshooting
        subject matching issues on datasets with many sources.

        :return: subject_id_fields
        :rtype: string, list of strings, or None
        """
        return None


class SourceProcessor:
    """
    Generates an iterable of data to import into the research database.

    Must be associated with the StandardLoadMixin. There used to be another mixin for loading,
    but it has been removed.

    It is associated with a Source in the data dictionary using the
    ``Source.processor`` field.
    """

    __metaclass__ = ABCMeta

    def __init__(self, oSource):
        self.source = oSource

    @abstractmethod
    def get_collection_id(self, record):
        """
        Reads one record from the source data collection and returns a unique ID for the record.

        For example, if this is a source of samples, could return a sample ID. If you
        had sample data in multiple sources, that sample ID could be used to merge
        data for the same sample.

        Collection IDs only apply to subcollections This method has no effect on a collection
        associated with the subject (root) collection.

        * If the ID matches an existing subdocument in the research database, data will be
          appended to that subdocument.
        * If no match, a new subdocument with the provided ID will be created.
        * If **None** is returned, a new subdocument with an auto ID will be created.
        * If **False** is returned, the data will not be added to the research database at all.

        :return: the record ID
        :rtype: str, integer, None, False
        """
        return None

    def get_data_last_updated_date(self):
        """
        Returns the datetime when this source was last updated.
        If this is a live data source, that will be now. If this is an archived data source, it
        will be whatever is the date last updated.
        """
        return datetime.now()

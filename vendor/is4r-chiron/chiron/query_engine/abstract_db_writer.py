from abc import ABC, abstractmethod


class DbWriter(ABC):
    """Handles interaction with the Chiron database during the ETL process.

    Has methods involved in preparing the database for the ETL, adding data to the database,
    checking the status of data in the database, and any finishing steps for the database after
    the ETL.

    :param oDataset: The Chiron dataset that will be written
    :type oDataset: model object
    :param use_staging: Whether a separate staging database should be used
    :type use_staging: bool
    :param oCollection: The Chiron collection to work with, can leave null if working with the
      subject collection or if not using relevant methods
    :type oCollection: model object
    """

    def __init__(self, oDataset, use_staging, oCollection=None):
        self.dataset = oDataset
        self.use_staging = use_staging
        self.collection = oCollection

    @abstractmethod
    def delete_existing_data(self, source=None):
        """Delete data in the database in preparation for reload.

        If a source is specified, deletes data related to that source. Otherwise deletes all
        data in the database. If self.use_staging=True, should only delete staging data.

        :param source: If only deleting a single source, the name of the source
        :type source: string, optional (default=None)
        :return: queryset of source(s) that were deleted
        :rtype: Django queryset
        """
        raise NotImplementedError("Mo method defined for delete_existing_data")

    def initialize_database(self, source, sources=[]):
        """Prepares a database for ETL process.

        Enables sharding if appropriate and performs any other steps needed prior to starting
        to load data. Note that this method does not truncate the database, use
        delete_existing_data instead.

        :param source: The single source to initialize
        :type source: string
        :param sources: The sources to generate the collections to initialize
        :type sources: list<Source>
        """
        pass

    @abstractmethod
    def insert_one_subject(self, record, alt_subject_ids):
        """Inserts one subject record with provided data.

        :param record: The subject data to be loaded where keys are concept permanent IDs and
          values are the values to be stored
        :type record: dict
        :param alt_subject_ids: Any alternative subject IDs to store where keys are the name of the
          subject ID (ex. "mrn") and values are the ID values for this subject.
        :type alt_subject_ids: dict
        :return: The subject ID of the created subject
        :rtype: various (string, int, object_id, etc.)
        """
        raise NotImplementedError("Abstract method has not been implemented")

    @abstractmethod
    def insert_empty_subject(self, alt_subject_ids):
        """Inserts a new subject with no data other than an ID and optional alternative IDs.

        This is used when loading a subcollection for a subject that doesn't exist yet.

        :param alt_subject_ids: Any alternative subject IDs to store where keys are the name of the
          subject ID (ex. "mrn") and values are the ID values for this subject.
        :type alt_subject_ids: dict
        :return: The subject ID of the created subject
        :rtype: various (string, int, object_id, etc.)
        """
        raise NotImplementedError("Abstract method has not been implemented")

    @abstractmethod
    def insert_one_subcollection(self, record, collection_id, subject_ids):
        """Inserts one subcollection record with provided data.

        :param record: The data to be loaded where keys are concept permanent IDs and
          values are the values to be stored
        :type record: dict
        :param collection_id: The ID of the collection, or None to autocreate collection ID,
          or False to skip this subcollection
        :type collection_id: various
        :param subject_ids: The ID or array of IDs for subject(s) that this subcollection should
          be associated with
        :type subject_ids: various
        :return: The ID of the created collection
        :rtype: various (usually string or int)
        """
        raise NotImplementedError("Abstract method has not been implemented")

    @abstractmethod
    def update_one_subject(self, match_rule, record, alt_subject_ids=None):
        """Updates one subject record identifed by provided match rule with provided data.

        :param match_rule: The definition of the subject(s) to update where the key is the
          subject field name to match (all specified fields must match)
        :type match_rule: dict
        :param record: The subject data to be loaded where keys are concept permanent IDs and
          values are the values to be stored
        :type record: dict
        :param alt_subject_ids: Any alternative subject IDs to store where keys are the name of the
          subject ID (ex. "mrn") and values are the ID values for this subject.
        :type alt_subject_ids: dict
        :return: The count of subjects that were updated
        :rtype: int
        """
        raise NotImplementedError("Abstract method has not been implemented")

    @abstractmethod
    def update_one_subcollection(self, record, collection_id, subject_ids):
        """Updates one subcollection record identifed by provided collection_id.

        :param record: The subcollection data to be loaded where keys are concept permanent IDs and
          values are the values to be stored
        :type record: dict
        :param collection_id: The ID of the collection, or None to autocreate collection ID,
          or False to skip this subcollection
        :type collection_id: various
        """
        raise NotImplementedError("Abstract method has not been implemented")

    @abstractmethod
    def find_subjects(self, match_rule, set_alt_ids=None):
        """Finds (and optionally updates IDs for) subjects matching the match_rule

        If a value is provided for set_alt_ids, will also write to the database to add any
        new alt subject IDs.

        :param match_rule: The definition of the subject(s) to update where the key is the
          subject field name to match (all specified fields must match)
        :type match_rule: dict
        :param set_alt_ids: Any alternative subject IDs to store where keys are the name of the
          subject ID (ex. "mrn") and values are the ID values for this subject.
        :type set_alt_ids: dict
        :return: list of subject IDs and dict of dicts with subject_id:alt_ids_dict
        :rtype: tuple with 1 array and 1 dict
        """
        raise NotImplementedError("Abstract method has not been implemented")

    @abstractmethod
    def find_one_subject(self, match_rule):
        """
        Looks up record and gets the autocreated subject ID and list of all source subject IDs
        """
        raise NotImplementedError("Abstract method has not been implemented")

    @abstractmethod
    def count_subject_records(self):
        """Returns the current count of subject records"""
        raise NotImplementedError("Abstract method has not been implemented")

    @abstractmethod
    def count_subcollection_records(self):
        """Returns the current count of subcollection records (self.collection must be defined)"""
        raise NotImplementedError("Abstract method has not been implemented")

    @abstractmethod
    def get_collection_stats(self):
        """Gets statistics about all collections.

        TODO: this might be too specific to MongoDB. We might want to modify our code so that
          this can return null values for irrelevant stats or a different set of stats.

        :return: subject_count, avg_doc_size, max_doc_size, max_doc_id
        :rtype: dict
        """
        raise NotImplementedError("Abstract method has not been implemented")

    def finalize_data(self):
        """Finishes up any needed changes to data after the data load is complete"""
        pass

    def create_indexes(self, only_text=False):
        """Creates all indexes needed for live database"""
        pass

    def finalize_subject_collection(self):
        """Performs any final steps to finish loading a source to the subject collection."""
        pass

    def finalize_subcollection(self):
        """Performs any final steps to finish loading a source to a subcollection."""
        pass

    def finalize_database(self):
        """Perform any final steps needed to get the database production ready.

        If self.use_staging=True will overwrite live database with staging database, and will do
        any other needed final database cleanup/preparation.
        """
        pass

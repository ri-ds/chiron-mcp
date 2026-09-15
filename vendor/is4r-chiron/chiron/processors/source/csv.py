import unicodecsv
import json

from chiron.processors.abstract import SourceProcessor, StandardLoadMixin
from chiron import chiron_settings
from chiron.processors.etl.clean_value import SimpleClean


class SourceCsv(StandardLoadMixin, SourceProcessor):
    """
    Source for CSV. The CSV file needs a header row. The records returned will
    be Python dicts.

    :param filepath: (required) the file location
    :type filepath: str
    :param collection_id_field: the header value for the collection ID, or None to use a random
      string
    :param subject_matching: string for a JSON object that defines the subject matching rule;
      definable properties are source_id_field, source_id_delimiter, destination_id_field,
      if_no_match
    :type subject_matching: json str
    :param subject_matching_source_id_field: (required if subject_matching not defined) The header
      value for the subject ID
    :type subject_matching_source_id_field: str
    :param subject_matching_source_id_delimiter: If a single CSV entry can list multiple values,
      the character(s) used to separate values
    :type subject_matching_source_id_delimiter: str
    :param subject_matching_destination_id_field: The name of the Chiron subject ID to match. Set
      to None to use default ("id")
    :type subject_matching_destination_id_field: str
    :param subject_matching_if_no_match: "create" (default) or "skip". If the subject ID doesn't
      match any existing Chiron subjects, do you want to create a new subject or skip this record?
    :type subject_matching_if_no_match: str
    :type collection_id_field: str
    :param add_subject_ids: Any additional subject ID values to pull from the record and store
      with this subject for matching in later sources. Provide a list of JSON objects defining
      "source_id_field" and "destionation_id_field".
    :type add_subject_ids: JSON str
    """

    def __init__(
        self,
        oSource,
        filepath,
        collection_id_field=None,
        subject_matching=None,
        subject_matching_source_id_field=None,
        subject_matching_source_id_delimiter=None,
        subject_matching_destination_id_field="id",
        subject_matching_if_no_match="create",
        add_subject_ids=None,
        delimiter=",",
        encoding="utf-8",
    ):
        super().__init__(oSource)
        self.source = oSource
        self.filepath = chiron_settings.CHIRON_SOURCE_DATA_DIRECTORY + filepath
        if collection_id_field == "None":
            self.collection_id_field = None
        else:
            self.collection_id_field = collection_id_field

        # build subject_matching rule(s)
        if subject_matching:
            self.subject_matching = json.loads(subject_matching)
        else:
            if not subject_matching_source_id_field:
                raise RuntimeError(
                    f"Source processor SourceCsv for {oSource} must either get arg "
                    "`subject_matching` or `subject_matching_source_id_field` when initialized"
                )
            self.subject_matching = {
                "source_id_field": subject_matching_source_id_field,
                "source_id_delimiter": subject_matching_source_id_delimiter,
                "destination_id_field": subject_matching_destination_id_field,
                "if_no_match": subject_matching_if_no_match,
            }
        self.add_subject_ids = {}
        if add_subject_ids:
            self.add_subject_ids = json.loads(add_subject_ids)
        self.subject_id_cleaner = SimpleClean(cast_to_type="string", convert_list_to_set=True)
        self.collection_id_cleaner = SimpleClean(cast_to_type="string", convert_list_to_set=True)
        self.delimiter = delimiter
        self.encoding = encoding

    def get_source(self):
        return self._iterator()

    def check_source_format(self):
        return "list of dicts"

    def _iterator(self):
        with open(self.filepath, "rb") as sourcefile:
            reader = unicodecsv.DictReader(
                sourcefile, delimiter=self.delimiter, encoding=self.encoding
            )  # might want option to set encoding
            for row in reader:
                record = row
                yield record

    def get_collection_id(self, record):
        """
        Returns a single collection ID using class parameter collection_id_field. If not found,
        returns None which will result in a new record being created.
        """
        if self.collection_id_field is None:
            return None
        raw = record[self.collection_id_field]
        collection_id = self.collection_id_cleaner.clean(raw)
        if collection_id == "":
            return None
        return collection_id

    def _determine_subject_ids_to_add(self, record, subject_ids):
        # will always at least want to add the IDs you're using for matching
        if len(subject_ids) == 1:
            add_ids = {
                self.subject_matching["destination_id_field"]: subject_ids[0],
            }
        else:
            add_ids = {
                self.subject_matching["destination_id_field"]: subject_ids,
            }
        if not self.add_subject_ids:
            return add_ids
        for entry in self.add_subject_ids:
            id_value = record.get(entry["source_id_field"])
            if id_value is not None and id_value != "":
                add_ids[entry["destination_id_field"]] = id_value
        return add_ids

    def get_subject_match_def(self, record):
        if_no_match = self.subject_matching.get("if_no_match", "create")
        delimiter = self.subject_matching.get("source_id_delimiter", None)

        # get the subject ID and split on delimiter if needed
        source_subject_id = record.get(self.subject_matching["source_id_field"])
        if delimiter and delimiter in source_subject_id and isinstance(source_subject_id, str):
            source_subject_id = source_subject_id.split(delimiter)

        subject_ids = self.subject_id_cleaner.clean(source_subject_id)
        if not isinstance(subject_ids, list):
            subject_ids = [subject_ids]

        # None and empty string are not acceptable subject ID values
        subject_ids = [id for id in subject_ids if id is not None and str(id) != ""]
        # skip if no subject_id values
        if len(subject_ids) == 0:
            return False

        # if we need a complex match_def instead of a flat value or list of values, create now
        destination_id_field = self.subject_matching.get("destination_id_field", "id")
        if destination_id_field != "id" or if_no_match != "create" or self.add_subject_ids:
            match_def = []
            for subject_id in subject_ids:
                match_def.append(
                    {
                        "match_rule": {destination_id_field: subject_id},
                        "add_ids": self._determine_subject_ids_to_add(record, subject_ids),
                        "if_no_match": if_no_match,
                    }
                )
            return match_def

        return subject_ids

    def get_subject_id_fields_used_for_matching(self):
        return self.subject_matching.get("destination_id_field", "id")

    def get_subject_id_fields_added(self):
        add_ids = []
        for entry in self.add_subject_ids:
            id = entry.get("destination_id_field", None)
            if id:
                add_ids.append(id)
        return add_ids

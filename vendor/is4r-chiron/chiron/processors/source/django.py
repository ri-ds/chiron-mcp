import json

from django.apps import apps
from django.core.paginator import Paginator

from chiron.processors.abstract import SourceProcessor, StandardLoadMixin
from chiron.processors.etl.clean_value import CleanStringWithWorkflow, SimpleClean
from chiron.processors.utils import DjangoModelObjectValueRetriever


def batch_model_iterator(
    Model,
    batch_size,
    select_related=[],
    prefetch_related=[],
    filter_rules={},
    limit_records_to=None,
):
    """Querysets pull all records into memory the first time they are used
    and will cause memory problems if they are too large.
    This iterator will instead load data in batches for the provided model.
    """
    q = Model.objects.all().order_by("pk")
    if filter_rules:
        q = q.filter(**filter_rules)
    if select_related:
        q = q.select_related(*select_related)
    if prefetch_related:
        q = q.prefetch_related(*prefetch_related)
    if limit_records_to:
        q = q[:limit_records_to]
    paginator = Paginator(q, batch_size)
    total_pages = paginator.num_pages
    page_number = 1
    while page_number <= total_pages:
        page = paginator.get_page(page_number)
        for obj in page:
            yield obj
        page_number += 1


class SourceDjangoModel(StandardLoadMixin, SourceProcessor):
    """
    A source processor that reads from a Django model.

    :param app: the Django app name where the model is located
    :type app: str
    :param model: the Django model name
    :type model: str
    :param collection_id_field: The name of the field where the collection_id is located. If not
      defined, the primary key of the Django model object will be used. If None, a random string
      will be generated.
    :type collection_id_field: str
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
    :param add_subject_ids: Any additional subject ID values to pull from the record and store
      with this subject for matching in later sources. Provide a list of JSON objects defining
      "source_id_field" and "destionation_id_field".
    :type add_subject_ids: JSON str
    :param max_batch_size: The maximum number of model records that will be loaded at once
    :type max_batch_size: int, optional (default=10,000)
    :param select_related: A comma separated list of models to pre-select
    :type select_related: str, optional
    :param prefetch_related: A comma separated list of models to pre-fetch
    :type prefetch_related: str, optional
    :param filter_rules: A JSON string of Django filter rules to limit model records returned
    :type filter_rules: JSON str, optional (default is all records are returned)
    """

    def __init__(
        self,
        oSource,
        app,
        model,
        collection_id_field="pk",
        subject_matching=None,
        subject_matching_source_id_field=None,
        subject_matching_destination_id_field="id",
        subject_matching_if_no_match="create",
        add_subject_ids=None,
        max_batch_size=10000,
        select_related="",
        prefetch_related="",
        filter_rules="{}",
    ):
        super().__init__(oSource)
        self.source = oSource
        self.app = app
        self.model = model
        self.collection_id_field = collection_id_field
        if collection_id_field == "None":
            self.collection_id_field = None

        # build subject_matching rule(s)
        if subject_matching:
            self.subject_matching = json.loads(subject_matching)
        else:
            if not subject_matching_source_id_field:
                raise RuntimeError(
                    f"Source processor SourceDjango for {oSource} must either get arg "
                    "`subject_matching` or `subject_matching_source_id_field` when initialized"
                )
            self.subject_matching = {
                "source_id_field": subject_matching_source_id_field,
                "destination_id_field": subject_matching_destination_id_field,
                "if_no_match": subject_matching_if_no_match,
            }
        self.add_subject_ids = {}
        if add_subject_ids:
            self.add_subject_ids = json.loads(add_subject_ids)
        self.max_batch_size = max_batch_size
        select_related_list = []
        for entry in select_related.split(","):
            val = entry.strip()
            if val:
                select_related_list.append(val)
        self.select_related = select_related_list
        prefetch_related_list = []
        for entry in prefetch_related.split(","):
            val = entry.strip()
            if val:
                prefetch_related_list.append(val)
        self.prefetch_related = prefetch_related_list
        self.filter_rules = json.loads(filter_rules)

        self.subject_id_retriever = DjangoModelObjectValueRetriever(
            self.subject_matching["source_id_field"], ignore_model_mismatch=False
        )
        self.add_id_retrievers = {}
        for entry in self.add_subject_ids:
            retriever = DjangoModelObjectValueRetriever(
                entry["source_id_field"], ignore_model_mismatch=False
            )
            self.add_id_retrievers[entry["destination_id_field"]] = retriever
        if self.collection_id_field:
            self.collection_id_retriever = DjangoModelObjectValueRetriever(
                self.collection_id_field, ignore_model_mismatch=False
            )
        if "workflow" in self.subject_matching:
            self.subject_id_cleaner = CleanStringWithWorkflow(
                self.subject_matching["workflow"], convert_list_to_set=True
            )
        else:
            self.subject_id_cleaner = SimpleClean(cast_to_type="string", convert_list_to_set=True)
        self.collection_id_cleaner = SimpleClean(cast_to_type="string", convert_list_to_set=True)

    def get_source(self, limit_records_to=None):
        Model = apps.get_model(self.app, self.model)
        return batch_model_iterator(
            Model,
            self.max_batch_size,
            self.select_related,
            self.prefetch_related,
            self.filter_rules,
            limit_records_to,
        )

    def check_source_format(self):
        return "queryset"

    def _determine_subject_ids_to_add(self, oRecord, subject_ids):
        add_ids = {}
        # if record creation is allowed and this is not a m2m field, also want to add the id
        # that is being used to match
        if len(subject_ids) == 1 and self.subject_matching.get("if_no_match", "create") != "skip":
            add_ids = {
                self.subject_matching["destination_id_field"]: subject_ids[0],
            }
        if not self.add_subject_ids:
            return add_ids
        for entry in self.add_subject_ids:
            retriever = self.add_id_retrievers[entry["destination_id_field"]]
            id_value = retriever(oRecord)
            if id_value is not None and id_value != "":
                add_ids[entry["destination_id_field"]] = id_value
        return add_ids

    def get_subject_match_def(self, oRecord):
        if_no_match = self.subject_matching.get("if_no_match", "create")
        raw = self.subject_id_retriever(oRecord)

        # if subject ID field doesn't exist, skip
        if raw == "***missing***":
            # TODO: log situation where Django field couldn't be found
            return False

        subject_ids = self.subject_id_cleaner.clean(raw)
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
                        "add_ids": self._determine_subject_ids_to_add(oRecord, subject_ids),
                        "if_no_match": if_no_match,
                    }
                )
            if len(match_def) == 1:
                return match_def[0]
            return match_def
        if len(subject_ids) == 1:
            return subject_ids[0]
        return subject_ids

    def get_collection_id(self, oRecord):
        # if no collection ID field defined, return None to create new record
        if not self.collection_id_field:
            return None

        # get the collection ID or collection IDs
        raw_val = self.collection_id_retriever(oRecord)

        # if subject ID field doesn't exist, skip
        if raw_val == "***missing***":
            # TODO: log situation where Django field couldn't be found
            return False

        cleaned_val = self.collection_id_cleaner.clean(raw_val)

        # if we ended up with multiple id values, can we collapse to one value?
        if isinstance(cleaned_val, list):
            cleaned_val = [id for id in cleaned_val if id is not None and str(id) != ""]
            if len(cleaned_val) == 0:
                return None
            if len(cleaned_val) == 1:
                return cleaned_val[0]
            else:
                raise ValueError("A single record had multiple IDs.")

        # return single value
        if cleaned_val == "":
            return None
        return cleaned_val

    def get_subject_id_fields_used_for_matching(self):
        return self.subject_matching.get("destination_id_field", "id")

    def get_subject_id_fields_added(self):
        add_ids = []
        for entry in self.add_subject_ids:
            id = entry.get("destination_id_field", None)
            if id:
                add_ids.append(id)
        return add_ids

import unicodecsv
import json
import string
import random

from dateutil.parser import parse
from dateutil.parser import ParserError

from chiron import models
from chiron import chiron_settings


def check_if_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def check_if_date(s):
    try:
        parse(s)
    except (ValueError, ParserError, OverflowError):
        return False
    return True


def random_string(stringLength=10):
    """Generate a random string of fixed length"""
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(stringLength))


class CsvFileAutocreate:
    """
    Helps with autocreating data dictionary concepts from a Django model.


    """

    def __init__(self, settings):
        self.settings = settings
        self.source_processor_args = {}  # dict with key arg_name
        self.concept_handler_args = {}  # dict of dicts with keys field_name:arg_name
        self.filename = self.settings["filename"]
        self.filepath = chiron_settings.CHIRON_SOURCE_DATA_DIRECTORY + self.filename
        self.dataset = self.determine_dataset()
        self.collection = self.determine_collection()
        self.source = self.determine_source()
        self.category = self.determine_category()
        self.delimiter = self.settings.get("delimiter", ",")
        self.encoding = self.settings.get("encoding", "utf-8")

    def determine_dataset(self):
        oDataset = None
        # if a dataset name is defined, get or create a dataset using that name
        dataset_name = self.settings.get("dataset")
        if dataset_name:
            oDataset = models.Dataset.objects.filter(unique_id=dataset_name).first()
            if not oDataset:
                oDataset = models.Dataset.objects.create(
                    unique_id=dataset_name,
                    display_name=dataset_name,
                    database_name=dataset_name,
                )
        # if there's not multiple datasets, get or create the default dataset
        else:
            qDataset = models.Dataset.objects.all()
            if qDataset.count() == 1:
                oDataset = qDataset[0]
            elif qDataset.count() == 0:
                oDataset = models.Dataset.objects.create(
                    unique_id="default", display_name="default", database_name="default1"
                )
        if oDataset:
            return oDataset
        raise ValueError("You must specify a dataset")

    def determine_collection(self):
        oCollection = None
        # if collection permanent ID, use that
        collection_id = self.settings.get("collection")
        load_to_root = self.settings.get("load_to_root", False)
        # if loading to root, check if a root collection is already defined
        if load_to_root and self.dataset.root_collection:
            oCollection = self.dataset.root_collection
        # use the collection ID to get or create a collection
        elif collection_id:
            # if dataset already exists see if collection already exists
            if self.dataset.pk:
                oCollection = models.Collection.objects.filter(
                    dataset=self.dataset, permanent_id=collection_id
                ).first()
            if not oCollection:
                oCollection = models.Collection(
                    permanent_id=collection_id,
                    name=collection_id,
                )
        # if still not set, find or create a new collection using the source name
        if not oCollection:
            collection_id = self.settings.get("unique_source_id")
            # if dataset already exists see if collection already exists
            if self.dataset.pk:
                oCollection = models.Collection.objects.filter(
                    dataset=self.dataset, permanent_id=collection_id
                ).first()
            if not oCollection:
                oCollection = models.Collection(
                    permanent_id=collection_id,
                    name=collection_id,
                )
        return oCollection

    def determine_source(self):
        unique_source_id = self.settings.get("unique_source_id")
        oSource = None
        # if the dataset already exists, check if the source already exists
        if self.dataset.pk:
            oSource = models.Source.objects.filter(
                collection__dataset=self.dataset, name=unique_source_id
            ).first()
        if not oSource:
            processor = models.Processor.objects.get(name="SourceCsv")
            oSource = models.Source(name=unique_source_id, processor=processor, execution_order=1)
            oSource.execution_order = 1
            oLastSource = (
                models.Source.objects.filter(collection__dataset=self.dataset)
                .order_by("-execution_order")
                .first()
            )
            if oLastSource:
                oSource.execution_order = oLastSource.execution_order + 1
        # set source processor args if needed
        if not oSource.pk:
            self.source_processor_args["filepath"] = self.settings["filename"]
            if "subject_matching" in self.settings:
                self.source_processor_args["subject_matching"] = json.dumps(
                    self.settings["subject_matching"]
                )
            elif "subject_id_field" in self.settings:
                self.source_processor_args["subject_matching_source_id_field"] = self.settings[
                    "subject_id_field"
                ]
            if "collection_id_field" in self.settings:
                self.source_processor_args["collection_id_field"] = self.settings[
                    "collection_id_field"
                ]
            if "add_subject_ids" in self.settings:
                self.source_processor_args["add_subject_ids"] = json.dumps(
                    self.settings["add_subject_ids"]
                )
        return oSource

    def determine_category(self):
        category_name = self.settings.get("category")
        if not category_name:
            category_name = self.settings.get("unique_source_id")
        oCategory = None
        # if the dataset already exists, check if the category already exists
        if self.dataset.pk:
            oCategory = models.Category.objects.filter(
                dataset=self.dataset, unique_id=category_name
            ).first()
        if not oCategory:
            oCategory = models.Category(unique_id=category_name, name=category_name, order=100)
        return oCategory

    def get_field_names(self):
        with open(self.filepath, "rb") as sourcefile:
            reader = unicodecsv.DictReader(
                sourcefile, encoding=self.encoding, delimiter=self.settings.get("delimiter", ",")
            )
            for row in reader:
                record = dict(row)
                all_fields = list(record.keys())
                break
        # exclude fields that have already been loaded
        field_names = []
        for field_name in all_fields:
            oCreated = models.AutocreatedField.objects.filter(
                dataset=self.dataset,
                unique_source_id=self.settings["unique_source_id"],
                field=field_name,
            ).first()
            if not oCreated:
                field_names.append(field_name)
        return field_names

    def check_data_type(self, fields):
        tracker = {}
        for field in fields:
            tracker[field] = {
                "count_total": 0,
                "count_non_empty": 0,
                "count_numbers": 0,
                "count_large_numbers": 0,  # lots of large numbers would suggest ID code
                "count_dates": 0,
                "distinct_values": set(),
            }
        with open(self.filepath, "rb") as sourcefile:
            reader = unicodecsv.DictReader(
                sourcefile, encoding=self.encoding, delimiter=self.settings.get("delimiter", ",")
            )
            for i, row in enumerate(reader):
                if i > 10_000:
                    break
                for field in fields:
                    tracker[field]["count_total"] += 1
                    value = row.get(field, "").strip()
                    if not value:
                        continue
                    tracker[field]["count_non_empty"] += 1
                    if check_if_number(value):
                        if len(str(float(value))) >= 6:
                            tracker[field]["count_large_numbers"] += 1
                        tracker[field]["count_numbers"] += 1
                    if check_if_date(value):
                        tracker[field]["count_dates"] += 1
                    tracker[field]["distinct_values"].add(value)
            results = {}
            for field in fields:
                if (
                    tracker[field]["count_numbers"] > 20
                    and tracker[field]["count_numbers"] - tracker[field]["count_non_empty"] == 0
                ):
                    if tracker[field]["count_large_numbers"] == tracker[field]["count_numbers"]:
                        results[field] = "TextHandler"
                    else:
                        results[field] = "FloatHandler"
                elif (
                    tracker[field]["count_dates"] > 20
                    and tracker[field]["count_dates"] - tracker[field]["count_non_empty"] == 0
                ):
                    results[field] = "DateHandler"
                elif (
                    len(tracker[field]["distinct_values"]) < 20
                    and tracker[field]["count_non_empty"] > 100
                ):
                    results[field] = "CategoryHandler"
                else:
                    results[field] = "TextHandler"
            return results

    def get_concepts(self, field_names):
        data_types = self.check_data_type(field_names)
        concepts = {}
        for idx, field_name in enumerate(field_names, 1):
            oConcept = models.Concept(name=field_name, order=idx)
            oConcept.permanent_id = "{}_{}".format(field_name, random_string())
            oConcept.concept_handler = models.ConceptHandler.objects.get(
                name=data_types[field_name]
            )
            concepts[field_name] = oConcept
            # save concept handler args if needed
            if not oConcept.pk:
                if field_name not in self.concept_handler_args:
                    self.concept_handler_args[field_name] = {}
                self.concept_handler_args[field_name]["field_name"] = field_name
        return concepts

    def count_concepts(self, concepts):
        return len(concepts)

    def save_concepts(self, concepts):
        """
        Saves the concept to the data dictionary along with any related objects
        that don't already exist (dataset, collection , etc.)
        """
        # iterate concepts
        # make sure all related models are saved
        collection_created = False
        if not self.dataset.pk:
            self.dataset.save()
        if not self.collection.pk:
            self.collection.dataset = self.dataset
            self.collection.save()
            collection_created = True
        # try to set the dataset root
        if not self.dataset.root_collection and self.settings.get("load_to_root"):
            self.dataset.root_collection = self.collection
            self.dataset.save()
        if not self.source.pk:
            self.source.collection = self.collection
            self.source.save()
            # set source processor args
            for name, value in self.source_processor_args.items():
                oArg = models.SourceProcessorArg(source=self.source, name=name, value=value)
                oArg.save()
        if not self.category.pk:
            self.category.dataset = self.dataset
            self.category.save()
        # save each concept
        for field_name, concept in concepts.items():
            if not concept.pk:
                concept.collection = self.collection
                concept.source = self.source
                concept.category = self.category
                concept.save()
                # set concept handler processor args
                for name, value in self.concept_handler_args[field_name].items():
                    oArg = models.ConceptHandlerArg(concept=concept, name=name, value=value)
                    oArg.save()
                    # mark the concept as imported so it won't be reimported next time
                    oCreated = models.AutocreatedField(
                        dataset=self.dataset,
                        unique_source_id=self.settings["unique_source_id"],
                        field=field_name,
                        associated_concept=concept,
                    )
                    oCreated.save()
        # try to set the event_id_field
        if collection_created:
            if self.settings.get("load_to_root"):
                for field_name, concept in concepts.items():
                    subject_id_field = self.settings.get("subject_matching", {}).get(
                        "source_id_field"
                    )
                    if not subject_id_field:
                        subject_id_field = self.settings.get("subject_id_field")
                    if field_name == subject_id_field:
                        self.collection.event_id_field = concept
                        self.collection.save()
                        break
            elif self.settings.get("collection_id_field"):
                for field_name, concept in concepts.items():
                    if field_name == self.settings["collection_id_field"]:
                        self.collection.event_id_field = concept
                        self.collection.save()
                        break

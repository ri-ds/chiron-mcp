import json
import string
import random

from django.apps import apps
from dateutil.parser import parse
from dateutil.parser import ParserError


from chiron import models


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


class DjangoOrmAutocreate:
    """
    Helps with autocreating data dictionary concepts from a Django model.
    """

    def __init__(self, settings):
        self.settings = settings
        self.select_related = []  # list of strings
        self.prefetch_related = []  # list of strings
        self.source_processor_args = {}  # dict with key arg_name
        self.concept_handler_args = {}  # dict of dicts with keys field_name:arg_name
        self.app_name = self.settings["app"]
        self.model_name = self.settings["model"]
        self.model = apps.get_model(self.app_name, self.model_name)
        self.dataset = self.determine_dataset()
        self.collection = self.determine_collection()
        self.source = self.determine_source()
        self.category = self.determine_category()

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
            collection_id = self.settings.get("source_name")
            if not collection_id:
                collection_id = self.model_name
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
        source_name = self.settings.get("source_name")
        if not source_name:
            source_name = self.model_name
        oSource = None
        # if the dataset already exists, check if the source already exists
        if self.dataset.pk:
            oSource = models.Source.objects.filter(
                collection__dataset=self.dataset, name=source_name
            ).first()
        if not oSource:
            processor = models.Processor.objects.get(name="SourceDjangoModel")
            oSource = models.Source(name=source_name, processor=processor, execution_order=1)
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
            self.source_processor_args["app"] = self.app_name
            self.source_processor_args["model"] = self.model_name
            if "subject_matching" in self.settings:
                subject_id_field = self.settings.get("subject_matching", {}).get("source_id_field")
                self.source_processor_args["subject_matching"] = json.dumps(
                    self.settings["subject_matching"]
                )
            else:
                subject_id_field = self.settings.get("subject_id_field")
                self.source_processor_args["subject_matching_source_id_field"] = subject_id_field
            # add select_related for subject_id if needed
            if "__" in subject_id_field:
                subject_id_path = subject_id_field.rsplit("__", 1)[0]
                self.select_related.append(subject_id_path)
            if "collection_id_field" in self.settings:
                collection_id_field = self.settings["collection_id_field"]
                if not collection_id_field:
                    # source processor args in the database are strings, so convert None values
                    # to the string "None"
                    collection_id_field = "None"
                self.source_processor_args["collection_id_field"] = collection_id_field
                if collection_id_field and "__" in collection_id_field:
                    collection_id_path = subject_id_field.rsplit("__", 1)[0]
                    self.select_related.append(collection_id_path)
            if "add_subject_ids" in self.settings:
                self.source_processor_args["add_subject_ids"] = json.dumps(
                    self.settings["add_subject_ids"]
                )
        return oSource

    def determine_category(self):
        oCategory = None
        category_name = self.settings.get("category")
        if not category_name:
            category_name = self.settings.get("source_name")
        if not category_name:
            category_name = self.model_name
        if self.dataset.pk:
            oCategory = models.Category.objects.filter(
                dataset=self.dataset, unique_id=category_name
            ).first()
        if not oCategory:
            oCategory = models.Category(unique_id=category_name, name=category_name, order=100)
        return oCategory

    def get_or_create_subcategory(self, subcategory_name):
        oCategory = models.Category.objects.filter(
            unique_id=subcategory_name, parent=self.category, dataset=self.dataset
        ).first()
        if not oCategory:
            oCategory = models.Category(
                unique_id=subcategory_name,
                parent=self.category,
                name=subcategory_name,
                order=100,
                dataset=self.dataset,
            )
            oCategory.save()
        return oCategory

    def get_field_names(self):
        all_fields = self.model._meta.get_fields(include_parents=False)
        model_groups = []
        fields = []
        field_names = [field.name for field in all_fields]
        for field in all_fields:
            if field.is_relation:
                continue
            # exclude fields that have a display value (feature for redcap_importer tool)
            if f"{field.name}_display_value" in field_names:
                continue
            oCreated = models.AutocreatedField.objects.filter(
                dataset=self.dataset, app=self.app_name, model=self.model_name, field=field.name
            ).first()
            if oCreated:
                continue
            fields.append(field)
        model_groups.append(
            {
                "model": self.model,
                "join_path": None,
                "fields": fields,
            }
        )
        for join_model_entry in self.settings.get("join_models", []):
            fields = []
            join_model_app_name = join_model_entry.get("app", self.app_name)
            join_model_name = join_model_entry["model"]
            join_model = apps.get_model(join_model_app_name, join_model_name)
            all_join_fields = join_model._meta.get_fields(include_parents=False)
            field_names = [field.name for field in all_join_fields]
            for field in all_join_fields:
                if field.is_relation:
                    continue
                # exclude fields that have a display value (feature for redcap_importer tool)
                if f"{field.name}_display_value" in field_names:
                    continue
                oCreated = models.AutocreatedField.objects.filter(
                    dataset=self.dataset,
                    app=join_model_app_name,
                    model=join_model_name,
                    field=field.name,
                ).first()
                if oCreated:
                    continue
                fields.append(field)
            model_groups.append(
                {
                    "model": join_model,
                    "join_path": join_model_entry["join_path"],
                    "fields": fields,
                }
            )
            self.prefetch_related.append(join_model_entry["join_path"])
        return model_groups

    def check_data_type(self, model_group):
        results = {}
        for field in model_group["fields"]:
            field_name = field.name
            type = field.get_internal_type()
            if type in ["AutoField"]:
                results[field_name] = "TextHandler"
            elif type in ["TextField", "CharField"]:
                count = (
                    model_group["model"]
                    .objects.all()
                    .order_by(field_name)
                    .values_list(field_name)
                    .distinct()
                    .count()
                )
                if count > 20:
                    results[field_name] = "TextHandler"
                else:
                    results[field_name] = "CategoryHandler"
            elif type in ["IntegerField"]:
                results[field_name] = "IntegerHandler"
            elif type in ["FloatField"]:
                results[field_name] = "FloatHandler"
            elif type in ["DateField", "DateTimeField"]:
                results[field_name] = "DateHandler"
            elif type in ["BooleanField", "NullBooleanField"]:
                results[field_name] = "BooleanHandler"
            else:
                results[field_name] = "TextHandler"
        return results

    def get_concepts(self, model_groups):
        concept_groups = {}
        idx = 1
        for model_group in model_groups:
            concepts = []
            data_types = self.check_data_type(model_group)
            for field in model_group["fields"]:
                field_name = field.name
                if model_group["join_path"]:
                    full_field_name = "{}__{}".format(model_group["join_path"], field_name)
                    subcategory_name = model_group["model"].__name__
                else:
                    full_field_name = field_name
                    subcategory_name = ""
                oConcept = models.Concept(name=field_name, order=idx)
                idx += 1
                oConcept.permanent_id = "{}_{}".format(field_name, random_string())
                oConcept.concept_handler = models.ConceptHandler.objects.get(
                    name=data_types[field_name]
                )
                oConcept.description = field.help_text
                concepts.append(
                    {
                        "concept": oConcept,
                        "app_name": model_group["model"]._meta.app_label,
                        "model_name": model_group["model"].__name__,
                        "field_name": field_name,
                        "full_field_name": full_field_name,
                    }
                )
                # save concept handler args if needed
                if not oConcept.pk:
                    if full_field_name not in self.concept_handler_args:
                        self.concept_handler_args[full_field_name] = {}
                    self.concept_handler_args[full_field_name]["field_name"] = full_field_name
            if concepts:
                concept_groups[subcategory_name] = concepts
        return concept_groups

    def count_concepts(self, concept_groups):
        response = 0
        for concepts in concept_groups.values():
            response += len(concepts)
        return response

    def save_concepts(self, concept_groups):
        """
        Saves the concept to the data dictionary along with any related objects
        that don't already exist (dataset, collection , etc.)
        """
        # if there are no concepts to load, do nothing
        if not concept_groups:
            return
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
            # add select_related and prefetch_related to source_processor_args
            if self.select_related:
                sr_str = ",".join(list(set(self.select_related)))
                self.source_processor_args["select_related"] = sr_str
            if self.prefetch_related:
                pr_str = ",".join(list(set(self.prefetch_related)))
                self.source_processor_args["prefetch_related"] = pr_str
            # set source processor args
            for name, value in self.source_processor_args.items():
                oArg = models.SourceProcessorArg(source=self.source, name=name, value=value)
                oArg.save()
        if not self.category.pk:
            self.category.dataset = self.dataset
            self.category.save()
        # save each concept
        for subcategory_name, entries in concept_groups.items():
            if subcategory_name:
                oCategory = self.get_or_create_subcategory(subcategory_name)
            else:
                oCategory = self.category
            for entry in entries:
                if not entry["concept"].pk:
                    entry["concept"].collection = self.collection
                    entry["concept"].source = self.source
                    entry["concept"].category = oCategory
                    entry["concept"].save()
                    # set concept handler processor args
                    for name, value in self.concept_handler_args[entry["full_field_name"]].items():
                        oArg = models.ConceptHandlerArg(
                            concept=entry["concept"], name=name, value=value
                        )
                        oArg.save()
                        # mark the concept as imported so it won't be reimported next time
                        oCreated = models.AutocreatedField(
                            dataset=self.dataset,
                            app=entry["app_name"],
                            model=entry["model_name"],
                            field=entry["field_name"],
                            associated_concept=entry["concept"],
                        )
                        oCreated.save()
        # try to set the event_id_field
        if collection_created:
            if self.settings.get("load_to_root"):
                for entries in concept_groups.values():
                    for entry in entries:
                        subject_id_field = self.settings.get("subject_matching", {}).get(
                            "source_id_field"
                        )
                        if not subject_id_field:
                            subject_id_field = self.settings.get("subject_id_field")
                        if entry["full_field_name"] == subject_id_field:
                            self.collection.event_id_field = entry["concept"]
                            self.collection.save()
                            break
            elif self.settings.get("collection_id_field"):
                for entries in concept_groups.values():
                    for entry in entries:
                        if entry["full_field_name"] == self.settings["collection_id_field"]:
                            self.collection.event_id_field = entry["concept"]
                            self.collection.save()
                            break

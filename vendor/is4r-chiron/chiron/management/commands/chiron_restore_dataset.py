import json
from copy import copy

from django.core.management.base import BaseCommand
from django.db import transaction

from chiron import models
from chiron import chiron_settings
from chiron.data_dictionary.drop_dataset import drop_dataset
from chiron.data_dictionary.preserve_permission_groups import PreservePermissionGroups
from chiron.helpers import prepare_backup_file_path


class Command(BaseCommand):
    """
    Restores a json data file saved using chiron_backup_dataset. Provide the name of the file
    to load.

    When overwriting an existing dataset, much of the context for that dataset will be preserved.
    The ChironUsers associated with the dataset will stay in place, along with any
    PermissionGroups they have. And reports will also be preserved. Be aware that if your new
    data dictionary deletes collections/concepts or changes their permanent_id values, you may
    end up with broken references as a result.

    .. code-block:: bash

        # overwrite existing dataset 'foo' from backup file
        python manage.py chiron_restore_dataset foo.json --overwrite

        # duplicate existing dataset 'foo' as new dataset 'bar'
        python manage.py chiron_backup_dataset foo
        python manage.py chiron_restore_dataset foo.json --unique-id=bar --handle-name-conflicts
    """

    help = "Reloads the data dictionary for a dataset from a JSON file"

    def print_out(self, *args):
        """A wrapper for self.stdout.write() that converts anything into a string"""
        strings = []
        for arg in args:
            strings.append(str(arg))
        self.stdout.write(",".join(strings))

    def print_err(self, *args):
        """A wrapper for self.stderr.write() that converts anything into a string"""
        strings = []
        for arg in args:
            strings.append(str(arg))
        self.stderr.write(",".join(strings))

    def add_arguments(self, parser):
        parser.add_argument(
            "filename",
            help=f"Provide the name of the file in {chiron_settings.CHIRON_DATA_DICT_BACKUP_DIR}/",
        )
        parser.add_argument(
            "--unique-id",
            # default="no_selection",
            help="Specify the unique_id to use for this dataset if different from the file name",
        )
        parser.add_argument(
            "--backup-dir",
            # default="no_selection",
            help="Specify the dir loc of your file if different from "
            "settings.CHIRON_DATA_DICT_BACKUP_DIR",
        )
        parser.add_argument(
            "--handle-name-conflicts",
            action="store_true",
            help=(
                "Concept.permanent_id must be unique across the entire Chiron instance."
                "Set this flag to modify conflicting names instead of raising an error."
            ),
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help=(
                "If a dataset with the same name already exists, truncate and reload the "
                "data dictionary for that dataset."
            ),
        )

    def handle(self, *args, **options):
        filename = options["filename"]
        dataset_unique_id = options["unique_id"]
        self.handle_name_conflicts = options["handle_name_conflicts"]

        # prepare filepath
        filepath, file_exists = prepare_backup_file_path(filename, options.get("backup_dir"))

        with open(filepath, "r") as f:
            self.dd = json.load(f)
        self.objects = {}

        # make sure there's not an existing dataset with the specified unique_id
        if dataset_unique_id:
            unique_id = dataset_unique_id
        else:
            unique_id = self.dd["dataset"]["unique_id"]
        oExistingDataset = models.Dataset.objects.filter(unique_id=unique_id).first()
        if oExistingDataset and not options["overwrite"]:
            raise Exception(
                f"Already a dataset named {unique_id}. Either specify a different "
                "name using `--unique-id` or flag `--overwrite` to overwrite the existing dataset."
            )

        with transaction.atomic():
            # create the dataset
            entry = copy(self.dd["dataset"])
            if oExistingDataset:
                # overwriting an existing dataset, update the dataset model object in place
                # (in order to preserve chironusers) and delete all related data
                del entry["id"]  # keep current id
                del entry["unique_id"]  # keep current unique_id
                del entry["database_name"]  # keep current database
                entry["root_collection_id"] = None  # set fk null for now
                for key, value in entry.items():
                    setattr(oExistingDataset, key, value)
                oExistingDataset.save()

                # try to save and later restore fk links between ChironUser and PermissionGroup
                preserve_pg = PreservePermissionGroups()
                preserve_pg.backup_to_memory(oExistingDataset)

                drop_dataset(oExistingDataset, keep_dataset_object=True)
                oDataset = oExistingDataset
            else:
                # creating a new dataset
                del entry["id"]
                del entry["root_collection_id"]
                if dataset_unique_id:
                    entry["unique_id"] = dataset_unique_id
                    entry["display_name"] = dataset_unique_id
                    entry["database_name"] = dataset_unique_id
                oDataset = models.Dataset(**entry)
                oDataset.save()
            self.dataset = oDataset

            self.create_all_objects(dataset_unique_id)
            self.update_objects()

            # recreate links between chironuser and permission groups
            if oExistingDataset and preserve_pg.permission_groups_found():
                preserve_pg.restore_to_database()
        self.print_out(
            f"Process complete. Your new dataset is '{oDataset.unique_id}' and is set"
            f" to use database/schema '{oDataset.database_name}'."
        )

    def create_all_objects(self, dataset_unique_id):
        """Creates all objects used by this dataset"""

        # create permission groups
        self.objects["permission_groups"] = []
        for original_entry in self.dd["permission_groups"]:
            entry = copy(original_entry)
            del entry["id"]
            del entry["concept_for_allowed_subjects_id"]
            del entry["allowed_concepts"]
            del entry["allowed_data_categories"]
            del entry["allowed_collections"]
            entry["dataset_id"] = self.dataset.id
            oPermissionGroup = models.PermissionGroup(**entry)
            oPermissionGroup.save()
            self.objects["permission_groups"].append(oPermissionGroup)

        # create default permission groups
        self.objects["default_permission_groups"] = []
        for original_entry in self.dd["default_permission_groups"]:
            entry = copy(original_entry)
            del entry["id"]
            entry["dataset_id"] = self.dataset.id
            entry["permission_group_id"] = self.lookup_permission_group_id(
                entry["permission_group_id"]
            )
            oDefault = models.DefaultPermissionGroup(**entry)
            oDefault.save()
            self.objects["default_permission_groups"].append(oDefault)

        # create collections
        self.objects["collections"] = []
        for original_entry in self.dd["collections"]:
            entry = copy(original_entry)
            del entry["id"]
            del entry["event_id_field_id"]
            del entry["event_name_field_id"]
            del entry["event_date_field_id"]
            del entry["event_end_date_field_id"]
            entry["dataset_id"] = self.dataset.id
            oCollection = models.Collection(**entry)
            oCollection.save()
            self.objects["collections"].append(oCollection)

        # create source
        self.objects["sources"] = []
        for original_entry in self.dd["sources"]:
            entry = copy(original_entry)
            del entry["id"]
            entry["collection_id"] = self.lookup_collection_id(entry["collection_id"])
            entry["processor_id"] = self.lookup_processor_id(entry["processor_id"])
            oSource = models.Source(**entry)
            oSource.save()
            self.objects["sources"].append(oSource)

        # create categories
        self.objects["categories"] = []
        for original_entry in self.dd["categories"]:
            entry = copy(original_entry)
            del entry["id"]
            del entry["parent_id"]
            entry["dataset_id"] = self.dataset.id
            # will wait to set parents until after all categories are loaded
            oCategory = models.Category(**entry)
            oCategory.save()
            self.objects["categories"].append(oCategory)

        # create concepts
        self.objects["concepts"] = []
        for original_entry in self.dd["concepts"]:
            entry = copy(original_entry)
            del entry["id"]
            # will need to set this later after all concepts have been loaded
            del entry["concept_for_prefilter_id"]
            entry["permanent_id"] = self.validate_permanent_id(entry["permanent_id"])
            entry["collection_id"] = self.lookup_collection_id(entry["collection_id"])
            entry["source_id"] = self.lookup_source_id(entry["source_id"])
            entry["concept_handler_id"] = self.lookup_concept_handler_id(
                entry["concept_handler_id"]
            )
            entry["category_id"] = self.lookup_category_id(entry["category_id"])
            oConcept = models.Concept(**entry)
            oConcept.save()
            self.objects["concepts"].append(oConcept)

        # create collection relationships
        self.objects["collection_relationships"] = []
        for original_entry in self.dd["collection_relationships"]:
            entry = copy(original_entry)
            del entry["id"]
            entry["pk_concept_id"] = self.lookup_concept_id(entry["pk_concept_id"])
            entry["fk_concept_id"] = self.lookup_concept_id(entry["fk_concept_id"])
            oRel = models.CollectionRelationship(**entry)
            oRel.save()
            self.objects["collection_relationships"].append(oRel)

        # create default_table_def_concepts
        self.objects["default_table_def_concepts"] = []
        for original_entry in self.dd["default_table_def_concepts"]:
            entry = copy(original_entry)
            del entry["id"]
            entry["dataset_id"] = self.dataset.id
            entry["concept_id"] = self.lookup_concept_id(entry["concept_id"])
            oDefault = models.DefaultTableDefConcept(**entry)
            oDefault.save()
            self.objects["default_table_def_concepts"].append(oDefault)

        # create concept handler args
        self.objects["concept_handler_args"] = []
        for original_entry in self.dd["concept_handler_args"]:
            entry = copy(original_entry)
            del entry["id"]
            entry["concept_id"] = self.lookup_concept_id(entry["concept_id"])
            oArg = models.ConceptHandlerArg(**entry)
            oArg.save()
            self.objects["concept_handler_args"].append(oArg)

        # create source processor args
        self.objects["source_processor_args"] = []
        for original_entry in self.dd["source_processor_args"]:
            entry = copy(original_entry)
            del entry["id"]
            entry["source_id"] = self.lookup_source_id(entry["source_id"])
            oArg = models.SourceProcessorArg(**entry)
            oArg.save()
            self.objects["source_processor_args"].append(oArg)

        # create source source dependencies
        self.objects["source_source_dependencies"] = []
        for original_entry in self.dd["source_source_dependencies"]:
            entry = copy(original_entry)
            del entry["id"]
            entry["source_id"] = self.lookup_source_id(entry["source_id"])
            entry["depends_on_source_id"] = self.lookup_source_id(entry["depends_on_source_id"])
            oDep = models.SourceSourceDependency(**entry)
            oDep.save()
            self.objects["source_source_dependencies"].append(oDep)

        # create concept concept dependencies
        self.objects["concept_concept_dependencies"] = []
        for original_entry in self.dd["concept_concept_dependencies"]:
            entry = copy(original_entry)
            del entry["id"]
            entry["concept_id"] = self.lookup_concept_id(entry["concept_id"])
            entry["depends_on_concept_id"] = self.lookup_concept_id(entry["depends_on_concept_id"])
            oDep = models.ConceptConceptDependency(**entry)
            oDep.save()
            self.objects["concept_concept_dependencies"].append(oDep)

        # create concept source dependencies
        self.objects["concept_source_dependencies"] = []
        for original_entry in self.dd["concept_source_dependencies"]:
            entry = copy(original_entry)
            del entry["id"]
            entry["concept_id"] = self.lookup_concept_id(entry["concept_id"])
            entry["depends_on_source_id"] = self.lookup_source_id(entry["depends_on_source_id"])
            oDep = models.ConceptSourceDependency(**entry)
            oDep.save()
            self.objects["concept_source_dependencies"].append(oDep)

        # create autocreated fields
        self.objects["autocreated_fields"] = []
        for original_entry in self.dd["autocreated_fields"]:
            entry = copy(original_entry)
            del entry["id"]
            entry["dataset_id"] = self.dataset.id
            entry["associated_concept_id"] = self.lookup_concept_id(entry["associated_concept_id"])
            oField = models.AutocreatedField(**entry)
            oField.save()
            self.objects["autocreated_fields"].append(oField)

    def update_objects(self):
        """Some objects need reference IDs, etc. updated after everything has been created"""
        # update dataset
        input_root_id = self.dd["dataset"]["root_collection_id"]
        if input_root_id:
            root_id = self.lookup_collection_id(input_root_id)
            self.dataset.root_collection_id = root_id
            self.dataset.save()

        # update permission groups
        for idx, entry in enumerate(self.dd["permission_groups"]):
            o = self.objects["permission_groups"][idx]
            if entry["concept_for_allowed_subjects_id"]:
                concept_id = self.lookup_concept_id(entry["concept_for_allowed_subjects_id"])
                o.concept_for_allowed_subjects_id = concept_id
                o.save()
            for input_concept_id in entry["allowed_concepts"]:
                concept_id = self.lookup_concept_id(input_concept_id)
                o.allowed_concepts.add(concept_id)
            for input_category_id in entry["allowed_data_categories"]:
                category_id = self.lookup_category_id(input_category_id)
                o.allowed_data_categories.add(category_id)
            for input_collection_id in entry["allowed_collections"]:
                collection_id = self.lookup_collection_id(input_collection_id)
                o.allowed_collections.add(collection_id)

        # update collections
        for idx, entry in enumerate(self.dd["collections"]):
            o = self.objects["collections"][idx]
            if entry["event_id_field_id"]:
                o.event_id_field_id = self.lookup_concept_id(entry["event_id_field_id"])
            if entry["event_name_field_id"]:
                o.event_name_field_id = self.lookup_concept_id(entry["event_name_field_id"])
            if entry["event_date_field_id"]:
                o.event_date_field_id = self.lookup_concept_id(entry["event_date_field_id"])
            if entry["event_end_date_field_id"]:
                o.event_end_date_field_id = self.lookup_concept_id(
                    entry["event_end_date_field_id"]
                )
            o.save()

        # update categories
        for idx, entry in enumerate(self.dd["categories"]):
            if entry["parent_id"]:
                o = self.objects["categories"][idx]
                o.parent_id = self.lookup_category_id(entry["parent_id"])
                o.save()

        # update concepts
        for idx, entry in enumerate(self.dd["concepts"]):
            if entry["concept_for_prefilter_id"]:
                o = self.objects["concepts"][idx]
                o.concept_for_prefilter_id = self.lookup_concept_id(
                    entry["concept_for_prefilter_id"]
                )
                o.save()

    def lookup_permission_group_id(self, input_permission_group_id):
        """
        The permission_group ID that goes in the database will usually be different from the
        one that came from the file.
        """
        for idx, entry in enumerate(self.dd["permission_groups"]):
            if entry["id"] == input_permission_group_id:
                output_permission_group_id = self.objects["permission_groups"][idx].id
                return output_permission_group_id
        raise Exception(f"Could not find a perm group matching id {input_permission_group_id}")

    def lookup_source_id(self, input_source_id):
        """
        The source_id that goes in the database will usually be different from the
        one that came from the file.
        """
        for idx, entry in enumerate(self.dd["sources"]):
            if entry["id"] == input_source_id:
                output_source_id = self.objects["sources"][idx].id
                return output_source_id
        raise Exception(f"Could not find a source matching id {input_source_id}")

    def lookup_collection_id(self, input_collection_id):
        """
        The collection_id that goes in the database will usually be different from the
        one that came from the file.
        """
        for idx, entry in enumerate(self.dd["collections"]):
            if entry["id"] == input_collection_id:
                output_collection_id = self.objects["collections"][idx].id
                return output_collection_id
        raise Exception(f"Could not find a collection matching id {input_collection_id}")

    def lookup_concept_id(self, input_concept_id):
        """
        The concept_id that goes in the database will usually be different from the
        one that came from the file.
        """
        for idx, entry in enumerate(self.dd["concepts"]):
            if entry["id"] == input_concept_id:
                output_concept_id = self.objects["concepts"][idx].id
                return output_concept_id
        raise Exception(f"Could not find a concept matching id {input_concept_id}")

    def lookup_category_id(self, input_category_id):
        """
        The category_id that goes in the database will usually be different from the
        one that came from the file.
        """
        if not input_category_id:
            return None
        for idx, entry in enumerate(self.dd["categories"]):
            if entry["id"] == input_category_id:
                output_category_id = self.objects["categories"][idx].id
                return output_category_id
        raise Exception(f"Could not find a category matching id {input_category_id}")

    def lookup_processor_id(self, input_processor_id):
        """
        The ID is an autonumber and won't necessarily be the same between the source system
        and the destionation system. This will figure out the correct ID for the destination
        system.
        """
        processor_entry = None
        for entry in self.dd["processors"]:
            if entry["id"] == input_processor_id:
                processor_entry = entry
        if not processor_entry:
            raise Exception(f"Could not find a processor entry matching id {input_processor_id}")
        oProcessor = models.Processor.objects.filter(name=processor_entry["name"]).first()
        if not oProcessor:
            raise Exception(f"Could not find a processor matching id {input_processor_id}")
        return oProcessor.id

    def lookup_concept_handler_id(self, input_concept_handler_id):
        """
        The ID is an autonumber and won't necessarily be the same between the source system
        and the destionation system. This will figure out the correct ID for the destination
        system.
        """
        concept_handler_entry = None
        for entry in self.dd["concept_handlers"]:
            if entry["id"] == input_concept_handler_id:
                concept_handler_entry = entry
        if not concept_handler_entry:
            raise Exception(
                f"Could not find a concept handler entry matching id {input_concept_handler_id}"
            )
        oHandler = models.ConceptHandler.objects.filter(name=concept_handler_entry["name"]).first()
        if not oHandler:
            raise Exception(
                f"Could not find a concept handle matching id {input_concept_handler_id}"
            )
        return oHandler.id

    def validate_permanent_id(self, permanent_id):
        """
        Concept.permanent_id *must* be unique across the entire Chiron instance, not just in
        the dataset. This will verify that it's unique.
        """
        oConcept = models.Concept.objects.filter(permanent_id=permanent_id).first()
        if oConcept:
            if self.handle_name_conflicts:
                i = 1
                while True:
                    new_permanent_id = f"{permanent_id}_{i}"
                    oConcept = models.Concept.objects.filter(permanent_id=new_permanent_id).first()
                    if not oConcept:
                        permanent_id = new_permanent_id
                        break
                    i += 1
            else:
                raise Exception(
                    f"Name clash for Concept.permanent_id '{permanent_id}'. "
                    "Use `--handle-name-conflicts` to load anyway "
                    "(conflicting permanent_id values will be modified)."
                )
        return permanent_id

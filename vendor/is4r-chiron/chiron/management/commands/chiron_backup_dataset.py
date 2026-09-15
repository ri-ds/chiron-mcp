import json

from django.core.management.base import BaseCommand

from chiron.helpers import dataset_command_line_selection, prepare_backup_file_path
from chiron import models


class Command(BaseCommand):
    """
    Backs up the chiron data dictionary for a single dataset to a JSON file.

    PermissionGroups are included in the backup, but User and ChironUser (user permission
    settings) models are not. Log and cache models are also not backed up.
    """

    help = "Backs up the chiron data dictionary for a dataset to a JSON file."

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
            "dataset_id",
            nargs="?",
            default="no_selection",
            help="The dataset id, or 'all' to run all, or leave blank to select from a list",
        )
        parser.add_argument(
            "--filename",
            # default="no_selection",
            help="Specify a file name to use (default is '{Dataset.unique_id}.json')",
        )
        parser.add_argument(
            "--backup-dir",
            # default="no_selection",
            help="Specify the dir loc of your file if different from "
            "settings.CHIRON_DATA_DICT_BACKUP_DIR",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite backup file if one with the same name already exists.",
        )

    def handle(self, *args, **options):
        # figure out which dataset
        qDataset = models.Dataset.objects.all()
        if qDataset.count() < 1:
            self.print_out("This instance doesn't currently have any datasets.")
            self.print_out("No changes were made")
            return
        dataset_id = options["dataset_id"]
        dataset_id = dataset_command_line_selection(qDataset, dataset_id, allow_all=False)
        oDataset = models.Dataset.objects.get(id=dataset_id)
        dataset_unique_id = oDataset.unique_id
        self.print_out(f"backing up the selected dataset '{dataset_unique_id}'")

        # prepare filepath
        filename = options["filename"] if options["filename"] else f"{oDataset.unique_id}.json"
        filepath, file_exists = prepare_backup_file_path(filename, options.get("backup_dir"))
        if file_exists and not options["overwrite"]:
            raise Exception(
                f"A file with the name {filename} already exisits. Use flag "
                "`--overwrite` to save anyway or "
                " `--filename=newname.json` to specify a different name."
            )

        # start loading data into backup variable
        backup = {}
        qDataset = models.Dataset.objects.filter(id=oDataset.id).values()
        backup["dataset"] = dict(qDataset[0])

        permission_groups = models.PermissionGroup.objects.filter(dataset=oDataset).values()
        # m2m fields don't get appended automatically
        for permission_group in permission_groups:
            oPermissionGroup = models.PermissionGroup.objects.get(id=permission_group["id"])
            allowed_concepts = []
            for oConcept in oPermissionGroup.allowed_concepts.all():
                allowed_concepts.append(oConcept.id)
            allowed_data_categories = []
            for oCategory in oPermissionGroup.allowed_data_categories.all():
                allowed_data_categories.append(oCategory.id)
            allowed_collections = []
            for oCollection in oPermissionGroup.allowed_collections.all():
                allowed_collections.append(oCollection.id)
            permission_group["allowed_concepts"] = allowed_concepts
            permission_group["allowed_data_categories"] = allowed_data_categories
            permission_group["allowed_collections"] = allowed_collections
        backup["permission_groups"] = list(permission_groups)

        qDefaultPermissionGroup = models.DefaultPermissionGroup.objects.filter(
            dataset=oDataset
        ).values()
        backup["default_permission_groups"] = list(qDefaultPermissionGroup)

        qCollection = models.Collection.objects.filter(dataset=oDataset).values()
        backup["collections"] = list(qCollection)

        qCollectionRelationship = models.CollectionRelationship.objects.filter(
            pk_concept__collection__dataset=oDataset
        ).values()
        backup["collection_relationships"] = list(qCollectionRelationship)

        qSource = models.Source.objects.filter(collection__dataset=oDataset).values()
        backup["sources"] = list(qSource)

        qCategory = models.Category.objects.filter(dataset=oDataset).values()
        backup["categories"] = list(qCategory)

        qConcept = models.Concept.objects.filter(collection__dataset=oDataset).values()
        backup["concepts"] = list(qConcept)

        qDefaultConcept = models.DefaultTableDefConcept.objects.filter(dataset=oDataset).values()
        backup["default_table_def_concepts"] = list(qDefaultConcept)

        qConceptHandlerArg = models.ConceptHandlerArg.objects.filter(
            concept__collection__dataset=oDataset
        ).values()
        backup["concept_handler_args"] = list(qConceptHandlerArg)

        qScArg = models.SourceProcessorArg.objects.filter(
            source__collection__dataset=oDataset
        ).values()
        backup["source_processor_args"] = list(qScArg)

        qSourceSource = models.SourceSourceDependency.objects.filter(
            source__collection__dataset=oDataset
        ).values()
        backup["source_source_dependencies"] = list(qSourceSource)

        qConceptConcept = models.ConceptConceptDependency.objects.filter(
            concept__collection__dataset=oDataset
        ).values()
        backup["concept_concept_dependencies"] = list(qConceptConcept)

        qConceptSource = models.ConceptSourceDependency.objects.filter(
            concept__collection__dataset=oDataset
        ).values()
        backup["concept_source_dependencies"] = list(qConceptSource)

        qAutocreatedField = models.AutocreatedField.objects.filter(dataset=oDataset).values()
        backup["autocreated_fields"] = list(qAutocreatedField)

        # need copies of processors and handlers for reference
        # TODO: should be able to filter to only relevant processors
        qProcessor = models.Processor.objects.all().values()
        backup["processors"] = list(qProcessor)
        qConceptHandler = models.ConceptHandler.objects.all().values()
        backup["concept_handlers"] = list(qConceptHandler)

        with open(filepath, "w") as f:
            json.dump(backup, f, indent=4, default=str)
        self.print_out(f"Your backup has been saved to `{filepath}`")

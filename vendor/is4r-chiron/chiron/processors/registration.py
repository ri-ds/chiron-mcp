import importlib
import inspect
import pkgutil
import sys

from django.apps import apps
from django.core import checks
from django.db.utils import DatabaseError

from chiron import chiron_settings, models
from chiron.processors.abstract import (
    ConceptHandler,
    SourceProcessor,
)


def import_submodules(package, recursive=True):
    """Import all submodules of a module, recursively, including subpackages

    :param package: package (name or actual module)
    :type package: str | module
    :rtype: dict[str, types.ModuleType]
    """
    if isinstance(package, str):
        package = importlib.import_module(package)
    results = {}
    for loader, name, is_pkg in pkgutil.walk_packages(package.__path__):
        full_name = package.__name__ + "." + name
        results[full_name] = importlib.import_module(full_name)
        if recursive and is_pkg:
            results.update(import_submodules(full_name))
    return results


class ProcessorRegistry:
    """
    Allows source processor and concept handler classes to be registered with Chiron and updates
    the SourceProcessor/ConceptHandler models accordingly.
    """

    # simple list of processor objects, used to track
    processor_registry = []
    handler_registry = []
    processor_handler_pairs = []
    update_completed = False
    ontologies_checked = False

    @staticmethod
    def fullname(o):
        klass = o.__class__
        module = klass.__module__
        if module == "builtins":
            return klass.__qualname__  # avoid outputs like 'builtins.str'
        return module + "." + klass.__qualname__

    @classmethod
    def _register_processor(cls, processor):
        python_path = "{}.{}".format(processor.__module__, processor.__name__)
        # if this is not a source processor, raise an error
        ancestors = inspect.getmro(processor)
        if SourceProcessor not in ancestors:
            msg = "Not an instance of SourceProcessor: {}".format(python_path)
            raise Exception(msg)
        # check if source processor with this name already registered
        existing = next(
            (d for d in cls.processor_registry if d["name"] == processor.__name__), None
        )
        # if there are two different processors with the same name, raise an error
        if existing and existing["python_path"] != python_path:
            msg = "You can't register two processors with the same name: {}, {}".format(
                existing["python_path"], python_path
            )
            raise Exception(msg)
        # otherwise this processor has already been registered, so we can skip
        elif existing:
            return
        # register the processor
        cls.processor_registry.append(
            {
                "name": processor.__name__,
                "python_path": python_path,
                "required_args": str(inspect.signature(processor)),
                # "types": types if types is list else [types],
                "is_source_processor": True,
                "is_etl_processor": False,
                "is_cohort_def_processor": False,
                "is_display_processor": False,
                "description": processor.__doc__,
            }
        )

    @classmethod
    def _register_handler(cls, handler):
        python_path = "{}.{}".format(handler.__module__, handler.__name__)
        # if this is not a concept handler, raise an error
        ancestors = inspect.getmro(handler)
        if ConceptHandler not in ancestors:
            msg = "Not an instance of ConceptHandler: {}".format(python_path)
            raise Exception(msg)
        # check if concept handler with this name already registered
        existing = next((d for d in cls.processor_registry if d["name"] == handler.__name__), None)
        # if there are two different concept handlers with the same name, raise an error
        if existing and existing["python_path"] != python_path:
            msg = "You can't register two concept handlers with the same name: {}, {}".format(
                existing["python_path"], python_path
            )
            raise Exception(msg)
        # otherwise this concept handler has already been registered, so we can skip
        elif existing:
            return
        # register the concept handler
        cls.handler_registry.append(
            {
                "name": handler.__name__,
                "python_path": python_path,
                # "required_args": str(inspect.signature(handler)),
                # "types": types if types is list else [types],
                "description": handler.__doc__,
            }
        )

    @classmethod
    def register(
        cls,
        source_processors,  # the source processor class(es)
        concept_handlers,  # the concept handler class(es)
    ):
        if not isinstance(source_processors, list):
            source_processors = [source_processors]
        if not isinstance(concept_handlers, list):
            concept_handlers = [concept_handlers]
        for processor in source_processors:
            cls._register_processor(processor)
        for handler in concept_handlers:
            cls._register_handler(handler)
        for processor in source_processors:
            processor_name = processor.__name__
            for handler in concept_handlers:
                handler_name = handler.__name__
                pair = (processor_name, handler_name)
                if pair not in cls.processor_handler_pairs:
                    cls.processor_handler_pairs.append(pair)

    @classmethod
    def check_ontology_dependencies(cls):
        """
        Concepts with datatype of "ontology" require the "ontologies" Django app. This app is
        optional: you don't need it if you don't have any concepts like this. Or you can set
        CHIRON_TREAT_ONTOLOGY_CONCEPTS_AS_TEXT=True in your Django settings, and any concepts
        like this will use the TextHander instead.

        This method makes sure you have a valid setup for ontologies, and will raise an error
        or warning if there are any problems. It is intended to be run when a Django
        management command is run - currently from chiron/admin.py
        """
        errors = []
        # don't run update if it has already been run
        if cls.ontologies_checked:
            return errors
        try:
            has_ontology_concepts = False
            oHandler = models.ConceptHandler.objects.filter(name="OntologyHandler").first()
            if oHandler:
                qConcept = models.Concept.objects.filter(concept_handler=oHandler)
                has_ontology_concepts = qConcept.count() != 0
        except DatabaseError:
            # don't run checks if the database isn't currently set up
            return errors
        if has_ontology_concepts:
            if chiron_settings.CHIRON_TREAT_ONTOLOGY_CONCEPTS_AS_TEXT:
                if apps.is_installed("ontologies"):
                    # user has ontologies app so remind them they're not using it
                    errors.append(
                        checks.Warning(
                            "You have ontology concepts in your data dictionary "
                            "and you have the optional ontologies "
                            "app installed. But your system is not using those features "
                            "because CHIRON_TREAT_ONTOLOGY_CONCEPTS_AS_TEXT "
                            "is set to True in your settings.",
                        )
                    )
                else:
                    # remind them of this setting
                    errors.append(
                        checks.Warning(
                            "Ontology concepts are being treated as standard text "
                            "concepts because CHIRON_TREAT_ONTOLOGY_CONCEPTS_AS_TEXT "
                            "is set to True in your settings.",
                        )
                    )
            else:
                # using ontology concepts so make sure "ontologies" is installed
                if not apps.is_installed("ontologies"):
                    errors.append(
                        checks.Error(
                            "The ontology app is not available or is not in your Django "
                            "INSTALLED_APPS. Either install it or use setting "
                            "CHIRON_TREAT_ONTOLOGY_CONCEPTS_AS_TEXT to treat ontology "
                            "concepts as standard text concepts instead."
                        )
                    )

        cls.ontologies_checked = True
        return errors

    @classmethod
    def update_registry(cls):
        errors = []
        # don't run update if it has already been run
        if cls.update_completed:
            return errors
        # don't run update for tests (Processor table won't exist yet in the database)
        try:
            models.Processor.objects.all().count()
        except DatabaseError:
            return errors
        # print a warning if the ontology service is available but turned off
        try:
            import ontologies.interface_class  # noqa: F401

            if chiron_settings.CHIRON_TREAT_ONTOLOGY_CONCEPTS_AS_TEXT:
                errors.append(
                    checks.Warning(
                        """Using text concept as ontology default but ontology service is found, 
                    toggle CHIRON_TREAT_ONTOLOGY_CONCEPTS_AS_TEXT in your settings to use
                    ontology instead"""
                    )
                )
        except ModuleNotFoundError:
            errors.append(
                checks.Warning(
                    """Ontology module not found. Please add it and set it up if you want full
                functionality"""
                )
            )
            if chiron_settings.CHIRON_TREAT_ONTOLOGY_CONCEPTS_AS_TEXT:
                errors.append(
                    checks.Warning(
                        "Using text concept as ontology default, ontology service is not found"
                    )
                )
        # make sure that modules registering processors are loaded
        for mod_path in chiron_settings.CHIRON_PROCESSOR_MODULES:
            try:
                importlib.import_module(mod_path)
                # import this module and all child modules
                # TODO: we haven't decided whether to import registration recursively from
                #  submodules or not. It might cause more problems than it solves.
                # import_submodules(mod_path)
            except ModuleNotFoundError as e:
                msg = (
                    "WARNING: The Chiron processor registry failed to find package/module '{}'"
                ).format(mod_path)
                errors.append(checks.Error(msg))
                errors.append(checks.Error(str(e)))
                errors.append(
                    checks.Info(
                        "This error can also be caused by a syntax problem in your package/module"
                    )
                )
                errors.append(checks.Info("Your pythonpath:", sys.path))

        # check for missing processors, warn if being used by a source, otherwise delete
        names = [d["name"] for d in cls.processor_registry]
        qProcessor = models.Processor.objects.filter(is_source_processor=True).exclude(
            name__in=names
        )
        if qProcessor:
            for oProcessor in qProcessor:
                qSource = models.Source.objects.filter(processor=oProcessor)
                if qSource:
                    msg = "Processor '{}' is used by Source but isn't registered".format(
                        oProcessor.name
                    )
                    errors.append(checks.Warning(msg))
                else:
                    oProcessor.delete()
        # create new / update existing source processor database entries
        for entry in cls.processor_registry:
            oProc = models.Processor.objects.filter(name=entry["name"]).first()
            if not oProc:
                oProc = models.Processor(name=entry["name"])
            oProc.python_path = entry["python_path"]
            oProc.required_args = entry["required_args"]
            oProc.description = entry["description"]
            oProc.is_source_processor = entry["is_source_processor"]
            oProc.is_etl_processor = False
            oProc.is_cohort_def_processor = False
            oProc.is_display_processor = False
            oProc.save()

        # check for missing handlers, warn if being used by a concept, otherwise delete
        names = [d["name"] for d in cls.handler_registry]
        qHandler = models.ConceptHandler.objects.exclude(name__in=names)
        if qHandler:
            for oHandler in qHandler:
                qConcept = models.Concept.objects.filter(concept_handler=oHandler)
                if qConcept:
                    msg = "Concept handler '{}' is used by a concept but isn't registered".format(
                        oHandler.name
                    )
                    errors.append(checks.Warning(msg))
                else:
                    oHandler.delete()
        # create new / update existing concept handler database entries
        for entry in cls.handler_registry:
            oHandler = models.ConceptHandler.objects.filter(name=entry["name"]).first()
            if not oHandler:
                oHandler = models.ConceptHandler(name=entry["name"])
            oHandler.python_path = entry["python_path"]
            oHandler.description = entry["description"]
            oHandler.save()

        # save valid pairs of source processor / concept handlers that can be used together
        for pair in cls.processor_handler_pairs:
            oProcessor = models.Processor.objects.get(name=pair[0])
            oHandler = models.ConceptHandler.objects.get(name=pair[1])
            oCombo, created = models.ProcessorHandlerCombo.objects.get_or_create(
                processor=oProcessor, handler=oHandler
            )

        # mark complete so we don't rerun
        cls.update_completed = True

        return errors

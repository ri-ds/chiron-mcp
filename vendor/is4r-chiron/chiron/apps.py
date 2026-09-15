from django.apps import AppConfig
from django.core import checks
from django.core.checks import Tags, register


def update_processors(app_configs, **kwargs):
    from chiron.processors import ProcessorRegistry

    errors = []

    # update chiron processors every time a management command is called
    try:
        errors += ProcessorRegistry.update_registry()
        errors += ProcessorRegistry.check_ontology_dependencies()
    except Exception as e:
        errors.append(checks.Error("There was an error checking the Chiron processor registry"))
        raise e

    return errors


class ChironConfig(AppConfig):
    name = "chiron"

    def ready(self):
        # import chiron.signals  # noqa

        register(update_processors, Tags.compatibility)

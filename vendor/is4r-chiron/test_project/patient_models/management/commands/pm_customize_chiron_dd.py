from django.core.management.base import BaseCommand

from chiron.models import Dataset, Concept, ConceptHandler


class Command(BaseCommand):
    """
    The Chiron dataset `dataset3_autocreated_copy2` is used to test data dictionary autocreate, but
    then the data is also used to test other Chiron features. In tests after autocreate has been
    run, this command can be run to further customize the data dictionary beyond what autocreate
    can do.
    """

    help = "Make minor changes to dataset3_autocreated_copy2 chiron dd after autocreate"

    # add optional command line arguments
    def add_arguments(self, parser):
        pass

    # this will be executed when the command is called
    def handle(self, *args, **options):
        self.stdout.write("customizing dataset3_autocreated_copy2 data dictionary")
        oDataset = Dataset.objects.get(unique_id="dataset3_autocreated_copy2")

        oConceptHandler = ConceptHandler.objects.get(name="TextHandler")
        oConcept = Concept.objects.get(
            collection__dataset=oDataset, permanent_id__startswith="m2m_text_field_"
        )
        oConcept.concept_handler = oConceptHandler
        oConcept.save()

        oConceptHandler = ConceptHandler.objects.get(name="IntegerWithCategoriesHandler")
        oConcept = Concept.objects.get(
            collection__dataset=oDataset, permanent_id__startswith="m2m_integer_category_field_"
        )
        oConcept.concept_handler = oConceptHandler
        oConcept.save()

        oConceptHandler = ConceptHandler.objects.get(name="FloatWithCategoriesHandler")
        oConcept = Concept.objects.get(
            collection__dataset=oDataset, permanent_id__startswith="m2m_float_category_field_"
        )
        oConcept.concept_handler = oConceptHandler
        oConcept.save()

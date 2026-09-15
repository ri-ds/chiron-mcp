import math
import random
from faker import Faker

from django.conf import settings

from chiron.processors.abstract import SourceProcessor
from chiron.processors.abstract import StandardLoadMixin
from chiron import models
from .source_encounter import SourceEncounter
from ontologies.models import BaseOntologyItem, Ontology


def get_random_ontology_codes(ontology_name, count):
    """
    Pulls specified number of codes from the provided ontology.
    """
    oOntology = Ontology.objects.get(name=ontology_name)
    qItem = BaseOntologyItem.objects.filter(ont_id=oOntology).order_by("?")[:count]
    response = []
    for oItem in qItem:
        response.append(oItem.code)
    return response


def procedure_iterator():
    # we need to get a list of patient_id values from mongo
    # we need to generate a list of med id / med name values
    # create records choosing randomly from our lists
    # maybe I can store lists as arrays and generate integer to specify index

    # generate a list of medications
    fake = Faker(use_weighting=False)
    fake.seed_instance(1913)

    encounter_count = settings.SMALL_COLLECTION_COUNT
    procedure_count = settings.SMALL_COLLECTION_COUNT
    avg_proc_per_encounter = math.floor(procedure_count / encounter_count)
    # 10% of patients get half encounters, 50% get half encounters, and 40% get no encounters
    first_10_percent = encounter_count * 0.1
    next_50_percent = encounter_count * 0.5

    procedures = []
    for i in range(1000):
        procedures.append(
            (
                fake.unique.numerify(text="DX######"),
                " ".join(fake.words(nb=4)),
            )
        )

    # iterate patients so we have the same ids
    oEncounterSource = models.Source.objects.get(name="faker_encounters")
    encounter_source = SourceEncounter(oEncounterSource)
    phecodes = get_random_ontology_codes("phecodex", settings.ONTOLOGY_UNIQUE_COUNT)
    rxnorm_codes = get_random_ontology_codes("rxnorm", settings.ONTOLOGY_UNIQUE_COUNT)
    for i, encounter_record in enumerate(encounter_source.get_source()):
        if i < first_10_percent:
            current_proc_count = avg_proc_per_encounter * 5
        elif i < (first_10_percent + next_50_percent):
            current_proc_count = avg_proc_per_encounter
        else:
            break
        for j in range(current_proc_count):
            proc_index = fake.random_int(min=0, max=999, step=1)
            try:
                record = {
                    "patient_id": encounter_record["patient_id"],
                    "encounter_id": encounter_record["encounter_id"],
                    "proc_id": fake.unique.numerify(text="###########"),
                    "proc_date": fake.date_between_dates(
                        encounter_record["encounter_start"], encounter_record["encounter_end"]
                    ),
                    "proc_code": procedures[proc_index][0],
                    "proc_name": procedures[proc_index][1],
                    "proc_phecode": random.choice(phecodes),
                    "proc_rxnorm": random.choice(rxnorm_codes),
                }
            except OSError:
                # getting a very occasional error with fake.date_between_dates() and not sure why
                continue
            yield record


class SourceProcedure(StandardLoadMixin, SourceProcessor):
    def get_source(self):
        """
        Return an iterable of dicts
        """
        iterator = procedure_iterator()
        return iterator

    def get_subject_match_def(self, record):
        """
        Get subject ID from record
        """
        return record["patient_id"]

    def get_collection_id(self, record):
        """
        Get collection ID from record (not relevant for Subject collection)
        """
        return record["proc_id"]

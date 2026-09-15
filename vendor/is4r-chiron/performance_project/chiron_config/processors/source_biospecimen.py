import math
from faker import Faker

from django.conf import settings

from chiron.processors.abstract import SourceProcessor
from chiron.processors.abstract import StandardLoadMixin
from chiron import models
from .source_encounter import SourceEncounter


def biospecimen_iterator():
    # we need to get a list of patient_id values from mongo
    # we need to generate a list of med id / med name values
    # create records choosing randomly from our lists
    # maybe I can store lists as arrays and generate integer to specify index

    # generate a list of medications
    fake = Faker(use_weighting=False)
    fake.seed_instance(1913)

    encounter_count = settings.SMALL_COLLECTION_COUNT
    biospecimen_count = settings.SMALL_COLLECTION_COUNT
    avg_dx_per_encounter = math.floor(biospecimen_count / encounter_count)
    # 10% of patients get half encounters, 50% get half encounters, and 40% get no encounters
    first_10_percent = encounter_count * 0.1
    next_50_percent = encounter_count * 0.5

    biospecimen = [
        (1, "blood"),
        (2, "plasma"),
        (3, "nasal"),
        (4, "urine"),
        (5, "stool"),
    ]
    for i in range(1000):
        biospecimen.append(
            (
                fake.unique.numerify(text="DX######"),
                " ".join(fake.words(nb=4)),
            )
        )

    # iterate patients so we have the same ids
    oEncounterSource = models.Source.objects.get(name="faker_encounters")
    encounter_source = SourceEncounter(oEncounterSource)
    for i, encounter_record in enumerate(encounter_source.get_source()):
        if i < first_10_percent:
            current_biospecimen_count = avg_dx_per_encounter * 5
        elif i < (first_10_percent + next_50_percent):
            current_biospecimen_count = avg_dx_per_encounter
        else:
            break
        for j in range(current_biospecimen_count):
            biospecimen_index = fake.random_int(min=0, max=4, step=1)
            try:
                record = {
                    "patient_id": encounter_record["patient_id"],
                    "encounter_id": encounter_record["encounter_id"],
                    "biospecimen_id": fake.unique.numerify(text="###########"),
                    "biospecimen_collection_date": fake.date_between_dates(
                        encounter_record["encounter_start"], encounter_record["encounter_end"]
                    ),
                    "biospecimen_type": biospecimen[biospecimen_index][1],
                    "freezer_position": fake.random_int(min=1, max=5000, step=1),
                }
            except OSError:
                # getting a very occasional error with fake.date_between_dates() and not sure why
                continue
            yield record


class SourceBiospecimen(StandardLoadMixin, SourceProcessor):
    def get_source(self):
        """
        Return an iterable of dicts
        """
        iterator = biospecimen_iterator()
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
        return record["biospecimen_id"]

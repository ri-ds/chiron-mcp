import math
from datetime import timedelta
from faker import Faker

from django.conf import settings

from chiron.processors.abstract import SourceProcessor
from chiron.processors.abstract import StandardLoadMixin
from chiron import models
from .source_patient import SourcePatient


def encounter_iterator():
    # we need to get a list of patient_id values from mongo
    # we need to generate a list of med id / med name values
    # create records choosing randomly from our lists
    # maybe I can store lists as arrays and generate integer to specify index

    # generate a list of medications
    fake = Faker(use_weighting=False)
    fake.seed_instance(1913)

    pt_count = settings.PATIENT_COUNT
    encounter_count = settings.SMALL_COLLECTION_COUNT
    avg_enc_per_patient = math.floor(encounter_count / pt_count)
    # 10% of patients get half encounters, 50% get half encounters, and 40% get no encounters
    first_10_percent = pt_count * 0.1
    next_50_percent = pt_count * 0.5

    # iterate patients so we have the same ids
    oPatientSource = models.Source.objects.get(name="faker_patients")
    patient_source = SourcePatient(oPatientSource)
    for i, patient_record in enumerate(patient_source.get_source()):
        if i < first_10_percent:
            current_enc_count = avg_enc_per_patient * 5
        elif i < (first_10_percent + next_50_percent):
            current_enc_count = avg_enc_per_patient
        else:
            break
        for j in range(current_enc_count):
            # enc_index = fake.random_int(min=0, max=999, step=1)
            enc_start = fake.date_object()
            record = {
                "patient_id": patient_record["patient_id"],
                "encounter_id": fake.unique.numerify(text="###########"),
                "encounter_start": enc_start,
                "encounter_end": enc_start + timedelta(days=fake.random_int(min=0, max=7, step=1)),
            }
            yield record


class SourceEncounter(StandardLoadMixin, SourceProcessor):
    def get_source(self):
        """
        Return an iterable of dicts
        """
        iterator = encounter_iterator()
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
        return record["encounter_id"]

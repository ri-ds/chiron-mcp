import math
from datetime import date
from faker import Faker

from django.conf import settings

from chiron.processors.abstract import SourceProcessor
from chiron.processors.abstract import StandardLoadMixin
from chiron import models
from .source_patient import SourcePatient


def med_iterator():
    # we need to get a list of patient_id values from mongo
    # we need to generate a list of med id / med name values
    # create records choosing randomly from our lists
    # maybe I can store lists as arrays and generate integer to specify index

    # generate a list of medications
    fake = Faker(use_weighting=False)
    fake.seed_instance(1913)

    pt_count = settings.PATIENT_COUNT
    med_count = settings.LARGE_COLLECTION_COUNT
    avg_med_per_patient = math.floor(med_count / pt_count)
    # 10% of patients get half meds, 50% get half meds, and 40% get no meds
    first_10_percent = pt_count * 0.1
    next_50_percent = pt_count * 0.5

    meds = []
    for i in range(1000):
        meds.append(
            (
                fake.unique.numerify(text="MED######"),
                " ".join(fake.words(nb=4)),
            )
        )

    # iterate patients so we have the same ids
    oPatientSource = models.Source.objects.get(name="faker_patients")
    patient_source = SourcePatient(oPatientSource)
    for i, patient_record in enumerate(patient_source.get_source()):
        if i < first_10_percent:
            current_med_count = avg_med_per_patient * 5
        elif i < (first_10_percent + next_50_percent):
            current_med_count = avg_med_per_patient
        else:
            break
        for j in range(current_med_count):
            med_index = fake.random_int(min=0, max=999, step=1)
            med_start = fake.date_object()
            record = {
                "patient_id": patient_record["patient_id"],
                "order_id": fake.unique.numerify(text="###########"),
                "med_id": meds[med_index][0],
                "med_name": meds[med_index][1],
                "med_start": med_start,
                "med_end": fake.date_between_dates(med_start, date.today()),
                "currently_taking": False,
                "med_dose": fake.random_int(min=1, max=10000, step=1) / 10,
                "med_units": fake.random_element(elements=("mg/ml", "g", "units", "mg/dl")),
                "med_comment": fake.sentence(nb_words=20, variable_nb_words=True),
            }
            yield record


class SourceMedication(StandardLoadMixin, SourceProcessor):
    def get_source(self):
        """
        Return an iterable of dicts
        """
        iterator = med_iterator()
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
        return record["order_id"]

from faker import Faker

from django.conf import settings

from chiron.processors.abstract import SourceProcessor
from chiron.processors.abstract import StandardLoadMixin


def patient_iterator():
    fake = Faker(use_weighting=False)
    fake.seed_instance(4816)
    for i in range(settings.PATIENT_COUNT):
        record = {
            "patient_id": fake.unique.numerify(text="###########"),
            "patient_firstname": fake.first_name(),
            "patient_lastname": fake.last_name(),
            "gender": fake.random_element(elements=("M", "F", None)),
            "marital_status": fake.null_boolean(),
            "patient_birthdate": fake.date_of_birth(minimum_age=0, maximum_age=99),
            "patient_deathdate": None,
            "healthcare_coverage": fake.random_int(min=100, max=50000, step=1),
            "healthcare_expenses": fake.random_int(min=0, max=2000000, step=1) / 100,
        }
        yield record


class SourcePatient(StandardLoadMixin, SourceProcessor):
    def get_source(self):
        """
        Return an iterable of dicts
        """
        iterator = patient_iterator()
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
        return record["patient_id"]

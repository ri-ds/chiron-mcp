"""
This module contains concept handlers for creating detailed age concepts. A detailed age concept
is not just a year,
but has details down to the day either as a year float values or age in days int value. If you
only need age in year, you can load that as a regular integer.

If your source data already has detailed ages, you can use those. Or once you load all your data,
you can create calculated detailed age concepts using a DOB concept and an event date concept
as input.

Generally dates are considered PHI, so detailed ages are a nice alternative when you don't want to
expose PHI. Longitudinal queries work with either dates or detailed ages (but your whole project
must use one or the other).
"""

import datetime

from chiron.processors.abstract import EtlProcessor
from chiron.processors.etl.django_field import EtlDjangoField
from chiron.processors.etl.clean_value import SimpleClean
from chiron.processors.utils import DjangoModelObjectValueRetriever


class EtlDictAgeInYearsToDays(EtlProcessor):
    """
    Loads a float value age where the whole number is the year and the decimal values
    gives fraction of a year. The value will be stored in the research database as days old, which
    is the most supported structure for ages in Chiron.

    If you have age as a year only, you can treat it as an integer instead.
    """

    def __init__(self, oConcept, field_name):
        super().__init__(oConcept)
        self.field_name = field_name

    def pull_concept_value_from_record(self, record):
        age_in_years = record.get(self.field_name, None)
        if age_in_years:
            age_in_days = round(float(age_in_years) * 365.25)
            return age_in_days
        return None


class EtlDjangoAgeInYearsToDays(EtlDjangoField):
    """
    Loads a float value age where the whole number is the year and the decimal values
    gives fraction of a year. The value will be stored in the research database as days old, which
    is the most supported structure for ages in Chiron.

    If you have age as a year only, you can treat it as an integer instead.
    """

    def pull_concept_value_from_record(self, record):
        # use the retriever to get the field value(s)
        retriever = DjangoModelObjectValueRetriever(
            self.full_field_name, ignore_model_mismatch=self.ignore_model_mismatch
        )
        age_in_years = retriever(record)
        if age_in_years not in [None, "***missing***"]:
            age_in_days = round(float(age_in_years) * 365.25)
            return age_in_days
        return None


class EtlCalculateAgeFromDates(EtlProcessor):
    """
    Calculates age in days at event using DOB and event date. Must have a DOB concept in the
    subject collection and an event date concept in the subcollection of interest.
    """

    def __init__(self, oConcept, dob_concept_id, event_date_concept_id):
        super().__init__(oConcept)
        self.concept = oConcept
        self.warnings = []
        # Warnings about any issues while cleaning values (ex. whitespace was stripped)
        self.dob_concept_id = dob_concept_id
        self.event_date_concept_id = event_date_concept_id
        self.input_date_cleaner = SimpleClean("date")

    def _make_date(self, value):
        if isinstance(value, datetime.datetime):
            return value.date()
        return value

    def pull_concept_value_from_record(self, record):
        dob = record["doc"].get(self.dob_concept_id, None)
        event_date = record["subdoc"].get(self.event_date_concept_id, None)
        dob = self.input_date_cleaner.clean(dob)
        event_date = self.input_date_cleaner.clean(event_date)
        if dob and event_date:
            delta = self._make_date(event_date) - self._make_date(dob)
            return delta.days
        return None

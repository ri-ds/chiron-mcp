"""
The current age should be saved as year only, and typically anyone over 89 should be grouped
as "90 and above"
"""

import datetime

from chiron.processors.abstract.etl_processor import EtlProcessor
from chiron.processors.etl.clean_value import SimpleClean


class EtlDictCurrentAgeFromDob(EtlProcessor):
    """
    Calculates current age in years from DOB. If over 89, sets to "90 and above". If a DOD
    is also provided, gives the age at date of death.
    """

    def __init__(self, oConcept, field_name, death_date_field_name=None):
        super().__init__(oConcept)
        self.concept = oConcept
        # Warnings about any issues while cleaning values (ex. whitespace was stripped)
        self.warnings = []
        self.dob_field = field_name
        self.dod_field = death_date_field_name
        self.input_date_cleaner = SimpleClean("date")
        self.data_cleaner = SimpleClean("integer/string")

    def pull_concept_value_from_record(self, record):
        dob = self.input_date_cleaner.clean(record.get(self.dob_field, None))
        if dob:
            dod = self.input_date_cleaner.clean(record.get(self.dod_field, None))
            end_date = dod if dod else datetime.date.today()
            age = (
                end_date.year - dob.year - ((end_date.month, end_date.day) < (dob.month, dob.day))
            )
            if age > 89:
                age = "90 and above"
            return self.data_cleaner.clean(age)
        return None

"""
This module contains specialized processors you can use to generate ID fields, especially
deidentified IDs. You can generate both subject IDs and IDs for subcollections (like a visit ID).

IDs are a useful for a user to ensuring a report has one record per patient, visit,
etc. But many IDs are PHI, so you might not want to show those.

An easy way to generate IDs is just as a random string or autoincremented number, but IDs
generated in this way will change every time the ETL is rerun. The ID fields here get around
this by using existing identifying field(s) (such as an MRN) and applying asymmetric encryption
to get a deidentified ID that will be the same for a subject every time.

If your source data already has an appropriate ID for a collection, no need to generate one here.
You can just load the ID as a regular text field.
"""

import hashlib

from django.conf import settings

from chiron.processors.abstract import EtlProcessor


class EtlGeneratedSubjectId(EtlProcessor):
    """
    Generates a deidentified subject ID using other attributes as input.

    - The value won't change even on rerun of the ETL (as long as the underlying inputs don't
      change).
    - Uses asymmetric encryption. Uses the SECRET_KEY in Django settings as a salt value to prevent
      brute force attempts to re-identify.

    Create a deidentified ID from an identified ID such as MRN or SSN:

    - Use the identified ID as input.

    Create a doubly deidentified ID (twice removed from identifying information):

    - Use an already deidentified ID (such as a study ID) as input.

    Create a deidentified ID when no usable ID is available:

    - Use any combination of fields that you're confident will uniquely identify a patient.
    - For example, last name and DOB would probably be sufficient on a small group of patients.
    - Use fields with stable values. If the input values change, this ID will also change.

    :input_fields: (str) A comma separated list of field name(s) to use as input
    :length: (int, default=10) How many values in your output string (must be an even number).
    """

    def __init__(self, oConcept, input_fields, length=10):
        super().__init__(oConcept)
        self.concept = oConcept
        # Warnings about any issues while cleaning values (ex. whitespace was stripped)
        self.input_fields = []
        for input_field in input_fields.split(","):
            self.input_fields.append(input_field.strip())
        self.warnings = []
        self.digest_size = round(length / 2)
        self.salt = getattr(settings, "SECRET_KEY", "nosalt :-(")
        if not self.salt:
            self.warnings.append(
                "You do not have SECRET_KEY defined in your Django settings. "
                "This deidentified ID would be more secure with a SECRET_KEY."
            )

    def pull_concept_value_from_record(self, record):
        # using blake2b hash, which allows a custom output length
        h = hashlib.blake2b(digest_size=self.digest_size)
        # if the Django secret key is available, use as a salt for the encryption
        h.update(self.salt.encode())
        # add each input value to the encryption input
        for input_field in self.input_fields:
            value = str(record.get(input_field))
            h.update(value.encode())
        # return the encrypted string
        return h.hexdigest().upper()


class EtlGeneratedSubcollectionId(EtlProcessor):
    """
    Generates a deidentified subcollection ID using other attributes as input.

    - The value won't change even on rerun of the ETL (as long as the underlying inputs don't
      change).
    - Uses asymmetric encryption. Uses the SECRET_KEY in Django settings as a salt value to prevent
      brute force attempts to re-identify.

    Create a deidentified ID from an identified ID such as Epic Encounter CSN:

    - Use the identified ID as input.

    Create a deidentified ID when no usable ID is available:

    - Use any combination of fields that you're confident will uniquely identify a record.
    - For example, could use procedure_name and visit_date for a procedure record assuming that
      nobody can have 2 of the same procedure on the same date.
    - Use fields with stable values. If the input values change, this ID will also change.

    :subcol_fields: (str) A comma sep list of field name(s) in this collection to use as input
    :subject_fields: (str) A comma sep list of field name(s) in the subject collection to use
      as input
    :length: (int, default=10) How many values in your output string (must be an even number).
    """

    def __init__(self, oConcept, subcol_fields="", subject_fields="", length=10):
        super().__init__(oConcept)
        self.concept = oConcept
        self.warnings = []
        # Warnings about any issues while cleaning values (ex. whitespace was stripped)
        self.subcol_fields = []
        for subcol_field in subcol_fields.split(","):
            self.subcol_fields.append(subcol_field.strip())
        self.subject_fields = []
        for subject_field in subject_fields.split(","):
            self.subject_fields.append(subject_field.strip())
        if not self.subcol_fields and not self.subject_fields:
            self.warnings.append("no input fields were defined, every ID will have the same value")
        self.digest_size = round(length / 2)
        self.salt = getattr(settings, "SECRET_KEY", "nosalt :-(")
        if not self.salt:
            self.warnings.append(
                "You do not have SECRET_KEY defined in your Django settings. "
                "This deidentified ID would be more secure with a SECRET_KEY."
            )

    def pull_concept_value_from_record(self, record):
        # using blake2b hash, which allows a custom output length
        h = hashlib.blake2b(digest_size=self.digest_size)
        # if the Django secret key is available, use as a salt for the encryption
        h.update(self.salt.encode())
        # add each input value to the encryption input
        for subcol_field in self.subcol_fields:
            value = str(record["subdoc"].get(subcol_field))
            h.update(value.encode())
        for subject_field in self.subject_fields:
            value = str(record["doc"].get(subject_field))
            h.update(value.encode())
        # return the encrypted string
        return h.hexdigest().upper()

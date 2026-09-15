from chiron.processors.abstract.concept_handler import ConceptHandler
from chiron.processors.etl.chiron_subject_id import EtlChironSubjectId
from chiron.processors.etl.auto_subject_id import (
    EtlGeneratedSubjectId,
    EtlGeneratedSubcollectionId,
)
from chiron.processors.concept_handlers.standard_concept_handlers import (
    TextHandler,
    IntegerWithCategoriesHandler,
    DetailedAgeHandler,
)
from chiron.processors.etl.detailed_age import EtlCalculateAgeFromDates
from chiron.processors.etl.current_age import EtlDictCurrentAgeFromDob
from chiron.processors import CohortDefText
from chiron.processors import DisplayText, DisplaySubjectHyperlink
from chiron import chiron_settings


class SubjectMatchingToTextHandler(ConceptHandler):
    """
    Copies a chiron subject ID field used for matching (stored in `_ids`) into a concept.
    Typically these fields are only used internally, so this is a way to make them available to
    users.

    - Must be used with source processor SourceSelf, and this source must be run after any sources
      that populate the subject ID field.
    - The value will be converted to a string.
    """

    display_name = "text"

    def get_stored_data_type(self):
        return ("varchar", 255)

    def set_kwarg_options(self):
        self.append_handler_arg_option("subject_id_name", "the subject ID name", required=True)

    def set_etl_processor(self, concept):
        self.etl_processor = EtlChironSubjectId(
            concept,
            subject_id_name=self.get_handler_arg_value("subject_id_name"),
            cast_to_type="string",
        )

    def set_cohort_def_processor(self, chironuser, dataset, concept, prefilter_value):
        self.cohort_def_processor = CohortDefText(
            chironuser, dataset, concept, prefilter_value=prefilter_value
        )

    def set_display_processor(self, chironuser, concept):
        self.display_processor = DisplayText(chironuser, concept)


class SubjectMatchingToSubjectHyperlinkHandler(SubjectMatchingToTextHandler):
    """
    Copies a chiron subject ID field used for matching (stored in `_ids`) into a concept.
    Typically these fields are only used internally, so this is a way to make them available to
    users. In some contexts, this ID can be used as a hyperlink to go to subject details view.

    - Must be used with source processor SourceSelf, and this source must be run after any sources
      that populate the subject ID field.
    - The value will be converted to a string.
    """

    display_name = "subject hyperlink"

    def get_stored_data_type(self):
        return {
            "val": ("varchar", 120),
            "link": "text",
        }

    def set_display_processor(self, chironuser, concept):
        self.display_processor = DisplaySubjectHyperlink(chironuser, concept)


class AutoSubjectIdHandler(TextHandler):
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

    def get_stored_data_type(self):
        return ("varchar", 120)

    def set_kwarg_options(self):
        desc = (
            "The dict key value(s) for any fields you want to generate "
            "the id from (as comma separated string)"
        )
        self.append_handler_arg_option("input_fields", desc, required=True)
        desc = (
            "The number of characters for the final ID (must be an even number). This "
            "should be long enough to prevent name clashes. Default is 10."
        )
        self.append_handler_arg_option("length", desc, default_value=10, required=False)

    def set_etl_processor(self, concept):
        self.etl_processor = EtlGeneratedSubjectId(
            concept,
            input_fields=self.get_handler_arg_value("input_fields"),
            length=self.get_handler_arg_value("length"),
        )


class AutoSubcollectionIdHandler(TextHandler):
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

    def get_stored_data_type(self):
        return ("varchar", 120)

    def set_kwarg_options(self):
        desc = (
            "The dict key value(s) for any subcollection fields you want to generate "
            "the id from (as comma separated string)"
        )
        self.append_handler_arg_option("subcol_fields", desc, required=False, default_value="")

        desc = (
            "The dict key value(s) for any subject collection fields you want to generate "
            "the id from (as comma separated string)"
        )
        self.append_handler_arg_option("subject_fields", desc, required=False, default_value="")

        desc = (
            "The number of characters for the final ID (must be an even number). This "
            "should be long enough to prevent name clashes. Default is 10."
        )
        self.append_handler_arg_option("length", desc, required=False, default_value=10)

    def set_etl_processor(self, concept):
        self.etl_processor = EtlGeneratedSubcollectionId(
            concept,
            subcol_fields=self.get_handler_arg_value("subcol_fields"),
            subject_fields=self.get_handler_arg_value("subject_fields"),
            length=self.get_handler_arg_value("length"),
        )


class CurrentAgeFromDobHandler(IntegerWithCategoriesHandler):
    """
    Uses a DOB (and optional) DOD to create a deidentified age field.

    - ages will be at the year level
    - patients over 89 will show as "90 and above".

    :field_name: (str) The field name for the date of birth
    :death_date_field_name: (str, optional) The field name for the date of death
    """

    def get_stored_data_type(self):
        return {
            "val": "text",  # the value as a string
            "num": "integer",  # number if numeric, else None
            "txt": "text",  # value as a string if non-numeric, else None
        }

    def set_kwarg_options(self):
        self.append_handler_arg_option("field_name", "the field name for DOB", required=True)
        self.append_handler_arg_option(
            "death_date_field_name", "the field name for DOD", required=False, default_value=None
        )

    def set_etl_processor(self, concept):
        self.etl_processor = EtlDictCurrentAgeFromDob(
            concept,
            field_name=self.get_handler_arg_value("field_name"),
            death_date_field_name=self.get_handler_arg_value("death_date_field_name"),
        )


class DetailedAgeFromDatesHandler(DetailedAgeHandler):
    """
    Use with the SourceSelfSubdoc processor to generate a detailed age at event from two dates
    (DOB and event date).

    - the source for this concept must be run after the referenced concepts have been loaded
    - the DOB must be in the subject collection and the event date must be in the subcollection

    :dob_concept_id: (str) The concept permanent ID for the date of birth
    :event_date_concept_id: (str) The concept permanent ID for the event
    """

    def get_stored_data_type(self):
        return "float"

    def set_kwarg_options(self):
        desc = "The concept permanent ID for the DOB concept in the subject collection"
        self.append_handler_arg_option("dob_concept_id", desc, required=True)

        desc = "The concept permanent ID for the event date concept in the subcollection"
        self.append_handler_arg_option("event_date_concept_id", desc, required=True)

    def set_etl_processor(self, concept):
        self.etl_processor = EtlCalculateAgeFromDates(
            concept,
            dob_concept_id=self.get_handler_arg_value("dob_concept_id"),
            event_date_concept_id=self.get_handler_arg_value("event_date_concept_id"),
        )


# For concepts using the ontology datatype (implemented by OntologyHandler),
# if a Chiron instance doesn't have the necessary ontologies app set up or
# does but doesn't have the necessary ontology data installed in it, you can
# fall back to using regular text concepts.
# In order to avoid accidentally switching, you must also change the setting
# CHIRON_TREAT_ONTOLOGY_CONCEPTS_AS_TEXT to True.

if chiron_settings.CHIRON_TREAT_ONTOLOGY_CONCEPTS_AS_TEXT:

    class OntologyHandler(TextHandler):
        display_name = "text"

else:

    class OntologyHandler(ConceptHandler):
        """
        Use with an ontology code field as the source. And you will need to provide the ontology
        ID. This integrates with the ontology Django app, which must be installed in your Django
        project and must have the corresponding ontologies loaded.
        """

        def get_stored_data_type(self):
            type = {
                "code": ("varchar", 150),
                "label": "text",
                "hierarchy": ("array", ("varchar", 150)),
            }
            return type

        def set_kwarg_options(self):
            self.append_handler_arg_option("field_name", "the code field name", required=True)
            self.append_handler_arg_option("ontology_id", "the ontology ID", required=True)
            self.append_handler_arg_option(
                "prepend_code",
                "whether or not to prepend the code to the label ",
                default_value=False,
            )
            self.append_handler_arg_option(
                "include_counts",
                "include record/subject counts with concept statistics (slower)",
                default_value=False,
            )

        def set_etl_processor(self, concept):
            from chiron.processors.etl.ontology import EtlOntologyConcept

            self.etl_processor = EtlOntologyConcept(
                concept,
                code_field_name=self.get_handler_arg_value("field_name"),
                source_format=self.check_source_format(),
                ontology_id=self.get_handler_arg_value("ontology_id"),
            )

        def set_cohort_def_processor(self, chironuser, dataset, concept, prefilter_value):
            from chiron.processors.cohort_def.ontology import CohortDefOntology

            self.cohort_def_processor = CohortDefOntology(
                chironuser,
                dataset,
                concept,
                prefilter_value=prefilter_value,
                ontology_id=self.get_handler_arg_value("ontology_id"),
                prepend_code=self.get_handler_arg_value("prepend_code"),
                include_counts=self.get_handler_arg_value("include_counts"),
            )

        def set_display_processor(self, chironuser, concept):
            from chiron.processors.display.ontology import DisplayOntology

            self.display_processor = DisplayOntology(chironuser, concept)

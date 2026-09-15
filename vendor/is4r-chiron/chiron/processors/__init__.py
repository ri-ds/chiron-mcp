from .registration import ProcessorRegistry

# Source and ETL processors for Django ORM
from .source.django import SourceDjangoModel
from .etl.django_field import EtlDjangoField
from .etl.django_multifield_merge import EtlDjangoMultifieldMerge

# other source and etl
from .source.self import SourceSelf
from .source.self_subdoc import SourceSelfSubdoc
from .source.csv import SourceCsv
from .etl.python_dict_item import EtlPythonDictItem
from .etl.python_dict_item_counter import EtlPythonDictItemCounter
from .etl.chiron_subject_id import EtlChironSubjectId

# cohort def processors
from .cohort_def.category import CohortDefCategory
from .cohort_def.date import CohortDefDate
from .cohort_def.date_deid import CohortDefDateDeid
from .cohort_def.number import CohortDefNumber
from .cohort_def.number_with_categories import CohortDefNumberWithCategories
from .cohort_def.text import CohortDefText
from .cohort_def.text_custom_sort import CohortDefTextCustomSort
from .cohort_def.boolean import CohortDefBoolean
from .cohort_def.detailed_age import CohortDefDetailedAge

# Display processors
from .display.category import DisplayCategory
from .display.date import DisplayDate
from .display.date_deid import DisplayDateDeid
from .display.number import DisplayNumber
from .display.text import DisplayText
from .display.text_custom_sort import DisplayTextCustomSort
from .display.boolean import DisplayBoolean
from .display.display_generic import DisplayGeneric
from .display.subject_hyperlink import DisplaySubjectHyperlink
from .display.number_with_categories import DisplayNumberWithCategories
from .display.detailed_age import DisplayDetailedAge

# Generic concept handlers
from .concept_handlers.standard_concept_handlers import IntegerHandler
from .concept_handlers.standard_concept_handlers import FloatHandler
from .concept_handlers.standard_concept_handlers import IntegerWithCategoriesHandler
from .concept_handlers.standard_concept_handlers import FloatWithCategoriesHandler
from .concept_handlers.standard_concept_handlers import CategoryHandler
from .concept_handlers.standard_concept_handlers import TextHandler
from .concept_handlers.standard_concept_handlers import BooleanHandler
from .concept_handlers.standard_concept_handlers import DateHandler
from .concept_handlers.standard_concept_handlers import SubjectHyperlinkHandler
from .concept_handlers.standard_concept_handlers import DetailedAgeHandler
from .concept_handlers.standard_concept_handlers import CurrentAgeHandler


from .concept_handlers.special_concept_handlers import AutoSubjectIdHandler
from .concept_handlers.special_concept_handlers import AutoSubcollectionIdHandler
from .concept_handlers.special_concept_handlers import SubjectMatchingToTextHandler
from .concept_handlers.special_concept_handlers import (
    SubjectMatchingToSubjectHyperlinkHandler,
)
from .concept_handlers.special_concept_handlers import CurrentAgeFromDobHandler
from .concept_handlers.special_concept_handlers import DetailedAgeFromDatesHandler
from .concept_handlers.special_concept_handlers import OntologyHandler


def get_built_in_standard_concept_handlers():
    response = [
        IntegerHandler,
        FloatHandler,
        IntegerWithCategoriesHandler,
        FloatWithCategoriesHandler,
        CategoryHandler,
        TextHandler,
        BooleanHandler,
        DateHandler,
        SubjectHyperlinkHandler,
        DetailedAgeHandler,
        CurrentAgeHandler,
    ]
    return response


ProcessorRegistry.register(
    source_processors=[SourceCsv, SourceSelf, SourceSelfSubdoc, SourceDjangoModel],
    concept_handlers=get_built_in_standard_concept_handlers(),
)

ProcessorRegistry.register(
    source_processors=[SourceCsv, SourceSelf, SourceSelfSubdoc, SourceDjangoModel],
    concept_handlers=[OntologyHandler],
)


ProcessorRegistry.register([SourceCsv, SourceSelf], AutoSubjectIdHandler)
ProcessorRegistry.register(SourceSelfSubdoc, AutoSubcollectionIdHandler)
ProcessorRegistry.register(SourceSelfSubdoc, DetailedAgeFromDatesHandler)
ProcessorRegistry.register([SourceCsv, SourceSelf], CurrentAgeFromDobHandler)
ProcessorRegistry.register(
    SourceSelf, [SubjectMatchingToTextHandler, SubjectMatchingToSubjectHyperlinkHandler]
)

__all__ = [
    "EtlDjangoField",
    "EtlDjangoMultifieldMerge",
    "EtlPythonDictItem",
    "EtlPythonDictItemCounter",
    "EtlChironSubjectId",
    "CohortDefCategory",
    "CohortDefDate",
    "CohortDefDateDeid",
    "CohortDefNumber",
    "CohortDefNumberWithCategories",
    "CohortDefText",
    "CohortDefTextCustomSort",
    "CohortDefBoolean",
    "CohortDefDetailedAge",
    "DisplayCategory",
    "DisplayDate",
    "DisplayDateDeid",
    "DisplayNumber",
    "DisplayText",
    "DisplayTextCustomSort",
    "DisplayBoolean",
    "DisplayGeneric",
    "DisplaySubjectHyperlink",
    "DisplayNumberWithCategories",
    "DisplayDetailedAge",
]

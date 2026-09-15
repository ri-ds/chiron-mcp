from chiron.processors.abstract import EtlProcessor
from .django_field import EtlDjangoField


class EtlDjangoMultifieldMerge(EtlProcessor):
    """Same behavior as EtlProcessorForDjangoField, except multiple django fields
    can be provided.
    After passing django_field and model_join_path like normal, provide additional
    fields
    by passing django_field2 & model_join_path2, django_field3 & model_join_path3,
    etc.
    """

    def __init__(self, oConcept, django_field, **kwargs):
        """
        django_field should be a comma separated list of fields
        """
        super().__init__(oConcept)
        self.concept = oConcept
        self.warnings = []
        self.cast_to_type = kwargs.get("cast_to_type", None)
        self.ignore_model_mismatch = kwargs.get("ignore_model_mismatch", True)
        child_processors = []
        for field_name in django_field.split(","):
            field_name = field_name.strip()
            child_processors.append(
                EtlDjangoField(
                    oConcept=oConcept,
                    django_field=field_name,
                    cast_to_type=self.cast_to_type,
                    ignore_model_mismatch=self.ignore_model_mismatch,
                    ignore_casting_errors=True,
                )
            )
        self.child_processors = child_processors

    def pull_concept_value_from_record(self, oRecord):
        values = []
        for child in self.child_processors:
            response, warnings = child.pull_concept_value_from_record_with_warnings(oRecord)
            self.warnings = self.warnings + warnings
            if isinstance(response, list):
                values = values + response
            elif response is not None:
                values.append(response)

        values = list(set(values))
        if len(values) == 0:
            return None
        # one result, return result
        if len(values) == 1:
            return values[0]
        # multiple results, return distinct values
        return values

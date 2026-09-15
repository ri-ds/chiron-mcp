from chiron.processors.abstract import EtlProcessor
from chiron.processors.etl.clean_value import SimpleClean
from chiron.processors.utils import DjangoModelObjectValueRetriever, ListOfDictsRetriever


class EtlOntologyConcept(EtlProcessor):
    def __init__(self, oConcept, code_field_name, source_format, ontology_id):
        from ontologies.interface_class import OntologyInterface

        # superclass sets self.concept and self.warnings
        super().__init__(oConcept)
        self.code_field_name = code_field_name
        self.source_format = source_format
        self.ontology_id = ontology_id
        self.oi = OntologyInterface(self.ontology_id, format=False)
        if source_format == "queryset":
            self.retriever = DjangoModelObjectValueRetriever(
                self.code_field_name, ignore_model_mismatch=True
            )
        else:
            self.retriever = ListOfDictsRetriever(self.code_field_name, string_val_separator=",")
        self.code_cleaner = SimpleClean("str")
        self.name_cleaner = SimpleClean("str")
        # self.hierarchy_cleaner = SimpleClean("str")
        self.retrieved_values = {}

    def pull_concept_value_from_record(self, oRecord):
        """
        Reads a single record and returns the final value to store in the research database
        """
        # use the retriever to get the field value(s)
        raw_code = self.retriever(oRecord)
        if raw_code == "***missing***":
            self._add_warning(
                None, f"field {self.full_field_name} was not defined in the model object"
            )
            raw_code = None
        cleaned_code = self.code_cleaner.clean(raw_code)
        if cleaned_code in self.retrieved_values:
            return self.retrieved_values[cleaned_code]
        for inval, warning in self.code_cleaner.get_warnings():
            self._add_warning(inval, warning)
        # print("code", code)
        code, raw_label, raw_hierarchy = self._get_ontology_info(cleaned_code)
        # print("code3", code, raw_label, raw_hierarchy)
        label = self.code_cleaner.clean(raw_label)
        # TODO: clean hierarchy? Or not necessary since we control the source data?
        hierarchy = raw_hierarchy
        for inval, warning in self.code_cleaner.get_warnings():
            self._add_warning(inval, warning)
        response = {
            "code": code,
            "label": label,
            "hierarchy": hierarchy,
        }
        self.retrieved_values[cleaned_code] = response
        return response

    def _get_ontology_info(self, code):
        from ontologies.models import BaseOntologyItem

        code_str = str(code)
        try:
            item = self.oi.get_item(code_str)
            label = item[1]
            ancestors = self.oi.get_ancestor_codes(code_str)
            hierarchy = [x[0] for x in ancestors]
            # hierarchy includes ancestors and this value
            hierarchy.append(item[0])

        # if the ontology item doesnt exist, then we create this instead
        except BaseOntologyItem.DoesNotExist:
            return (
                code_str,
                "unmapped {}".format(code_str),
                ["chiron_unrecognized_code"],
            )
        return (code_str, label, hierarchy)

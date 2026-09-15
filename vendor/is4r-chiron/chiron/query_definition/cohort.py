from copy import deepcopy

from chiron.query_definition import cohort_def_functions as cdfuncs
from chiron.models import Collection, Concept


class Cohort:
    """Represents a cohort of subjects."""

    def __init__(self, chironuser, cohort_def=None):
        if cohort_def is None:
            cd_info = cdfuncs.clean_active_cohort_def(chironuser, include_metadata=True)
        else:
            cd_info = cdfuncs.clean_cohort_def(cohort_def, chironuser, include_metadata=True)
        self.cohort_def = cd_info["cohort_def"]
        self.extended_cohort_def = cd_info["extended_cohort_def"]
        self.errors = cd_info["errors"]
        self.warnings = cd_info["warnings"]
        self.chironuser = chironuser
        self.internal_cohort_def = self.create_internal_cohort_def()

    def cohort_unique_hash(self):
        """
        Returns a string that uniquely identifies this cohort.
        This can be used to match a cohort in a cache
        """
        pass

    def create_internal_cohort_def(self):
        internal_cd = list()
        for criteria_set in self.cohort_def:
            new_entry = deepcopy(criteria_set)
            oCollection = Collection.objects.filter(
                permanent_id=new_entry["collection_id"],
                dataset=self.chironuser.dataset,
            ).first()
            new_entry["collection"] = oCollection
            new_entry["is_root_collection"] = oCollection.is_root_collection
            new_filter_rules = list()
            for filter_rule in new_entry["list"]:
                new_filter_rules.append(self._filter_rule_add_info(filter_rule))
            new_entry["list"] = new_filter_rules
            internal_cd.append(new_entry)
        return internal_cd

    def _filter_rule_add_info(self, filter_rule):
        new_filter_rule = deepcopy(filter_rule)
        if new_filter_rule.get("entry_type") == "or_group":
            child_filter_rules = list()
            for child_filter_rule in new_filter_rule["list"]:
                child_filter_rules.append(self._filter_rule_add_info(child_filter_rule))
            new_filter_rule["list"] = child_filter_rules
            return new_filter_rule
        concept_id = new_filter_rule["concept_id"]
        oConcept = Concept.objects.get(permanent_id=concept_id)
        new_filter_rule["concept"] = oConcept
        return new_filter_rule

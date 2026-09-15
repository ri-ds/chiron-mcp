import hashlib

from django.db import transaction

from chiron import chiron_settings
from chiron import helpers
from chiron.models import CachedCohort


class CachedCohortWrapper:
    """
    Use to access cache of subject counts and subject ids for a cohort
    """

    def __init__(self, chironuser, cohort):
        self.chironuser = chironuser
        self.cohort = cohort
        self.set_subject_permission_hash(chironuser)
        self.set_cohort_def_hash(cohort.cohort_def)

    def set_subject_permission_hash(self, chironuser):
        """
        Returns a unique string that can be used to determine if two chironuser's
        subject permissions are the same. Good for determining if cached data
        from ChironUser A can be used for ChironUser B.
        """
        concepts = self.chironuser.list_concepts_for_allowed_subjects()
        if concepts is None:
            hash_input = "all"
        else:
            concept_ids = [x.permanent_id for x in concepts]
            concept_ids.sort()
            hash_input = ",".join(concept_ids)
        hash_val = hashlib.md5(hash_input.encode())
        self.subject_permission_hash = hash_val.hexdigest()

    def set_cohort_def_hash(self, cohort_def):
        # TODO: try to give same hash for irrelevant changes like different order or entry_ids
        hash_input = helpers.to_json_string(cohort_def)
        hash_val = hashlib.md5(hash_input.encode())
        self.cohort_def_hash = hash_val.hexdigest()

    def find_matching_cache_entry(self):
        """
        Returns the cache entry or None if not found
        """
        if not chiron_settings.CHIRON_USE_CACHES:
            return None
        oCache = CachedCohort.objects.filter(
            dataset=self.chironuser.dataset,
            cohort_def_hash=self.cohort_def_hash,
            subject_permission_hash=self.subject_permission_hash,
        ).first()
        return oCache

    def save_new_cache_entry(self, count):
        if not chiron_settings.CHIRON_USE_CACHES:
            helpers.print_query_info(
                "Attempt to save to cache ignored because CHIRON_USE_CACHES is False"
            )
            return None
        # set up DB transaction to handle saving new cache entry
        with transaction.atomic():
            # if existing entry, need to remove
            oCache = self.find_matching_cache_entry()
            if oCache:
                oCache.delete()
            # create entry
            oCache = CachedCohort(
                dataset=self.chironuser.dataset.unique_id,
                cohort_def_hash=self.cohort_def_hash,
                subject_permission_hash=self.subject_permission_hash,
                count=count,
            )
            oCache.save()
        return oCache

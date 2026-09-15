import hashlib

from chiron import helpers
from chiron.models import CachedConceptStats
from chiron import chiron_settings

from . import hashing


class CachedConceptStatsWrapper:
    """
    Use to work with the CachedConceptStats model which stores statistical data about concepts
    """

    def __init__(self, chironuser, cohort, concept, prefilter_value):
        self.chironuser = chironuser
        self.cohort = cohort
        self.concept = concept
        if not prefilter_value:
            self.prefilter_value = None
        else:
            self.prefilter_value = str(prefilter_value)
        self.set_subject_permission_hash()
        self.set_cohort_def_hash()

    def set_subject_permission_hash(self):
        """
        Returns a unique string that can be used to determine if two users' subject permissions
        are the same. Good for determining if cached data from User A can be used for User B.
        """
        hash_input = hashing.create_subject_permission_hash(self.chironuser)
        hash_val = hashlib.md5(hash_input.encode())
        self.subject_permission_hash = hash_val.hexdigest()

    def set_cohort_def_hash(self):
        hash_input = hashing.create_cohort_def_hash(self.cohort.cohort_def)
        hash_val = hashlib.md5(hash_input.encode())
        self.cohort_def_hash = hash_val.hexdigest()

    def find_matching_cache_entry(self):
        """
        Returns the cache entry or None if not found
        """
        if not chiron_settings.CHIRON_USE_CACHES:
            return None
        oCache = CachedConceptStats.objects.filter(
            dataset=self.chironuser.dataset.unique_id,
            cohort_def_hash=self.cohort_def_hash,
            subject_permission_hash=self.subject_permission_hash,
            concept_id=self.concept.permanent_id,
            prefilter_value=self.prefilter_value,
        ).first()
        return oCache

    def save_new_cache_entry(self, stats):
        if not chiron_settings.CHIRON_USE_CACHES:
            helpers.print_query_info(
                "Attempt to save to cache ignored because CHIRON_USE_CACHES is False"
            )
            return None
        # if existing entry, need to remove
        oCache = self.find_matching_cache_entry()
        if oCache:
            oCache.delete()
        # create entry
        oCache = CachedConceptStats(
            dataset=self.concept.collection.dataset.unique_id,
            cohort_def_hash=self.cohort_def_hash,
            subject_permission_hash=self.subject_permission_hash,
            concept_id=self.concept.permanent_id,
            prefilter_value=self.prefilter_value,
        )
        oCache.set_stats(stats)
        oCache.save()
        return oCache

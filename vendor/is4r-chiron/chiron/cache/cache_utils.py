"""
Functions related to caches that don't fit in another module
TODO: Rename this if needed
"""

import json

from django.conf import settings
from django.db import connection

from chiron import models
from chiron.query_engine import get_querytool
from chiron import helpers


def clear_cached_data(dataset=None):
    """Clear Cached Data

    Specify the dataset object to clear or None to clear entire cache.
    """
    engine = settings.DATABASES["default"]["ENGINE"]
    num_datasets = models.Dataset.objects.count()
    if num_datasets == 1:
        dataset = None

    if dataset is None:
        if engine == "django.db.backends.sqlite3":
            print("SQLite3 detected. Clearing all cache tables.")
            qCachedCohort = models.CachedCohort.objects.all()
            qCachedCohort.delete()
            qCachedConceptStats = models.CachedConceptStats.objects.all()
            qCachedConceptStats.delete()
        else:
            print("Clearing all cache tables.")
            cursor = connection.cursor()
            cursor.execute("TRUNCATE TABLE chiron_cachedcohort RESTART IDENTITY CASCADE")
            cursor.execute("TRUNCATE TABLE chiron_cachedconceptstats RESTART IDENTITY CASCADE")
    else:
        cached_cohort_qs = models.CachedCohort.objects.all()
        cached_concept_stats_qs = models.CachedConceptStats.objects.all()

        # apply the dataset filter if provided
        if dataset:
            print(f"Clearing cache for dataset: {dataset}")
            cached_cohort_qs = cached_cohort_qs.filter(dataset=dataset.unique_id)
            cached_concept_stats_qs = cached_concept_stats_qs.filter(dataset=dataset.unique_id)

        # clear the data
        cached_cohort_qs.delete()
        cached_concept_stats_qs.delete()


def cache_concepts(oDataset=None, collections=[]):
    """
    Loops through all of the current published concepts and caches the
    results for an empty cohort def.
    """
    if not settings.CHIRON_USE_CACHES:
        helpers.print_query_info(
            "Attempt to cache concepts ignored because CHIRON_USE_CACHES is False"
        )
        return None

    # work with one dataset at a time
    if oDataset:
        qDataset = [oDataset]
    else:
        qDataset = models.Dataset.objects.all()

    for oDataset in qDataset:
        # Build out unique permission hashes for all users
        unique_chironusers = {}
        # Get one chiron user for each unique combination of permission groups.
        qChironUser = models.ChironUser.objects.filter(dataset=oDataset)
        for oChironUser in qChironUser:
            perm_str = oChironUser.list_permission_groups()
            if perm_str not in unique_chironusers.keys():
                unique_chironusers[perm_str] = oChironUser

        # setup the caches for the concept stats for each unique chiron user
        total_users = len(unique_chironusers.values())
        qConcept = models.Concept.objects.filter(
            published=True, collection__dataset=oDataset, include_in_cohort_def=True
        )

        # only do the concepts within the provided collections
        if collections:
            qConcept = qConcept.filter(collection__in=collections)

        total_count = total_users * qConcept.count()
        print(f"Caching concepts for {total_users} unique permission set(s).")
        i = 0
        for oChironUser in unique_chironusers.values():
            # temporarily give this user full PHI access (this change will not be saved)
            oChironUser.access_level = "phi"
            for concept in qConcept:
                i += 1
                print(f"Progress: {str(i)}/{str(total_count)}", end="\r")
                # If this user doesn't have access to this concept, skip.
                if not concept.check_permission_group(oChironUser):
                    continue

                if concept.concept_for_prefilter:
                    # cache the concepts prefilter value
                    _attempt_to_cache_concept(concept.concept_for_prefilter, oChironUser)

                # create the cache
                _attempt_to_cache_concept(concept, oChironUser)


def _attempt_to_cache_concept(concept, chiron_user):
    """
     Attempts to cache the concept statistics and if it fails, just print out
     that it did not cachc.

    :param concept: The concept to cache
    :type concept: class: chiron.models.data_definition_models.Concept
    :param chiron_user: The chiron user
    :type chiron_user: class: chiron.models.user_models.ChironUser
    """
    cd_processor = concept.get_cohort_def_processor(chiron_user)
    try:
        cd_processor.get_statistics([])
    except Exception as e:
        print(f"error caching concept stats for {concept.permanent_id}: {e}")


def cache_cohort(chiron_user, cohort_def):
    """Cache Cohort

    Standalone function to cache an arbitrary Cohort Def.

    :param user: Chiron User
    :type user: class: chiron.models.user_models.ChironUser
    :param cohort_def: Cohort Def
    :type cohort_def: list
    """
    # Get Django user
    # django_user = get_user_model().objects.get(chironuser=user)
    # Set up Data Tool
    data_tool = get_querytool(chiron_user, cohort_def)
    # Cache cohort
    data_tool.get_cohort_count()


def cache_reports(oDataset=None):
    """Cache Saved Cohorts

    Caches saved cohorts.
    Note that this operation may take a long time.
    """
    # Query for saved cohorts
    saved_cohort_queryset = models.UserCreatedContent.objects.filter(
        type=models.UserCreatedContent.Type.TABLE
    )
    if oDataset:
        saved_cohort_queryset = saved_cohort_queryset.filter(dataset=oDataset)
    # Iterate through saved cohorts and cache if applicable
    # TODO: Users often have the same permissions, so running for every user is somewhat
    #   inefficient. However, it is only checking the cache more than it needs to, not actually
    #   rerunning the query.
    for saved_cohort in saved_cohort_queryset:
        # Get cohort def from saved cohort
        cohort_def = json.loads(saved_cohort.definition)["cohort_def"]
        # Cache cohort for creator
        try:
            cache_cohort(saved_cohort.creator, cohort_def)
            # Cache cohort for share users
            for share_user in saved_cohort.share_with.all():
                cache_cohort(share_user, cohort_def)
        except Exception as e:
            # The process shouldn't be stopped for individual reports that fail to run
            print("WARNING: unable to cache cohort: " + str(e))
            continue
        # TODO: What if the report is public? Should we update the cache for all users?

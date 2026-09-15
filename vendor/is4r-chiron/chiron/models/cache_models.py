import json

from django.db import models


#  ABSTRACT MODELS ###################################################################


class TimeStampedModel(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# #####################################################################################


class CachedConceptStats(TimeStampedModel):
    """
    Cache value is uniquely identified by cohort_def_hash, subject_permission_hash, concept_id,
    and prefilter value.
    """

    dataset = models.SlugField(max_length=60)
    cohort_def_hash = models.CharField(max_length=32, db_index=True)
    subject_permission_hash = models.CharField(max_length=32, db_index=True)
    concept_id = models.SlugField(max_length=120, db_index=True)
    prefilter_value = models.CharField(max_length=1000, db_index=True, blank=True, null=True)
    # TODO: might want the cohort def processor name to check if it's been changed
    stats = models.TextField()

    class Meta:
        verbose_name_plural = "cached concept stats"

    def get_stats(self):
        stats = json.loads(self.stats)
        return stats

    def set_stats(self, stats):
        self.stats = json.dumps(stats)


class CachedCohort(TimeStampedModel):
    """
    Stores information (currently just the subject count) about a user-defined cohort.
    """

    dataset = models.SlugField(max_length=60)
    cohort_def_hash = models.CharField(max_length=32, db_index=True)
    subject_permission_hash = models.CharField(max_length=32, db_index=True)
    count = models.IntegerField()

    class Meta:
        unique_together = (
            "dataset",
            "cohort_def_hash",
            "subject_permission_hash",
        )

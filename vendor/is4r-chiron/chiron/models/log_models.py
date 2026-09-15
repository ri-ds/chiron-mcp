import datetime

from django.db import models


class EtlLog(models.Model):
    """
    Log to track an entire ETL event (chiron_run_etl management command)
    """

    class Status(models.TextChoices):
        ETL_STARTED = "ETL started", "ETL started"
        ETL_COMPLETED = "ETL completed", "etl_completed"

    dataset = models.SlugField(max_length=60, blank=True, null=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices)
    tracking_subject_matching = models.BooleanField()
    using_staging = models.BooleanField()
    abbreviated_load = models.BooleanField()
    comment = models.TextField(blank=True, null=True)

    @classmethod
    def get_latest_record(cls, oDataset):
        oLog = (
            cls.objects.filter(status=cls.Status.ETL_COMPLETED, dataset=oDataset)
            .order_by("-start_date")
            .first()
        )
        return oLog

    def get_duration(self):
        if not self.start_date or not self.end_date:
            return None
        delta = self.end_date - self.start_date
        delta = delta - datetime.timedelta(microseconds=delta.microseconds)
        return delta

    def count_sources_loaded(self):
        return self.sourceetllog_set.all().count()

    class Meta:
        ordering = ["-start_date"]


class SourceEtlLog(models.Model):
    """
    Log to track the ETL event for a specific source
    """

    etl_log = models.ForeignKey("EtlLog", on_delete=models.CASCADE)
    source = models.CharField(max_length=120)
    destination_collection = models.SlugField(max_length=120)
    load_start_date = models.DateTimeField()
    load_end_date = models.DateTimeField(null=True)
    data_last_updated_date = models.DateTimeField()

    # stats about data load
    count_source_records_read = models.IntegerField(blank=True, null=True)
    count_source_records_loaded = models.IntegerField(blank=True, null=True)
    count_subjects_updated = models.IntegerField(blank=True, null=True)
    count_subjects_created = models.IntegerField(blank=True, null=True)
    count_subject_docs_start = models.IntegerField(blank=True, null=True)
    count_subject_docs_end = models.IntegerField(blank=True, null=True)
    count_collection_docs_updated = models.IntegerField(blank=True, null=True)
    count_collection_docs_created = models.IntegerField(blank=True, null=True)
    count_collection_docs_start = models.IntegerField(blank=True, null=True)
    count_collection_docs_end = models.IntegerField(blank=True, null=True)

    class Meta:
        ordering = ["load_start_date"]

    def get_duration(self):
        if not self.load_start_date or not self.load_end_date:
            return None
        delta = self.load_end_date - self.load_start_date
        delta = delta - datetime.timedelta(microseconds=delta.microseconds)
        return delta

    def get_subject_docs_change(self):
        if self.count_subject_docs_start is None or self.count_subject_docs_end is None:
            return None
        return self.count_subject_docs_end - self.count_subject_docs_start

    def get_collection_docs_change(self):
        if self.count_collection_docs_start is None or self.count_collection_docs_end is None:
            return None
        return self.count_collection_docs_end - self.count_collection_docs_start

    def get_concept_logs(self):
        """
        Returns a dict with concept_id:qConceptIssueEtlLog
        - qConceptIssue
        - oConcept
        """
        qConceptIssue = self.conceptissueetllog_set.all()
        concept_ids = (
            qConceptIssue.order_by("concept_id").values_list("concept_id", flat=True).distinct()
        )
        response = {}
        for concept_id in concept_ids:
            qSingleConceptIssue = qConceptIssue.filter(concept_id=concept_id)
            response[concept_id] = qSingleConceptIssue
        return response


class SourceRecordEtlLog(models.Model):
    """
    Log to track the ETL event for a single record from a single source being loaded.

    This log can get large and is only populated when option `--track-subject-matching` is set.
    """

    source_log = models.ForeignKey(SourceEtlLog, on_delete=models.CASCADE)

    # info from subject_match_manager
    match_def = models.TextField(blank=True, null=True)
    add_ids = models.TextField(blank=True, null=True)
    if_no_match = models.CharField(max_length=20)

    # was the subject created or matched
    subject_created = models.BooleanField()

    # more infor about the created/matched subject
    subject_id = models.CharField(max_length=120, blank=True, null=True)
    subject_start_ids = models.TextField(blank=True, null=True)
    subject_final_ids = models.TextField(blank=True, null=True)
    iterations = models.IntegerField(default=1)

    class Meta:
        ordering = ["id"]


class ConceptIssueEtlLog(models.Model):
    """
    Tracks a specific action or problem about a concept during the ETL. For example, count of how
    many strings had whitespace stripped.
    """

    source_log = models.ForeignKey(SourceEtlLog, on_delete=models.CASCADE)
    concept_id = models.SlugField(max_length=120)
    issue = models.CharField(max_length=120)
    issue_description = models.TextField(blank=True, null=True)
    count = models.IntegerField()


class ConceptIssueExampleEtlLog(models.Model):
    """
    Save specific examples of input values that had issues.
    """

    concept_issue = models.ForeignKey(ConceptIssueEtlLog, on_delete=models.CASCADE)
    input_datatype = models.TextField(blank=True, null=True)
    input_value = models.TextField(blank=True, null=True)
    stored_datatype = models.TextField(blank=True, null=True)
    stored_value = models.TextField(blank=True, null=True)

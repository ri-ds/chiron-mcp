import datetime

from chiron.models import (
    EtlLog,
    SourceEtlLog,
    SourceRecordEtlLog,
    ConceptIssueEtlLog,
    ConceptIssueExampleEtlLog,
)


class Logger:
    """
    Stores info about an ETL data load in the Django database
    """

    def __init__(self, dataset, track_subject_matching):
        self.dataset = dataset
        self.etl_log = None
        self.source_logs = {}
        self.record_logs = []
        self.previous_record_etl_data = {}
        self.comments = []
        self.track_subject_matching = track_subject_matching

    def add_log_comment(self, comment):
        self.comments.append(comment)

    def start_etl_log(self, use_staging, abbreviated):
        """
        Creates an ETL log record with information about this ETL
        """
        self.etl_log = EtlLog(
            dataset=self.dataset.unique_id,
            start_date=datetime.datetime.now(),
            status=EtlLog.Status.ETL_STARTED,
            tracking_subject_matching=self.track_subject_matching,
            using_staging=use_staging,
            abbreviated_load=abbreviated,
        )
        self.etl_log.save()

    def finalize_etl_log(self):
        """
        Finishes the ETL log record that was created by `start_etl_log`
        """
        if not self.etl_log:
            raise NotImplementedError("Trying to finalize the ETL log before it was created.")
        self.etl_log.status = EtlLog.Status.ETL_COMPLETED
        self.etl_log.end_date = datetime.datetime.now()
        self.etl_log.comment = "\n".join(self.comments)
        self.etl_log.save()

    def start_source_log(
        self,
        oSource,
        data_last_updated_date,
        count_subject_docs_start=None,
        count_collection_docs_start=None,
    ):
        """
        Creates an initial source_log entry and adds it to self.source_logs.
        Also creates a concept_issue_logs dict that will be used to track info about the data
        load for specific concepts.
        """
        source_name = oSource.name
        source_log = SourceEtlLog(
            etl_log=self.etl_log,
            source=source_name,
            destination_collection=oSource.collection.permanent_id,
            load_start_date=datetime.datetime.now(),
            data_last_updated_date=data_last_updated_date,
            count_subject_docs_start=count_subject_docs_start,
            count_collection_docs_start=count_collection_docs_start,
        )
        self.source_logs[source_name] = {
            "log_entry": source_log,
            "concept_issue_logs": {},
        }
        if count_collection_docs_start:
            self.source_logs[source_name][
                "log_entry"
            ].count_collection_docs_start = count_collection_docs_start
        self.source_logs[source_name]["log_entry"].save()

    def report_concept_issue(self, oSource, concept_id, issue, input_value, stored_value):
        source_name = oSource.name
        issue_logs = self.source_logs[source_name]["concept_issue_logs"]
        if concept_id not in issue_logs:
            issue_logs[concept_id] = {}
        if issue not in issue_logs[concept_id]:
            issue_logs[concept_id][issue] = {
                "count": 1,
                "examples": [(input_value, stored_value)],
            }
        else:
            issue_logs[concept_id][issue]["count"] += 1
            if len(issue_logs[concept_id][issue]["examples"]) < 5:
                issue_logs[concept_id][issue]["examples"].append((input_value, stored_value))

    def finalize_source_log(
        self,
        oSource,
        count_subject_docs_end=None,
        count_collection_docs_end=None,
        count_source_records_read=None,
        count_source_records_loaded=None,
        count_collection_docs_updated=None,
        count_collection_docs_created=None,
    ):
        source_name = oSource.name
        if source_name not in self.source_logs:
            raise NotImplementedError("Trying to finalize source ETL log before it was created.")
        log_entry = self.source_logs[source_name]["log_entry"]
        log_entry.load_end_date = datetime.datetime.now()
        log_entry.count_subject_docs_end = count_subject_docs_end
        log_entry.count_collection_docs_end = count_collection_docs_end
        log_entry.count_source_records_read = count_source_records_read
        log_entry.count_source_records_loaded = count_source_records_loaded
        log_entry.count_collection_docs_updated = count_collection_docs_updated
        log_entry.count_collection_docs_created = count_collection_docs_created
        log_entry.save()
        # also save concept issue logs
        issue_logs = self.source_logs[source_name]["concept_issue_logs"]
        for concept_id, issues in issue_logs.items():
            for issue, entry in issues.items():
                oIssue = ConceptIssueEtlLog(
                    source_log=log_entry, concept_id=concept_id, issue=issue, count=entry["count"]
                )
                oIssue.save()
                for example in entry["examples"]:
                    oExample = ConceptIssueExampleEtlLog(
                        concept_issue=oIssue,
                        input_datatype=type(example[0]),
                        input_value=str(example[0]),
                        stored_datatype=type(example[1]),
                        stored_value=str(example[1]),
                    )
                    oExample.save()

    def start_record_log(
        self,
        oSource,
        subject_match_manager,
        subject_created,
        subject_id,
        subject_final_ids=None,
    ):
        if oSource.name not in self.source_logs:
            raise NotImplementedError("Trying to log a source record before the source.")
        record_etl_data = {
            "source_log": self.source_logs[oSource.name]["log_entry"],
            "match_def": str(subject_match_manager.match_rule),
            "add_ids": str(subject_match_manager.add_ids),
            "if_no_match": subject_match_manager.if_no_match,
            "subject_created": subject_created,
            "subject_id": subject_id,
            "subject_final_ids": str(subject_final_ids),
        }
        if record_etl_data == self.previous_record_etl_data:
            self.record_logs[-1].iterations += 1
        else:
            oRecordLog = SourceRecordEtlLog(**record_etl_data)
            self.record_logs.append(oRecordLog)
            self.previous_record_etl_data = record_etl_data

    def finalize_record_logs(self):
        """This simply saves all to the database. It's faster to do as a bulk load."""
        # keep the last record in case it's still being iterated
        last_record = None
        if len(self.record_logs) > 0:
            last_record = self.record_logs.pop()
        SourceRecordEtlLog.objects.bulk_create(self.record_logs)
        if last_record:
            self.record_logs = [last_record]

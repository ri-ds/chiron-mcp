import datetime


class SubjectMatchManager:
    """
    Subjects can be matched using either a simple ID value or a dict defining a complex set of
    rules. This class takes that subject_match_def as an argument and provides a standardized
    set of properties and methods regardless of the type of subject_match_def.
    """

    def __init__(self, subject_match_def):
        # set default values
        self.initial_match_def = subject_match_def
        self.match_rule = {}
        self.if_no_match = "create"  # create, skip (TODO: might want option to raise error)
        self.add_ids = {}
        self.source_id = None

        # add custom values
        if subject_match_def is None:
            pass
        elif subject_match_def is False:
            self.if_no_match = "skip"
        elif not isinstance(subject_match_def, dict):
            self.match_rule = {"id": subject_match_def}
            self.add_ids = {"id": subject_match_def}
        else:
            self.match_rule = subject_match_def.get("match_rule", {})
            self.add_ids = subject_match_def.get("add_ids", {})
            self.if_no_match = subject_match_def.get("if_no_match", "create")
            self.source_id = subject_match_def.get("source_id", None)

    def can_skip_record(self):
        if not self.match_rule and self.if_no_match == "skip":
            return True
        return False

    def get_alt_subject_ids(self):
        """
        Returns any Subject IDs to add that aren't null
        """
        return {k: v for k, v in self.add_ids.items() if v}

    def get_subject_match_rule(self):
        return self.match_rule


def print_subject_match_details(source, dest_col, subject_match_manager, action):
    """action can be "updated", "created", "ignored" """
    print("------------------------------------------------------------")
    print("loading from {} to {}".format(source, source.collection.permanent_id))
    print("action taken:", action)
    print("match_rule:", subject_match_manager.match_rule)
    print("add_ids:", subject_match_manager.get_add_ids_statement())
    print("if no match:", subject_match_manager.if_no_match)
    if action == "updated":
        cursor = dest_col.find(subject_match_manager.match_rule)
        for idx, doc in enumerate(cursor):
            print("matched record {}. _id={}; _ids={}".format(idx + 1, doc["_id"], doc["_ids"]))
    print("------------------------------------------------------------")


def get_subject_match_managers(processor, source_record):
    """
    Converts a subject_match_def into a list of SubjectMatchManagers
    Usually will return one, but I allow multiples, so maybe always return an array
    """
    subject_match_def = processor.get_subject_match_def(source_record)
    subject_match_managers = []
    if not isinstance(subject_match_def, list):
        subject_match_manager = SubjectMatchManager(subject_match_def)
        if not subject_match_manager.can_skip_record():
            subject_match_managers.append(subject_match_manager)
    else:
        for entry in subject_match_def:
            subject_match_manager = SubjectMatchManager(entry)
            if not subject_match_manager.can_skip_record():
                subject_match_managers.append(subject_match_manager)
    return subject_match_managers


def instantiate_etl_processors(oSource, source_processor):
    """
    Instantiate ETL Processors for a collection. This is run once and saved so that the ETL
    processors don't have to be re-instantiated for every record.
    """
    etl_processors = {}
    qConcept = oSource.concept_set.filter(published=True).exclude(concept_handler__isnull=True)
    for oConcept in qConcept:
        if oConcept.permanent_id not in etl_processors:
            etl_processors[oConcept.permanent_id] = oConcept.get_etl_processor(
                source_processor=source_processor
            )
    return etl_processors


def generate_record_data(qConcept, etl_processors, source_record, logger):
    """
    Convert a source_record into a dict ready to be loaded into MongoDB.
    """
    doc = {}
    for oConcept in qConcept:
        value, warnings = etl_processors[
            oConcept.permanent_id
        ].pull_concept_value_from_record_with_warnings(source_record)
        # value = prepare_value_for_mongo(value)
        if logger:
            for warning in warnings:
                logger.report_concept_issue(
                    oConcept.source,
                    oConcept.permanent_id,
                    issue=warning[1],
                    input_value=warning[0],
                    stored_value=value,
                )
        if value is not None:
            doc[oConcept.permanent_id] = value
    return doc


class PerformanceTracker:
    """
    set up as callable object so that I can persist datetime across calls
    """

    def __init__(self, rate_limit_seconds=20):
        self.rate_limit_seconds = rate_limit_seconds  # min seconds between calls
        self.batch_start_time = datetime.datetime.now()  # start timer for first batch
        self.batch_start_index = 0  # set first start index
        self.first_batch = True  # first batch is handled differently

    def print_notification(self, current_index):
        batch_end_time = datetime.datetime.now()
        seconds = (batch_end_time - self.batch_start_time).total_seconds()
        records = current_index - self.batch_start_index
        if seconds < self.rate_limit_seconds and not self.first_batch:
            return  # run some more before printing
        batch_rate = records / seconds
        print(
            "{} records loaded | most recent {} rate = {}/sec".format(
                current_index, records, int(batch_rate)
            )
        )
        self.first_batch = False
        self.batch_start_time = batch_end_time
        self.batch_start_index = current_index

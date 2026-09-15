from . import helpers
from chiron import chiron_settings


def populate_subcollection(
    oSource,
    writer,
    notify_count=1000,
    logger=None,
    abbreviated=False,
    db_refresh_func=None,
):
    """Writes an entire source to the database.

    This is for a data source that is many:1 or many:many with a subject.

    :param obj oSource: The Django model object for the source.
    :param obj writer: A db_writer object (get using query_engine.get_db_writer())
    :param int notify_count: Print progress to stdout every n records. Note that there's also a
      minimum time limit to avoid printing too many messages.
    :param obj logger: an etl.logger.Logger() object which tracks data load stats in the Django
      system database.
    :param bool abbreviated: True if only a partial load for testing.
    :param function db_refresh_func: A function that refreshes databases, used to prevent timeouts.
    :return: The count of records read.
    """

    source_processor = oSource.get_processor()
    etl_processors = helpers.instantiate_etl_processors(oSource, source_processor)
    count_sources_for_collection = oSource.collection.source_set.count()

    if logger:
        logger.start_source_log(
            oSource,
            data_last_updated_date=source_processor.get_data_last_updated_date(),
            count_subject_docs_start=writer.count_subject_records(),
            count_collection_docs_start=writer.count_subcollection_records(),
        )

    # get all concepts we need to import for this source
    qConcept = oSource.concept_set.filter(published=True).exclude(concept_handler__isnull=True)

    source_record_count = 0
    tracker = helpers.PerformanceTracker()

    abbreviated_settings = None
    if abbreviated:
        abbreviated_settings = chiron_settings.CHIRON_ABBREVIATED_ETL_RECORD_COUNTS.get(
            oSource.name, chiron_settings.CHIRON_ABBREVIATED_ETL_DEFAULT_RECORD_COUNT
        )

    counts = {
        "read": 0,
        "write": 0,
        "match": 0,
    }
    abbreviated_count_method = ""
    abbreviated_count_limit = None
    for source_record in source_processor.get_source():
        # if running an abbreviated data load, check if it's time to quit
        if abbreviated:
            abbreviated_count_method = abbreviated_settings[0]
            abbreviated_count_limit = abbreviated_settings[1]
            counting = abbreviated_count_method
            if abbreviated_count_method in ["match_full", "match_strict"]:
                counting = "match"
            if counts[counting] >= abbreviated_count_limit:
                break

        # increment read counter
        counts["read"] += 1

        # create subject match manager(s) and determine if we can skip
        subject_match_managers = helpers.get_subject_match_managers(
            source_processor, source_record
        )
        if not subject_match_managers:
            # if logger.track_subject_matching:
            #     print("Skipping record")
            continue

        # create the subcollection document
        record = helpers.generate_record_data(qConcept, etl_processors, source_record, logger)
        subcollection_id = source_processor.get_collection_id(source_record)
        # writer.add_data(record)
        # writer.set_subcollection_id(subcollection_id)

        if record:
            subject_ids = []
            subject_created = False

            # typically 1 subject match manager per record, but can be any number
            for subject_match_manager in subject_match_managers:
                # look for existing subject(s) in the subject collection
                match_rule = subject_match_manager.get_subject_match_rule()
                if match_rule:
                    alt_subject_ids = subject_match_manager.get_alt_subject_ids()
                    subject_id_list, alt_ids = writer.find_subjects(match_rule, alt_subject_ids)
                    if logger and logger.track_subject_matching:
                        for subject_id, alt in alt_ids.items():
                            logger.start_record_log(
                                oSource,
                                subject_match_manager,
                                subject_created=False,
                                subject_id=subject_id,
                                subject_final_ids=alt,
                            )
                    subject_ids += subject_id_list

            # if no matching subjects, should we create one?
            if not subject_ids and abbreviated_count_method != "match_strict":
                # we will only create 1 new record even if multiple subject_match_managers were
                # returned
                subject_match_manager = subject_match_managers[0]
                if subject_match_manager.if_no_match == "create":
                    # create new empty subject document and add any alt ids
                    alt_ids = subject_match_manager.get_alt_subject_ids()
                    subject_id = writer.insert_empty_subject(alt_ids)
                    subject_ids.append(subject_id)
                    subject_created = True

            # now that we have found/created associated subject document(s), we can
            # add the subcollection document
            if subject_ids:
                # attempt to update an existing subcollection document
                record_count = 0
                if subcollection_id and count_sources_for_collection > 1:
                    record_count = writer.update_one_subcollection(
                        record, subcollection_id, subject_ids
                    )
                # if no subcollection documents were updated, insert new
                if record_count == 0 and abbreviated_count_method != "match_strict":
                    writer.insert_one_subcollection(record, subcollection_id, subject_ids)
                    counts["write"] += 1
                else:
                    counts["write"] += 1
                    counts["match"] += 1
                if logger and logger.track_subject_matching:
                    for subject_id in subject_ids:
                        # TODO: this can log subject_final_ids incorrectly since it doesn't include
                        #  already present ids. It will be added correctly, just not logged
                        #  correctly.
                        logger.start_record_log(
                            oSource,
                            subject_match_manager,
                            subject_created=subject_created,
                            subject_id=subject_id,
                            subject_final_ids=subject_match_manager.get_alt_subject_ids(),
                        )

        source_record_count += 1
        if source_record_count % notify_count == 0:
            tracker.print_notification(source_record_count)
            # want to finalize record logs intermittently to free up memory
            if logger:
                logger.finalize_record_logs()

    writer.finalize_subject_collection()
    writer.finalize_subcollection()

    if db_refresh_func is not None:
        db_refresh_func()
    if logger:
        # the db engine for the writer might be stale
        writer.refresh_engine()
        logger.finalize_source_log(
            oSource,
            count_source_records_read=counts["read"],
            count_source_records_loaded=counts["write"],
            count_collection_docs_updated=counts["match"],
            count_collection_docs_created=counts["write"] - counts["match"],
            count_subject_docs_end=writer.count_subject_records(),
            count_collection_docs_end=writer.count_subcollection_records(),
        )
        logger.finalize_record_logs()

    return source_record_count

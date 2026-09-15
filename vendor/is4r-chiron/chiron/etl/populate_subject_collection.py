from . import helpers

from chiron import chiron_settings


def populate_subject_collection(
    oSource,
    writer,
    notify_count=1000,
    logger=None,
    abbreviated=False,
    db_refresh_func=None,
):
    """Writes an entire source to the database.

    This is for a data source that is 1:1 with a subject.

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
    source_record_count = 0
    tracker = helpers.PerformanceTracker()

    # instantiate ETL processors needed for this source
    source_processor = oSource.get_processor()
    etl_processors = helpers.instantiate_etl_processors(oSource, source_processor)

    if logger:
        logger.start_source_log(
            oSource,
            data_last_updated_date=source_processor.get_data_last_updated_date(),
            count_subject_docs_start=writer.count_subject_records(),
        )

    abbreviated_settings = None
    if abbreviated:
        abbreviated_settings = chiron_settings.CHIRON_ABBREVIATED_ETL_RECORD_COUNTS.get(
            oSource.name, chiron_settings.CHIRON_ABBREVIATED_ETL_DEFAULT_RECORD_COUNT
        )

    # get all concepts we need to import for this source
    qConcept = oSource.concept_set.filter(published=True).exclude(concept_handler__isnull=True)

    counts = {
        "read": 0,
        "write": 0,
        "match": 0,
    }
    abbreviated_count_method = ""
    for source_record in source_processor.get_source():
        # if running an abbreviated data load, check if it's time to quit
        if abbreviated:
            abbreviated_count_method = abbreviated_settings[0]
            counting = abbreviated_count_method
            if counting in ["match_full", "match_strict"]:
                counting = "match"
            if counts[counting] >= abbreviated_settings[1]:
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

        # create the subject document
        record = helpers.generate_record_data(qConcept, etl_processors, source_record, logger)

        if record:
            # typically 1 subject match manager per record, but can be any number
            for subject_match_manager in subject_match_managers:
                # add alt ids to the document
                alt_subject_ids = subject_match_manager.get_alt_subject_ids()
                # generate the mongo update filter to use with this document
                match_rule = subject_match_manager.get_subject_match_rule()
                if match_rule:
                    # attempt to update an existing record
                    update_count = writer.update_one_subject(match_rule, record, alt_subject_ids)
                    # if no records were updated, reset update filter so that the insert statement
                    # will still run
                    if update_count == 0:
                        match_rule = None
                    else:
                        if logger and logger.track_subject_matching:
                            subject_id, source_subject_ids = writer.find_one_subject(match_rule)
                            logger.start_record_log(
                                oSource,
                                subject_match_manager,
                                subject_created=False,
                                subject_id=subject_id,
                                subject_final_ids=source_subject_ids,
                            )
                        counts["write"] += 1
                        counts["match"] += 1
                    # action = "updated"

                # updating an existing record didn't happen, so insert a new one
                if not match_rule and abbreviated_count_method != "match_strict":
                    if subject_match_manager.if_no_match == "create":
                        inserted_id = writer.insert_one_subject(record, alt_subject_ids)
                        if logger and logger.track_subject_matching:
                            logger.start_record_log(
                                oSource,
                                subject_match_manager,
                                subject_created=True,
                                subject_id=inserted_id,
                                subject_final_ids=alt_subject_ids,
                            )
                        # action = "created"
                        counts["write"] += 1
                    else:
                        # action = "ignored"
                        pass

        source_record_count += 1
        if source_record_count % notify_count == 0:
            tracker.print_notification(source_record_count)
            # want to finalize record logs intermittently to free up memory
            if logger:
                logger.finalize_record_logs()

    writer.finalize_subject_collection()

    if db_refresh_func is not None:
        db_refresh_func()
    if logger:
        # the db engine for the writer might be stale
        writer.refresh_engine()
        logger.finalize_source_log(
            oSource,
            count_source_records_read=counts["read"],
            count_source_records_loaded=counts["write"],
            count_subject_docs_end=writer.count_subject_records(),
        )
        logger.finalize_record_logs()

    return source_record_count

class LongitudinalCombos:
    """Determine criteria set combos for longitudinal queries.

    Criteria sets on event-type collections can be related to each other by relative date.
    For example, all patients who started taking aspiring within 1 week after a burn diagnosis -
    the medication criteria set and diagnosis criteria set form a longitudinal combo, which is
    treated differently in the query.

    Longitudinal combos aren't always easy to determine. There can be more than one, and they can
    also form into longer chains of 3+ events that are all related by relative date. This class
    has methods to inspect a cohort definition and determine the combos to use in the query.
    """

    def __init__(self, cohort):
        self.cohort = cohort

    def determine_longitudinal_combos(self):
        """Get the longitudinal combos for a cohort definition.

        :returns: data structure with all combos to use for this query. Each combo will be an
          array with at least 2 criteria sets.
        :rtype: array of arrays of dicts
        """
        # TODO: for now I'm assuming only chains of length 2

        # get all criteria sets that reference other criteria sets
        criteria_sets = self.cohort.create_internal_cohort_def()
        from_sets = []
        for criteria_set in criteria_sets:
            if criteria_set.get("event_rule", {}).get("type") == "relative_to_other_event":
                from_sets.append(criteria_set)

        # get all referenced criteria sets
        combos = []
        for from_set in from_sets:
            target = from_set["event_rule"]["target_entry_id"]
            to_set = next(item for item in criteria_sets if item["entry_id"] == target)
            combos.append([from_set, to_set])
        return combos

    def get_criteria_sets_involved_in_relative_date_rules(self):
        pass


class LongitudinalCombo:
    def __init__(self, combo):
        self.combo = combo

    def get_collection_index(self, oCollection):
        collection_id = oCollection.permanent_id
        if (
            collection_id == self.combo[0]["collection_id"]
            and collection_id == self.combo[1]["collection_id"]
        ):
            return [0, 1]
        if collection_id == self.combo[0]["collection_id"]:
            return 0
        if collection_id == self.combo[1]["collection_id"]:
            return 1
        return None

    def get_criteria_sets(self):
        return self.combo

    def get_criteria_set(self, index=0):
        return self.combo[index]

    def get_collections(self):
        collections = []
        for criteria_set in self.combo:
            collections.append(criteria_set["collection"])
        return collections

    def get_collection(self, index=0):
        return self.combo[index]["collection"]

    def get_entry_ids(self):
        ids = []
        ids.append(self.combo[0]["entry_id"])
        ids.append(self.combo[1]["entry_id"])
        return ids

    def get_entry_id(self, index=0):
        return self.combo[index]["entry_id"]

    def generate_subquery_id(self, outer_table, index=0):
        return (
            self.combo[0]["entry_id"] + self.combo[1]["entry_id"] + str(outer_table) + str(index)
        )

    def generate_sql_alchemy_clauses_for_event(self, table0, table1):
        """

        :param table0: the sqlalchemy table or alias for the first related collection
        :param table1: the sqlalchemy table or alias for the second related collection
        :return:
        """
        clauses = []
        range_start_days_from_target = self.combo[0]["event_rule"]["range_start_days_from_target"]
        range_end_days_from_target = self.combo[0]["event_rule"]["range_end_days_from_target"]
        reference_date = self.combo[0]["event_rule"]["reference_date"]
        range_start_target = self.combo[0]["event_rule"]["range_start_target"]
        range_end_target = self.combo[0]["event_rule"]["range_end_target"]
        date_concept0 = self.combo[0]["collection"].event_date_field.permanent_id
        if reference_date == "end":
            date_concept0 = self.combo[0]["collection"].event_end_date_field.permanent_id
        date_concept1_range_start = self.combo[1]["collection"].event_date_field.permanent_id
        date_concept1_range_end = self.combo[1]["collection"].event_date_field.permanent_id
        if range_start_target == "end":
            date_concept1_range_start = self.combo[1][
                "collection"
            ].event_end_date_field.permanent_id
        if range_end_target == "end":
            date_concept1_range_end = self.combo[1]["collection"].event_end_date_field.permanent_id
        date_column0 = getattr(table0.c, date_concept0)
        date_column1_range_start = getattr(table1.c, date_concept1_range_start)
        date_column1_range_end = getattr(table1.c, date_concept1_range_end)
        clause = date_column0 - date_column1_range_start >= range_start_days_from_target
        clauses.append(clause)
        clause = date_column0 - date_column1_range_end <= range_end_days_from_target
        clauses.append(clause)
        return clauses

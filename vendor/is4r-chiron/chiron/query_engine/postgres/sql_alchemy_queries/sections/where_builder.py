from sqlalchemy import select, and_, or_, func

from chiron.query_engine.postgres.sql_alchemy_queries import AbstractSqlAlchemyPartBuilder
from chiron.models import Concept
from chiron.query_engine.postgres.sql_alchemy_queries.event_filters import (
    get_where_clause_for_event_filter,
)


class WhereStatementBuilder(AbstractSqlAlchemyPartBuilder):
    def modify_statement(self, statement):
        """Modifies a SQL alchemy statement to add all WHERE filters."""
        clause = self.build_full_where_clause()
        if clause is not None:
            statement = statement.where(clause)
        return statement

    def build_full_where_clause(self):
        """Builds the entire WHERE clause for this query statement. If there
        is nothing to apply, returns None.
        """
        clauses = []
        # filter data based on user permissions
        permission_clause = self.get_main_query_clauses_for_permission_groups()
        if permission_clause is not None:
            clauses.append(permission_clause)
        # filter subjects based on cohort def
        clauses += self.get_main_query_clauses_for_subject_filtering()
        # filter subcollections based on cohort def and table def
        for collection in self.query_info.get_core_collections():
            clause = self.get_main_query_clause_for_subcollection_filtering(collection)
            if clause is not None:
                clauses.append(clause)
        # apply any prefilters specified for this query
        clauses += self.generate_prefilter_clause()
        if not clauses:
            return None
        return and_(*clauses)

    def get_main_query_clauses_for_permission_groups(self):
        subject_table = self.query_info.get_sql_alchemy_table_for_subject()
        relevant_concepts = self.chironuser.list_concepts_for_allowed_subjects()
        # if None, they are allowed to see everyone
        if relevant_concepts is None:
            return None
        # if empty list, they are allowed to see nobody
        if len(relevant_concepts) == 0:
            column = subject_table.c._subject_id
            return column == None  # noqa
        # at least one concept must match
        clauses = []
        for oConcept in relevant_concepts:
            child_processor = oConcept.get_cohort_def_processor_without_user()
            clause = child_processor.get_sql_alchemy_bool_clause(subject_table)
            clauses.append(clause)
        clause = or_(*clauses)
        return clause

    def generate_prefilter_clause(self):
        clauses = []
        for collection_id, prefilter in self.prefilters.items():
            concept_id = self.prefilters[collection_id]["concept_id"]
            oConcept = Concept.objects.get(permanent_id=concept_id)
            table = self.query_info.get_sql_alchemy_table_for_concept(oConcept)
            clause = getattr(table.c, concept_id) == self.prefilters[collection_id]["value"]
            clauses.append(clause)
        return clauses

    def get_main_query_clauses_for_subject_filtering(self):
        """Returns subject sql alchemy filters for the main WHERE clause.

        The subject filters only define the cohort, then for a specific report table there may be
        additional filters to get the correct records for that cohort.
        """
        clauses = []
        completed_criteria_sets = []
        for criteria_set in self.cohort.internal_cohort_def:
            oCollection = criteria_set["collection"]
            if oCollection.is_root_collection:
                c1, lookup_tables = self.get_clauses_for_criteria_set(criteria_set)
                clauses += c1
                completed_criteria_sets.append(criteria_set["entry_id"])

        # apply any longitudinal combos
        subject_table = self.query_info.get_sql_alchemy_table_for_subject()
        for combo in self.query_info.get_longitudinal_combos():
            clause = self.get_full_filter_clause_for_longitudinal_combo(
                combo, self.alias_manager.TYPE_SUBJECT_FILTER, subject_table, "_subject_id"
            )
            if clause is not None:
                clauses.append(clause)
            for criteria_set in combo.get_criteria_sets():
                completed_criteria_sets.append(criteria_set["entry_id"])

        # apply any remaining criteria sets
        for criteria_set in self.cohort.internal_cohort_def:
            if criteria_set["entry_id"] not in completed_criteria_sets:
                clause = self.get_subject_filter_clause_for_criteria_set(criteria_set)
                if clause is not None:
                    clauses.append(clause)
                completed_criteria_sets.append(criteria_set["entry_id"])
        return clauses

    def get_main_query_clause_for_subcollection_filtering(self, oCollection):
        if oCollection.is_root_collection:
            return None
        clauses = []
        completed_criteria_sets = []

        # apply any related longitudinal combos
        table = self.query_info.get_sql_alchemy_table_for_collection(oCollection)
        for combo in self.query_info.get_longitudinal_combos():
            collection_index = combo.get_collection_index(oCollection)
            if collection_index is None:
                continue

            fully_stacked = True
            for combo_collection in combo.get_collections():
                if combo_collection not in self.query_info.get_core_collections():
                    fully_stacked = False
            if collection_index == [0, 1]:
                clause1 = self.get_full_filter_clause_for_longitudinal_combo(
                    combo, self.alias_manager.TYPE_SUBCOL_FILTER, table, "_id", reversed=True
                )
                clause2 = self.get_full_filter_clause_for_longitudinal_combo(
                    combo, self.alias_manager.TYPE_SUBCOL_ALT_FILTER, table, "_id", reversed=False
                )
                clauses.append(clause1)
                clauses.append(clause2)
            elif fully_stacked:
                clause = self.get_one_sided_filter_clause_for_longitudinal_combo(
                    combo, combo.get_collection_index(oCollection)
                )
                if clause is not None:
                    clauses.append(clause)
            else:
                is_reversed = combo.get_collection_index(oCollection) == 1
                clause = self.get_full_filter_clause_for_longitudinal_combo(
                    combo,
                    self.alias_manager.TYPE_SUBCOL_FILTER,
                    table,
                    "_id",
                    reversed=is_reversed,
                )
                if clause is not None:
                    clauses.append(clause)
            for criteria_set in combo.get_criteria_sets():
                completed_criteria_sets.append(criteria_set["entry_id"])

        # apply any remaining criteria sets
        for criteria_set in self.cohort.internal_cohort_def:
            if criteria_set["collection"] != oCollection:
                continue
            if criteria_set["entry_id"] in completed_criteria_sets:
                continue
            clause = self.get_subcollection_filter_clause_for_criteria_set(criteria_set)
            if clause is not None:
                clauses.append(clause)

        # return value
        if len(clauses) == 1:
            return clauses[0]
        if len(clauses) > 1:
            return or_(*clauses)
        return None

    def get_clauses_for_criteria_set(self, criteria_set, subquery_type=None, subquery_id=None):
        """Get all sql alchemy filters for a criteria set.
        subquery_type and criteria_set ID will be used to create a group of table aliases

        :param criteria_set:
        :param subquery_type:
        :param subquery_id:
        :return:
        """
        clauses = []
        lookup_tables = []
        for filter_rule in criteria_set["list"]:
            # check if there's a lookup table to use, if not use passed collection_table (which
            # might be an alias)

            clause, new_lookup_tables = self.get_clause_for_criteria_set_entry(
                criteria_set, filter_rule, subquery_type, subquery_id
            )
            clauses.append(clause)
            for lookup_table in new_lookup_tables:
                if lookup_table not in lookup_tables:  # and lookup_table != table:
                    lookup_tables.append(lookup_table)
        event_clause, event_lookup_tables = self.get_clause_for_event_filter(
            criteria_set, subquery_type, subquery_id
        )
        if event_clause is not None:
            clauses.append(event_clause)
        for lookup_table in event_lookup_tables:
            if lookup_table not in lookup_tables:
                lookup_tables.append(lookup_table)
        return clauses, lookup_tables

    def get_clause_for_event_filter(self, criteria_set, subquery_type, subquery_id):
        lookup_tables = []
        event_clause = None
        event_rule = criteria_set.get("event_rule", {}).get("type", "no_restriction")
        if event_rule in ["no_restriction", "relative_to_other_event"]:
            return event_clause, lookup_tables
        oCollection = criteria_set["collection"]
        # determine event start date column
        start_concept = oCollection.event_date_field
        start_concept_table = self.query_info.get_sql_alchemy_table_for_concept(start_concept)
        if subquery_type:
            subquery_id = subquery_id if subquery_id else criteria_set["entry_id"]
            start_concept_table = self.alias_manager.get_concept_alias(
                subquery_type, subquery_id, start_concept
            )
        start_column = getattr(start_concept_table.c, start_concept.permanent_id)
        lookup_tables.append(start_concept_table)
        # determine event end date column
        end_column = None
        end_concept = oCollection.event_end_date_field
        if end_concept:
            end_concept_table = self.query_info.get_sql_alchemy_table_for_concept(end_concept)
            if subquery_type:
                subquery_id = subquery_id if subquery_id else criteria_set["entry_id"]
                end_concept_table = self.alias_manager.get_concept_alias(
                    subquery_type, subquery_id, end_concept
                )
            end_column = getattr(start_concept_table.c, end_concept.permanent_id)
            lookup_tables.append(end_concept_table)
        event_clause = get_where_clause_for_event_filter(criteria_set, start_column, end_column)
        return event_clause, lookup_tables

    def get_subject_filter_clause_for_criteria_set(self, criteria_set):
        """Create subquery filter to apply a subcollection criteria set to the subject.

        Uses a subcollection criteria set to filter the subjects using subject_id. Final statement
        will be in the form if "subject_id IN (SELECT...)"
        """
        count_type = criteria_set.get("subcol_count_restriction", {}).get("type", "at least")
        count_value = criteria_set.get("subcol_count_restriction", {}).get("value", 1)
        # subjects will always have at least zero matches
        if count_type == "at least" and count_value == 0:
            return None

        subquery_type = self.alias_manager.TYPE_SUBJECT_FILTER
        collection_alias, m2m_alias = self.alias_manager.get_collection_alias(
            subquery_type,
            criteria_set["entry_id"],
            criteria_set["collection"],
            include_m2m=True,
        )
        clauses, lookup_tables = self.get_clauses_for_criteria_set(
            criteria_set, subquery_type=subquery_type
        )
        subject_table = self.query_info.get_sql_alchemy_table_for_subject()

        # simpler handling if "in" or "not in" rule will suffice
        if (count_type == "at least" and count_value == 1) or (
            count_type in ["at most", "exactly"] and count_value == 0
        ):
            if m2m_alias is None:
                subquery = select(collection_alias.c._subject_id)
            else:
                subquery = select(m2m_alias.c._subject_id)
                subquery = subquery.join_from(
                    m2m_alias,
                    collection_alias,
                    collection_alias.c._id == m2m_alias.c._collection_id,
                )
            subquery = self.alias_manager.add_custom_from_statement(
                subquery,
                subquery_type,
                criteria_set["entry_id"],
            )
            if clauses:
                subquery = subquery.where(and_(*clauses))
            if count_type == "at least" and count_value == 1:
                clause = subject_table.c._subject_id.in_(subquery)
            else:  # count_value = 0
                clause = subject_table.c._subject_id.not_in(subquery)
            return clause

        # handling that works for all subcollection count cases
        subquery = select(func.count(collection_alias.c._id))
        if m2m_alias is None:
            clauses.append(collection_alias.c._subject_id == subject_table.c._subject_id)
        else:
            subquery = subquery.join_from(
                collection_alias,
                m2m_alias,
                collection_alias.c._id == m2m_alias.c._collection_id,
            )
            clauses.append(m2m_alias.c._subject_id == subject_table.c._subject_id)
        subquery = self.alias_manager.add_custom_from_statement(
            subquery,
            subquery_type,
            criteria_set["entry_id"],
        )
        subquery = subquery.where(and_(*clauses))
        if count_type == "at least":
            return subquery.scalar_subquery() >= count_value
        elif count_type == "at most":
            return subquery.scalar_subquery() <= count_value
        # else count_type == "exactly"
        return subquery.scalar_subquery() == count_value

    def get_subcollection_filter_clause_for_criteria_set(self, criteria_set):
        """Create subquery filter to apply a subcollection criteria set to that subcollection.

        Final statement will be in the form if "mysubcol._id IN (SELECT...)"
        """
        # if we're removing subjects that match, don't want to use to filter encounters
        count_type = criteria_set.get("subcol_count_restriction", {}).get("type", "at least")
        count_value = criteria_set.get("subcol_count_restriction", {}).get("value", 1)
        if (count_type == "at most" or count_type == "exactly") and count_value == 0:
            return None
        oCollection = criteria_set["collection"]
        subquery_type = self.alias_manager.TYPE_SUBCOL_FILTER
        outer_table = self.query_info.get_sql_alchemy_table_for_collection(oCollection)
        inner_table = self.alias_manager.get_collection_alias(
            subquery_type, criteria_set["entry_id"], oCollection
        )
        subclauses, lookup_tables = self.get_clauses_for_criteria_set(
            criteria_set, subquery_type=subquery_type
        )
        subquery = select(inner_table.c._id)
        subquery = self.alias_manager.add_custom_from_statement(
            subquery, subquery_type, criteria_set["entry_id"]
        )
        if subclauses:
            subquery = subquery.where(and_(*subclauses))
        clause = outer_table.c._id.in_(subquery)
        return clause

    def build_criteria_set_entry_clause(self, processor, entry, collection_table, concept_table):
        """
        Used by get_clause_for_criteria_set_entry(). Includes special handling if
        exclude_selected is True (which requires a full subquery).

        :param processor: The cohort def processor for this concept
        :param entry: The criteria set entry in the cohort def
        :param concept_table: The sqlalchemy table with the value for this concept
        :return:
        """
        exclude_selected = entry.get("exclude_selected", False)
        if exclude_selected:
            if entry["concept"].collection.is_root_collection:
                subject_table = self.query_info.get_sql_alchemy_table_for_subject()
                subject_alias = subject_table.alias()
                alias = concept_table.alias()
                if entry["concept"].multivalue:
                    subquery = select(subject_alias.c._subject_id).outerjoin(
                        alias, subject_alias.c._subject_id == alias.c._collection_id
                    )
                else:
                    subquery = select(alias.c._subject_id)
                clause = processor.get_sql_alchemy_clause(entry, alias)
                subquery = subquery.where(clause)
                outer_clause = subject_table.c._subject_id.not_in(subquery)
                return outer_clause
            else:  # this is a subcollection concept
                alias = concept_table.alias()
                if entry["concept"].multivalue:
                    collection_alias = collection_table.alias()
                    subquery = select(collection_alias.c._id).outerjoin(
                        alias, collection_alias.c._id == alias.c._collection_id
                    )
                else:
                    subquery = select(alias.c._id)
                clause = processor.get_sql_alchemy_clause(entry, alias)
                subquery = subquery.where(clause)
                outer_clause = collection_table.c._id.not_in(subquery)
                return outer_clause
        clause = processor.get_sql_alchemy_clause(entry, concept_table)
        return clause

    def append_prefilter_rule_to_clause(self, clause, entry, oConcept, subquery_type, subquery_id):
        prefilter_value = entry.get("prefilter_value")
        if not prefilter_value:
            return clause, None
        prefilter_concept = oConcept.concept_for_prefilter
        prefilter_table = self.alias_manager.get_concept_alias(
            subquery_type, subquery_id, prefilter_concept
        )
        prefilter_column = getattr(prefilter_table.c, prefilter_concept.permanent_id)
        prefilter_clause = prefilter_column == prefilter_value
        clause = and_(clause, prefilter_clause)
        if prefilter_concept.multivalue:
            return clause, prefilter_table
        return clause, None

    def get_clause_for_criteria_set_entry(
        self, criteria_set, entry, subquery_type=None, subquery_id=None
    ):
        """Takes one criteria set entry and generates the WHERE filter.

        This is the step that will communicate with the concept cohort def processor to get
        something specific for this data type.

        :param criteria_set:
        :param entry:
        :param subquery_type:
        :param subquery_id:
        :return:
        """
        lookup_tables = []
        if entry.get("entry_type", "") == "or_group":
            child_clauses = []
            for child_filter_rule in entry["list"]:
                oConcept = child_filter_rule["concept"]
                child_processor = oConcept.get_cohort_def_processor_without_user()
                child_table = self.query_info.get_sql_alchemy_table_for_concept(oConcept)
                collection_table = self.query_info.get_sql_alchemy_table_for_collection(
                    child_filter_rule["concept"].collection
                )
                if subquery_type:
                    subquery_id = subquery_id if subquery_id else criteria_set["entry_id"]
                    child_table = self.alias_manager.get_concept_alias(
                        subquery_type, subquery_id, oConcept
                    )
                    collection_table = self.alias_manager.get_collection_alias(
                        subquery_type, subquery_id, oConcept.collection
                    )
                child_clause = self.build_criteria_set_entry_clause(
                    child_processor, child_filter_rule, collection_table, child_table
                )
                child_clause, prefilter_table = self.append_prefilter_rule_to_clause(
                    child_clause, child_filter_rule, oConcept, subquery_type, subquery_id
                )
                if prefilter_table is not None:
                    lookup_tables.append(prefilter_table)
                child_clauses.append(child_clause)
                if oConcept.multivalue:
                    lookup_tables.append(child_table)
            clause = or_(*child_clauses)
        else:
            oConcept = entry["concept"]
            processor = oConcept.get_cohort_def_processor_without_user()
            concept_table = self.query_info.get_sql_alchemy_table_for_concept(oConcept)
            collection_table = self.query_info.get_sql_alchemy_table_for_collection(
                entry["concept"].collection
            )
            if subquery_type:
                subquery_id = subquery_id if subquery_id else criteria_set["entry_id"]
                concept_table = self.alias_manager.get_concept_alias(
                    subquery_type, subquery_id, oConcept
                )
                collection_table = self.alias_manager.get_collection_alias(
                    subquery_type, subquery_id, oConcept.collection
                )
            clause = self.build_criteria_set_entry_clause(
                processor, entry, collection_table, concept_table
            )
            clause, prefilter_table = self.append_prefilter_rule_to_clause(
                clause, entry, oConcept, subquery_type, subquery_id
            )
            if prefilter_table is not None:
                lookup_tables.append(prefilter_table)
            if oConcept.multivalue:
                lookup_tables.append(concept_table)
        return clause, lookup_tables

    def get_one_sided_filter_clause_for_longitudinal_combo(self, combo, collection_index):
        """
        Subquery will use an alias for one side of the combo and link it to the table in the
        main query.

        example:
        encounter._id IN
        (SELECT DISTINCT encounter_2._id
         FROM encounter AS encounter_2
             WHERE encounter_2.encounter_start - lab_result_event.lab_event_date_2 >= 0
             AND encounter_2.encounter_start - lab_result_event.lab_event_date_2 <= 60)
        """
        not_collection_index = 1 if collection_index == 0 else 0
        outer_table = self.query_info.get_sql_alchemy_table_for_collection(
            combo.get_collection(collection_index)
        )
        outer_table_other = self.query_info.get_sql_alchemy_table_for_collection(
            combo.get_collection(not_collection_index)
        )
        subquery_type = self.alias_manager.TYPE_SUBJECT_FILTER
        subquery_id = combo.generate_subquery_id(outer_table)
        inner_table = self.alias_manager.get_collection_alias(
            subquery_type, subquery_id, combo.get_collection(collection_index)
        )
        if collection_index == 0:
            clauses = self.get_clauses_for_longitudinal_combo(
                combo, subquery_type, subquery_id, None, table1=outer_table_other
            )
        else:
            clauses = self.get_clauses_for_longitudinal_combo(
                combo, subquery_type, None, subquery_id, table0=outer_table_other
            )
        column = getattr(inner_table.c, "_id")
        subquery = select(column).select_from(inner_table).distinct()
        lookup_aliases = self.alias_manager.get_aliases(subquery_type, subquery_id, "lookup")
        for entry in lookup_aliases:
            subquery = subquery.outerjoin(
                entry["alias"], entry["alias"].c._collection_id == entry["parent_alias"].c._id
            )
        if clauses:
            subquery = subquery.where(and_(*clauses))
        clause = outer_table.c._id.in_(subquery)
        return clause

    def get_full_filter_clause_for_longitudinal_combo(
        self, combo, subquery_type, outer_table, inner_id, reversed=False
    ):
        if subquery_type is None:
            subquery_type = self.alias_manager.TYPE_SUBJECT_FILTER
        subquery_id0 = combo.generate_subquery_id(outer_table, index=0)
        subquery_id1 = combo.generate_subquery_id(outer_table, index=1)
        table0 = self.alias_manager.get_collection_alias(
            subquery_type, subquery_id0, combo.get_collection(index=0)
        )
        # table1 alias needs to be referenced by a different subquery_id in case it's the same
        # collection as table0
        table1 = self.alias_manager.get_collection_alias(
            subquery_type, subquery_id1, combo.get_collection(index=1)
        )
        clauses = self.get_clauses_for_longitudinal_combo(
            combo, subquery_type, subquery_id0, subquery_id1
        )
        if reversed:
            column = getattr(table1.c, inner_id)
        else:
            column = getattr(table0.c, inner_id)
        subquery = (
            select(column)
            .select_from(table0)
            .join(table1, table0.c._subject_id == table1.c._subject_id)
            .distinct()
        )
        lookup_aliases = self.alias_manager.get_aliases(subquery_type, subquery_id0, "lookup")
        for entry in lookup_aliases:
            subquery = subquery.outerjoin(
                entry["alias"], entry["alias"].c._collection_id == entry["parent_alias"].c._id
            )
        lookup_aliases = self.alias_manager.get_aliases(subquery_type, subquery_id1, "lookup")
        for entry in lookup_aliases:
            subquery = subquery.outerjoin(
                entry["alias"], entry["alias"].c._collection_id == entry["parent_alias"].c._id
            )
        if clauses:
            subquery = subquery.where(and_(*clauses))
        clause = outer_table.c._id.in_(subquery)
        return clause

    def get_clauses_for_longitudinal_combo(
        self,
        combo,
        subquery_type,
        subquery_id0,
        subquery_id1,
        table0=None,
        table1=None,
    ):
        """

        :param combo: LongitudinalCombo object
        :param subquery_type:
        :param subquery_id0:
        :param subquery_id1:
        :param table0: the sqlalchemy table or alias for the first related collection. Leave as
          None to fetch alias from alias_manager based on other arguments provided.
        :param table1: the sqlalchemy table or alias for the second related collection. Leave as
          None to fetch alias from alias_manager based on other arguments provided.
        :return:
        """
        # main_combo_entry = combo.get_criteria_set(1) if reverse else combo.get_criteria_set(0)
        if table0 is None:
            table0 = self.alias_manager.get_collection_alias(
                subquery_type, subquery_id0, combo.get_collection(index=0)
            )
        if table1 is None:
            table1 = self.alias_manager.get_collection_alias(
                subquery_type, subquery_id1, combo.get_collection(index=1)
            )
        clauses = []
        if subquery_id0 is not None:
            clauses1, lookup_tables1 = self.get_clauses_for_criteria_set(
                combo.get_criteria_set(0), subquery_type, subquery_id0
            )
            clauses += clauses1
        if subquery_id1 is not None:
            clauses2, lookup_tables2 = self.get_clauses_for_criteria_set(
                combo.get_criteria_set(1), subquery_type, subquery_id1
            )
            clauses += clauses2
        date_clauses = combo.generate_sql_alchemy_clauses_for_event(table0, table1)
        clauses += date_clauses
        return clauses

    def get_clauses_related_to_collection(self, oCollection, entry_id, aggregation_criteria_set):
        """This one is for select statement.

        clauses is list of lists that should be organized as OR/AND. Tables lists tables needed
        form FROM clause
        """
        collection_id = oCollection.permanent_id
        clause_groups = []
        finished_entry_ids = []
        addl_alias_references = []

        subquery_type = self.alias_manager.TYPE_SELECT

        # find all combos where first element matches
        for combo in self.query_info.get_longitudinal_combos():
            if oCollection != combo.get_collection(0):
                continue
            entry_ids = combo.get_entry_ids()
            # for multiple criteria sets on the same collection, user might have specified one
            if aggregation_criteria_set and aggregation_criteria_set != entry_ids[0]:
                continue
            # if the other table is stacked, want to do one-sided query that links to that
            if combo.get_collection(1) in self.query_info.get_core_collections():
                table1 = self.query_info.get_sql_alchemy_table_for_collection(
                    combo.get_collection(1)
                )
                clauses = self.get_clauses_for_longitudinal_combo(
                    combo, subquery_type, entry_id, None, table1=table1
                )
            # if the other table is aggregated, want to do full query
            else:
                clauses = self.get_clauses_for_longitudinal_combo(
                    combo, subquery_type, entry_id, entry_ids[1]
                )
            clause_groups.append(clauses)
            addl_alias_references.append(entry_ids[1])
            finished_entry_ids.append(combo.get_entry_id(0))

        # find all combos where second element matches
        for combo in self.query_info.get_longitudinal_combos():
            if oCollection != combo.get_collection(1):
                continue
            entry_ids = combo.get_entry_ids()
            # for multiple criteria sets on the same collection, user might have specified one
            if aggregation_criteria_set and aggregation_criteria_set != entry_ids[1]:
                continue
            # if the other table is stacked, want to link to that rather than creating alias
            if combo.get_collection(0) in self.query_info.get_core_collections():
                table0 = self.query_info.get_sql_alchemy_table_for_collection(
                    combo.get_collection(0)
                )
                clauses = self.get_clauses_for_longitudinal_combo(
                    combo, subquery_type, None, entry_id, table0=table0
                )
            else:
                clauses = self.get_clauses_for_longitudinal_combo(
                    combo, subquery_type, entry_ids[0], entry_id
                )
            clause_groups.append(clauses)
            addl_alias_references.append(entry_ids[0])
            finished_entry_ids.append(combo.get_entry_id(1))

        for criteria_set in self.cohort.internal_cohort_def:
            # if we're removing subjects that match, don't want to use to filter encounters
            count_type = criteria_set.get("subcol_count_restriction", {}).get("type", "at least")
            count_value = criteria_set.get("subcol_count_restriction", {}).get("value", 1)
            if (count_type == "at most" or count_type == "exactly") and count_value == 0:
                continue
            if criteria_set["collection_id"] != collection_id:
                continue
            if aggregation_criteria_set and criteria_set["entry_id"] != aggregation_criteria_set:
                continue
            if criteria_set["entry_id"] in finished_entry_ids:
                continue
            clauses, lookup_tables = self.get_clauses_for_criteria_set(
                criteria_set, subquery_type, entry_id
            )
            clause_groups.append(clauses)
        return clause_groups, addl_alias_references

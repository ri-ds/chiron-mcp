from chiron import models

from chiron.query_engine.postgres.sql_alchemy_queries.longitudinal_combos import LongitudinalCombo
from chiron.query_engine.postgres import database


class QueryInfo:
    """Determine information relevant to how a query should be run in SQL.

    The approach for setting up a query will vary depending on many factors. This class
    looks at some of those factors and provided inf that will help the query builder decide
    how to structure the SQL statement.

    It's very important that a single instance of this class is used to build a SQL query. The
    class stores references to SQL alchemy table objects, and SQL Alchemy will treat two different
    table objects as separate tables even if they reference the same database table.

    :param obj dataset: The Django model object for the dataset.
    :param obj cohort: The query_definition.Cohort object
    :param obj table: The query_definition.Table object, or None if no results table is being
      created
    :param obj target_collection: Optionally provide the Django model object for the collection
      you're retrieving data about (for more efficient queries)
    :param dict prefilters:
    """

    def __init__(self, dataset, cohort, table=None, target_collection=None, prefilters=None):
        self.dataset = dataset
        self.cohort = cohort
        self.table = table
        self.target_collection = target_collection
        self.prefilters = prefilters if prefilters else {}
        self.sql_alchemy_tables = {}
        self.sql_alchemy_lookup_tables = {}
        self.after_query_modifiers = {}
        self.sortable_columns = {}
        self.combos = []
        self.core_lookup_tables = None

    def add_to_relevant_concept_ids(self, concept, include_prefilter=True):
        """Add a concept to self.relevant_concept_ids.

        Will verify that the concept exists and hasn't been added already. Will also
        add the associated prefilter concept if it exists and hasn't been added already.
        """
        if concept:
            if concept.permanent_id not in self.relevant_concept_ids:
                self.relevant_concept_ids.append(concept.permanent_id)
            if include_prefilter:
                prefilter = concept.concept_for_prefilter
                if prefilter:
                    if prefilter.permanent_id not in self.relevant_concept_ids:
                        self.relevant_concept_ids.append(prefilter.permanent_id)

    def get_relevant_concept_ids(self, include_concept=None):
        """Get a list of concept IDs relevant to this query.

        The list will include the optional provided concept and its prefilter if set,
        all concepts referenced in the cohort_def, all concepts referenced in the
        table_def (if this query uses a table_def), and all concepts needed to
        determine user permission.
        """
        self.relevant_concept_ids = []
        for criteria_set in self.cohort.internal_cohort_def:
            for entry in criteria_set["list"]:
                if "entry_type" in entry and entry["entry_type"] == "or_group":
                    for subentry in entry.get("list", []):
                        self.add_to_relevant_concept_ids(subentry["concept"])
                else:
                    self.add_to_relevant_concept_ids(entry["concept"])
        if self.table:
            for entry in self.table.internal_table_def["fields"]:
                self.add_to_relevant_concept_ids(entry["concept"])
        if include_concept:
            self.add_to_relevant_concept_ids(include_concept)
        for oPermissionGroup in models.PermissionGroup.objects.all():
            self.add_to_relevant_concept_ids(
                oPermissionGroup.concept_for_allowed_subjects, include_prefilter=False
            )
        return self.relevant_concept_ids

    def get_sql_alchemy_table_for_subject(self):
        """Get the SQL alchemy table object for the postgres subject table."""
        return self.get_sql_alchemy_table_for_collection(self.dataset.root_collection)

    def get_sql_alchemy_table_for_collection(
        self, oCollection, include_m2m=False, include_concept=None
    ):
        """Get the SQL alchemy table object(s) for a postgres subcollection table.

        :param oCollection: The Django model object for the desired collection.
        :param include_m2m: Return a tuple that includes the M2M table linking an M2M
          subcollection to a subject
        :return:
        :rtype: SQL alchemy table object or tuple of two SQL alchemy table objects
        """
        if oCollection.permanent_id in self.sql_alchemy_tables:
            if include_m2m:
                return self.sql_alchemy_tables[oCollection.permanent_id]
            return self.sql_alchemy_tables[oCollection.permanent_id][0]
        if oCollection.is_root_collection:
            table = database.generate_sql_alchemy_table_for_subject_collection(
                oCollection, relevant_concept_ids=self.get_relevant_concept_ids(include_concept)
            )
            self.sql_alchemy_tables[oCollection.permanent_id] = (table, None)
        else:
            table, m2m_table = database.generate_sql_alchemy_table_for_subcollection(
                oCollection, relevant_concept_ids=self.get_relevant_concept_ids(include_concept)
            )
            self.sql_alchemy_tables[oCollection.permanent_id] = (table, m2m_table)
        if include_m2m:
            return self.sql_alchemy_tables[oCollection.permanent_id]
        return self.sql_alchemy_tables[oCollection.permanent_id][0]

    def get_sql_alchemy_table_for_concept(self, oConcept):
        """Get the SQL Alchemy table object for the table storing this concept.

        :param oConcept: The Django model object for the desired concept.
        :return: The SQL alchemy table, This will be the parent collection table for regular
          concepts and a lookup table for concepts that can store multiple values.
        """
        if not oConcept.multivalue:
            return self.get_sql_alchemy_table_for_collection(
                oConcept.collection, include_concept=oConcept
            )
        if oConcept.permanent_id in self.sql_alchemy_lookup_tables:
            return self.sql_alchemy_lookup_tables[oConcept.permanent_id]
        table = database.generate_sql_alchemy_lookup_table_for_concept(oConcept)
        self.sql_alchemy_lookup_tables[oConcept.permanent_id] = table
        return self.sql_alchemy_lookup_tables[oConcept.permanent_id]

    def get_grouping_method(self):
        """Should the query use GROUP BY or DISTINCT for grouping values."""
        for entry in self.table.internal_table_def["fields"]:
            if entry.get("aggregate"):
                return "group_by"
        return "distinct"

    def get_core_collections(self):
        """Returns list of collection model objects that should be used in the core FROM statement.

        Queries often involve some things being done as part of the main query, and some things
        being done inside subqueries. This returns the list of collections for the main
        FROM statement.
        """
        all_collections = []
        core_collections = []
        all_collections.append(self.dataset.root_collection)
        core_collections.append(self.dataset.root_collection)
        # add collections used in table def
        if self.table is not None:
            for entry in self.table.internal_table_def["fields"]:
                collection = entry["concept"].collection
                if collection not in all_collections:
                    all_collections.append(collection)
                if not entry.get("aggregate"):
                    collection = entry["concept"].collection
                    if collection not in core_collections:
                        core_collections.append(collection)
        # add collections used in prefilter
        for collection_id, prefilter in self.prefilters.items():
            oCollection = models.Collection.objects.get(
                permanent_id=collection_id, dataset=self.dataset
            )
            if oCollection not in all_collections:
                all_collections.append(oCollection)
            if oCollection not in core_collections:
                core_collections.append(oCollection)
        # add any specified target collection
        if self.target_collection and self.target_collection not in core_collections:
            core_collections.append(self.target_collection)
        # TODO: This code is intended to speed up certain queries - where the only stacked
        #    columns are from the root collection and all agg columns are from the same
        #    subcollection. But there are some rare contexts where this causes problems, so I
        #    would need to think through this carefully before turning the feature back on.
        # if there's only 1 subcollection even with aggregation, go ahead and include it
        # if len(core_collections) == 1 and len(all_collections) == 2:
        #     return all_collections
        return core_collections

    def get_core_lookup_tables(self):
        """
        These are the lookup tables that should be implemented in the main from statement.
        """
        # don't rerun if already run
        if self.core_lookup_tables is not None:
            return self.core_lookup_tables
        # build out the data structure of the response
        response = {}
        core_collections = self.get_core_collections()
        for oCollection in core_collections:
            response[oCollection.permanent_id] = []
        # lookup concepts associated with table def should be included
        if self.table:
            for entry in self.table.internal_table_def["fields"]:
                oConcept = entry["concept"]
                if not oConcept.multivalue:
                    continue
                collection_id = oConcept.collection.permanent_id
                if collection_id in response:
                    table = self.get_sql_alchemy_table_for_concept(oConcept)
                    if table not in response[collection_id]:
                        response[collection_id].append(table)
        # lookup concepts associated with cohort def and in subject collection should be included
        for criteria_set in self.cohort.internal_cohort_def:
            oCollection = criteria_set["collection"]
            if oCollection.is_root_collection:
                for filter_rule in criteria_set["list"]:
                    oConcept = filter_rule["concept"]
                    if not oConcept.multivalue:
                        continue
                    collection_id = oConcept.collection.permanent_id
                    table = self.get_sql_alchemy_table_for_concept(oConcept)
                    if collection_id not in response:
                        response[collection_id] = []
                    if table not in response[collection_id]:
                        response[collection_id].append(table)
        # lookup concepts associated with prefilters
        for collection_id, prefilter in self.prefilters.items():
            oCollection = models.Collection.objects.get(
                permanent_id=collection_id, dataset=self.dataset
            )
            concept_id = self.prefilters[collection_id]["concept_id"]
            oConcept = models.Concept.objects.get(permanent_id=concept_id, collection=oCollection)
            if not oConcept.multivalue:
                continue
            table = self.get_sql_alchemy_table_for_concept(oConcept)
            if table not in response[collection_id]:
                response[collection_id].append(table)
        self.core_lookup_tables = response
        return self.core_lookup_tables

    def get_longitudinal_combos(self):
        """Get a list of all longitudinal combos for this cohort definition.

        :return: A list of 2-value tuples with the two criteria sets for the longitudinal combo.
        """
        if self.combos:
            return self.combos
        combos = []
        criteria_sets = self.cohort.internal_cohort_def
        for criteria_set in criteria_sets:
            if criteria_set.get("event_rule", {}).get("type") == "relative_to_other_event":
                target_entry_id = criteria_set["event_rule"]["target_entry_id"]
                target_criteria_set = next(
                    (item for item in criteria_sets if item["entry_id"] == target_entry_id), None
                )
                combo = LongitudinalCombo([criteria_set, target_criteria_set])
                combos.append(combo)
        self.combos = combos
        return combos

    def check_collection_in_longitudinal_combo(self, oCollection):
        """In the cohort definition, is this collection involved in a longitudinal combo?

        :param oCollection: The Django model object for the collection
        :return: True or False
        """
        for combo in self.get_longitudinal_combos():
            if combo.get_collection_index(oCollection) is not None:
                return True
        return False

    def get_longitudinal_combo_for_criteria_set(self, criteria_set):
        """Returns longitudinal combo or None
        :return:
        """
        # TODO: this will eventually have to handle chains of 2+ instead of just combos
        combos = self.get_longitudinal_combos()
        for combo in combos:
            if criteria_set in combo.get_criteria_sets():
                return combo
        return None

    def find_subcollection_relationship(self, from_col, to_col):
        """Determine if two subcollections have a direct relationship.

        Subcollections can have a relationship defined in the CollectionRelationship model. This
        will search for such a relationship and return the related model object. Returns None
        if no relationship exists.
        """
        qRel = models.CollectionRelationship.objects.all()
        for oRel in qRel:
            if oRel.get_pk_collection() == from_col and oRel.get_fk_collection() == to_col:
                return oRel
            if oRel.get_fk_collection() == from_col and oRel.get_pk_collection() == to_col:
                return oRel
        return None

    def find_subcollection_relationship_from_list(self, from_col, to_cols):
        """Does the from collection have direct relationships to any of the to collections.

        Collections can be related to each other as defined in the CollectionRelationship table.
        Will return the first CollectionRelationship model object found, or None if no
        relationships.

        :param from_col: Django model object for collection of interest.
        :param to_cols: List of Django model objects for collections to check.
        :return: CollectionRelationship Django model object or None
        """
        for to_col in to_cols:
            if to_col == from_col:
                continue
            oRel = self.find_subcollection_relationship(from_col, to_col)
            if oRel:
                return oRel
        return None

    def find_subcollection_relationship_from_collection_ids(self, collection_id1, collection_id2):
        """Does the from collection have direct relationships to the to collection.

        This is just a wrapper for find_subcollection_relationship() that allows
        you to provide IDs instead of Django model objects.

        :param from_col: ID for collection of interest.
        :param to_cols: ID for collection to check for relationship to.
        :return: CollectionRelationship Django model object or None
        """
        from_col = models.Collection.objects.get(permanent_id=collection_id1)
        to_col = models.Collection.objects.get(permanent_id=collection_id2)
        return self.find_subcollection_relationship(from_col, to_col)

    def register_after_query_modifier(self, position, func):
        if func:
            self.after_query_modifiers[position] = func

    def register_sortable_column(self, entry_id, column):
        self.sortable_columns[entry_id] = column

    def get_sql_alchemy_table_for_concept_search(self):
        table = self.sql_alchemy_tables.get("concept_search")
        if not table:
            table = database.generate_sql_alchemy_table_for_concept_search()
            self.sql_alchemy_tables["concept_search"] = table
        return table

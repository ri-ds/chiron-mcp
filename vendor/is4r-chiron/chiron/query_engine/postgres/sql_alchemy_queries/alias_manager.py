class AliasManager:
    """Track SQL Alchemy table aliases for subqueries.

    In SQL alchemy, when running a subquery you can prevent a table name clash by using a table
    alias. Once the alias is created, the alias object must be tracked so that all sections of
    the subquery reference the same alias object. This class just exists to help store and retrieve
    alias objects.

    :param query_info: A query_engine.postgres.sql_alchemy_queries.query_info.QueryInfo object
    """

    # a WHERE statement for a criteria set applied for filtering subjects
    TYPE_SUBJECT_FILTER = "subject_filter"
    # a WHERE statement for a criteria set applied for filtering a subcollection
    TYPE_SUBCOL_FILTER = "subcollection_filter"
    # use if you have two filters on the same subcollection
    TYPE_SUBCOL_ALT_FILTER = "subcollection_alt_filter"
    # a SELECT statement for a criteria set to retrieve a column
    TYPE_SELECT = "select"

    def __init__(self, query_info):
        self.query_info = query_info
        self.subquery_aliases = {}

    def get_aliases(self, subquery_type, entry_id, table_type=None):
        """
        Returns all aliases specified as a list of dicts with table_type, alias, and may also
        include parent_alias or m2m_alias
        """
        reference = self.subquery_aliases.get(subquery_type, {}).get(entry_id, {})
        response = []
        for table_name, entry in reference.items():
            if table_type is None or entry["table_type"] == table_type:
                response.append(entry)
        return response

    def get_collection_alias(self, subquery_type, entry_id, oCollection, include_m2m=False):
        """
        Subqueries use aliases, but that alias must be shared for the whole subquery. This creates
        a table alias, but also tracks which aliases have already been created and returns existing
        when available.

        Returns a table alias if the concept is 1:many with subject. If many:many with subject,
        returns a tuple with collection alias and m2m join table alias.
        """
        table, m2m_table = self.query_info.get_sql_alchemy_table_for_collection(
            oCollection, include_m2m=True
        )
        # store alias if not already stored
        if subquery_type not in self.subquery_aliases:
            self.subquery_aliases[subquery_type] = {}
        if entry_id not in self.subquery_aliases[subquery_type]:
            self.subquery_aliases[subquery_type][entry_id] = {}
        if table.name not in self.subquery_aliases[subquery_type][entry_id]:
            m2m_alias = m2m_table.alias() if m2m_table is not None else None
            value = {
                "table_type": "collection",
                "alias": table.alias(),
                "m2m_alias": m2m_alias,
            }
            self.subquery_aliases[subquery_type][entry_id][table.name] = value
        # get the alias and return
        reference = self.subquery_aliases[subquery_type][entry_id][table.name]
        if include_m2m:
            return (reference["alias"], reference["m2m_alias"])
        return reference["alias"]

    def get_concept_alias(self, subquery_type, entry_id, oConcept, include_parent=False):
        """
        Subqueries use aliases, but that alias must be shared for the whole subquery. This creates
        a table alias, but also tracks which aliases have already been created and returns existing
        when available.

        Returns a table alias if the concept is in the collection table. If the concept is in
        a separate lookup table, returns a tuple with the lookup table alias and the collection
        table alias.
        """
        # if no lookup table, can just return the collection alias
        concept_table = self.query_info.get_sql_alchemy_table_for_concept(oConcept)
        collection_table = self.query_info.get_sql_alchemy_table_for_collection(
            oConcept.collection
        )
        collection_alias = self.get_collection_alias(subquery_type, entry_id, oConcept.collection)
        # store the lookup table alias if not already stored
        if concept_table == collection_table:
            if include_parent:
                return (collection_alias, None)
            return collection_alias
        if subquery_type not in self.subquery_aliases:
            self.subquery_aliases[subquery_type] = {}
        if entry_id not in self.subquery_aliases[subquery_type]:
            self.subquery_aliases[subquery_type][entry_id] = {}
        if concept_table.name not in self.subquery_aliases[subquery_type][entry_id]:
            # store as tuple
            self.subquery_aliases[subquery_type][entry_id][concept_table.name] = (
                concept_table.alias(),
                collection_alias,
            )
            self.subquery_aliases[subquery_type][entry_id][concept_table.name] = {
                "table_type": "lookup",
                "alias": concept_table.alias(),
                "parent_alias": collection_alias,
            }
        # get the alias and return
        reference = self.subquery_aliases[subquery_type][entry_id][concept_table.name]
        if include_parent:
            return (reference["alias"], reference["parent_alias"])
        return reference["alias"]

    def add_custom_from_statement(self, statement, subquery_type, entry_id):
        """Automatically generates a FROM statement based on created aliases.

        Uses all aliases created for this subquery_type and entry_id to build a FROM statement.
        The changes get applied to the provided SQL alchemy statment and returned as a
        modified SQL alchemy statement.

        :param statement: The SQL alchemy statement to apply the changes to
        :param str subquery_type:
        :param str entry_id:
        :return: a new SQL alchemy statement
        """
        collection_aliases = self.get_aliases(subquery_type, entry_id, table_type="collection")
        # TODO: situations where there is more than 1 table in the subquery
        statement = statement.select_from(collection_aliases[0]["alias"])
        lookup_aliases = self.get_aliases(subquery_type, entry_id, table_type="lookup")
        for entry in lookup_aliases:
            lookup_alias = entry["alias"]
            collection_alias = entry["parent_alias"]
            statement = statement.outerjoin(
                lookup_alias, collection_alias.c._id == lookup_alias.c._collection_id
            )
        return statement

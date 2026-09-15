from chiron.query_engine.postgres.sql_alchemy_queries import AbstractSqlAlchemyPartBuilder


class FromStatementBuilder(AbstractSqlAlchemyPartBuilder):
    def modify_statement(self, statement):
        subject_table = self.query_info.get_sql_alchemy_table_for_subject()
        core_collections = self.query_info.get_core_collections()
        core_lookup_tables = self.query_info.get_core_lookup_tables()
        statement = statement.select_from(subject_table)
        added_collections = []
        added_lookups = []
        for oCollection in core_collections:
            table = self.query_info.get_sql_alchemy_table_for_collection(oCollection)
            if not oCollection.is_root_collection:
                statement, added_lookups = self._join_collection_table_to_statement(
                    statement, oCollection, added_collections, added_lookups
                )
            for lookup_table in core_lookup_tables[oCollection.permanent_id]:
                if lookup_table not in added_lookups:
                    statement = statement.outerjoin(
                        lookup_table, table.c._id == lookup_table.c._collection_id
                    )
                    added_lookups.append(lookup_table)
            added_collections.append(oCollection)
        return statement

    def _join_collection_table_to_statement(
        self, statement, oCollection, added_collections, added_lookups
    ):
        """
        checks if this can join to an existing collection using subcol relationships instead
        of joining to subject. If yes, will go ahead and do it. returns:
        - new statement
        - True if it added the collection
        - a list of any lookup tables it also added
        """
        is_longitudinal = self.query_info.check_collection_in_longitudinal_combo(oCollection)
        if is_longitudinal:
            # do a simple join by subject_id to the subject table
            statement = self._join_collection_table_by_subject_id(statement, oCollection)
            return statement, added_lookups
        oRel = self.query_info.find_subcollection_relationship_from_list(
            oCollection, added_collections
        )
        if not oRel:
            # do a simple join by subject_id to the subject table
            statement = self._join_collection_table_by_subject_id(statement, oCollection)
            return statement, added_lookups
        fk_table = self.query_info.get_sql_alchemy_table_for_concept(oRel.fk_concept)
        fk_collection_table = self.query_info.get_sql_alchemy_table_for_collection(
            oRel.fk_concept.collection
        )
        pk_table = self.query_info.get_sql_alchemy_table_for_collection(oRel.pk_concept.collection)
        pk_field = getattr(pk_table.c, oRel.pk_concept.permanent_id)
        fk_field = getattr(fk_table.c, oRel.fk_concept.permanent_id)
        if oRel.get_pk_collection() == oCollection:
            if fk_table != fk_collection_table:
                # SITUATION 1: already added table is FK and FK field is in a lookup table
                # join fk lookup table to fk collection
                if fk_table not in added_lookups:
                    statement = statement.outerjoin(
                        fk_table, fk_collection_table.c._id == fk_table.c._collection_id
                    )
                    added_lookups.append(fk_table)
                # now join the new collection table to the fk lookup table
                statement = statement.outerjoin(pk_table, pk_field == fk_field)
            else:
                # SITUATION 2: already added table is FK, no lookup table involved
                statement = statement.outerjoin(pk_table, pk_field == fk_field)
        else:
            if fk_table != fk_collection_table:
                # SITUATION 3: already added table is PK and FK field is in a lookup table
                # join fk lookup table to pk collection
                statement = statement.outerjoin(fk_table, fk_field == pk_field)
                added_lookups.append(fk_table)
                # now join the new collection table to its lookup table
                statement = statement.outerjoin(
                    fk_collection_table, fk_collection_table.c._id == fk_table.c._collection_id
                )
            else:
                # SITUATION 4: already added table is PK, no lookup table involved
                statement = statement.outerjoin(fk_table, fk_field == pk_field)
        return statement, added_lookups

    def _join_collection_table_by_subject_id(self, statement, oCollection):
        subject_table = self.query_info.get_sql_alchemy_table_for_subject()
        table, m2m_table = self.query_info.get_sql_alchemy_table_for_collection(
            oCollection, include_m2m=True
        )
        if oCollection.many_to_many_with_subject:
            statement = statement.outerjoin(
                m2m_table, subject_table.c._id == m2m_table.c._subject_id
            )
            statement = statement.outerjoin(table, m2m_table.c._collection_id == table.c._id)
        else:
            statement = statement.outerjoin(table, subject_table.c._id == table.c._subject_id)
        return statement

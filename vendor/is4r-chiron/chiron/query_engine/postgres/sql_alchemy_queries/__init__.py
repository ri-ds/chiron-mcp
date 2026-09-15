from abc import ABC, abstractmethod


class AbstractSqlAlchemyPartBuilder(ABC):
    def __init__(
        self, chironuser, cohort, table, characterize_query, alias_manager, prefilters=None
    ):
        self.chironuser = chironuser
        self.dataset = chironuser.dataset
        self.cohort = cohort
        self.table = table
        self.query_info = characterize_query
        self.alias_manager = alias_manager
        self.prefilters = prefilters if prefilters else {}

    @abstractmethod
    def modify_statement(self, statement):
        raise NotImplementedError("Abstract method has not been implemented")

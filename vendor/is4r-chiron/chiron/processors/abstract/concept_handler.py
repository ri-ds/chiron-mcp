from abc import ABCMeta, abstractmethod


class ConceptHandler:
    """
    There are three types of processors used on concepts: ETL, Cohort Def and Display. These
    work in coordination with each other. The ConceptHandler is a logical combination of the
    three along with any appropriate customization settings.
    """

    __metaclass__ = ABCMeta

    def __init__(
        self, chironuser, dataset, concept, prefilter_value=None, source_processor=None, **kwargs
    ):
        self.chironuser = chironuser
        self.dataset = dataset
        self.concept = concept
        self.prefilter_value = prefilter_value
        self.set_kwarg_options()
        self.handler_args = kwargs
        # preset the source processor to save time
        self.source_processor = source_processor

    def get_stored_data_type(self):
        """Returns the data type that will be stored in the database for this value.

        Options are: "text", "integer", "float", "date", "boolean" and ("varchar", n) where n is
        the maximum string length. There are also complex data structures that combine 2 or
        more standard data types. For example, an ID string with an associated hyperlink could
        be stored as data type {"val": ("varchar", 20), "link": "text"}

        :return: Simple data type as string/tuple, or complex data type as dict
        :rtype: string, tuple, or dict (default="text")
        """
        return "text"

    @abstractmethod
    def set_kwarg_options(self):
        raise NotImplementedError("ConceptHandlers require the set_kwarg_options method")

    @abstractmethod
    def set_etl_processor(self, concept):
        """Creates a valid ETL processor and stores it in self.etl_processor."""
        raise NotImplementedError("ConceptHandlers require the set_etl_processor method")

    def get_etl_processor(self):
        """Returns the ETL processor for this concept handler."""
        if hasattr(self, "etl_processor"):
            return self.etl_processor
        self.set_etl_processor(self.concept)
        return self.etl_processor

    @abstractmethod
    def set_cohort_def_processor(self, chironuser, dataset, concept, prefilter_value):
        """Creates a valid cohort def processor and stores it in self.cohort_def_processor."""
        raise NotImplementedError("ConceptHandlers require the set_cohort_def_processor method")

    def get_cohort_def_processor(self):
        """Returns the cohort def processor for this concept handler."""
        if hasattr(self, "cohort_def_processor"):
            return self.cohort_def_processor
        self.set_cohort_def_processor(
            self.chironuser, self.dataset, self.concept, self.prefilter_value
        )
        return self.cohort_def_processor

    @abstractmethod
    def set_display_processor(self, chironuser, concept):
        """Creates a valid display processor and stores it in self.display_processor."""
        raise NotImplementedError("ConceptHandlers require the set_display_processor method")

    def get_display_processor(self):
        """Returns the display processor for this concept handler."""
        if hasattr(self, "display_processor"):
            return self.display_processor
        self.set_display_processor(self.chironuser, self.concept)
        return self.display_processor

    def set_deid_cohort_def_processor(self, chironuser, dataset, concept, prefilter_value):
        """Creates deid cohort def processor and stores it in self.deid_cohort_def_processor.

        Optionally define an alternative cohort def processor that can hide PHI.
        ex. a date processor that only allows you to view/query data by year
        """
        self.deid_cohort_def_processor = None

    def get_deid_cohort_def_processor(self):
        """Returns the deidentified cohort def processor for this concept handler."""
        if hasattr(self, "deid_cohort_def_processor"):
            return self.deid_cohort_def_processor
        self.set_deid_cohort_def_processor(
            self.chironuser, self.dataset, self.concept, self.prefilter_value
        )
        return self.deid_cohort_def_processor

    def set_deid_display_processor(self, chironuser, concept):
        """Creates deid display processor and stores it in self.deid_display_processor.

        Optionally define an alternative display processor that can hide PHI.
        ex. a date processor that always converts a date to year before displaying
        """
        self.deid_display_processor = None

    def get_deid_display_processor(self):
        """Returns the deidentified display processor for this concept handler."""
        if hasattr(self, "deid_display_processor"):
            return self.deid_display_processor
        self.set_deid_display_processor(self.chironuser, self.concept)
        return self.deid_display_processor

    def check_source_format(self):
        """
        Get a description from the source processor about what sort of iterable it generates.
        This can be useful for different handling for different types of iterators (queryset,
        list of dicts, etc.)
        """
        # instantiated source_processor may be provided to save time
        if self.source_processor:
            return self.source_processor.check_source_format()
        return self.concept.source.check_source_format()

    def append_handler_arg_option(
        self,
        name,
        description="",
        default_value=None,
        required=True,
    ):
        entry = {
            "description": description,
            "default": default_value,
            "required": required,
        }
        if not hasattr(self, "handler_arg_options"):
            self.handler_arg_options = {}
        self.handler_arg_options[name] = entry

    def remove_handler_arg_option(self, name):
        if name in self.handler_arg_options:
            del self.handler_arg_options[name]

    def get_handler_arg_value(self, name):
        if name in self.handler_args:
            return self.handler_args[name]
        if name in self.handler_arg_options:
            return self.handler_arg_options[name]["default"]
        raise ValueError("Field {} is not an option for this concept handler".format(name))

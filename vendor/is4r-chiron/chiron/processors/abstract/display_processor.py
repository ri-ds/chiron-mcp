from abc import ABCMeta


from chiron.processors.display import aggregation
from chiron.processors.sort_functions import sort_keygen_generic
from chiron.processors.display_functions import display_generic
from chiron import helpers


class DisplayProcessor:
    """
    Manages how a concept is incorporated into output datasets. It is associated with a concept in
    the data dictionary using the ``Concept.display_processor`` field.

    IMPORTANT METHOD WORKFLOWS:

    Creating a Table Def Entry:

    - set_aggregation_method() - sets a list of aggregation objects that can be applied to this
      concept
    - get_form_options() - data needed to display a table def entry form
    - validate_form() - checks if a form submission is valid
    - generate_table_def_entry() - converts form submission into a dict to be added to cohort def

    Applying a Table Def Entry to a Results Set:

    - get_header_display_value() - the label for this column in the results output
    - get_individual_display_value() - how to convert the stored concept value into a string
    - get_display_value3() - how to convert the database output value into a string
    """

    __metaclass__ = ABCMeta

    def __init__(self, chironuser, oConcept, **kwargs):
        self.chironuser = chironuser
        self.concept = oConcept
        self.td_entry = None  # some methods require td_entry to be set (use set_td_entry())
        self.args = {}
        self.cleaned = {}
        for key, value in kwargs.items():
            self.args[key] = value
        self.warnings = []
        self.errors = []
        self.set_aggregation_methods()
        self.set_sort_keygen_function()
        self.set_display_function()
        self.output_type = "html"
        self.map_settings = None  # settings for mapping values coming from database to different
        # values. Set this using get_map_settings(). Only run when needed
        # because it can take time.

    def set_sort_keygen_function(self):
        """
        Sets the default function that will be used to generate key for sorting. The key will take
        an input value and return the value to use for sorting.
        """
        self.sort_keygen_function = sort_keygen_generic

    def set_display_function(self):
        """
        Sets the default function that will be used to display a value in final results.
        """
        self.display_function = display_generic

    def set_aggregation_methods(self):
        """
        Sets a list of AggregationMethod objects that can be applied to this concept. This is
        automatically called by the init method.
        """
        self.aggregation_methods = [
            aggregation.ListDistinct(),
            aggregation.CountDistinct(),
            aggregation.ListAll(),
            aggregation.CountAll(),
            aggregation.MostFrequent(),
        ]
        # if collection for this concept is an event, we can get earliest and most recent
        if self.concept.collection.event_date_field:
            self.aggregation_methods.append(aggregation.Latest())
            self.aggregation_methods.append(aggregation.Earliest())

    def use_subvalue(self, td_entry):
        """Should a subvalue be used for this table def entry.

        Complex concepts can have 1 or more subvalues. If a subvalue should be queried in place
        of the normal concept value, returns the name of the subvalue, otherwise returns None.
        """
        return None

    def set_td_entry(self, td_entry):
        self.td_entry = td_entry

    def get_default_aggregation_settings(self):
        if self.concept.collection.is_root_collection:
            aggregate = False
            aggregation_method = None  # stack
        else:
            aggregate = True
            aggregation_method = "list_distinct"
        return {
            "aggregate": aggregate,
            "aggregation_method": aggregation_method,
        }

    def get_form_options(self, table_def):
        """
        Returns a list of options for customizing a table_def_entry
        """
        if self.td_entry is None:
            raise AttributeError("the table def entry for the processor is not set")
        aggregation_method = self.td_entry.get("aggregation_method") if self.td_entry else None
        options = []
        for agg_option in self.aggregation_methods:
            # print(agg_option)
            options.append(
                {
                    "id": agg_option.id,
                    "group": agg_option.group,
                    "label": agg_option.label,
                    "selected": aggregation_method == agg_option.id,
                    "inputs": agg_option.get_inputs(self.chironuser, self.td_entry),
                }
            )
        response = {
            "aggregation_options": options,
        }
        return response

    def validate_form(self, form_data):
        """
        If provided form validates, returns True and populates self.cleaned dict with any data
        needed to generate a table def entry. If validation fails, returns False and adds
        error message strings to self.errors list.

        :param form_data: the HTTP POST arguments from the client
        :type form_data: dict
        :return: whether form validated
        :rtype: boolean
        """
        self.cleaned = {}
        for key, value in form_data.items():
            self.cleaned[key] = value
        # get the custom settings (this stuff should be done in the processor)
        aggregation_method = form_data.get(
            "aggregation_method", self.get_default_aggregation_settings()["aggregation_method"]
        )
        # stack isn't an aggregation method, it is an aggregation style
        if not aggregation_method or aggregation_method == "stack":
            self.cleaned["aggregate"] = False
            self.cleaned["aggregation_method"] = None
            self.cleaned["aggregation_criteria_set"] = None
        else:
            self.cleaned["aggregate"] = True
            self.cleaned["aggregation_method"] = aggregation_method
        return True

    def generate_table_def_entry(self):
        """
        Returns the table_def entry definition for this column
        NOTE: This should typically be run after validate_table_form has successfully run.
        Otherwise, it will just generate a default entry with no customization.

        :return: the table def entry
        :rtype: dict
        """
        td_entry = self._generate_td_entry_template()
        settings = self.cleaned if hasattr(self, "cleaned") else {}
        if not settings:
            settings = self.get_default_aggregation_settings()
        if settings.get("entry_alias"):
            td_entry["alias"] = settings["entry_alias"]
        td_entry["aggregate"] = settings["aggregate"]
        td_entry["aggregation_method"] = settings["aggregation_method"]
        if settings.get("aggregation_criteria_set"):
            td_entry["aggregation_criteria_set"] = settings["aggregation_criteria_set"]
        if td_entry["aggregate"] and td_entry["aggregation_method"]:
            agg_option = self._get_agg_option_by_id(td_entry["aggregation_method"])
            if agg_option:
                aggregation_settings = agg_option.set_custom_settings(self.cleaned)
                if aggregation_settings:
                    td_entry["aggregation_settings"] = aggregation_settings
        return td_entry

    def get_sort_key_function(self, column_index, reverse):
        """
        Returns a function that will be used by Python for sorting. The input data type can change
        depending on whether any categorization or aggregation was applied, so that needs to be
        taken into account.

        This method can be complex but the function it returns should be simple because it will
        be run repeatedly.
        """
        # if aggregated, let the aggregation method do the sorting
        if self.td_entry and self.td_entry.get("aggregate", False):
            aggregation_method_id = self.td_entry.get(
                "aggregation_method", self.get_default_aggregation_settings()["aggregation_method"]
            )
            aggregation_obj = self._get_agg_option_by_id(aggregation_method_id)
            aggregation_settings = self.td_entry.get("aggregation_settings", {})
            return aggregation_obj.get_sort_key_function(
                self.sort_keygen_function, column_index, reverse, aggregation_settings
            )
        # if mapped, set the sort function based on mapping
        if self.map_settings is not None:
            sort_func = self.map_settings["sort_function"]
        else:  # or just set the standard sort function
            sort_func = self.sort_keygen_function
        # need to wrap get_sort_value with dict column selector
        return lambda x: sort_func(x[column_index])

    def get_header_display_value(self, prepend_value=""):
        """
        Returns a display name for the column
        """
        if self.td_entry is None:
            raise AttributeError("the table def entry for the processor is not set")
        prefix = ""
        if self.td_entry.get("aggregate"):
            aggregation_method_id = self.td_entry.get(
                "aggregation_method", self.get_default_aggregation_settings()["aggregation_method"]
            )
            aggregation = self._get_agg_option_by_id(aggregation_method_id)
            header = aggregation.get_header_display_value(self.concept, self.td_entry)
            if prepend_value:
                header = "[{}] {}".format(prepend_value, header)
            return header
        if prefix:
            return "{} {}".format(prefix, self.concept.name)
        return self.concept.name

    def get_display_value3(self, value, output_type):
        # TODO: should I check if td_entry is set here, or will that degrade performance?
        if output_type in ["python", "json"] and value is None:
            return None
        if value is None:
            return ""
        if isinstance(value, tuple):
            value = dict(value)
        if self.td_entry.get("aggregate"):
            aggregation_method_id = self.td_entry.get(
                "aggregation_method", self.get_default_aggregation_settings()["aggregation_method"]
            )
            aggregation = self._get_agg_option_by_id(aggregation_method_id)
            return aggregation.get_display_value3(
                self.td_entry, value, self.display_function, output_type
            )
        if self.map_settings:
            display_func = self.map_settings["display_function"]
            return display_func(value, output_type)
        return self.display_function(value, output_type)

    def sql_alchemy_map_in_query(self, column):
        """Map existing values to new values during a SQL alchemy query.

        If stored value needs to be converted to a different value (ex. round date to decade),
        this can define the Postgres function(s) for doing that.
        """
        return column

    def sql_alchemy_map_after_query(self, value):
        """Conversion of mapped SQL alchemy values to a final query result.

        Takes the output resulting fom sql_alchemy_map_in_query() and converts it to a final
        query result. For example, if you rounded dates to the decade, you might want to convert
        that to a category string (1960 -> "1960s", 1970 -> "1970s"). This behavior could
        technically be handled fully in Postgres using a "CASE WHEN" statement, but that won't
        always be the most performant approach. The output of this will still get processed by
        get_display_value() as the final, final step.
        """
        return value

    def map_to_value(self, value):
        """
        If value from database needs to be converted to a different value (ex. date to year or
        number to category), that mapping is done here.

        This changes the actual value that gets used to build the report, which can affect
        grouping. If you just want to change how the value is displayed, use get_display_value().
        """
        return value

    def get_map_settings(self):
        """
        Settings for how map_to_value() will work. This can change the value type, so these
        settings may also affect which sort function and display function to use.
        """
        if self.map_settings is not None:
            return self.map_settings
        self.map_settings = {}
        return self.map_settings

    def calculate_aggregate_value(self, value):
        # might want a check to see if this is array, that the field should be aggregated,
        # that self.td_entry is set, etc.
        # or don't bother checking for better performance
        aggregation_method_id = self.td_entry.get(
            "aggregation_method", self.get_default_aggregation_settings()["aggregation_method"]
        )
        aggregation = self._get_agg_option_by_id(aggregation_method_id)
        return aggregation.calculate_agg_value(self.td_entry, value, self.sort_keygen_function)

    def get_data_type(self):
        """
        Returns a human-readable string describing the data type (text, integer, etc.).
        This is used to generate a data dictionary.
        """
        return ""

    def check_requires_event_dates(self):
        aggregation_method = self.td_entry.get(
            "aggregation_method", self.get_default_aggregation_settings()["aggregation_method"]
        )
        if aggregation_method is None or aggregation_method == "stack":
            return False
        aggregation = self._get_agg_option_by_id(aggregation_method)
        return aggregation.check_requires_event_dates(self.td_entry)

    def _get_agg_option_by_id(self, id):
        return next((item for item in self.aggregation_methods if item.id == id), None)

    def _generate_td_entry_template(self, additional_args=None):
        """
        Generates a universal base that can be used by self.generate_cohort_def_entry()

        :param additional_args: concept-specific values to include in cd_entry
        :type additional_args: dict
        :return: a cd_entry with concept_id and entry_id set
        :rtype: dict
        """
        # Build Table Definition entry template
        response = {
            "entry_id": helpers.generate_entry_id(),
            "concept_id": self.concept.permanent_id,
        }
        # Add additional arguments to template if applicable
        if additional_args:
            response.update(additional_args)
        # Return template
        return response

from abc import ABCMeta, abstractmethod
import datetime
import copy


class AggregationMethod:
    """
    Has methods needed to aggregate a concept in the final output table.

    Subclasses need to set an id, label, and group property in their __init__ method.
    """

    __metaclass__ = ABCMeta

    def __init__(self, id, label, group):
        """
        The init method needs to set an id, label, and group value. Most subclasses will want
        to override the init method with one that sets sensible defaults. ex:

        def __init__(self, id="max", label="maximum value", group="aggregate"):
            super().__init__(id, label, group)

        :param id: a unique identifier for this aggregation method
        :type id: string
        :param label: the human-readable label for this aggregation method
        :type id: string
        :param group: a group name that can be used to organize aggregation methods in the UI
        :type group: string
        """
        self.id = id
        self.label = label
        self.group = group

    def get_inputs(self, chironuser, td_entry):
        """
        returns a list of dicts that define custom settings for this aggregation option

        :id: (str) a unique id to identify this input
        :label: (str) the human-readable label for this input
        :type: (str) "select" for HTML select and "ajax_select" for select tool that must lookup
          options
        :options: (list of tuples) for type="select"; id/value pairs for options
        :options_callback: (str) for type="ajax_select"; the url where options can be looked up
        :selected: (str) value that should be selected by default
        """
        return []

    def set_custom_settings(self, input_data):
        """
        takes an input_data dict from post request and returns a dict of values that will be saved
        to the table def entry
        """
        return {}

    def check_requires_event_dates(self, td_entry):
        """
        Does this aggregation option require the event date(s) from the parent collection?
        """
        return False

    @abstractmethod
    def get_header_display_value(self, oConcept, td_entry):
        """
        Returns a header label for this aggregated column.

        :param oConcept: the concept being aggregated
        :type oConcept: model object
        :param td_entry: the column definition
        :type td_entry: dict
        :return: header label
        :rtype: string
        """
        raise NotImplementedError(
            "This AggregationMethod doesn't define a get_header_display_value method."
        )

    def get_display_value3(self, td_entry, value, default_value_method, output_type):
        """
        convert the calculated aggregate value to the final display value
        """
        return str(value)

    @abstractmethod
    def calculate_agg_value(self, td_entry, value, display_processor_sort_value_func=None):
        """Converts the database query output into a final aggregated value.

        :param td_entry: (dict) the definition for this aggregated table column
        :param value: (various) the "value" for this column in this record as it comes from the
          database query, usually will be a list that can be used to calculated a final aggregated
          value
        :param display_processor_sort_value_func:
        :return:
        """
        raise NotImplementedError(
            "This AggregationMethod doesn't define a calculate_agg_value method."
        )

    def _date_to_string(self, value):
        """
        Utility function that converts a date to a string.
        """
        return str(value)[:10]

    def get_sort_key(self, value):
        """
        Returns the value from the report that will be used for sorting. By default, this is the
        column value itself.
        """
        return value[self.column_index]

    def get_sort_key_date(self, value):
        """
        This can be used to sort date values
        """
        val = value[self.column_index]
        if val is None:
            return datetime.datetime(datetime.MINYEAR, 1, 1)
        return val

    def get_sort_key_function(
        self, display_processor_sort_value_func, column_index, reverse, aggregation_settings
    ):
        """
        Returns the function that will be used for sorting the report. The column_index gives
        which report column this field is in.

        :param display_processor_sort_value_func: The function that would normally be used to
          sort the non-aggregated value.
        :type display_processor_sort_value_func: python function
        :param column_index: The index position of this column in the report
        :type column_index: integer
        :param reverse: In some instances, sort key might work differently if reverse sorting
        :type reverse: boolean
        :param aggregation_settings: Any settings included in the td_entry
        :type aggregation_settings: python dict
        """
        self.column_index = column_index
        self.display_processor_sort_value_func = display_processor_sort_value_func
        self.reverse = reverse
        self.aggregation_settings = aggregation_settings
        return self.get_sort_key

    def _get_value_list_no_nulls(self, concept_id, value):
        value = [x[concept_id] for x in value if x.get(concept_id) is not None]
        return value

    def _get_value_list(self, concept_id, value):
        value = [x.get(concept_id, None) for x in value]
        return value

    def _remove_records_with_null_values(self, concept_id, value):
        value = [x for x in value if x.get(concept_id) is not None]
        return value

    def _get_event_list(self, concept_id, event_date_field, value):
        """
        The query process can end up duplicating collection records. This uses the _id to
        remove duplicate records.
        """
        value = [
            (x[event_date_field], x.get(concept_id))
            for x in value
            if x.get(event_date_field) is not None
        ]
        return value

    def _get_event_list_no_nulls(self, concept_id, event_date_field, value):
        """
        The query process can end up duplicating collection records. This uses the _id to
        remove duplicate records.
        """
        value = [
            (x[event_date_field], x.get(concept_id))
            for x in value
            if x.get(event_date_field) is not None and x.get(concept_id) is not None
        ]
        return value

    def _get_ordinal_string(self, n):
        """
        Convert an integer into its ordinal representation::

            make_ordinal(0)   => '0th'
            make_ordinal(3)   => '3rd'
            make_ordinal(122) => '122nd'
            make_ordinal(213) => '213th'
        """
        n = int(n)
        suffix = ["th", "st", "nd", "rd", "th"][min(n % 10, 4)]
        if 11 <= (n % 100) <= 13:
            suffix = "th"
        return str(n) + suffix

    def _merge_duplicates_for_different_subjects(self, concept_id, value):
        """
        For subcollections that are m:m with subject, might have duplicate subcollection records
        with different _subject_id values. This will remove _subject_id and merge any
        duplicates found.
        """
        new_value = []
        for in_entry in value:
            if not in_entry:
                continue
            out_entry = copy.copy(in_entry)
            del out_entry["_subject_id"]
            if out_entry not in new_value:
                new_value.append(out_entry)
        return new_value

    def flatten_postgres_json_agg_result_values_only(self, value):
        if isinstance(value, list) and len(value) == 1 and value[0] is None:
            return None
        if value and isinstance(value[0], list):
            flat_list = []  # use a dict for faster lookup
            for sublist in value:
                if sublist:
                    for item in sublist:
                        if item is not None:
                            flat_list.append(item)
            value = list(set(flat_list))
        return value

    def flatten_postgres_json_agg_result_with_ids(self, value, remove_nulls=False):
        if isinstance(value, list) and len(value) == 1 and value[0] is None:
            return None
        if value and isinstance(value[0], list):
            added_ids = {}
            for sublist in value:
                if sublist:
                    for item in sublist:
                        if item is not None and item["f1"] not in added_ids:
                            added_ids[item["f1"]] = item
            value = list(added_ids.values())
        if remove_nulls:
            value = [x for x in value if x["f2"] is not None]
        return value

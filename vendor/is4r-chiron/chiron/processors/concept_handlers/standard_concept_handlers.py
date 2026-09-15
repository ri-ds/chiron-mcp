from chiron.processors.abstract.concept_handler import ConceptHandler
from chiron.processors.etl.python_dict_item import EtlPythonDictItem
from chiron.processors.etl.django_field import EtlDjangoField
from chiron.processors.etl.django_multifield_merge import EtlDjangoMultifieldMerge
from chiron.processors.etl.detailed_age import EtlDjangoAgeInYearsToDays, EtlDictAgeInYearsToDays
from chiron.processors.cohort_def.detailed_age import CohortDefDetailedAge


from chiron.processors import (
    CohortDefText,
    CohortDefDateDeid,
    CohortDefBoolean,
    CohortDefDate,
    CohortDefNumber,
    CohortDefNumberWithCategories,
    CohortDefCategory,
)
from chiron.processors import (
    DisplayText,
    DisplayDate,
    DisplayBoolean,
    DisplayDateDeid,
    DisplayNumber,
    DisplayNumberWithCategories,
    DisplayCategory,
    DisplaySubjectHyperlink,
    DisplayDetailedAge,
)


class IntegerHandler(ConceptHandler):
    """
    Import and use an integer value.

    - Works with any source that returns an array of dicts.
    - If the input is not an integer, attempts to cast/round it to an integer
    - Any value that can't be cast/round to an integer will be stored as null.

    :param field_name: the key name of the integer field in the input dict
    :type field_name: str
    :param string_val_separator: if the input field can be a string with multiple values,
      what character(s) should the string be parsed on?
    :type string_val_separator: str, optional
    """

    display_name = "integer"

    def get_stored_data_type(self):
        return "integer"

    def set_kwarg_options(self):
        self.append_handler_arg_option("field_name", "the field name", required=True)
        desc = "a character used to separate multiple values in a single entry"
        self.append_handler_arg_option(
            "string_val_separator", desc, default_value=None, required=False
        )

        self.append_handler_arg_option(
            "number_is_year",
            "True for better handling of year values in things like histograms",
            default_value=False,
        )

    def _set_etl_processor_for_queryset(self, concept):
        """Querysets return model objects and require special handling"""
        field_name = self.get_handler_arg_value("field_name")
        if "," in field_name:
            processor_to_use = EtlDjangoMultifieldMerge
        else:
            processor_to_use = EtlDjangoField
        self.etl_processor = processor_to_use(
            concept,
            django_field=self.get_handler_arg_value("field_name"),
            cast_to_type="int",
            ignore_casting_errors=True,
        )

    def set_etl_processor(self, concept):
        # special handling for Django querysets, which return model objects instead of dicts
        if self.check_source_format() == "queryset":
            self._set_etl_processor_for_queryset(concept)
            return
        # otherwise, assume you're getting an iterable of dicts
        self.etl_processor = EtlPythonDictItem(
            concept,
            field_name=self.get_handler_arg_value("field_name"),
            cast_to_type="int",
            ignore_casting_errors=True,
            string_val_separator=self.get_handler_arg_value("string_val_separator"),
        )

    def set_cohort_def_processor(self, chironuser, dataset, concept, prefilter_value):
        self.cohort_def_processor = CohortDefNumber(
            chironuser,
            dataset,
            concept,
            prefilter_value=prefilter_value,
            is_integer=True,
            number_is_year=self.get_handler_arg_value("number_is_year"),
        )

    def set_display_processor(self, chironuser, concept):
        self.display_processor = DisplayNumber(chironuser, concept)


class FloatHandler(ConceptHandler):
    """
    Import and use a float value.

    - Works with any source that returns an array of dicts.
    - If the input is not a float, attempts to cast it to an float
    - Any value that can't be cast to a float will be stored as null.

    :param field_name: the key name of the float field in the input dict
    :type field_name: str
    :param string_val_separator: if the input field can be a string with multiple values,
      what character(s) should the string be parsed on?
    :type string_val_separator: str, optional
    """

    display_name = "floating point number"

    def get_stored_data_type(self):
        return "float"

    def set_kwarg_options(self):
        self.append_handler_arg_option("field_name", "the field name", required=True)
        desc = "a character used to separate multiple values in a single entry"
        self.append_handler_arg_option(
            "string_val_separator", desc, default_value=None, required=False
        )

    def _set_etl_processor_for_queryset(self, concept):
        """Querysets return model objects and require special handling"""
        field_name = self.get_handler_arg_value("field_name")
        if "," in field_name:
            processor_to_use = EtlDjangoMultifieldMerge
        else:
            processor_to_use = EtlDjangoField
        self.etl_processor = processor_to_use(
            concept,
            django_field=self.get_handler_arg_value("field_name"),
            cast_to_type="float",
            ignore_casting_errors=True,
        )

    def set_etl_processor(self, concept):
        # special handling for Django querysets, which return model objects instead of dicts
        if self.check_source_format() == "queryset":
            self._set_etl_processor_for_queryset(concept)
            return
        # otherwise, assume you're getting an iterable of dicts
        self.etl_processor = EtlPythonDictItem(
            concept,
            field_name=self.get_handler_arg_value("field_name"),
            cast_to_type="float",
            ignore_casting_errors=True,
            string_val_separator=self.get_handler_arg_value("string_val_separator"),
        )

    def set_cohort_def_processor(self, chironuser, dataset, concept, prefilter_value):
        self.cohort_def_processor = CohortDefNumber(
            chironuser, dataset, concept, prefilter_value=prefilter_value, is_integer=False
        )

    def set_display_processor(self, chironuser, concept):
        self.display_processor = DisplayNumber(chironuser, concept)


class IntegerWithCategoriesHandler(ConceptHandler):
    """
    Import and use an integer value that can also have text categories instead of integers.

    - Works with any source that returns an array of dicts.
    - If the input is not an integer, attempts to cast/round it to an integer.
    - Any non-empty string value that can't be cast/round to an integer will be treated as a
      category.
    - integers are stored internally as {"num": val, "val": val} and categories are stored
      as {"txt": val, "val": val}

    :param field_name: the key name of the integer field in the input dict
    :type field_name: str
    :param string_val_separator: if the input field can be a string with multiple values,
      what character(s) should the string be parsed on?
    :type string_val_separator: str, optional
    """

    display_name = "integer with categories"

    def get_stored_data_type(self):
        return {
            "val": "text",  # the value as a string
            "num": "integer",  # number if numeric, else None
            "txt": "text",  # value as a string if non-numeric, else None
        }

    def set_kwarg_options(self):
        self.append_handler_arg_option("field_name", "the field name", required=True)
        desc = "a character used to separate multiple values in a single entry"
        self.append_handler_arg_option(
            "string_val_separator", desc, default_value=None, required=False
        )

    def _set_etl_processor_for_queryset(self, concept):
        """Querysets return model objects and require special handling"""
        field_name = self.get_handler_arg_value("field_name")
        if "," in field_name:
            processor_to_use = EtlDjangoMultifieldMerge
        else:
            processor_to_use = EtlDjangoField
        self.etl_processor = processor_to_use(
            concept,
            django_field=self.get_handler_arg_value("field_name"),
            cast_to_type="integer/string",
            ignore_casting_errors=True,
        )

    def set_etl_processor(self, concept):
        # special handling for Django querysets, which return model objects instead of dicts
        if self.check_source_format() == "queryset":
            self._set_etl_processor_for_queryset(concept)
            return
        # otherwise, assume you're getting an iterable of dicts
        self.etl_processor = EtlPythonDictItem(
            concept,
            field_name=self.get_handler_arg_value("field_name"),
            cast_to_type="integer/string",
            ignore_casting_errors=True,
            string_val_separator=self.get_handler_arg_value("string_val_separator"),
        )

    def set_cohort_def_processor(self, chironuser, dataset, concept, prefilter_value):
        self.cohort_def_processor = CohortDefNumberWithCategories(
            chironuser, dataset, concept, prefilter_value=prefilter_value, is_integer=True
        )

    def set_display_processor(self, chironuser, concept):
        self.display_processor = DisplayNumberWithCategories(chironuser, concept)


class FloatWithCategoriesHandler(ConceptHandler):
    """
    Import and use a float value that can also have text categories instead of floats.

    - Works with any source that returns an array of dicts.
    - If the input is not a float, attempts to cast it to a float.
    - Any non-empty string value that can't be cast to a float will be treated as a
      category.
    - floats are stored internally as {"num": val, "val": val} and categories are stored
      as {"txt": val, "val": val}

    :param field_name: the key name of the float field in the input dict
    :type field_name: str
    :param string_val_separator: if the float field can be a string with multiple values,
      what character(s) should the string be parsed on?
    :type string_val_separator: str, optional
    """

    display_name = "floating point number with categories"

    def get_stored_data_type(self):
        return {
            "val": "text",  # the value as a string
            "num": "float",  # number if numeric, else None
            "txt": "text",  # value as a string if non-numeric, else None
        }

    def set_kwarg_options(self):
        self.append_handler_arg_option("field_name", "the field name", required=True)
        desc = "a character used to separate multiple values in a single entry"
        self.append_handler_arg_option(
            "string_val_separator", desc, default_value=None, required=False
        )

    def _set_etl_processor_for_queryset(self, concept):
        """Querysets return model objects and require special handling"""
        field_name = self.get_handler_arg_value("field_name")
        if "," in field_name:
            processor_to_use = EtlDjangoMultifieldMerge
        else:
            processor_to_use = EtlDjangoField
        self.etl_processor = processor_to_use(
            concept,
            django_field=self.get_handler_arg_value("field_name"),
            cast_to_type="float/string",
            ignore_casting_errors=True,
        )

    def set_etl_processor(self, concept):
        # special handling for Django querysets, which return model objects instead of dicts
        if self.check_source_format() == "queryset":
            self._set_etl_processor_for_queryset(concept)
            return
        # otherwise, assume you're getting an iterable of dicts
        self.etl_processor = EtlPythonDictItem(
            concept,
            field_name=self.get_handler_arg_value("field_name"),
            cast_to_type="float/string",
            ignore_casting_errors=True,
            string_val_separator=self.get_handler_arg_value("string_val_separator"),
        )

    def set_cohort_def_processor(self, chironuser, dataset, concept, prefilter_value):
        self.cohort_def_processor = CohortDefNumberWithCategories(
            chironuser, dataset, concept, prefilter_value=prefilter_value, is_integer=False
        )

    def set_display_processor(self, chironuser, concept):
        self.display_processor = DisplayNumberWithCategories(chironuser, concept)


class CategoryHandler(ConceptHandler):
    """
    Import and use a category value.

    - Works with any source that returns an array of dicts.
    - Categories are strings with a limited number of options. For fields that could have
      many different values (ex. ID or free text fields) use TextHandler instead.
    - Non-string values will be cast to a string.

    :param field_name: the key name of the float field in the input dict
    :type field_name: str
    :param string_val_separator: if the input field can be a string with multiple values,
      what character(s) should the string be parsed on?
    :type string_val_separator: str, optional
    """

    display_name = "category"

    def get_stored_data_type(self):
        return ("varchar", 255)

    def set_kwarg_options(self):
        self.append_handler_arg_option("field_name", "the field name", required=True)
        desc = "a character used to separate multiple values in a single entry"
        self.append_handler_arg_option(
            "string_val_separator", desc, default_value=None, required=False
        )

    def _set_etl_processor_for_queryset(self, concept):
        """Querysets return model objects and require special handling"""
        field_name = self.get_handler_arg_value("field_name")
        if "," in field_name:
            processor_to_use = EtlDjangoMultifieldMerge
        else:
            processor_to_use = EtlDjangoField
        self.etl_processor = processor_to_use(
            concept,
            django_field=self.get_handler_arg_value("field_name"),
            cast_to_type="varchar255",
        )

    def set_etl_processor(self, concept):
        # special handling for Django querysets, which return model objects instead of dicts
        if self.check_source_format() == "queryset":
            self._set_etl_processor_for_queryset(concept)
            return
        # otherwise, assume you're getting an iterable of dicts
        self.etl_processor = EtlPythonDictItem(
            concept,
            field_name=self.get_handler_arg_value("field_name"),
            cast_to_type="varchar255",
            string_val_separator=self.get_handler_arg_value("string_val_separator"),
        )

    def set_cohort_def_processor(self, chironuser, dataset, concept, prefilter_value):
        self.cohort_def_processor = CohortDefCategory(
            chironuser, dataset, concept, prefilter_value=prefilter_value
        )

    def set_display_processor(self, chironuser, concept):
        self.display_processor = DisplayCategory(chironuser, concept)


class TextHandler(ConceptHandler):
    """
    Import and use a text value.

    - Works with any source that returns an array of dicts.
    - For text fields that are repetitive (ex. gender), consider using CategoryHandler
      instead.
    - Non-string values will be cast to a string.

    :param field_name: the key name of the float field in the input dict
    :type field_name: str
    :param string_val_separator: if the input field can be a string with multiple values,
      what character(s) should the string be parsed on?
    :type string_val_separator: str, optional
    """

    display_name = "text"

    def get_stored_data_type(self):
        return "text"

    def set_kwarg_options(self):
        self.append_handler_arg_option("field_name", "the field name", required=True)
        desc = "a character used to separate multiple values in a single entry"
        self.append_handler_arg_option(
            "string_val_separator", desc, default_value=None, required=False
        )

    def _set_etl_processor_for_queryset(self, concept):
        """Querysets return model objects and require special handling"""
        field_name = self.get_handler_arg_value("field_name")
        if "," in field_name:
            processor_to_use = EtlDjangoMultifieldMerge
        else:
            processor_to_use = EtlDjangoField
        self.etl_processor = processor_to_use(
            concept,
            django_field=self.get_handler_arg_value("field_name"),
            cast_to_type="string",
        )

    def set_etl_processor(self, concept):
        # special handling for Django querysets, which return model objects instead of dicts
        if self.check_source_format() == "queryset":
            self._set_etl_processor_for_queryset(concept)
            return
        # otherwise, assume you're getting an iterable of dicts
        self.etl_processor = EtlPythonDictItem(
            concept,
            field_name=self.get_handler_arg_value("field_name"),
            cast_to_type="string",
            string_val_separator=self.get_handler_arg_value("string_val_separator"),
        )

    def set_cohort_def_processor(self, chironuser, dataset, concept, prefilter_value):
        self.cohort_def_processor = CohortDefText(
            chironuser, dataset, concept, prefilter_value=prefilter_value
        )

    def set_display_processor(self, chironuser, concept):
        self.display_processor = DisplayText(chironuser, concept)


class SubjectHyperlinkHandler(TextHandler):
    """
    Import an ID that uniquely identifies a subject. In some contexts, this ID can be used
    as a hyperlink to go to subject details view.

    - Works with any source that returns an array of dicts.
    - Non-string values will be cast to a string.
    - Behavior is similar to TextHandler.

    :param field_name: the key name of the float field in the input dict
    :type field_name: str
    :param string_val_separator: if the input field can be a string with multiple values,
      what character(s) should the string be parsed on?
    :type string_val_separator: str, optional
    """

    display_name = "subject hyperlink"

    def get_stored_data_type(self):
        return {
            "val": ("varchar", 120),
            "link": "text",
        }

    def set_display_processor(self, chironuser, concept):
        self.display_processor = DisplaySubjectHyperlink(chironuser, concept)


class BooleanHandler(ConceptHandler):
    """
    Import and use a nullable boolean (true/false/null) value.

    - Works with any source that returns an array of dicts.
    - can handle a wide variety of string values (case insensitive)
        - converts to True: "true", "t", "yes", "y", "1"
        - converts to False: "false", "f", "no", "n", "0"
        - converts to None: "none", "null", "n/a", "unknown", ""
    - in any other situation, will use python casting to decide if value is truthy or falsy

    :param field_name: the key name of the float field in the input dict
    :type field_name: str
    """

    display_name = "true/false"

    def get_stored_data_type(self):
        return "boolean"

    def set_kwarg_options(self):
        self.append_handler_arg_option("field_name", "the field name", required=True)

    def _set_etl_processor_for_queryset(self, concept):
        """Querysets return model objects and require special handling"""
        field_name = self.get_handler_arg_value("field_name")
        if "," in field_name:
            processor_to_use = EtlDjangoMultifieldMerge
        else:
            processor_to_use = EtlDjangoField
        self.etl_processor = processor_to_use(
            concept,
            django_field=self.get_handler_arg_value("field_name"),
            cast_to_type="bool",
        )

    def set_etl_processor(self, concept):
        # special handling for Django querysets, which return model objects instead of dicts
        if self.check_source_format() == "queryset":
            self._set_etl_processor_for_queryset(concept)
            return
        # otherwise, assume you're getting an iterable of dicts
        self.etl_processor = EtlPythonDictItem(
            concept,
            field_name=self.get_handler_arg_value("field_name"),
            cast_to_type="bool",
        )

    def set_cohort_def_processor(self, chironuser, dataset, concept, prefilter_value):
        self.cohort_def_processor = CohortDefBoolean(
            chironuser, dataset, concept, prefilter_value=prefilter_value
        )

    def set_display_processor(self, chironuser, concept):
        self.display_processor = DisplayBoolean(chironuser, concept)


class DateHandler(ConceptHandler):
    """
    Import and use a date value.

    - Works with any source that returns an array of dicts.
    - If the input is a string, attempts to use `dateutil` library to parse to date.
    - Any value that can't be parsed to a date will be stored as null.
    - If the concept is flagged as PHI, users without PHI access will always see the year only.

    :param field_name: the key name of the date field in the input dict
    :type field_name: str
    :param string_val_separator: if the input field can be a string with multiple values, what
      character(s) should the string be parsed on?
    :type string_val_separator: str, optional
    """

    display_name = "date"

    def get_stored_data_type(self):
        return "date"

    def set_kwarg_options(self):
        self.append_handler_arg_option("field_name", "the field name", required=True)
        desc = "a character used to separate multiple values in a single entry"
        self.append_handler_arg_option(
            "string_val_separator", desc, default_value=None, required=False
        )

    def _set_etl_processor_for_queryset(self, concept):
        """Querysets return model objects and require special handling"""
        field_name = self.get_handler_arg_value("field_name")
        if "," in field_name:
            processor_to_use = EtlDjangoMultifieldMerge
        else:
            processor_to_use = EtlDjangoField
        self.etl_processor = processor_to_use(
            concept,
            django_field=self.get_handler_arg_value("field_name"),
            cast_to_type="date",
            ignore_casting_errors=True,
        )

    def set_etl_processor(self, concept):
        # special handling for Django querysets, which return model objects instead of dicts
        if self.check_source_format() == "queryset":
            self._set_etl_processor_for_queryset(concept)
            return
        # otherwise, assume you're getting an iterable of dicts
        self.etl_processor = EtlPythonDictItem(
            concept,
            field_name=self.get_handler_arg_value("field_name"),
            cast_to_type="date",
            ignore_casting_errors=True,
            string_val_separator=self.get_handler_arg_value("string_val_separator"),
        )

    def set_cohort_def_processor(self, chironuser, dataset, concept, prefilter_value):
        self.cohort_def_processor = CohortDefDate(
            chironuser, dataset, concept, prefilter_value=prefilter_value
        )

    def set_display_processor(self, chironuser, concept):
        self.display_processor = DisplayDate(chironuser, concept)

    def set_deid_cohort_def_processor(self, chironuser, dataset, concept, prefilter_value):
        self.deid_cohort_def_processor = CohortDefDateDeid(
            chironuser, dataset, concept, prefilter_value=prefilter_value
        )

    def set_deid_display_processor(self, chironuser, concept):
        self.deid_display_processor = DisplayDateDeid(chironuser, concept)


class DetailedAgeHandler(ConceptHandler):
    """
    Use to load age detailed age fields from a list of dicts.

    - Age should either be year float (where decimal portion is a fraction of the year) or age in
      days.
    - If you only have the year, you should load it as a regular integer instead.

    :field_name: (str) The field name for the date of birth
    :source_format: "age in days" (default) or "year float"
    """

    display_name = "detailed age"

    def get_stored_data_type(self):
        return "float"

    def set_kwarg_options(self):
        self.append_handler_arg_option("field_name", "the field name", required=True)
        desc = "Specify whether the source data is 'age in days' (default) or 'year float'"
        self.append_handler_arg_option(
            "source_format", desc, required=False, default_value="age in days"
        )

    def _set_etl_processor_for_queryset(self, concept):
        """Querysets return model objects and require special handling"""
        if self.get_handler_arg_value("source_format") == "age in days":
            self.etl_processor = EtlDjangoField(
                concept,
                django_field=self.get_handler_arg_value("field_name"),
                cast_to_type="float",
                ignore_casting_errors=True,
            )
        else:  # source_format == "year float"
            self.etl_processor = EtlDjangoAgeInYearsToDays(
                concept,
                django_field=self.get_handler_arg_value("field_name"),
            )

    def set_etl_processor(self, concept):
        # special handling for Django querysets, which return model objects instead of dicts
        if self.check_source_format() == "queryset":
            self._set_etl_processor_for_queryset(concept)
            return
        # otherwise, assume you're getting an iterable of dicts
        if self.get_handler_arg_value("source_format") == "age in days":
            self.etl_processor = EtlPythonDictItem(
                concept,
                field_name=self.get_handler_arg_value("field_name"),
                cast_to_type="float",
                ignore_casting_errors=True,
            )
        else:  # source_format == "year float"
            self.etl_processor = EtlDictAgeInYearsToDays(
                concept,
                field_name=self.get_handler_arg_value("field_name"),
            )

    def set_cohort_def_processor(self, chironuser, dataset, concept, prefilter_value):
        self.cohort_def_processor = CohortDefDetailedAge(
            chironuser, dataset, concept, prefilter_value=prefilter_value
        )

    def set_display_processor(self, chironuser, concept):
        self.display_processor = DisplayDetailedAge(chironuser, concept)


class CurrentAgeHandler(ConceptHandler):
    """
    Import an integer or float to get a deidentified current age.

    - Will convert to an age integer if stored as float or string
    - Any ages over 89 will be converted to a category "90 and above"
    - integers are stored internally as {"num": val, "val": val} and categories are stored
      as {"txt": val, "val": val}

    :param field_name: the key name of the integer field in the input dict
    :type field_name: str
    :param string_val_separator: if the input field can be a string with multiple values,
      what character(s) should the string be parsed on?
    :type string_val_separator: str, optional
    """

    display_name = "integer with categories"

    def get_stored_data_type(self):
        return {
            "val": "text",  # the value as a string
            "num": "integer",  # number if numeric, else None
            "txt": "text",  # value as a string if non-numeric, else None
        }

    def set_kwarg_options(self):
        self.append_handler_arg_option("field_name", "the field name", required=True)
        desc = "a character used to separate multiple values in a single entry"
        self.append_handler_arg_option(
            "string_val_separator", desc, default_value=None, required=False
        )

    def _set_etl_processor_for_queryset(self, concept):
        """Querysets return model objects and require special handling"""
        field_name = self.get_handler_arg_value("field_name")
        if "," in field_name:
            processor_to_use = EtlDjangoMultifieldMerge
        else:
            processor_to_use = EtlDjangoField
        self.etl_processor = processor_to_use(
            concept,
            django_field=self.get_handler_arg_value("field_name"),
            cast_to_type="current_age",
            ignore_casting_errors=True,
        )

    def set_etl_processor(self, concept):
        # special handling for Django querysets, which return model objects instead of dicts
        if self.check_source_format() == "queryset":
            self._set_etl_processor_for_queryset(concept)
            return
        # otherwise, assume you're getting an iterable of dicts
        self.etl_processor = EtlPythonDictItem(
            concept,
            field_name=self.get_handler_arg_value("field_name"),
            cast_to_type="current_age",
            ignore_casting_errors=True,
            string_val_separator=self.get_handler_arg_value("string_val_separator"),
        )

    def set_cohort_def_processor(self, chironuser, dataset, concept, prefilter_value):
        self.cohort_def_processor = CohortDefNumberWithCategories(
            chironuser, dataset, concept, prefilter_value=prefilter_value, is_integer=True
        )

    def set_display_processor(self, chironuser, concept):
        self.display_processor = DisplayNumberWithCategories(chironuser, concept)

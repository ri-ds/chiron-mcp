def convert_data_list_to_set(data_list):
    """
    UTILITY FUNCTION
    Returns only unique, non-null values from provided data_list.

    Chiron allows multiple values to be stored in a single concept entry as a list.
    This is useful when you have multiple values for a concept, but don't want
    to create a whole new Collection for that one concept. Typically it's better to store the
    unique set of values rather than a repetitive list.

    IN: ['Hispanic', 'Caucasian', 'Caucasian', None, 'Caucasian', None]
    OUT: ['Hispanic', 'Caucasian']

    IN: ['Caucasian', None]
    OUT: 'Caucasian'

    IN: ['Caucasian', 'Caucasian', 'Caucasian']
    OUT: 'Caucasian'

    IN: []
    OUT: None

    IN: [None, None, None, None]
    OUT: None

    """
    # remove nulls
    response = list(filter(None, data_list))
    # if there were no non-null values, return None
    if len(response) == 0:
        return None
    # remove duplicates
    response = list(set(response))

    if len(response) == 1:
        return response[0]
    return response


class ListOfDictsRetriever:
    def __init__(self, field_name, string_val_separator=None):
        self.field_name = field_name
        self.string_val_separator = string_val_separator

    def __call__(self, record):
        raw = record[self.field_name]
        if self.string_val_separator and isinstance(raw, str):
            raw = raw.split(self.string_val_separator)
        return raw


class DjangoModelObjectValueRetriever:
    """
    Retrieves a field from a model object, can follow joins and will return a list of values if
    any joins traversed are 1:many or many:many.

    ignore_model_mismatch: if True, error will be raised if Django field can't be found. If
      false, will return string "***missing***"
    """

    # maybe cast_to_type, ignore_casting_errors, data_cleaner
    def __init__(self, full_field_name, ignore_model_mismatch=False):
        if "." in full_field_name:
            # switched from dot separated to double underscore separated in Chiron 4
            full_field_path = full_field_name.split(".")
        else:
            full_field_path = full_field_name.split("__")
        self.django_field = full_field_path.pop()
        self.model_join_path = full_field_path
        self.ignore_model_mismatch = ignore_model_mismatch

    def __call__(self, oRecord):
        raw = self._get_record_data(oRecord)
        return raw

    def _lookup_relationships(self, records, path):
        """records - the queryset or list of model objects to start with
        path - the name of the next place to go, this could be 1:1 like
               'patient' or 1:many like 'visit_set'
        returns list of all model objects found after traversing the path
        """
        response = []
        for oRecord in records:
            # we're traversing a join to the next model on the model_join_path, sometime we'll get
            # back a queryset, sometimes will get back a single model object
            child_records = []
            try:
                # if 1:many or many:many, we can run the all() command to get the queryset
                child_records = list(getattr(oRecord, path).all())
            except AttributeError:
                # if that fails, that means we are getting a single model object
                child = getattr(oRecord, path, None)
                # If the relationship is not set for this record, could end up getting None or
                # the attr could be missing depending on the type of relationship. Either way,
                # it should be skipped.
                if child is not None:
                    child_records = [child]
            response += child_records
        return response

    def _get_record_data(self, oRecord):
        """
        Grabs the field value(s) from the record
        """
        # if the value is in this model, can just return it
        if not self.model_join_path:
            return getattr(oRecord, self.django_field, "***missing***")
        # if the value is in another model, need to do joins to get the value
        # 1:many joins will return querysets (multiple records), so we have to be prepared to
        # get multiple values back
        records = [oRecord]
        # traverse one model join at a time until we get to the model object or queryset where
        # the desired field is
        for path in self.model_join_path:
            if self.ignore_model_mismatch:
                try:
                    records = self._lookup_relationships(records, path)
                except AttributeError:
                    # indicates that data model doesn't match expected
                    return None
            else:
                records = self._lookup_relationships(records, path)
        if len(records) == 1:
            return getattr(records[0], self.django_field, "***missing***")
        # if there is more than one value (because we did joins), need to return the set of values
        fields = []
        for record in records:
            val = getattr(record, self.django_field, "***missing***")
            if val is not None:
                fields.append(val)
        return convert_data_list_to_set(fields)

import sys
import math
import copy
import json
import random
import string
from pathlib import Path
import os

from datetime import datetime

from chiron import chiron_settings
from chiron.models import Source


def print_query_info(*info_strings):
    """Prints the provided query info string to stdout when appropriate.

    Any useful debugging information about a query can be passed to this function, and
    the function will determine from context how to handle it. Currently it checks the
    CHIRON_GET_QUERY_PERFORMANCE setting and either prints to stdout or ignores.
    """
    if chiron_settings.CHIRON_GET_QUERY_PERFORMANCE:
        print(*info_strings)


def apply_min_limit(value, set_to_zero=False):
    """
    Will convert a numeric subject count value to "<n" string based on the min limit in settings.
    This is used to hide small numbers from people who are only allowed to see aggregated data.
    It does not check user permissions, so should only be called when needed.
    """
    min_limit = chiron_settings.CHIRON_AGG_SUBJECT_COUNT_MIN_LIMIT
    if value < min_limit and value > 0:
        if set_to_zero:
            return 0
        return "<{}".format(min_limit)
    return value


def generate_entry_id():
    """
    User-created definitions (like the cohort def or table def) are constructed of various
    definition parts. In general, all parts need an ID so that they can be identified later.
    """
    return "".join(
        random.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits)
        for _ in range(12)
    )


def to_json_string(obj, indent=None):
    """Convert the provided dict, list, string, object, etc. to a JSON string.

    Works the same as something like json.dumps() but can handle things that json.dumps() can't
    handle, such as Python dates.
    """
    encodable_obj = make_json_encodable(obj)
    return json.dumps(encodable_obj, indent=indent)


def make_json_encodable(input_obj):
    """Convert the provided dict, list, string, etc. to all JSON encodable data types.

    Can iterate through any nested object and converts anything that's not JSON encodable to
    a string representation. It does not actually convert the entire input value to a JSON string
    - use to_json_string() for that.
    """
    try:
        obj = copy.deepcopy(input_obj)
    except Exception:
        obj = input_obj
    # if isinstance(obj, tuple):
    #     print(obj)
    #     obj = dict(obj)
    if isinstance(obj, dict):
        newdict = {}
        for key, val in obj.items():
            if isinstance(key, tuple):
                key = str(key)
            newdict[key] = make_json_encodable(val)
        return newdict
    if isinstance(obj, list):
        newlist = []
        for val in obj:
            newlist.append(make_json_encodable(val))
        return newlist
    else:
        try:
            json.dumps(obj)
            return obj
        except TypeError:
            return str(obj)


def date_strings_to_python_dates(input_obj):
    """
    Convert all date strings found in input_obj to python dates. The input_obj can be any
    nested combination of lists and dicts.
    """
    obj = copy.deepcopy(input_obj)
    if isinstance(obj, dict):
        newdict = {}
        for key, val in obj.items():
            newdict[key] = date_strings_to_python_dates(val)
        return newdict
    if isinstance(obj, list):
        newlist = []
        for val in obj:
            newlist.append(date_strings_to_python_dates(val))
        return newlist
    else:
        try:
            mydate = datetime.strptime(obj, "%Y-%m-%d %H:%M:%S")
            return mydate
        except (ValueError, TypeError):
            pass
        try:
            mydate = datetime.strptime(obj, "%Y-%m-%d")
            return mydate
        except (ValueError, TypeError):
            pass
        return obj


def to_datetime(date):
    """
    Convert a Python date value to a datetime set a midnight
    """
    return datetime.combine(date, datetime.min.time())


def prepare_backup_file_path(filename, backup_dir=None):
    """Prepares the filepath to store a Chiron data dictionary fixture.

    Determines full filepath for the backup file name, creates the parent directory/directories
    if they don't exist, and checks if the file already exists or not.

    :filename: (str) The name of the backup fixture file to store.
    :backup_dir: (str) The directory path where the file should be stored, or leave blank
      to use Django setting CHIRON_DATA_DICT_BACKUP_DIR/
    :response: The full filepath to use for the file, and whether the file already exists.
    :rtype: (str, bool)
    """
    if not backup_dir:
        backup_dir = chiron_settings.CHIRON_DATA_DICT_BACKUP_DIR
    # make sure all directories on the path exist
    Path(backup_dir).mkdir(parents=True, exist_ok=True)
    filepath = os.path.join(backup_dir, filename)
    file_exists = os.path.exists(filepath)
    return filepath, file_exists


def dataset_command_line_selection(qDataset, existing_dataset_id=None, allow_all=False):
    """
    Prompt user to select a dataset ID from provided queryset. If an existing_dataset_id is
    provided, will skip the prompt as long as the provided value is a valid dataset_id.

    :param qDataset: The queryset of allowed datasets
    :type qDataset: a queryset of chiron.models.Dataset objects
    :param existing_dataset_id: The existing value if already set either dataset.id int or
      dataset.unique_id slug
    :type existing_dataset_id: int, string or None
    :param allow_all: Will allow the user to select "all" as an option
    :type allow_all: boolean
    """
    if qDataset.count() == 1:
        return qDataset[0].id
    allowed_ids = []
    print_lines = ["SELECT A DATASET TO USE"]
    if allow_all:
        allowed_ids.append("all")
        print_lines.append("all : Run this command for all datasets")
    for oDataset in qDataset:
        allowed_ids.append(str(oDataset.id))
        db_name = oDataset.get_actual_database_name()
        print_lines.append(f"{oDataset.id} : {oDataset.unique_id} (DB/Schema name: {db_name})")
    if str(existing_dataset_id) in allowed_ids:
        return existing_dataset_id
    # check if dataset.unique_id was provided instead of dataset.id
    if existing_dataset_id:
        for oDataset in qDataset:
            if oDataset.unique_id == str(existing_dataset_id):
                return oDataset.id
    for line in print_lines:
        print(line)
    dataset_id = input("Enter the dataset id or 'exit' to quit: ")
    if dataset_id == "exit":
        sys.exit()
    if dataset_id not in allowed_ids:
        dataset_id = dataset_command_line_selection(qDataset, dataset_id, allow_all)
    return dataset_id


def round_sig_3(
    input_value, rounding_method=round, min_num_decimals=None, round_whole_number=True
):
    """
    Rounds a number using 3 significant digits

    :param input_value: The input number to round
    :type input_value: int, float, str (if it can be converted to a number)
    :param rounding_method: The method to use for rounding. Default is round.
    :type rounding_method: function
    :param min_num_decimals: The minimum number of decimals to keep
    :type min_num_decimals: int
    :param round_whole_number: If True, can also round to the left of the decimal
      example: 34785 -> 34800
    :type round_whole_number: bool
    :return: The new formated nubmer
    :rtype: float | int
    """
    SIGNIFICANT_DIGITS = 3

    if input_value is None:
        return None

    # try to convert input_value to float for calculations
    try:
        input_float = float(input_value)
    except ValueError:
        return input_value

    if not round_whole_number:
        if input_float > 100:
            return round(input_float)

    # initially calculate decimals needed
    number_parts = str(input_float).split(".")
    num_decimals = SIGNIFICANT_DIGITS - len(number_parts[0])

    # handle leading zeros in decimals
    if number_parts[0] == "0" and number_parts[1].startswith("0"):
        # add number of leading zeros to sig digits
        for digit in number_parts[1]:
            num_decimals += 1
            if digit != "0":
                break

    # round with decimals
    # the decimal adjuster allows alternative rounding methods such as math.ceil
    if min_num_decimals is not None and num_decimals < min_num_decimals:
        num_decimals = min_num_decimals
    decimal_adjuster = pow(10, num_decimals)
    val = rounding_method(input_float * decimal_adjuster) / decimal_adjuster
    if num_decimals <= 0:
        return int(val)
    return val


def age_in_days_to_years_days(age_in_days):
    """
    Convert age in days to years and days
    """

    if age_in_days is None:
        return None, None
    age_in_days_normalized = abs(age_in_days)
    years = math.floor(age_in_days_normalized / 365.25)
    years_as_days = math.floor(years * 365.25)
    days = age_in_days_normalized - years_as_days

    # since we use 1/4 of a day for calculation there are
    # times when its represented as 365 days instaed of 1 year
    if days >= 365:
        days = 0
        years += 1

    # setup modifier for handling of negative ages
    modifier = -1 if age_in_days < 0 else 1
    return int(years * modifier), int(days * modifier)


def get_all_related_sources(dataset, source_name):
    """Returns a queryset of Source objects

    - dataset is None, source_name is None: returns all sources
    - dataset is set, source_name is None: returns all sources for dataset
    - dataset is None, source_name is set: returns all sources associated with the same collection
      as the provided source
    - dataset is set, source_name is set: returns all sources associated with the same collection
      as the provided source in the same dataset
    """
    # base source query to filter out excluded sources and order by execution order
    queryset = Source.objects.filter(exclude_from_etl=False).order_by("execution_order")

    # Return all sources if we are not wanthing anything specific
    if source_name is None and dataset is None:
        return queryset

    # if there is a dataset contstrating add that filter
    if source_name is None and dataset:
        return queryset.filter(collection__dataset=dataset)

    # if there is no dataset just use the source name filter
    if dataset is None:
        try:
            source_obj = queryset.get(name=source_name)
        except Source.DoesNotExist:
            print(f"Source {source_name} does not exist.")
            sys.exit(1)
        except Source.MultipleObjectsReturned:
            print(f"Source {source_name} matched more than one record.")
            sys.exit(1)
        return queryset.filter(collection=source_obj.collection)

    # use the dataset and source name constraints
    try:
        source_obj = queryset.get(name=source_name, collection__dataset=dataset)
    except Source.DoesNotExist:
        print(f"Source {source_name} does not exist.")
        sys.exit(1)
    except Source.MultipleObjectsReturned:
        print(f"Source {source_name} matched more than one record.")
        sys.exit(1)

    # now that we have a source use its collection to get all soruces with the
    # same dataset and collection
    return queryset.filter(collection=source_obj.collection, collection__dataset=dataset)


def get_all_collections_from_source_name(dataset, source_name):
    sources = get_all_related_sources(dataset, source_name)
    collections = set([])
    for source in sources:
        collections.add(source.collection)
    return collections

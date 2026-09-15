from django.conf import settings


# don't edit this directly, each setting can be overridden using the Django settings
# this file makes a useful reference for all chiron-specific settings and their default
# values


def get_setting(setting_name, alt):
    return getattr(settings, setting_name, alt)


def alert_deprecated_setting(setting_name):
    if hasattr(settings, setting_name):
        print(
            f"WARNING: You have {setting_name} defined in your Django settings, "
            "but that setting is no longer in use."
        )


# WEBSITE DISPLAY AND BEHAVIOR ####################################################################

CHIRON_SITE_TITLE = get_setting("CHIRON_SITE_TITLE", "Chiron Data Exploration Tool")
"""
For the built-in website, the title is displayed in the Navbar and various other places.
"""

CHIRON_FOOTER_TEMPLATE = get_setting("CHIRON_FOOTER_TEMPLATE", "chiron/core/footer.html")
"""
For the built-in website, allows a custom django template to use for the page footer.
"""

CHIRON_EXTRA_NAVBAR_ITEMS = get_setting("CHIRON_EXTRA_NAVBAR_ITEMS", None)
"""
For the built-in website, allows a custom django template to include addl links in nav menu.
"""

CHIRON_INFOBAR = get_setting("CHIRON_INFOBAR", "")
"""
You can display an infobar at the top of all built-in views. For example, a warning bar
that this is a test site. CHIRON_INFOBAR should have a string of the content to display and
CHIRON_INFOBAR_TYPE should have the type of bar, which will usually be indicated
by color:

"info" -> blue
"warning" -> orange
"danger" -> red
"""

CHIRON_INFOBAR_TYPE = get_setting("CHIRON_INFOBAR_TYPE", "info")  # info, warning, or danger
"""
You can display an infobar at the top of all built-in views. For example, a warning bar
that this is a test site. CHIRON_INFOBAR should have a string of the content to display and
CHIRON_INFOBAR_TYPE should have the type of bar, which will usually be indicated
by color:

"info" -> blue
"warning" -> orange
"danger" -> red
"""

CHIRON_LOGOUT_URL = get_setting("CHIRON_LOGOUT_URL", "/accounts/logout")
"""
The Chiron navbar has a logout link.
"""

CHIRON_SHOW_ANALYSIS_VIEW = get_setting("CHIRON_SHOW_ANALYSIS_VIEW", False)
"""
Include the analysis view on the built-in UI
"""

CHIRON_AGG_DELIMITER = get_setting("CHIRON_AGG_DELIMITER", "; ")
"""
When aggregating result columns, use this delimiter for separating the values.
"""

# DATA DICTIONARY #################################################################################

# date, age_in_days, age_in_years
CHIRON_EVENT_CONCEPT_TYPE = get_setting("CHIRON_EVENT_CONCEPT_TYPE", "date")
"""
The event query system allows date concepts to be associated with specific collections (using
collection.event_date_field and collection.event_end_date_field) indicating when an event occurred.
Then users can do temporal queries at the collection level.

You can either use date concepts for events, or you can use detailed age concepts - which
internally store an integer value for age in days. The advantage of using ages instead of dates
is that dates are generally considered PHI.

Ages and dates can't be compared against each other. You must choose one or the other to
specify here and then use globally across your application.

OPTIONS: "date", "detailed_age"
"""

# DATABASE #####################################################################################

CHIRON_DATABASE = get_setting("CHIRON_DATABASE", "postgres")
"""
The database system to use for storing subject data. Currently the only option is "postgres".
"""

CHIRON_USE_STAGING_DURING_ETL = get_setting("CHIRON_USE_STAGING_DURING_ETL", False)
"""
Applies to `python manage.py chiron_run_etl` command. Normally, existing data is
deleted at the start of the ETL process and repopulated. If this setting is True, data will be
loaded into separate staging tables and existing data will be kept until the end
of the ETL process. Upon successful completion of the ETL, the old collections will be replaced
by the staging collections.
"""

CHIRON_KEEP_DATABASE_BACKUP = get_setting("CHIRON_KEEP_DATABASE_BACKUP", False)
"""
This setting is only relevant when CHIRON_USE_STAGING_DURING_ETL=True. Upon successful preparation
of the staging database/schema - if False the live database/schema will be deleted and replaced.
If True, the live database/schema will instead be saved with the suffix "_backup" appended.
Only one backup copy is saved at a time, so a new backup will overwrite previous backups.
"""

CHIRON_SQL_ALCHEMY_CONNECTION_STRING = get_setting("CHIRON_SQL_ALCHEMY_CONNECTION_STRING", None)
"""
The connection string for the database where the actual research data will be stored. This is
separate from the database where application data and the data dictionary are stored. Currently,
only Postgres is supported.

example: "postgresql://myuser:mypassword@localhost:5432/my_database"
"""

CHIRON_POSTGRES_SCHEMA_NAME_PREPEND = get_setting("CHIRON_POSTGRES_SCHEMA_NAME_PREPEND", "")
"""
Each Chiron dataset is stored in its own Postgres schema. By default, the schema name is defined
in the data dictionary `Dataset.database_name`. Use this setting to optionally prepend
text to that name (for example, during tests could prepend "test" to all schema names).
"""

CHIRON_REQUIRE_SUCCESSFUL_CONCEPT_SEARCH_UPDATE = get_setting(
    "CHIRON_REQUIRE_SUCCESSFUL_CONCEPT_SEARCH_UPDATE", True
)
"""
The concept search table allows users to search for concepts by keyword (instead of by browsing).
If a staging schema is being used (CHIRON_USE_STAGING_DURING_ETL=True) and there is an error while
updating the concept search table:

- True: The entire ETL update will be canceled, old data will stay in place
- False: The ETL update will complete anyway (which means concept search might not work on the website).
"""

CHIRON_PG_CONN_OPTIONS_SITE = get_setting(
    "CHIRON_PG_CONN_OPTIONS_SITE", {"statement_timeout": "30min"}
)
"""
Any additional Postgres connection options you want to set when using SQL Alchemy to query the
research data from the website. Should be a dict where keys are setting names and values
are the desired value. Note that the search_path defining the schema 
name is automatically set, so don't attempt to set it here. 

This will not affect chiron-specific management commands, only Django management commands such as
"runserver". 

default: {"statement_timeout": "30min"}

See more options here: https://www.postgresql.org/docs/current/runtime-config-client.html
"""

CHIRON_PG_CONN_OPTIONS_MGMT = get_setting(
    "CHIRON_PG_CONN_OPTIONS_MGMT", {"statement_timeout": "30min"}
)
"""
Any additional Postgres connection options you want to set when using SQL Alchemy to query the
research data from a chiron-specific management command, such as chiron_run_etl. Note that the
search_path defining the schema name is automatically set, so don't attempt to set it here.
Should be a dict where keys are setting names and values are the desired value.

This will only affect chiron management commands (starting with "chiron"). To customize other
commands, use CHIRON_PG_CONN_OPTIONS_SITE.

default: {"statement_timeout": "30min"}

See more options here: https://www.postgresql.org/docs/current/runtime-config-client.html
"""

# FILEPATHS #######################################################################################

alert_deprecated_setting("CHIRON_DATA_DICT_FIXTURE_PATH")
"""
### DEPRECATED - USE CHIRON_DATA_DICT_BACKUP_DIR INSTEAD ###
For backing up and restoring the Chiron data dictionary (management commands chiron_backup_dd
and chiron_restore_dd), where should the fixture file be stored.
"""

CHIRON_DATA_DICT_BACKUP_DIR = get_setting("CHIRON_DATA_DICT_BACKUP_DIR", "chiron_config/backups")
"""
For backing up and restoring from the Chiron data dictionary (management commands chiron_backup_dd,
chiron_restore_dd, chiron_backup_dataset, chiron_restore_dataset), where should the fixture
json files be stored.
"""

CHIRON_AUTOCREATE_SOURCE_LISTS = get_setting(
    "CHIRON_AUTOCREATE_SOURCE_LISTS",
    "chiron_config.autocreate.autocreate_source_lists",
)
"""
The path to where you dictionary of autocreate source lists is stored.
"""


CHIRON_PROCESSOR_MODULES = get_setting("CHIRON_PROCESSOR_MODULES", ["chiron.processors"])
"""
Processor classes must be registered with Chiron. List any packages/modules that load processors
here to ensure that they are loaded during registry updates. If you include a module path,
that module will be checked. If you include a package path,
looks in the `__init__.py` file for the package.

The recommended location for registering custom processors is anywhere in
`[your_project]/chiron_config/processors/`. Then this setting would need to be:

CHIRON_PROCESSOR_MODULES = ["chiron.processors", "chiron_config.processors"]
"""

CHIRON_DATA_SUMMARY_FUNCTION_PATH = get_setting(
    "CHIRON_DATA_SUMMARY_FUNCTION_PATH", "chiron.views.views.get_data_summary_string"
)
"""
You can customize what's shown on the built-in home page. This function will take a request object
as an argument and should return an HTML string.
"""

CHIRON_SOURCE_DATA_DIRECTORY = get_setting("CHIRON_SOURCE_DATA_DIRECTORY", "")
"""
If loading source data from files, the directory path to prepend
ex. C://Users/meinken/data/
ex. ../../data/
"""

# USERS AND PERMISSIONS ###########################################################################

CHIRON_AGG_SUBJECT_COUNT_MIN_LIMIT = get_setting("CHIRON_AGG_SUBJECT_COUNT_MIN_LIMIT", 5)
"""
For users with access_level="agg" (only allowed to see aggregated data), what is the minimum
subject count they can see? Anything below that will show with a less-than sign. Zero subjects
will still show as "0".
"""

# PERFORMANCE AND CACHING #########################################################################

CHIRON_USE_CACHES = get_setting("CHIRON_USE_CACHES", False)
"""
Chiron can cache various patient data and stats to improve performance. Setting to True will
improve performance, but might cause problems in a development environment where you're actively
modifying the data dictionary.
"""

CHIRON_GET_QUERY_PERFORMANCE = get_setting("CHIRON_GET_QUERY_PERFORMANCE", False)
"""
The query engine can print various statements as stdout that help with debugging query
problems. This includes the amount of time it takes for each query step to run and notifications
when a cache was used. Set to true to turn these statements on.
"""

CHIRON_ABBREVIATED_ETL_DEFAULT_RECORD_COUNT = get_setting(
    "CHIRON_ABBREVIATED_ETL_DEFAULT_RECORD_COUNT", ("read", 100)
)
"""
A tuple with the count method and number of records to load for all sources
when using the abbreviated ETL.

:("read", n): Run until n records have been read, regardless of whether those records were loaded.
:("write", n): Run until n records have been loaded.
:("match_full", n): Only counts updates to an existing subject (i.e. adding data to a subject
  that was loaded in a previous step). Creation of new subjects can still happen
  (assuming `if_no_match="create"`) but will not count toward the 100.
:("match_strict", n): Same as match full, but will not bother to create new subjects even when
  `if_no_match="create"`.
"""

CHIRON_ABBREVIATED_ETL_RECORD_COUNTS = get_setting("CHIRON_ABBREVIATED_ETL_RECORD_COUNTS", {})
"""
The specific source record counts to import

.. code-block:: python

    CHIRON_ABBREVIATED_ETL_RECORD_COUNTS = {
        "my_source": ("read", 500),
        "my_source2": ("match_strict", 12),
    }
"""

CHIRON_BULK_INSERT_BATCH_SIZE = get_setting("CHIRON_BULK_INSERT_BATCH_SIZE", 100000)
"""
The batch insert size to use when inserting data, defaults to 100000
"""

CHIRON_MAX_HISTOGRAM_BINS = get_setting("CHIRON_MAX_HISTOGRAM_BINS", 30)
"""
The maxiumum number of bins to display in the histograms, defaults to 30
"""

# EMAIL NOTIFICATION SETTINGS ##############################################################

CHIRON_EMAIL_NOTIFICATIONS = get_setting("CHIRON_EMAIL_NOTIFICATIONS", False)
"""
Determines whether Chiron will send email notifications.
"""

CHIRON_EMAIL_FROM = get_setting("CHIRON_EMAIL_FROM", None)
"""
Email address for Chiron to use in email notifications
"""


# ONTOLOGY SETTINGS ##############################################################

CHIRON_TREAT_ONTOLOGY_CONCEPTS_AS_TEXT = get_setting(
    "CHIRON_TREAT_ONTOLOGY_CONCEPTS_AS_TEXT", False
)
"""
Whether or not to load ontology concepts as text concepts if the ontology module does not exist in
the project.
"""

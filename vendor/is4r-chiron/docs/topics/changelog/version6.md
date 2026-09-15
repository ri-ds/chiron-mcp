# Version 6

## Version 6.5.4 (2/2/2026)

- (chore) Updating requirement files for inheritance to minimize duplication of requirements
- (chore) Upgrading CodeQL runner to latest versions
- (bugfix) Fixing the integrity check for JS bootstrap-datepicker
- (bugfix) Fixing a bug with date compare, overwriting min variable with max
- (chore) Fixing some warnings about duplicate assignments/unused vars
- (improvement) Improving speed of the table_def actions
- (chore) Fixing alert about accessing the DB during startup

This release is some bug fixes as well as developer improvements with speed and warnings.

## Version 6.5.3 (8/15/2025)

**Email Content**

- _(bugfix)_ The email system was incorrectly providing HTML-formatting for plaintext email messages. This resulted in users getting plaintext emails with HTML markup visible. Fixed to supply both plaintext formatted and HTML formatted body strings as expected by the Django service.
- _(bugfix)_ URLs in emails were fixed to include the dataset name, aligning with API v2 formats.

**Histogram Bins**

- new setting CHIRON_MAX_HISTOGRAM_BINS (default=30) to limit the max number of histogram bins
  - The number of histogram bins used to show numeric data is calculated using the square-root choice algorithm. This algorithm has no upper limit and gets large as the number of values grows, causing performance and display issues.

**Performance Improvements**

For text concepts, it's possible to build a cohort def filter with any number of values selected. Several performance problems were discovered when trying to use a filter with 25000+ values.

- The 3rd party tool sqlparse was causing performance issues in some situations.
  - This was for pretty formatting of debug stdout info when CHIRON_GET_QUERY_PERFORMANCE=True.
  - However, the formatting was being applied even when the setting was turned off. So the performance hit affects all systems.
  - For now we have completely stopped using sqlparse. It is a requirement of Django so it should not be removed from your environment.
- The entry validation loop in `CohortDefText.validate_form()` was experiencing severe performance degradation with large datasets, taking up to 7.8 seconds to process entries in my 25000+ subject id entry. Profiling revealed the bottleneck was in the membership testing operations within the validation loop.

**Errors Handling Cohort Def User Input**

- Bugfix: Fixed issue where Age In Days Range would eliminate values of 0 due to 0 evaluating as False in Python.

## Version 6.5.2 (6/12/2025)

**Database System**

- _(bugfix)_ Support different characters in schema names by quoting.
- _(bugfix)_ Fixing the single source loader for multi datasets
- _(feature)_ Added a management command to create db indexes only.

**Notifications**

- _(bugfix)_ Fixed mistakes in how notifications (emails) were being sent.
  - APIv1 - When using the new UI, emails were never being sent.
  - APIv2 - When using the new UI, emails were not being sent when reports were created, only when they were later edited.

**Data Dictionary**

- _(bugfix)_ Fixing the age_in_days_to_years_days function to handle negative dates and adding tests for it.
- _(feature)_ new concept handler argument option for built-in concept handler `IntegerHandler`
  - number_is_year (default=False)
  - Set to True for better handling of year values in things like histograms.

## Version 6.5.1 (2/26/2025)

- Changed formatting in `setup.py` because people were reporting problems installing with `pip` and `setuptools`.

## Version 6.5.0 (2/25/2025)

- Added a new ontology datatype for concepts. This feature has additional requirements and setup instructions. It is optional and off by default. See more info about it in the {ref}`ontology app installation instructions<installing-ontology-app>`.
- BUGFIX: The `chiron_restore_dataset` management command was incorrectly removing saved reports even when updating a dataset in place.

### version compatibility

- Use with [new Chiron UI version 1.0.0](https://github.com/cchmc/is4r-chiron-ui). This is the first official production release.
- The built-in UI is still supported, but not for the new ontology datatype fields. Support for the built-in UI will probably go away altogether in the next year.
- Use with [optional ontology-app version 1.0.0](https://github.com/cchmc/is4r-chiron-ui).

### upgrade from 6.4.x

If you don't want to use the new ontology datatype, no action is required. However, you might want to change the new setting to True. This will disable any warnings about the missing dependency.

```python
# explicitly disable the ontology concept feature to avoid getting any related warnings
CHIRON_TREAT_ONTOLOGY_CONCEPTS_AS_TEXT = True
```

If you do want to use the new ontology datatype, follow the {ref}`ontology app installation instructions<installing-ontology-app>`.

## Version 6.4.4 (2/6/2025)

- New Django settings `CHIRON_PG_CONN_OPTIONS_SITE` and `CHIRON_PG_CONN_OPTIONS_MGMT`. These allow optional client connection options to be passed to Postgres every time a connection is established.
  - Note that these are only used for SQL Alchemy connections to query actual research data. Connections to system data (Django site tables, User table, Chiron data dictionary tables, etc.) are managed by Django and defined/customized in the `DATABASES` setting.
  - the MGMT settings are used by all custom Chiron management commands, the SITE settings are used by all other management commands (including runserver, which is normally what your actual website is running on).
- Bugfix: For both of the new Postgres connection options, a default "statement_timeout" of "30min" is defined. Prior to this, there was no timeout unless defined on the Posgres server itself. This meant if a SQL query couldn't finish executing for any reason, it would continue running indefinitely.

## Version 6.4.3 (11/15/2024)

- New field `Dataset.extra_header_links` allows for extra headers in the top navigation that link out to a provided URL.
- Bugfixes for the ETL process
  - Modified ETL to reduce risk of a Postgres database timeout during the ETL process.
  - Caches were failing to clear in some cases, resulting in stale data showing up on the website.
  - Indexing weren't getting set up properly for systems using a staging schema.
- Concept search feature was modified to fix a bug where concepts marked unpublished or not included still showed up in results.

### upgrade from 6.3.x

There is a new field in the Dataset model, so you need to update the Django database schema:

- Run migrations to apply database schema change

```shell
python manage.py migrate

# if you have multiple databases defined in Django you may need to run migrations on all
python manage.py migrate --databse=mydatabase
```

Any fixtures that you have saved also need to be updated for the new data schema.

```shell
python manage.py chiron_backup_dd

# or if you backup datasets individually
python manage.py chiron_backup_dataset
```

## Version 6.3.3 (9/9/2024)

- We made documentation on running and creating tests for Django, which will hopefully make it easier to create
  new tests. See the [tests section in the Chiron developer documentation](https://cchmc.github.io/is4r-chiron/topics/tests.html).
- guaranteed repeatable sorting for reports
  - Reports are now always sorted by all stacked columns regardless of sort options the user has chosen. It will apply
    user-selected sorting first, then any additional stacked columns. This ensures a report is sorted the same way
    every time it is run, which eliminates the risk of duplicating or dropping columns on paginated results.
- Fixed a bug in API 2 when a report has no project. And we have actually decided to make report project a required field
  going forward. However, this restriction is currently only enforced in the new UI and legacy reports can still exist
  without a project.
- fixed bug in column sort for earliest/latest aggregation
  - In certain Postgres environments, some aggregation methods using custom Postgres functions were returning incorrect results.
    Specifically, sorting by collection event date/age was treating the value as a string rather than as a date or integer
    respectively.
  - We didn't determine which Postgres environments were causing the issue. Instead, we just went ahead and made
    the Postgres functions more specific about datatypes. The query engine will check `chiron_settings.CHIRON_EVENT_CONCEPT_TYPE`
    and use the appropriate function with the appropriate data types for your data.

## Version 6.3.2 (8/26/2024)

- bugfix: the cache data and concept search data weren't being updated correctly during the ETL in some contexts
- added some new fields in API v2 responses, shouldn't be any backwards-incompatible changes
- fixed various bugs related to the ETL, API v2, and the new histograms

## Version 6.3.1 (8/6/2024)

- bugfix: Concept stats for detailed age concepts had an error. It was causing the website query view to fail
  when user attempts to view one of these concepts.
- bugfix: The setting field `Source.include_in_etl` in the Source model was being ignored - all sources were being
  loaded during the ETL even if this was set to False.

## Version 6.3.0 (8/2/2024)

- bugfix: In some situations, wasn't using the correct database (staging vs live) when populating the concept search table.
- Fix several bugs related to using Postgres for research data.
- Added some new options for handling the situation if a user doesn't have access to view a dataset. New bool field `Dataset.list_visible` defines whether the user should even see that the dataset exists when they look at the list of datasets available. New email field `Dataset.contact_email` can be used to let a user know who they should contact to inquire about getting access to the dataset. Note that currently, Chiron does not send an email requesting access for the user - this is just a way for them to get the email address and send their own email.
- New fields in the Dataset model: logo_url, list_visible, contact_email
- New fields in API v2 endpoint `/api/v2/dataset/`: logo_url, list_visible, contact_email
- Removed fields from API v2 endpoint `/api/v2/auth/`: accessLevel, chironUserId
- new API endpoint: `/api/concept_categories/concept_search/`

**Improvements: Permissions in the API**

There were some vague areas regarding the permissions users have in certain contexts. The rules have been clarified better, and the API code was modified to match the better-defined rules, as well as implement permission rules in a more consistent way.

- Users with `ChironUser.access_level=AGG` on a dataset can only use the aggregate view (to see pivottables). They can't use the query view or the results view, they can't define a cohort, and they can't see reports. Previously there were some versions of Chiron where users could see a modified version of the query view and define cohorts.
- The Concept endpoints (starting with `/api/concepts/`) are designated as endpoints that can return research data. So the endpoints will be disabled for users with `ChironUser.access_level=AGG` on a dataset. The endpoints are also disabled if `ChironUser.can_view_workspace=False`.
- The less strict alternative to Concept endpoints for getting data about concepts is ConceptCategory (starting with `/api/concept_categories/`). This can be used to get all sorts of metadata about concepts, just not the concept data itself. While ConceptCategory has different endpoints from Concept, it can be used to accomplish many of the same things. We've also added the endpoint `/api/concept_categories/concept_search` for finding concepts that match a search string - as this functionality was previously only available in the Concept ViewSet.

See the confluence notes for a full explanation of permission rules: [https://confluence.research.cchmc.org/pages/viewpage.action?pageId=248349155](https://confluence.research.cchmc.org/pages/viewpage.action?pageId=248349155)

**Feature: ETL Load Single Source**

- Can't be the subject collection, must be a subcollection.
- This feature still needs some work before it functions correctly in all situations. There are a variety of ways it could screw up your dataset. And when it does it will probably not report any errors, so it will seem like it worked. For that reason, you must pass `--force` to indicate that you understand the risks.
- We are hoping to have an improved ETL process soon that will have reliable loading of single sources with better documentation for how to use.

**Improvements: Number Histograms**

- We use the popular square-root choice algorithm for determining the number of bins. Previously we used our own algorithm which often had too many or too few bins based on the number of data points.
- Previously the minimum size for a bin was one. Now bins can be whatever size is needed based on the range and number of bins. (NOTE: Integer concepts still have a minimum bin size of one.)
- Bin labels showing the bin range have been improved. We use square brackets or parentheses to indicate whether the cutoff value is included or excluded from the bin. We round bin cutoffs to 3 significant digits (this is done prior to calculations so that the count value for the bin will always agree with the displayed number). And we format large/small numbers using "k" or scientific notation as appropriate for easy readability.

### upgrade from 6.2.x

- There are important changes to API v2. If you are using the new Chiron UI, you must get the latest version.

- Run migrations to apply database schema changes (3 new fields in Dataset model).

```shell
python manage.py migrate

# if you have multiple databases defined in Django you may need to run migrations on all
python manage.py migrate --databse=mydatabase
```

Any fixtures that you have saved need to be updated for the new data schema.

```shell
python manage.py chiron_backup_dd

# or if you backup datasets individually
python manage.py chiron_backup_dataset
```

## Version 6.2.0 (5/31/2024)

**Major Changes**

- Adds API v2, which is designed to work with a new React-based UI.
  - Continues API v1 which supports the original Django UI. We plan to phase out the Django UI.
- Adds email notifications for sharing and updating User Content items.

**Minor Changes**

- Improvements to display of detailed ages.
- Replaced black/flake8 formatting with Ruff.
- Removed unnecessary restriction on backing up a system with single dataset.
- Fixes to the pivot table in analysis view including better sorting and more reasonable number of categories created for continuous variables.
- Support for custom delimiters and encodings when using a CSV file as a data source.

### upgrade from 6.1.x

- There are no changes to the Django models. You should not have to run migrations.
- The following pip requirements have been removed: `pymongo`, `black`, `flake8`
- The following pip requirements have been added: `ruff`
- There are new optional Django settings for Chiron email:
  - `CHIRON_EMAIL_NOTIFICATIONS` (default False): Determines whether Chiron will send email notifications.
  - `CHIRON_EMAIL_FROM` (default None): Email address for Chiron to use in email notifications.

## Version 6.1.2 (2/23/24)

- additional data dict validation for concept roles that don't allow multivalue (validation is run at start of the ETL)
- regex query support for text concepts
- successful concept search is required in ETL by default
- dataset schema view for admin using Mermaid JS

## Version 6.1.1 (2/1/2024)

The SQL Alchemy engine is now created as a singleton, and the pool of connections it opens is limited
to one instead of SQL Alchemy's default of 5 (though it will allow extra temporary connections if
needed, which will be immediately removed once closed). The goal of these changes
is to prevent problems during the ETL such as connection timeouts or too many connections being
opened at once.

Added new sorting options to use when iterating the Chiron database itself is as a source (SourceSelf processor).

The ordering of steps closing out the ETL process has been improved. After the database is finalized (which includes copying staged data into place), these are the closing steps:

1. Clear caches.
2. Mark the ETL log as complete. This was moved earlier to more accurately reflects what's going on in the user interface, as this is the point where users will see the new data.
3. Refresh the concept search collection. This was moved earlier since concept search will not work until this is populated.
4. Refresh caches. This was moved to the last step since it is only for performance so is less essential than other steps.

## Version 6.1.0 (released 1/11/2024)

Removed all references to MongoDB in the code and data dictionary data schema.

### Upgrade from 6.0.x

- The following Chiron global settings have changed
  - CHIRON_DATABASE - Removed option for "mongodb". Currently the only (and default) option
    is "postgres".
  - CHIRON_MONGO_CONNECTION_SETTINGS - Setting has been removed.
  - CHIRON_MONGO_DATABASE_NAME_OVERRIDE - Setting has been removed. You can use
    CHIRON_POSTGRES_SCHEMA_NAME_PREPEND to accomplish a similar thing for Postgres.
  - MAX_CACHED_SUBJECT_IDS - Setting has been removed. Subject ID lists for user-defined cohorts
    are no longer cached. The purpose of caching those was to speed up MongoDB queries. We
    do still cache the subject count for cohorts.
- Review custom processors for any broken references
  - Source Processors
    - `SourceSelfRdbms` class was renamed to `SourceSelf`
    - `SourceSelfSubdocRdbms` class was renamed to `SourceSelfSubdoc`
  - Cohort Def Processors
    - `get_mongo_match_def` method was removed.
    - `get_mongo_match_def_full` method was removed.
  - Aggregation classes
    - `mongodb_aggregate` method was renamed to `calculate_agg_value`
  - Data Dictionary Models
    - `Concept.unwind` field was renamed to `Concept.multivalue`
    - `Dataset.mongo_database_name` field was renamed to `Dataset.database_name`
    - `Dataset.get_actual_mongo_database_name()` method was renamed to
      `Dataset.get_actual_database_name()`
  - And in general, it would be good to do a text search across your custom processors for any use
    of the word "mongo" - just to make sure there isn't anything else that was overlooked.

- Run migrations to apply database schema changes

```shell
python manage.py migrate

# if you have multiple databases defined in Django you may need to run migrations on all
python manage.py migrate --databse=mydatabase
```

- At this point, your site should be working normally. It might be a good idea to try out the ETL
  and click around the website.

- Any fixtures that you have saved need to be updated for new data schema

```shell
python manage.py chiron_backup_dd

# or if you backup datasets individually
python manage.py chiron_backup_dataset
```

- Be aware of changes to management commands
  - `chiron_create_indexes`, `chiron_drop_indexes`, `chiron_view_indexes` commands have been
    removed. Indexes will automatically be created during `chiron_run_etl`. Any other changes
    you want to indexes can be done directly against the Postgres database.
  - `chiron_check_unwinds` was renamed to `chiron_set_multivalue`. This name change removes the
    MongoDB-specific word "unwind" and also clarifies that it performs an actual action against
    the data dictionary, not just a check.

## Version 6.0.4 (released 12/7/2023)

Improved ETL performance including setting up most Postgres indexes after the ETL is finished.

New setting `CHIRON_KEEP_DATABASE_BACKUP=True` will save the database from the previous ETL when
a staging schema is also being used (`CHIRON_USE_STAGING_DURING_ETL=True`).

## Version 6.0.3 (released 11/9/2023)

**NOTE: An upgrade to 6.0.3 requires a rerun of chiron_run_etl to get latest data schema.**

The staging schema wasn't being used for PostreSQL even when CHIRON_USE_STAGING_DURING_ETL was
set to True. This has been corrected.

System fields used in PostgreSQL tables were renamed to avoid name clashes with concept permanent IDs.

Version numbers for PIP requirements were updated.

A bug on queries when a user had no permission groups set was fixed.

## Version 6.0.2 (released 10/26/2023)

The code for self-referential source processors SourceSelf and SourceSelfSubdoc was refactored
to make it easier to read and to extend for custom source processors.

Concept fields are truncated to 255 characters during the ETL because that is the maximum allowed
string length for those fields in Postgres.

Various performance improvements made to code.

## Version 6.0.1 (released 10/3/2023)

Fixed bugs in the new Postgres query engine causing incorrect data to be returned - especially
related to relative date queries.

## Version 6.0.0 (released 9/14/2023)

The core goal of this release is to switch from MongoDB to Postgres for storing
research data.

Note: Code referencing MongoDB hasn't been 100% stripped out yet. However, if you set
`CHIRON_DATABASE = "postgres"` in your settings, your site should no longer attempt to use
MongoDB for anything. Fully removing MongoDB is planned for version 6.1.

### Upgrade from 5.0.x

1. Update the code. Chiron 6 code has now been merged into the `develop` and `main` branches.

```shell
git fetch
git checkout develop
```

2. Install new requirements for Postgres and SQL Alchemy.

```shell
pip install -r requirements.txt
```

3. Run database migrations. This is for your Django system tables and chiron data dictionary.
   Your new Postgres database with the actual research data will be handled separately by SQL
   Alchemy instead of Django.

```shell
python manage.py migrate

# for multidatabase systems, be sure to run migrations on all databases.
python manage.py migrate --database=mydatabase
```

4. Permanent IDs for Collections and Concepts are used to name your Postgres tables and fields.
   Permanent IDs can be up to 120 characters long, but Postgres has a maximum name length of 63
   characters. You can use this management command to generate a list of IDs that are too long,
   then use the Django admin (or edit in the database directly) to fix.

```shell
python manage.py chiron_shorten_ids
```

Note: Changing permanent IDs will break any reports that reference them. If you think any of
your long IDs might be referenced in a report, contact John and we can make a plan for handling
it.

5. Add settings to use Postgres.
   - This is for storing the research data and should generally be a separate database from your Django application data.
   - It's set up to have one Postgres database for the entire instance, and each dataset will be stored in its own schema.
   - The Postgres database must exist, and the user must be able to create schemas along with normal DDL and DQL permissions.

```python
CHIRON_DATABASE = "postgres"
CHIRON_SQL_ALCHEMY_CONNECTION_STRING = "postgresql://myuser:mypassword@localhost:5432/my_database"
```

6. Update any custom CohortDef processors.

CohortDef processors have two new methods you will need to implement:

- get_sql_alchemy_clause()
- get_sql_alchemy_bool_clause()

7. Run the ETL as normal - it should load into Postgres instead of MongoDB.

```shell
python manage.py chiron_run_etl
```


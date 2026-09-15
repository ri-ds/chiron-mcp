# Version 4

## Version 4.3.x (develop-4 branch)

*no breaking changes since version 4.3.2*

## Version 4.3.2 (released 12/19/2022)

**bug fixes**
- MongoDB subcollections were not getting populated fully when there were no permission groups,
  resulting in a KeyError during queries.

## Version 4.3.1 (released 12/13/22)

**New features**
- beta support for M2M subcollections now ready for production (allows M2M relationship between
  a subcollection and subject)
- `chiron_restore_dataset` management command preserves existing user created content (reports)
  when updating an existing dataset

**bug fixes**
- fixed several incorrect references to Django user instead of chironuser (affected report API endpoints)
- fixed outdated broken references in number_with_categories cohort def processor
- fixed error on name clashes between different datasets (same name should be allowed on all entities
  except concept.permanent_id)

## Version 4.3.0 (released 10/27/22)

**New features**
- new management commands {ref}`cmd-chiron-backup-dataset` and {ref}`cmd-chiron-restore-dataset`
- better stability and performance for DocumentDB
- important security updates for multi-dataset systems
- stable release of performance_project - can be used to compare query performance between two
  Chiron environments


**Upgrade from 4.2.0**
- There were changes to the static files. You should rerun `python manage.py collectstatic` in
  your production environment. 
- The setting CHIRON_RUNNING_ETL has been removed. Management commands involved with the ETL
    process will use a singleton for the MongoDB client (to avoid 30 minute inactivity timeout
    error), and any other commands will start a new client each time.
- The setting CHIRON_DATA_DICT_FIXTURE_PATH has been removed. Please use CHIRON_DATA_DICT_BACKUP_DIR
  instead. All backups from chiron_backup_dd and chiron_backup_dataset will go in this directory. The
  default path is `chiron_config/backups/`.
    - If you have your old fixture file at `chiron_config/fixtures.json`, you can move it to
      `chiron_config/backups/full_dd.json`.
- The package `chiron.autocreate` was renamed to `chiron.data_dictionary`. If you use the
  `chiron_autocreate_dd` feature, you probably have references to this in your `chiron_config`
  that will need to be updated:
```python
# old broken references
from chiron.autocreate.csv_autocreate import CsvFileAutocreate
from chiron.autocreate.django_autocreate import DjangoOrmAutocreate

# update to
from chiron.data_dictionary.csv_autocreate import CsvFileAutocreate
from chiron.data_dictionary.django_autocreate import DjangoOrmAutocreate
```
- The setting `CHIRON_PRINT_QUERY_INFO` was renamed to `CHIRON_GET_QUERY_PERFORMANCE`

  
    
## Version 4.2.0 (released 8/29/22)

**New features**
1. Added data issue tracking for during the ETL. Problems with data (ex. str input for a date
   concept can't be parsed to a date) will generally be added to the log info instead of raising
   an error and stopping the whole ETL process. Go to the "ETL Logs" backend view in the built-in
   UI to browse data issues.
2. Can customize the delimiter for aggregated field in reports.

**Upgrade from 4.1.x**
- Need to run database migrations.
- Changes to abstract ETL processor class will have to be applied to any custom ETL processors
    - method `pull_record_data_from_source()` was renamed to `pull_concept_value_from_record()`
    - method `cast()` was renamed to `_cast()`
    - method `convert_data_list_to_set()` was renamed to `_convert_data_list_to_set()`
    - `__init__()` method should initialize warnings `self.warnings=[]`
- new setting `chiron_settings.CHIRON_AGG_DELIMITER`
    - no action required but you can set this if you want something besides the default `; `

## Version 4.1.0 (released 8/3/22)

1. Deprecated code and model fields related to the old processor registry were removed.
2. {ref}`admin-views` in the built-in UI were cleaned up and added to documentation.
3. Support for datasets (previously in beta) is now stable and ready for production use.
    - Home Page shows active dataset and lets you change the active dataset.
    - Each dataset allows you to define whether new users can access automatically and what their default permissions should be.
    - In admin, validation to make sure FK relationships are only between objects belonging to the same dataset.
    - New fields in dataset to override global settings such as CHIRON_SITE_TITLE and CHIRON_FOOTER_TEMPLATE - gives better ability to customize how the site looks for each dataset
   
**Upgrade from 4.0.x**
- Run django migrations `python manage.py migrate`
- If you have custom processors, remove all references to ProcessorRegistryOld.



## Version 4.0.1 (released 7/18/22)

1. Patch for major bug causing all analysis view queries to fail.

### Version 4.0.0 (released 6/30/22)

1. *(beta feature)* A single Chiron instance can now have multiple datasets. This is achieved using a Dataset
    model - each collection belongs to a Dataset.
2. Processors and processor arguments for concepts are no longer defined in the Concept model
    directly. Instead, they are bundled into a ConceptHandler class, and the concept model
    defines the concept handler to use.
    - If you have custom processors, you have to upgrade to the new way to register them. See new notes on {ref}`registering-custom-processors`.
3. Autocreating the data dictionary now uses source lists instead of modeltree text files. A
    source list is a Python list with each entry defining a source to create.
    - See {ref}`autocreate-the-data-dictionary`
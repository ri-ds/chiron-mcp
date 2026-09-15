# Version 5

## version 5.0.6 (released 3/9/2023)

- Switched from CircleCI to GitHub Actions for testing. New setup also does black formatting and
  flake8 linting.

## version 5.0.5 (released 3/7/2023)

- Fixed a bug in the detailed age processor `EtlDictAgeInYearsToDays`

## version 5.0.4 (released 3/3/2023)

- The concept_for_allowed_subjects in a permission group should only be cast to a boolean value
  if it's not already a boolean value. Not all MongoDB and DocumentDB versions support the `toBool`
  method.
- Only pre-cache concepts that are flagged as include_in_cohort_def.

## version 5.0.3 (released 2/17/2023)

- concept search now supports partial word matching from the start of the word
  - ex. `pass` will match `passport number` (but `port` will not)
- fixed bug in built-in UI that was using a hard-coded API URL

## version 5.0.2 (released 1/25/2023)

- fixed bug related to installing chiron using pip

## Version 5.0.1 (released 1/24/2023)

- fixed bugs related to using ages for event collections

## Version 5.0.0 (released 1/20/2023)

### Upgrade from 4.3.X

**Update your custom processors and concept handlers**

There have been a lot of changes to source processor classes and concept handler classes. If you have custom processors, you will have to go through and fix them:

1. Globally, any reference to "SourceCollection" has been changed to "Source". You may have to update broken references in your custom processors. For example:
  - `chiron.processors.abstract.SourceCollectionProcessor` was moved to `chiron.processors.abstract.SourceProcessor`.
  - method `get_source_collection()` was renamed to `get_source()`

2. Remove references to `ETL._cast()` method

The abstract ETL processor used to have a `_cast()` method. That has been replaced with new CleanValue classes.

3. Most of the concept handler classes have been renamed. You may have to update references in your code. 
  - any references to `get_built_in_dict_concept_handlers()` and `get_built_in_django_concept_handlers()` should be changed to `get_built_in_standard_concept_handlers()`
  - any references to concept handlers that start with "Dict" or "Django" have probably been merged. For example, "DictIntegerHandler" and "DjangoIntegerHandler" are now just "IntegerHandler"


This should cover the majority of changes, but you may run into other errors depending on your setup. If `python manage.py` can run without printing any error messages, you're probably good (and warnings about unregistered concept handlers will be dealt with in a later step).

**data dictionary updates**

4. Run database migrations.

```
python manage.py migrate
```

- FYI, Some source processor arg names will be automatically updated:
    - `root_collection_id_field` -> `subject_matching_source_id_field`
    - `subject_id_delimiter` -> `subject_matching_source_id_delimiter`


**Names of most concept_handler classes have changed**

Instead of having separate concept handlers for lists of dicts vs querysets, most of the built-in concept handlers have been modified to support both.

5. Run this custom script to update all your concept handler names in the registry.

```shell
# rename django handlers
python manage.py chiron_merge_handlers DjangoCategoryHandler CategoryHandler
python manage.py chiron_merge_handlers DjangoTextHandler TextHandler
python manage.py chiron_merge_handlers DjangoDateHandler DateHandler
python manage.py chiron_merge_handlers DjangoBooleanHandler BooleanHandler
python manage.py chiron_merge_handlers DjangoIntegerHandler IntegerHandler
python manage.py chiron_merge_handlers DjangoFloatHandler FloatHandler
python manage.py chiron_merge_handlers DjangoIntegerWithCategoriesHandler IntegerWithCategoriesHandler
python manage.py chiron_merge_handlers DjangoFloatWithCategoriesHandler FloatWithCategoriesHandler
python manage.py chiron_merge_handlers DjangoSubjectHyperlinkHandler SubjectHyperlinkHandler

# rename dict handlers
python manage.py chiron_merge_handlers DictCategoryHandler CategoryHandler
python manage.py chiron_merge_handlers DictTextHandler TextHandler
python manage.py chiron_merge_handlers DictDateHandler DateHandler
python manage.py chiron_merge_handlers DictBooleanHandler BooleanHandler
python manage.py chiron_merge_handlers DictIntegerHandler IntegerHandler
python manage.py chiron_merge_handlers DictFloatHandler FloatHandler
python manage.py chiron_merge_handlers DictIntegerWithCategoriesHandler IntegerWithCategoriesHandler
python manage.py chiron_merge_handlers DictFloatWithCategoriesHandler FloatWithCategoriesHandler
python manage.py chiron_merge_handlers DictSubjectHyperlinkHandler SubjectHyperlinkHandler

# rename age handlers
python manage.py chiron_merge_handlers DjangoDetailedAgeHandler DetailedAgeHandler
python manage.py chiron_merge_handlers DictDetailedAgeHandler DetailedAgeHandler

# rename other custom handlers
python manage.py chiron_merge_handlers SubjectIdTextHandler SubjectMatchingToTextHandler
python manage.py chiron_merge_handlers SubjectIdSubjectHyperlinkHandler SubjectMatchingToSubjectHyperlinkHandler
python manage.py chiron_merge_handlers GeneratedSubjectIdHandler AutoSubjectIdHandler
python manage.py chiron_merge_handlers GeneratedSubcollectionIDHandler AutoSubcollectionIdHandler
python manage.py chiron_merge_handlers DictCurrentAgeFromDobHandler CurrentAgeFromDobHandler
python manage.py chiron_merge_handlers CalculateDetailedAgeFromDatesHandler DetailedAgeFromDatesHandler
```

6. Running `python manage.py` should now give you zero errors and zero warnings.

7. (optional) There are two new optional methods in SourceProcessor to help with tracking subject matching. If you have complex needs for subject matching, check them out.
  - get_subject_id_fields_used_for_matching()
  - get_subject_id_fields_added()

8. If you keep a JSON backup of your data dictionary, rerun management commands to create backups on your latest data schema.

```
python manage.py chiron_backup_dd
# or
python manage.py chiron_backup_dataset
```


**new age/date handling for event system**

If you use absolute dates for subcollection events, you can skip this section. But if you use detailed ages (i.e. age in days or age in years as float), there is a new concept data type `detailed_age` that you must start using

You can import `detailed age` from a variety of formats. It will store values as age in days internally. 

9. For source data that's already storing detailed age info, change the concept handler to DetailedAgeHandler and specify in ConceptHandlerArgs `source_format="age in days"` (default) or `source_format= year float"`.
10. If you want to calculate a detailed age using DOB and an event date, use the concept handler DetailedAgeFromDatesHandler.
11. Chiron setting CHIRON_EVENT_CONCEPT_TYPE should be changed to either "dates" or "detailed_age". If you were previously using "age_in_days" or "age_in_years", you **MUST** change the value to "detailed_age" and you **MUST** change all subcollection date concepts (defined in Collection.event_date_field and Collection.event_end_date_field) to use a handler that implements detailed_age (either DetailedAgeHandler or DetailedAgeFromDatesHandler).
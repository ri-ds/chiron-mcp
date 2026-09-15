# Deploy to Production

## Copying the data dictionary

The data dictionary can be copied into a JSON file (a Django fixture) in your development environment and restored in your production environment.

Use the setting {ref}`CHIRON_DATA_DICT_BACKUP_DIR <chiron-settings-file-location>` to specify a backup directory, default is `chiron_config/backups`.

```
# save database data dictionary to a django fixture
python manage.py chiron_backup_dd

# restore database data dictionary from a django fixture
python manage.py chiron_restore_dd
```

## Customize settings for the production site

A lot of custom behavior for your production site can be configured in {ref}`chiron-settings`.

## Setting up Research Database Indexes

The Chiron ETL process creates indexes on certain ID fields before the ETL starts because they help speed up the ETL process. But most of your concept fields are 
indexed after the ETL. All this is done automatically for you during `chiron_run_etl`.

## Using staging collections in the database

In your {ref}`Chiron settings<chiron-settings-database>`, if you set `CHIRON_USE_STAGING_DURING_ETL=True`the chiron_run_etl command will leave the production tables in place while it runs and load everything into a separate staging schema. Once the ETL is complete, the production schema is deleted and the staging schema will be renamed to take its place.

There are a few advantages to this:

- The website can continue to be used while the ETL is running.
- The original data will only be replaced if the ETL process completes successfully. If there's any error during the ETL, you won't be left with a half-finished database.

You can also set `CHIRON_KEEP_DATABASE_BACKUP=True` to save a copy of the old production schema instead of replacing it. 

## Users and user permissions

Each user needs a Django user account. There is also a {ref}`ChironUser model<chiron-user-model>` that is 1:1 with the Django user model. Chiron users are automatically created the first time Django users try to access Chiron (unless you've changed that behavior in your chiron settings).

There are **a lot** of options for customizing user access to Chiron and to specific concepts and patients. 
See {ref}`how-to-manage-users` for details.
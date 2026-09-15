# Run the ETL

Once the data dictionary is set up, you can load data from your sources into the research database anytime. The process
is guided by the Source model, and sources will be loaded in order according to {ref}`Source.execution_order<source-model>`.

The research database connection is defined in your {ref}`Chiron settings<chiron-settings-database>`. The database name for each dataset
is defined in your {ref}`Dataset table<dataset-model>`.

```
python manage.py chiron_run_etl
```

This command fully erases the existing data and reloads everything from scratch. If your system has 
multiple datasets you will be prompted to select one.

## Partial Loading

**Option 1:** Exclude specific source lists from the ETL 

{ref}`Sources<source-model>` have an exclude_from_etl option. Set to True for the sources you wish to skip and then run `chiron_run_etl` as usual. Any fields those Sources load into will show as having no data.

**Option 2:** Load an abbreviated subset of data

For quick testing, you can do an abbreviated run, which will load a small number of records from
every source.

```
# abbreviated ETL
python manage.py chiron_run_etl --abbreviated
```

The settings {ref}`CHIRON_ABBREVIATED_ETL_DEFAULT_RECORD_COUNT<chiron-settings-performance>` and {ref}`CHIRON_ABBREVIATED_ETL_RECORD_COUNTS<chiron-settings-performance>` 
can be used to control how many records are loaded in an abbreviated run.


**Option 3:** Load a single source

You can also load data from a single Source, but it doesn't always work correctly, so it's not recommended for production.

```
# good for a quick test, but not recommended for production systems
python manage.py chiron_run_etl --source=my_source_id
```




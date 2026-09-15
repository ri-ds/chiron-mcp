# Performance Project

A Django project for testing Chiron query performance. It uses the Python faker library to generate a dataset.

## Set Up

**Step 1: Edit Settings**

If you want to have custom settings you can create a file `performance_project/project/custom_settings.py`.
This can be used to customize any settings you need for your local environment and is excluded from git.
Use example file `performance_project/project/custom_settings.py.example` as a template.

**Step 2: Create the Databases**

Initialize the SQLite database

```
cd chiron/performance_project
python manage.py restore_project_state
```

Generate the MongoDB data

- This takes about 20 minutes

```
python manage.py chiron_run_etl
```

View the site

```
python manage.py runserver
```

## Running benchmarks

There is a benchmark script to run that will use the performance project and test the API endpoints speed.

First start the chiron instance running. You can run with caches on or off, and this will affect
whether the benchmark tests use caches or not.

```bash
# run with caches on
python manage.py runserver

# run with caches off
python manage.py runserver --settings=project.benchmark_settings_no_cache
```

Then in a separate terminal you can run your tests:

- this takes several minutes, and setting i > 1 will increase the time.
- see the -h output for config values

```bash
python manage.py run_benchmark -i 1 http://localhost:8000
```

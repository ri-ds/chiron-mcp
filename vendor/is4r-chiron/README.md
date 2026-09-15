# Chiron

Chiron is a data exploration/reporting tool for research data with a strong focus on human-subject/patient data and longitudinal data.

## Documentation

[Chiron Developer Documentation](https://cchmc.github.io/is4r-chiron/)
- Developer documentation for setting up a Chiron instance with your own datasets.

[Chiron User Documentation](https://ri-ds.github.io/chiron_user_docs/)
- We've also started creating documentation for end users.

The following resources require permission to access:

- [GitHub repo](https://github.com/cchmc/is4r-chiron)
- [GitHub repo for new UI](https://github.com/cchmc/is4r-chiron-ui)
- [Chiron Confluence Space](https://confluence.research.cchmc.org/display/CHIR/Chiron)
- [Chiron Jira Project](https://jira.research.cchmc.org/projects/CHIR/summary)

## Install the library as a pip package

You can remove the @branch if you just want the master branch
```shell
pip install <repo_url>@branch#egg=chiron
```


Example
```shell
pip install git+https://github.com/cchmc/is4r-chiron.git@v6.3.1#egg=chiron
```

## Install source code for development

get the latest develop version
```shell
git clone https://github.com/cchmc/is4r-chiron.git
cd is4r-chiron
git checkout develop
```

choose one install option
```shell
# standard install (includes packages needed for linting and testing)
pip install -r requirements/dev.txt

# minimal install (only packages required to run chiron)
pip install -r requirements/base.txt

# docs install (includes packages needed for linting, testing, and building
# documentation)
pip install -r requirements/docs.txt
```

If you have any concepts using the ontology datatype (introduced in version
6.5), you should install those requirements in addition to whichever  install
option you selected above.
```shell
pip install -r requirements/ontologies.txt
```

## Linting and formatting code

Run these commands from the repo root directory.
```shell
ruff check
ruff format
```

## Running tests

You'll need to configure your test environment first, especially defining
database connections.

Run these commands from the repo root directory.
```shell
python -m pytest
```

[More info about the Test Project](https://cchmc.github.io/is4r-chiron/topics/tests.html)

## Building Documentation

Make sure you have all the dependencies installed from `requirements/docs.txt`.

```shell
cd docs
sphinx-build -b html . ../../chiron_docs
```

## Chiron Test Project

There is an included Django project that is used for running tests. You
can run this project with the Django dev server same as with any Django
project.

```shell
cd test_project
python manage.py restore_test_project_state
python manage.py runserver
```

[More info about the Test Project](https://cchmc.github.io/is4r-chiron/topics/tests.html)


### Optional Ontology Testing

first install latest version of ontology app ` pip install git+https://{YOUR GITHUB TOKEN}@github.com/cchmc/is4r-chiron-ontology.git@develop`

then, in your settings_custom.py and test_settings_custom.py add ontologies to your installed apps,
migrate if you have to
```
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "crispy_forms",
    "rest_framework",
    "chiron",
    "ontologies",
    "main",
    "patient_models",
]
```

if you want to run the tests without ontologies, makes sure the CHIRON_TREAT_ONTOLOGY_CONCEPTS_AS_TEXT setting is True, otherwise it raises an error

you will have to run the `ontology_load --o source_data/ontology_source/fyler_test.json` management command from  to create the test ontology data.

after that, you can run `python manage.py restore_test_project_state` to run the etl with the new ontology concept.

## Chiron Performance Project

There is also an included Django project that is used for testing performance.
So far we've been using it intermittently as needed, so it's not always kept
up to date.

[More info about the Performance Project](https://cchmc.github.io/is4r-chiron/topics/utilities/performance_testing.html)

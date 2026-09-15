# Chiron Tests

Chiron is set up as a Django app only. So it needs to be integrated into a Django project in order to be fully functional.

Rather than try to run tests on Chiron by itself, we have a small Django project "Test Project" that is used for automated tests. In addition to making it easier to run Chiron for testing, the Test Project has several pre-defined resources: test source data (csv files and Django models), test datasets using that source data, and a test admin user with test reports. These resources are all available to use in tests instead of building everything from scratch.

## How to run the tests

The Test Project and all tests are directly in the Chiron repo. You'll need Python 3 and a PostgreSQL server.

If you haven't already, clone the repo and install requirements
```shell
git clone https://github.com/cchmc/is4r-chiron.git
python3 -m venv env
source env/bin/activate
cd is4r-chiron
pip install -r requirements.txt
```

Default Django settings for tests are in `test_project/test_settings.py`. By default, both the Django database and the research database use a single PostgreSQL database with the following settings:
- database name: chiron
- user: postgres
- password: postgres

You can override any of these settings by creating a file `test_project/test_settings_custom.py` and adding the custom settings you want. This file is in the `.gitignore`. For example, if you wanted to use SQLite3 as the Django test database and to change the database name and credentials for the Posgres research database:

```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(os.path.join(BASE_DIR, "db.sqlite3")),
    }
}

CHIRON_SQL_ALCHEMY_CONNECTION_STRING = (
    "postgresql://myusername:mypw@localhost:5432/chiron_tests"
)
```
Django always creates databases for testing from scratch, and should destroy them automatically when the tests finish. Chiron custom code follows the same behavior and should automatically remove any (SQL Alchemy) research databases and any files (like fixtures) it creates during tests. If any created databases or files aren't removed, that indicates there's a problem with how the tests are configured.

Once you've finished customizing Django settings for your environment, you can go ahead and run the tests. Note, these are run from the repo root directory, not the `test_project` directory.

```shell
python -m pytest
```

## How to view the Test Project

The Test Project can be run with the Django dev server just like any Django project. This can be useful for troubleshooting failing tests and for adding new data dictionary elements or reports to use in new tests.

If you haven't already, clone the repo and install requirements
```shell
git clone https://github.com/cchmc/is4r-chiron.git
python3 -m venv env
source env/bin/activate
cd is4r-chiron
pip install -r requirements.txt
```

The Django test server will use settings file `test_project/project/setting.py`. You can override any of these settings by creating a file `test_project/project/settings_custom.py` and adding the custom settings you want.

Now you should be able to run Test Project using the Django dev server:
```shell
cd test_project

# create data schemas, load default users and data, run the etl
python manage.py restore_test_project_state

# start the Django server
python manage.py runserver
```
  
  View your site in a web browser at `http://localhost:8000`.

## How to get existing resources for tests

To take advantage of pre-defined source data, chiron datasets, and chiron reports you need to load them. For Chiron tests, we're doing this at the class level using the `setUpTestData()` method. There's also a `setUp()` method, but I've managed to avoid using that so far. Just a quick comment on the difference:

- **setUp()/tearDown()** - Django automatically starts a fresh application instance and creates fresh, empty database(s) for each test method. These methods are used for any custom database/application setup you want to do before a test method runs, and any custom teardown you need to do to make sure everything the test created gets destroyed. Importantly, these methods are run once for each test method, so any system state changes in one test method will not affect other test methods.
- **setUpTestData()** - A class-level method that actually only runs once regardless of how many test methods your class has. It uses various tricks such as database transactions/rollbacks to simulate the behavior of `setUp()`. The advantage is it can be run faster.

See the Django documentation for more info about all the different ways you can do setup/teardown for tests.

Here's how you can use `setUpTestData()` to get existing resources to use in your test:
```python
from .utils.base_testcase import BaseTestCase

class MyTest(BaseTestCase):

    @classmethod  
    def setUpTestData(cls):  
        # There is one Django app with patient data models you can
        # use as source data. The following method populates these
        # models from a fixture file. This data is used by DS3,
        # so you should always run this before loading that dataset.
        cls.load_patient_model_app_data()

        # The following method initializes your chiron data dictionary
        # with 3 stored datasets (DS1_STORED, DS2_STORED, DS3_STORED)
        # and loads all saved reports. You should always run this
        # unless you want to test an empty Chiron system on purpose.
        # Note that this does not actually load any research data.
        cls.initialize_chiron()

        # To load the actual research data for a dataset, use this 
        # method with the class constant identifier for the dataset.
        cls.load_dataset(cls.DS1_STORED)
        cls.load_dataset(cls.DS2_STORED)
        ...

        # There are also several datasets defined as autocreate source
        # lists. You can autocreate one of theses datasets and load
        # its research data with the same method as for stored datasets.
        cls.load_dataset(cls.DS3_AUTO_C2)
        cls.load_dataset(cls.DS3_AUTO_C3)
        ...

        # If instead you just want to autocreate the data dictionary
        # for the dataset but not actually load any data, use this method
        # instead.
        cls.load_dataset_dd(cls.DS3_AUTO_C2)

    ...
```

## How to get or create users for tests

After you run `cls.initialize_chiron()`, there will be 3 Django users:

**admin**
    - Django superuser
    - has full access (including PHI) to dataset1_stored, dataset2_stored, dataset3_stored
    - owns all Chiron reports that are used to test report system
**demouser**
- for dataset1_stored
    - has "deid" access level
    - is in the "married" permission group which only allows access to married subjects and has some additional limits on concepts/categories that can be viewed
- no access to any other datasets
**agguser**
- for dataset1_stored
    - has "agg" access level
    - can see all subjects and concepts (within the limits set by the "agg" access level)
- no access to any other datasets

While these users are technically available to use in tests, I typically don't. Users are easy to set up, so for tests I prefer to explicitly define the users and their permissions. I define the user and their permissions in the `setUpTestData()` method, then I create the user directly in a test method using the `setup_user()` method.

```python
from .utils.base_testcase import BaseTestCase

class MyTest(BaseTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.initialize_chiron()
        cls.load_dataset(cls.DS1_STORED)

        # Define a couple users. See parameters for 
        # `BaseTestCase.setup_user()` for all available options.
        # Note, you couldn't create the user oject here as a class
        # property because of the unique limitations of setUpTestData()
        # - namely, all class properties must be duplicatable with
        # copy.deepcopy().
        cls.testuser1 = {
            "dataset_name": cls.DS1_STORED,
            "username": "testuser1",
            "access_level": "deid",
            "permission_groups": ["married"],
        }
        cls.testuser2 = {
            "dataset_name": cls.DS1_STORED,
            "username": "testuser2",
            "access_level": "agg",
            "permission_groups": ["all"],
        }

    def test_myfirsttest(self):
        # creates the Django User and ChironUser(s), logs them in,
        # and starts a session with the specified dataset
        # `cls.DS1_STORED`.
        self.setup_user(**self.testuser1)
        ...
        
    def test_mysecondtest(self):
        # Note you can also get the ChironUser model object back,
        # which can be used to get the Dataset and Django User
        # model objects if needed.
        oChironUser = self.setup_user(**self.testuser2)
        oDataset = oChironUser.dataset
        oUser = oChironUser.user
        ...
```


## How to make changes to pre-defined resources

If the existing Test Project resources don't cover the needs for your test, you have a few options:

1. Create the resource (dataset, collection, concept, report, etc.) yourself in your test class code.
2. Get an existing resource and modify it to what you need in your test class code.
3. Create new pre-defined Test Project resources. These will then be available for any test class to use.

Be careful about editing existing resources. If you edit something already being used by tests, you could break those tests. In general, it's safer to add new resources unless you've checked carefully how an existing resource is currently being used.

The first step will be to set up and run the test project using the Django development server. See "How to view the Test Project". You should then be able to view the test project (with all the pre-defined resources) at "http://localhost:8000".

From this point, the basic workflow will be the same regardless of what resources you're changing or adding the the Test Project.
1. Use the running Test Project instance to make whatever changes/additions you want.
2. Backup those changes to code (into fixture files) with the provided script:
```shell
python manage.py save_test_project_state
```
3. Check the fixture files to make sure the changes are what you expected
    - Changes to stored datasets will end up in `test_project/chiron_config/backups/full_dd.json`
    - Changes to reports, users, or user permissions will end up in `test_project/test_project.json`
    - Changes to the `patient_model` app data (used as a Chiron data source for dataset3) will end up in `test_project/patient_model_data.json` 
4. Your changes should now be available to all Chiron tests. Write your new tests using your new/modified resources.
5. Save the updated fixture files to the code repo alongside your new test code.

### Example 1: create a new test report

Reports must have an owner. You should use the "admin" user unless there's a good reason not to.

Log in as "admin" and select the dataset you're interested in. Then build a report like usual using the Query View and the Results View. Save the report with a meaningful name, description, and project to help other developers understand what the report is testing.

Run `save_test_project_state` and you should be able to see the changes in `test_project/test_project.json` using `git staging` and `git diff`. That's it, you can start using the new report in your tests.

### Example 2: Add a new collection and a new source model for it

In this example we will add a new collection to dataset3 and create a new model in the patient_models app with dummy data to populate the collection.

Log in as "admin" and select dataset3_stored. Because the stored test datasets are so heavily customized, I don't try to use autocreate to manage them. The easiest way to make changes is probably the Django Admin.

Start by making a new Django model in `test_project/patient_models/models.py`. This will hold the source data that Chiron imports during the ETL. Once your model is ready, make a new migration file for it and run migrations to update your database.

```shell
python manage.py makemigrations patient_models
python manage.py migrate
```

Next, register the model with Django Admin `test_project/patient_models/admin.py`. Now you should be able to see the model in your Django Admin. Use this to add the dummy data you want for your tests.

Next, create the new data dictionary elements you want. You'll need a Collection record, one Concept record for each concept in your collection, a Source record (that will reference the Django model you just created), and maybe a Category record for adding those concepts to the Concept hierarchy. Rather than adding model objects from scratch, it's often easiest to start with a similar record and use "Add as new" to duplicate it. Then just change the field values that are different.

To test if your ETL works correctly, you can run `python manage.py chiron_run_etl` and select the appropriate dataset. Then once you're satisfied with everything, you can run `python manage.py save_test_project_state`.

At this point, you should see changes to the following files:
- `test_project/patient_models/models.py` - your new source model
- `test_project/patient_models/admin.py` - registering your new source model with the Django Admin
- `test_project/patient_models/migrations/*.py` - the migration for your new source model
- `test_project/patient_model_data.json` - the dummy data for your new source model
- `test_project/chiron_config/backups/full_dd.json` - the new Chiron collection and related concepts, sources, etc.

You can now start using the new collection in your tests.


## How to reset the Test Project

If you start making changes to resources in the Test Project an it doesn't go well, you may get to a point where you want to abort and start over from scratch.

To do this, just erase the Django database for the Test Project. If you're using default settings, you will do this by deleting `test_project/db.sqlite3`. Then rerun the command to restore it like new:

```shell
python manage.py restore_test_project_state
```



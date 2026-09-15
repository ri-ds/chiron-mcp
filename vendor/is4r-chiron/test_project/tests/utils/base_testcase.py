import json
import os

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from django.core.management import call_command
from chiron.models import ChironUser, PermissionGroup, Dataset, Concept
from chiron.etl import ChironEtl
from chiron.query_engine import get_db_writer
from rest_framework.reverse import reverse
from main.utils import setup_default_chironuser_permission_groups


class BaseTestCase(APITestCase):
    """
    Testing datasets that load from fixture with initialize_dd():
        - dataset1_stored
            - fairly complex dataset used to test reports and concept stats
            - used to test data access permission on a single dataset

        - dataset2_stored
            - used to test autocreate and ETL from CSV files (subject matching, etc.)
            - used in combination with default to test multi-dataset systems handling dataset
              permissions
            - used to test complex subject matching
            - used to test some custom ETL processors like detailed age, deid id

        - dataset3_stored
            - used to test autocreate and ETL from Django models (subject matching, etc.)
            - used to test complex collection relationships, m:m subcollections

    Testing datasets that are autocreated using load_dataset_dd():
        - dataset2_autocreated
            - same as dataset2_stored that can be loaded from a fixture

        - dataset3_autocreated
            - similar to dataset3_stored that can be loaded from a fixture
            - additional customization is done with management command "pm_customize_chiron_dd"

        - dataset3_autocreated_copy2, dataset3_autocreated_copy3
            - configured exactly like dataset3_autocreated
            - used to test for errors caused by multi-dataset systems, especially name clashes

    """

    expected_data_dir = "test_project/tests/expected_data/"
    expected_stat_dir = "test_project/tests/expected_stats/"
    maxDiff = None  # show full difference when two long strings don't match

    DS1_STORED = "dataset1_stored"
    DS2_STORED = "dataset2_stored"
    DS3_STORED = "dataset3_stored"
    DS2_AUTO = "dataset2_autocreated"
    DS3_AUTO = "dataset3_autocreated"
    DS3_AUTO_C2 = "dataset3_autocreated_copy2"
    DS3_AUTO_C3 = "dataset3_autocreated_copy3"

    @classmethod
    def tearDownClass(cls):
        for dataset in Dataset.objects.all():
            writer = get_db_writer(dataset, use_staging=False)
            writer.delete_existing_data()
        super().tearDownClass()

    @classmethod
    def load_dataset_dd(cls, dataset_unique_id):
        """
        Will load the data dictionary for specified dataset. The method used to create the
        data dictionary depends on the dataset.
        """
        if dataset_unique_id == "dataset3_autocreated_copy2":
            # used to test autocreate and ETL from django models
            call_command("chiron_autocreate_dd", "dataset3_autocreated_copy2")
            call_command("pm_customize_chiron_dd")
        elif dataset_unique_id == "dataset3_autocreated_copy3":
            # exact duplicate of dataset3_autocreated_copy2 used to test for handling of name
            # clashes
            call_command("chiron_autocreate_dd", "dataset3_autocreated_copy3")
        elif dataset_unique_id == "dataset2_autocreated":
            call_command("chiron_autocreate_dd", "dataset2_autocreated")
        oDataset = Dataset.objects.get(unique_id=dataset_unique_id)
        return oDataset

    @classmethod
    def initialize_ontology(cls):
        """
        Tries to import the ontologies module, returns if not found, otherwise
        it loads the fyler ontology data into the database
        """
        try:
            import ontologies.interface_class  # noqa: F401

            call_command(
                "ontology_load", "--o", "test_project/source_data/ontology_source/fyler_test.json"
            )
        except ModuleNotFoundError:
            print("Ontology module not found, ")
        return

    @classmethod
    def initialize_chiron(cls):
        """
        Sets up the database and data dictionary with three stored datasets.
        Loads test users ("admin", "demouser", "agguser") and their saved
        reports needed for some tests.
        """
        cls.initialize_ontology()
        call_command("chiron_restore_dd")
        call_command("loaddata", "test_project/test_project.json")
        setup_default_chironuser_permission_groups()

    @classmethod
    def load_patient_model_app_data(cls):
        """
        Loads saved data for models in the patient_model app.
        """
        call_command("loaddata", "test_project/patient_model_data.json")

    @classmethod
    def load_dataset(cls, dataset_unique_id):
        """
        Mimics `chiron_run_etl` management command. If you try to run it in setUpTestData()
        using Django's call_command() method, you'll get an error related to transactions.
        """
        oDataset = cls.load_dataset_dd(dataset_unique_id)
        create_log = False
        notification_count = 1000
        source = None
        track_subject_matching = False
        abbreviated = False
        etl = ChironEtl(
            oDataset.id,
            notification_count,
            create_log,
            source,
            track_subject_matching,
            abbreviated,
            refresh_database_connections=False,
        )

        etl.run()

    @classmethod
    def chiron_run_single_etl(cls, dataset_unique_id, source_name=None):
        oDataset = cls.load_dataset_dd(dataset_unique_id)
        create_log = False
        notification_count = 1000
        source = None
        track_subject_matching = False
        abbreviated = False
        etl = ChironEtl(
            oDataset.id,
            notification_count,
            create_log,
            source,
            track_subject_matching,
            abbreviated,
            refresh_database_connections=False,
            force_single_source=False,
        )

        etl.run()

    def setup_user(
        self,
        dataset_name,
        username,
        access_level=None,
        permission_groups=None,
        addl_dataset_access=None,
        start_session=True,
    ):
        """Creates a Django user, logs the user in, creates an associated ChironUser for the
        specified dataset, starts a session for that dataset, and returns the ChironUser object.

        - If access_level or permission_groups are set to None, Chiron will set default values.
        - If you want the user to also have access to other datasets, use the addl_dataset_access
          parameter.
        - If you want to create just a Django user with no access to datasets, set dataset_name
          and addl_dataset_access to None.
        - If you don't want to log the user in or start a dataset session, use start_session=False.
        """
        oUser, created = get_user_model().objects.get_or_create(username=username)
        oChironUser = None
        if start_session:
            self.log_in(oUser)
        if dataset_name:
            oDataset = Dataset.objects.get(unique_id=dataset_name)
            oChironUser = self._create_chironuser(
                oUser, oDataset, access_level=access_level, permission_groups=permission_groups
            )
        if addl_dataset_access:
            for entry in addl_dataset_access:
                o = Dataset.objects.get(unique_id=entry["dataset_name"])
                oChironUser = self._create_chironuser(
                    oUser,
                    o,
                    access_level=entry.get("access_level", None),
                    permission_groups=entry.get("permission_groups", None),
                )
        if start_session and dataset_name:
            self.start_dataset_session(oDataset)
        return oChironUser

    def _create_chironuser(self, user, dataset, access_level=None, permission_groups=None):
        """
        Creates a Chironuser for the specified user/dataset.

        note: This does not use the defaults defined in the Dataset model. To create a chironuser
        with default permissions for this dataset, simply start doing queries without explicitly
        creating a chironuser.

        :param access_level: specify access level or None for default ("deid")
        :type access_level: str, optional
        :param permission_groups: specify permission groups or None for no permission groups
        :type permission_groups: list of strings
        """
        chironuser, created = ChironUser.objects.get_or_create(user=user, dataset=dataset)
        if access_level:
            chironuser.access_level = access_level
            chironuser.save()
        if permission_groups:
            for group_name in permission_groups:
                oPG = PermissionGroup.objects.get(name=group_name)
                chironuser.permission_groups.add(oPG)
        return chironuser

    def log_in(self, user):
        """force login the specified Django user"""
        self.client.force_login(user=user)

    def start_dataset_session(self, dataset, follow=False):
        """selects dataset for this session, first run log_in for the user you want to use"""
        url = reverse("chiron:select_dataset")
        data = {"dataset_id": dataset.id}
        response = self.client.post(url, data, follow=follow)
        return response

    def check_report(self, report_id, datafile_name):
        """
        Get the specified report and test against a saved copy.

        query like:
        http://localhost:8000/api/report_tools/75/export_json/
        """
        url = reverse("chiron:api:report_tools-list") + "{}/export_json/".format(report_id)
        data = {}
        response = self.client.get(url, data)
        self.assertEqual(response.status_code, 200)
        output = response.json()
        with open("{}{}".format(self.expected_data_dir, datafile_name), encoding="utf-8") as f:
            expected = json.load(f)
        if output["records"] != expected:
            print("failed report id: ", report_id)
            print("expected", expected)
            print("output", output["records"])

        self.assertEqual(output["records"], expected)

    def check_stats(
        self, oDataset, concept_id, datafile_name, startswith_match=False, prefilter_value=None
    ):
        """
        Get stats for the specified concept in the specified dataset and compare against the
        specified datafile for a match. Use startswith_match=True if you don't know the exact
        ID of your concept.

        http://localhost:8000/api/concepts/[concept_id]/cohort_def_callback/
        """
        if startswith_match:
            oConcept = Concept.objects.filter(
                collection__dataset=oDataset.id, permanent_id__startswith=concept_id
            ).first()
        else:
            oConcept = Concept.objects.filter(
                collection__dataset=oDataset.id, permanent_id__startswith=concept_id
            ).first()
        url = reverse("chiron:api:concepts-list") + "{}/cohort_def_callback/".format(
            oConcept.permanent_id
        )
        data = {}
        if prefilter_value:
            data["prefilter_value"] = prefilter_value
        response = self.client.get(url, data)
        # print("resp", response.json())
        self.assertEqual(response.status_code, 200)
        output = response.json()
        with open(os.path.join(self.expected_stat_dir, datafile_name), encoding="utf-8") as f:
            expected = json.load(f)
        # if we're not matching the concept ID exactly, we need to take it out before comparing
        if startswith_match:
            del output["permanent_id"]
            del expected["permanent_id"]
        if not self.assertEqual(output, expected):
            print("failed dataset: ", datafile_name)

    def check_stats_are_blocked(
        self, oDataset, concept_id, startswith_match=False, prefilter_value=None
    ):
        """
        Get stats for the specified concept in the specified dataset and compare against the
        specified datafile for a match. Use startswith_match=True if you don't know the exact
        ID of your concept.

        http://localhost:8000/api/concepts/[concept_id]/cohort_def_callback/
        """
        if startswith_match:
            oConcept = Concept.objects.filter(
                collection__dataset=oDataset.id, permanent_id__startswith=concept_id
            ).first()
        else:
            oConcept = Concept.objects.filter(
                collection__dataset=oDataset.id, permanent_id__startswith=concept_id
            ).first()
        url = reverse("chiron:api:concepts-list") + "{}/cohort_def_callback/".format(
            oConcept.permanent_id
        )
        data = {}
        if prefilter_value:
            data["prefilter_value"] = prefilter_value
        response = self.client.get(url, data)
        self.assertEqual(response.status_code, 403)

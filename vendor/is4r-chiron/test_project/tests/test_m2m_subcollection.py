# from django.test import TestCase

from .utils.base_testcase import BaseTestCase
from chiron import chiron_settings


class M2MSubCollectionTest(BaseTestCase):
    """
    Tests concept statistics and reports for subcollections with a many:many relationship to
    subject. The main risk in this situation is that a subcol record associated with multiple
    subjects gets counted more than once.
    """

    @classmethod
    def setUpTestData(cls):
        chiron_settings.CHIRON_GET_QUERY_PERFORMANCE = False

        # populate patient data tables that will be used as sources
        cls.load_patient_model_app_data()

        # create data dictionary for some other datasets
        # This is just to make sure having multiple datasets doesn't break any of our tests.
        cls.initialize_chiron()
        cls.load_dataset(cls.DS3_STORED)
        cls.testuser = {
            "dataset_name": cls.DS3_STORED,
            "username": "testuser",
        }

    def test_m2m_autocreate_and_etl(self):
        """Check functioning of autocreate and ETL for various data"""
        oChironUser = self.setup_user(**self.testuser)
        oDataset = oChironUser.dataset
        # look at a concept to make sure the data is loaded
        fields = {
            "m2m_id_field_": "stat43.json",
        }
        for concept_id, filename in fields.items():
            self.check_stats(oDataset, concept_id, filename, startswith_match=True)

    def test_m2m_report_aggregation_for_count_and_list(self):
        """M2M subcollections check that count and list aggregation all work correctly"""
        self.setup_user(**self.testuser)
        for i in range(113, 121):
            self.check_report(i, f"query{i}.json")

    def test_m2m_concept_stats(self):
        """Check that different concept datatypes for m2m subcol return correct stat info"""
        oChironUser = self.setup_user(**self.testuser)
        oDataset = oChironUser.dataset
        fields = {
            # standard category field
            "m2m_category_field_": "stat44.json",
            # category field that includes empty values
            "m2m_sometimes_field_": "stat45.json",
            # all the other data types
            "m2m_text_field_": "stat46.json",
            "m2m_date_field_": "stat47.json",
            "m2m_integer_field_": "stat48.json",
            "m2m_float_field_": "stat49.json",
            "m2m_boolean_field_": "stat50.json",
            "m2m_integer_category_field_": "stat51.json",
            "m2m_float_category_field_": "stat52.json",
        }
        for concept_id, filename in fields.items():
            self.check_stats(oDataset, concept_id, filename, startswith_match=True)

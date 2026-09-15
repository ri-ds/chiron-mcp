# from django.test import TestCase

from .utils.base_testcase import BaseTestCase


class DjangoEtlTest(BaseTestCase):
    """
    Tests autocreate and ETL for some django models
    """

    @classmethod
    def setUpTestData(cls):
        # populate patient data tables that will be used as sources
        cls.load_patient_model_app_data()
        cls.initialize_chiron()
        cls.load_dataset(cls.DS3_AUTO_C2)
        cls.load_dataset(cls.DS3_AUTO_C3)
        cls.testuser = {
            "dataset_name": cls.DS3_AUTO_C2,
            "username": "testuser",
        }

    def test_django_autocreate(self):
        """Check configuration of data dict and data after autocreating from Django models"""
        oChironUser = self.setup_user(**self.testuser)
        oDataset = oChironUser.dataset
        self.check_stats(oDataset, "subject_field_", "stat36.json", startswith_match=True)

    def test_django_autocreate_concept_types(self):
        """Check functioning of autocreate and ETL for various data"""
        oChironUser = self.setup_user(**self.testuser)
        oDataset = oChironUser.dataset
        fields = {
            "boolean_field_": "stat37.json",
            "category_field_": "stat38.json",
            "date_field_": "stat39.json",
            "float_field_": "stat40.json",
            "integer_field_": "stat41.json",
            "text_field_": "stat42.json",
        }
        for concept_id, filename in fields.items():
            self.check_stats(oDataset, concept_id, filename, startswith_match=True)

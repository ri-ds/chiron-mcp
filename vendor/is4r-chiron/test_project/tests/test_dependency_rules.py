from django.db.models.deletion import ProtectedError

from .utils.base_testcase import BaseTestCase
from chiron.models import Dataset, Source
from chiron.data_dictionary.validate import validate_data_dictionary


class DependencyRuleTests(BaseTestCase):
    """
    Tests output of reports involving relationships between subcollections (defined in the
    SubcollectionRelationship model).
    """

    @classmethod
    def setUpTestData(cls):
        cls.load_patient_model_app_data()
        cls.initialize_chiron()

    def test_data_dict_validation_no_problems(self):
        """stored dataset shouldn't have any validation issues"""
        oDataset = Dataset.objects.get(unique_id=self.DS3_STORED)
        validation_rules = validate_data_dictionary(oDataset)
        self.assertEqual(len(validation_rules), 0)

    def test_data_dict_validation_source_source_dependency_run_after(self):
        """Error when dependent source is run too late"""
        oDataset = Dataset.objects.get(unique_id=self.DS3_STORED)
        validation_rules = validate_data_dictionary(oDataset)
        self.assertEqual(len(validation_rules), 0)

        oSource = Source.objects.get(collection__dataset=oDataset, name="Subject")
        oSource.execution_order = 500
        oSource.save()

        validation_rules = validate_data_dictionary(oDataset)
        self.assertNotEqual(len(validation_rules), 0)

    def test_data_dict_validation_source_source_dependency_missing(self):
        """Error when dependent source is not run"""
        oDataset = Dataset.objects.get(unique_id=self.DS3_STORED)
        validation_rules = validate_data_dictionary(oDataset)
        self.assertEqual(len(validation_rules), 0)

        oSource = Source.objects.get(collection__dataset=oDataset, name="Subject")
        oSource.exclude_from_etl = True
        oSource.save()

        validation_rules = validate_data_dictionary(oDataset)
        self.assertNotEqual(len(validation_rules), 0)

    def test_source_source_dependency_deletion_attempt(self):
        """Error when attempt to delete dependent source"""
        oDataset = Dataset.objects.get(unique_id=self.DS3_STORED)
        validation_rules = validate_data_dictionary(oDataset)
        self.assertEqual(len(validation_rules), 0)

        oSource = Source.objects.get(collection__dataset=oDataset, name="Subject")
        oSource.exclude_from_etl = True
        with self.assertRaises(ProtectedError):
            oSource.delete()

    def test_data_dict_validation_concept_source_dependency_run_after(self):
        """Error when dependent source is run too late"""
        oDataset = Dataset.objects.get(unique_id=self.DS3_STORED)
        validation_rules = validate_data_dictionary(oDataset)
        self.assertEqual(len(validation_rules), 0)

        oSource = Source.objects.get(
            collection__dataset=oDataset, name="SubColComplexSubjectMatching"
        )
        oSource.execution_order = 500
        oSource.save()

        validation_rules = validate_data_dictionary(oDataset)
        self.assertNotEqual(len(validation_rules), 0)

    def test_data_dict_validation_concept_source_dependency_missing(self):
        """Error when dependent source is not run"""
        oDataset = Dataset.objects.get(unique_id=self.DS3_STORED)
        validation_rules = validate_data_dictionary(oDataset)
        self.assertEqual(len(validation_rules), 0)

        oSource = Source.objects.get(
            collection__dataset=oDataset, name="SubColComplexSubjectMatching"
        )
        oSource.exclude_from_etl = True
        oSource.save()

        validation_rules = validate_data_dictionary(oDataset)
        self.assertNotEqual(len(validation_rules), 0)

    def test_concept_source_dependency_deletion_attempt(self):
        """Error when concept-source dependency attempt to delete"""
        oDataset = Dataset.objects.get(unique_id=self.DS3_STORED)
        validation_rules = validate_data_dictionary(oDataset)
        self.assertEqual(len(validation_rules), 0)

        oSource = Source.objects.get(
            collection__dataset=oDataset, name="SubColComplexSubjectMatching"
        )
        oSource.exclude_from_etl = True
        with self.assertRaises(ProtectedError):
            oSource.delete()

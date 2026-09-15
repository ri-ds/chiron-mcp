import shutil

# from django.test import TestCase
from django.core.management import call_command
from django.core.exceptions import ObjectDoesNotExist

from .utils.base_testcase import BaseTestCase
from chiron.models import Dataset
from chiron.models import SourceSourceDependency, ConceptSourceDependency


class BackupRestoreTest(BaseTestCase):
    """
    Tests management commands chiron_backup_dd, chiron_restore_dd, chiron_backup_dataset
    chiron_restore_dataset
    """

    @classmethod
    def setUpTestData(cls):
        # populate patient data tables that will be used as sources
        cls.load_patient_model_app_data()
        cls.initialize_chiron()
        cls.load_dataset(cls.DS3_STORED)
        cls.load_dataset(cls.DS3_AUTO_C2)
        cls.load_dataset(cls.DS3_AUTO_C3)

    def tearDown(self):
        # remove any backups that were created; runs after each test
        shutil.rmtree("tmp_backup")

    def test_backup_restore_dataset(self):
        """
        Check that backing up and restoring the data dictionary for a dataset leaves the
        state unchanged.
        """
        self.check_dataset()
        call_command(
            "chiron_backup_dataset",
            "dataset3_autocreated_copy2",
            "--overwrite",
            "--backup-dir=tmp_backup",
        )
        call_command(
            "chiron_restore_dataset",
            "dataset3_autocreated_copy2.json",
            "--overwrite",
            "--backup-dir=tmp_backup",
        )
        self.check_dataset()

    def test_backup_drop_restore_dataset(self):
        """
        Check workflow backup a dataset, drop the dataset, then restore the dataset.
        - the data dict for the dataset should be gone after dropping
        - the data dict for the dataset should be returned to original state after restore
        - the chironuser(s) for the dataset should be lost
        """
        self.check_dataset()
        call_command(
            "chiron_backup_dataset",
            "dataset3_autocreated_copy2",
            "--overwrite",
            "--backup-dir=tmp_backup",
        )
        call_command("chiron_drop_dataset", "dataset3_autocreated_copy2")
        #
        with self.assertRaises(ObjectDoesNotExist):
            self.check_dataset()
        call_command(
            "chiron_restore_dataset",
            "dataset3_autocreated_copy2.json",
            "--backup-dir=tmp_backup",
        )
        # TODO: check if chironuser is gone
        self.check_dataset()

    def test_backup_restore_dataset_dependency_rules(self):
        """
        Some fetures, such as depencency rules, don't exist on autocreated datasets and don't
        affect queries. So we have this separate test to make sure that backup/restore preserves
        those features.
        """
        initial_rule_counts = self.get_depencency_rule_counts()
        call_command(
            "chiron_backup_dataset",
            "dataset3_stored",
            "--overwrite",
            "--backup-dir=tmp_backup",
        )
        call_command(
            "chiron_restore_dataset",
            "dataset3_stored.json",
            "--overwrite",
            "--backup-dir=tmp_backup",
        )
        self.compare_dependency_rule_counts(initial_rule_counts)

    def test_backup_drop_restore_dataset_dependency_rules(self):
        """ "
        Some fetures, such as depencency rules, don't exist on autocreated datasets and don't
        affect queries. So we have this separate test to make sure that backup/drop/restore
        preserves those features.
        """
        initial_rule_counts = self.get_depencency_rule_counts()
        call_command(
            "chiron_backup_dataset",
            "dataset3_stored",
            "--overwrite",
            "--backup-dir=tmp_backup",
        )
        call_command("chiron_drop_dataset", "dataset3_stored")
        call_command(
            "chiron_restore_dataset",
            "dataset3_stored.json",
            "--backup-dir=tmp_backup",
        )
        self.compare_dependency_rule_counts(initial_rule_counts)

    def get_depencency_rule_counts(self):
        oDataset = Dataset.objects.get(unique_id="dataset3_stored")
        counts = {}
        counts["source_source"] = SourceSourceDependency.objects.filter(
            source__collection__dataset=oDataset
        ).count()
        counts["concept_source"] = ConceptSourceDependency.objects.filter(
            concept__source__collection__dataset=oDataset
        ).count()
        # TODO: I don't have any concept-concept dependencies yet
        # counts["concept_concept"] = ConceptConceptDependency.objects.filter(
        #     concept__source__collection__dataset=oDataset
        # ).count()
        return counts

    def compare_dependency_rule_counts(self, rule_counts):
        """returns true if current rule counts match the rule counts passed"""
        new_counts = self.get_depencency_rule_counts()
        for key, count in rule_counts.items():
            self.assertEqual(count, new_counts[key])
            self.assertNotEqual(count, 0)

    def check_dataset(self):
        """
        Perform some repeatable checks to verify the dataset is still loaded correctly
        """
        oDataset = Dataset.objects.get(unique_id=self.DS3_AUTO_C2)
        self.setup_user(self.DS3_AUTO_C2, "testuser")
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

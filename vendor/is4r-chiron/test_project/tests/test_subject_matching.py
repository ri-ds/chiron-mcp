# from django.test import TestCase

from .utils.base_testcase import BaseTestCase


class SubjectMatchingTest(BaseTestCase):
    """
    Tests autocreate and ETL where there are complex subject matching rules
    (for both CSV and Django data)
    """

    @classmethod
    def setUpTestData(cls):
        # populate patient data tables that will be used as sources
        cls.load_patient_model_app_data()
        cls.initialize_chiron()
        cls.load_dataset(cls.DS2_STORED)
        cls.load_dataset(cls.DS3_STORED)
        cls.testuser2 = {
            "dataset_name": cls.DS2_STORED,
            "username": "testuser",
            "access_level": "phi",
        }
        cls.testuser3 = {
            "dataset_name": cls.DS3_STORED,
            "username": "testuser",
            "access_level": "phi",
        }

    # TODO: this test was designed to run directly against MongoDB. It would need to be modified
    #   before it can be run against Postgres.
    # def test_load_multiple_ids(self):
    #     """Check that id, ssn, and passport_number were all loaded"""
    #     oDataset = self.setup_dataset2_testuser()
    #
    #     # TODO: could eventually test this using a report by pulling ID fields into concepts,
    #     #   for now check against mongo database directly
    #
    #     # check that subject ids (id, ssn, and passport_number) all loaded correctly
    #     subject_col = get_subject_mongo_col(oDataset)
    #     subjects = list(subject_col.find({"_ids.ssn": "999-73-5361"}))
    #     self.assertEqual(len(subjects), 1)
    #     doc = subjects[0]
    #     self.assertEqual(doc["_ids"]["passport_number"], "X88275464X")
    #     self.assertEqual(doc["_ids"]["id"], "034e9e3b-2def-4559-bb2a-7850888ae060")
    #
    #     # check handling of missing value for passport number
    #     subject_col = get_subject_mongo_col(oDataset)
    #     subjects = list(subject_col.find({"_ids.ssn": "999-52-4112"}))
    #     self.assertEqual(len(subjects), 1)
    #     doc = subjects[0]
    #     self.assertNotIn("passport_number", doc["_ids"])
    #     self.assertEqual(doc["_ids"]["id"], "ggggg-patient-with-no-subcollections")

    def test_complex_subject_matching_csv(self):
        """Encounters match on an alternative subject ID field (passport_number), and don't
        get created ("skip") if no match.
        """
        self.setup_user(**self.testuser2)
        self.check_report(126, "query{}.json".format(126))

    def test_complex_subject_matching_django(self):
        """Encounters match on an alternative subject ID field (passport_number), and don't
        get created ("skip") if no match.
        """
        self.setup_user(**self.testuser3)
        self.check_report(127, "query{}.json".format(127))

    def test_complex_subject_matching_django_m2m_subcol(self):
        """Encounters match on an alternative subject ID field (passport_number), and don't
        get created ("skip") if no match.
        """
        self.setup_user(**self.testuser3)
        self.check_report(128, "query{}.json".format(128))

    def test_calculated_field_concept_from_chiron_subject_id(self):
        """Encounters match on an alternative subject ID field (passport_number), and don't
        get created ("skip") if no match.
        """
        self.setup_user(**self.testuser3)
        self.check_report(129, "query{}.json".format(129))

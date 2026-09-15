# from django.test import TestCase

from .utils.base_testcase import BaseTestCase


class CollectionRelationshipTests(BaseTestCase):
    """
    Tests output of reports involving relationships between subcollections (defined in the
    SubcollectionRelationship model).
    """

    @classmethod
    def setUpTestData(cls):
        cls.load_patient_model_app_data()
        cls.initialize_chiron()
        cls.load_dataset(cls.DS1_STORED)
        cls.load_dataset(cls.DS3_STORED)
        cls.testuser1 = {
            "dataset_name": cls.DS1_STORED,
            "username": "testuser",
            "access_level": "phi",
            "permission_groups": ["all"],
        }
        cls.testuser3 = {
            "dataset_name": cls.DS3_STORED,
            "username": "testuser",
            "access_level": "phi",
        }

    def test_collection_relationships(self):
        """
        General tests for basic expected report behavior with collection relationships
        """
        self.setup_user(**self.testuser1)
        for i in range(103, 109):
            if i == 108:
                # TODO: there's a 3 way chain you could build from aliquot->sample->encounter
                #  that would give more specific (better) results
                continue
            self.check_report(i, "query{}.json".format(i))
        for i in range(111, 112):
            self.check_report(i, "query{}.json".format(i))

    def test_collection_relationships_involving_m2m_subcol(self):
        """
        Testing m2m subcollection used in combination with a collection relationship
        """
        self.setup_user(**self.testuser3)
        for i in range(123, 126):
            self.check_report(i, "query{}.json".format(i))

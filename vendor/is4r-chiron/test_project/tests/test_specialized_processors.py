from .utils.base_testcase import BaseTestCase
from rest_framework.reverse import reverse


class SpecializedProcessorsTest(BaseTestCase):
    """
    Test specialized built-in processors
    """

    @classmethod
    def setUpTestData(cls):
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

    def test_autocreated_subject_id(self):
        """
        An autocreated subject ID should be the same every time the ETL is run, be unique for
        unique inputs, and have the specified number of characters
        """
        self.setup_user(**self.testuser2)
        self.check_report(130, "query{}.json".format(130))

    def test_autocreated_subcollection_id(self):
        """
        An autocreated subcol ID should be the same every time the ETL is run, be unique for
        unique inputs, and have the specified number of characters
        """
        self.setup_user(**self.testuser2)
        self.check_report(131, "query{}.json".format(131))

    def test_calculated_age_at_event(self):
        """
        Age should be the difference in days between birthdate and encounter date
        """
        self.setup_user(**self.testuser2)
        self.check_report(133, "query{}.json".format(133))

    def test_calculated_current_age(self):
        """
        Should generate age based on DOB, if DOD get age at time of death,
        """
        self.setup_user(**self.testuser2)
        url = reverse("chiron:api:report_tools-list") + "{}/export_json/".format(132)
        data = {}
        response = self.client.get(url, data)
        self.assertEqual(response.status_code, 200)
        output = response.json()
        records = output["records"]
        # someone with a death date should show age at time of death
        self.assertEqual(records[3][3], 40)
        # someone over 89 should show as "90 and above"
        self.assertEqual(records[4][3], "90 and above")

    def test_current_age_from_age(self):
        """
        Should generate a deidentified age from an age, removing any decimal parts and grouping
        patients over 89.
        """
        self.setup_user(**self.testuser3)
        self.check_report(134, "query{}.json".format(134))

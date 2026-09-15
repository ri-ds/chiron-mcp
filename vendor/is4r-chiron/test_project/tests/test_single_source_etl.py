from .utils.base_testcase import BaseTestCase


class SingleSourceTest(BaseTestCase):
    dataset = None

    @classmethod
    def setUpTestData(cls):
        # populate patient data tables that will be used as sources
        cls.load_patient_model_app_data()

        # create data dictionary for some other datasets
        # This is just to make sure having multiple datasets doesn't break any of our tests.
        cls.initialize_chiron()

        # create and load an identical dataset; This is to test for errors from name clashes.
        dataset3_copy3 = cls.load_dataset_dd(cls.DS3_AUTO_C3)
        cls.load_dataset(dataset3_copy3.unique_id)
        cls.dataset = dataset3_copy3

        # rerun single collection etl
        cls.chiron_run_single_etl(cls.dataset.unique_id, "SubCollection")

    def test_single_source(self):
        # check on stats
        self.setup_user(self.DS3_AUTO_C3, "testuser")
        self.check_stats(self.dataset, "subject_field_", "stat36.json", startswith_match=True)

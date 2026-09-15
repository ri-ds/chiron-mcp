import json

# from django.test import TestCase
from rest_framework.reverse import reverse

from .utils.base_testcase import BaseTestCase
from chiron import chiron_settings


class ConceptStatisticsTest(BaseTestCase):
    """
    Mostly looking at callback data for concept:
    http://localhost:8000/api/concepts/[concept_id]/cohort_def_callback/
    """

    @classmethod
    def setUpTestData(cls):
        cls.initialize_chiron()
        cls.load_dataset(cls.DS1_STORED)
        cls.load_dataset(cls.DS2_STORED)
        cls.cohort_def = [
            {
                "entry_type": "criteria_set",
                "entry_id": "fUrWc3ZiuLqD",
                "collection_id": "subject",
                "list": [
                    {
                        "terms": [],
                        "entry_id": "9KLFn1KMGo8w",
                        "concept_id": "patient_id",
                        "exclude_selected": True,
                        "include_null_and_missing": True,
                    }
                ],
            }
        ]
        cls.cohort_def_str = json.dumps(cls.cohort_def)
        cls.testuser1 = {
            "dataset_name": cls.DS1_STORED,
            "username": "testuser",
            "access_level": "phi",
            "permission_groups": ["all"],
        }
        cls.testuser2 = {
            "dataset_name": cls.DS2_STORED,
            "username": "testuser",
            "access_level": "phi",
        }

    def test_stats(self):
        """Test stat output of every type of cohort def processor"""
        oChironUser = self.setup_user(**self.testuser1)
        oDataset = oChironUser.dataset
        self.check_stats_full(oDataset, "birth_place", "stat4.json")
        self.check_stats_full(oDataset, "race_2", "stat5.json")
        self.check_stats_full(oDataset, "healthcare_coverage_2", "stat6.json")
        self.check_stats_full(oDataset, "healthcare_expenses_2", "stat7.json")
        self.check_stats_full(oDataset, "married", "stat8.json")
        self.check_stats_full(oDataset, "subcol_simple_encounter_id", "stat9.json")
        self.check_stats_full(oDataset, "subcol_simple_enc_class", "stat10.json")
        self.check_stats_full(oDataset, "subcol_simple_base_cost", "stat11.json")
        self.check_stats_full(oDataset, "subcol_simple_claim_cost", "stat12.json")
        self.check_stats_full(oDataset, "subcol_simple_encounter_date", "stat13.json")
        self.check_stats_full(oDataset, "subcol_simple_paid", "stat14.json")
        self.check_stats_full(oDataset, "complex_coverage", "stat16.json")
        self.check_stats_full(oDataset, "complex_expenses", "stat17.json")
        self.check_stats_full(oDataset, "payer_coverage_float_with_text", "stat19.json")

    def test_stats_recent_concept_datatypes(self):
        """There are some new concept datatypes that aren't covered in test_stats()."""
        oChironUser = self.setup_user(**self.testuser2)
        oDataset = oChironUser.dataset
        # detailed age
        self.check_stats(oDataset, "d2_age_at_start", "stat53.json")
        # TODO: are there more data types I'm not testing stats for?

    def test_stats_with_prefilters(self):
        oChironUser = self.setup_user(**self.testuser1)
        oDataset = oChironUser.dataset
        self.check_stats_full(oDataset, "lab_date", "stat20.json")
        self.check_stats_full(oDataset, "lab_date", "stat21.json", "Body Height")
        self.check_stats_full(oDataset, "lab_value_string", "stat22.json", "Body Height")
        self.check_stats_full(oDataset, "lab_value_number", "stat23.json", "Body Height")
        self.check_stats_full(oDataset, "lab_units", "stat24.json", "Body Height")
        self.check_stats_full(oDataset, "lab_value_is_numeric", "stat25.json")
        self.check_stats_full(oDataset, "lab_value_is_numeric", "stat26.json", "Body Height")
        self.check_stats_full(oDataset, "lab_value_num_cat", "stat27.json", "QALY")

    def test_required_prefilters(self):
        """If a prefilter is required for a concept, attempt to get stats should generate a 400"""
        self.setup_user(**self.testuser1)
        self.check_stat_errors("lab_value_string", 404)
        self.check_stat_errors("lab_value_number", 404)
        self.check_stat_errors("lab_units", 404)
        self.check_stat_errors("lab_value_num_cat", 404)

    def check_stats_full(self, oDataset, concept_id, datafile_name, prefilter_value=None):
        """
        Runs normal check_stats and also runs using a cohort that includes all patients.
        Both queries should return the same result.
        """
        # standard check_stats
        oChironUser = self.setup_user(**self.testuser1)
        oDataset = oChironUser.dataset
        self.check_stats(oDataset, concept_id, datafile_name, prefilter_value=prefilter_value)

        # custom check stats for cohort_def that matches all patients
        url = reverse("chiron:api:concepts-list") + "{}/cohort_def_callback/".format(concept_id)
        data = {}
        if prefilter_value:
            data["prefilter_value"] = prefilter_value
        data["cohort_def"] = self.cohort_def_str
        response = self.client.get(url, data=data)
        self.assertEqual(response.status_code, 200)
        output = response.json()
        # remove perf as that data changes and cannot be mocked reliably
        if "perf" in output:
            del output["perf"]
        with open("{}{}".format(self.expected_stat_dir, datafile_name), encoding="utf-8") as f:
            expected = json.load(f)
        if not self.assertEqual(output, expected):
            print("failed dataset: ", datafile_name)

        # test stats when cohort def includes everyone (should be same as no cohort def)
        data["cohort_def"] = self.cohort_def_str
        response = self.client.get(url, data=data)
        self.assertEqual(response.status_code, 200)
        output = response.json()
        # remove perf as that data changes and cannot be mocked reliably
        if "perf" in output:
            del output["perf"]
        if not self.assertEqual(output, expected):
            print("failed dataset: ", datafile_name)

    def check_stat_errors(self, concept_id, error_code, prefilter_value=None):
        url = reverse("chiron:api:concepts-list") + "{}/cohort_def_callback/".format(concept_id)
        data = {}
        if prefilter_value:
            data["prefilter_value"] = prefilter_value
        # test stats when no cohort def
        response = self.client.get(url, data=data)
        self.assertEqual(response.status_code, error_code)

    def _test_perf_stats(self, concept_id):
        url = reverse("chiron:api:concepts-list") + "{}/cohort_def_callback/".format(concept_id)
        data = {}
        chiron_settings.CHIRON_GET_QUERY_PERFORMANCE = True
        response = self.client.get(url, data=data)
        self.assertEqual(response.status_code, 200, f"{concept_id}: is not a valid response")
        self.assertTrue("perf" in response.data, f"{concept_id}: did not find perf in response")
        self.assertTrue(
            "cache_mode" in response.data, f"{concept_id}: did not find cache_mode in response"
        )
        chiron_settings.CHIRON_GET_QUERY_PERFORMANCE = False
        response = self.client.get(url, data=data)
        self.assertTrue(
            "perf" not in response.data,
            f"{concept_id}: found perf in response when its not supposed to",
        )
        self.assertTrue(
            "cache_mode" not in response.data,
            f"{concept_id}: found cache_mode in response when its not supposed to",
        )

    def test_perf_data(self):
        self.setup_user(**self.testuser1)
        self._test_perf_stats("healthcare_coverage")
        self._test_perf_stats("healthcare_coverage_2")
        self._test_perf_stats("complex_coverage")
        self._test_perf_stats("complex_expenses")
        self._test_perf_stats("ethnicity")
        self._test_perf_stats("patient_firstname")
        self._test_perf_stats("marital_status")
        self._test_perf_stats("patient_birthdate")
        self._test_perf_stats("patient_id")
        self._test_perf_stats("enc_cost_as_string")
        self._test_perf_stats("full_name")
        self._test_perf_stats("value_strange_sort")

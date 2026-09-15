import json
import warnings

# from django.test import TestCase
from django.apps import apps
from rest_framework.reverse import reverse

from chiron import chiron_settings
from .utils.base_testcase import BaseTestCase


if apps.is_installed("ontologies") and not chiron_settings.CHIRON_TREAT_ONTOLOGY_CONCEPTS_AS_TEXT:

    class OntologyConceptTest(BaseTestCase):
        """
        Testing that ontology display and results work correctly
        """

        @classmethod
        def setUpTestData(cls):
            cls.initialize_chiron()
            cls.load_dataset(cls.DS2_STORED)
            cls.cohort_def = [
                {
                    "entry_type": "criteria_set",
                    "entry_id": "JhLdzqaZSFTT",
                    "collection_id": "d2_patients",
                    "list": [
                        {
                            "terms": [
                                {
                                    "label": "Cardiovascular diagnoses",
                                    "code": "Cardiovascular_diagnoses",
                                    "leaf": 1,
                                },
                                {"label": "Procedures", "code": "Procedures", "leaf": 1},
                            ],
                            "entry_id": "UgywUVJzyN3V",
                            "concept_id": "FYLER",
                            "exclude_selected": False,
                            "include_null_and_missing": False,
                            "include_ontology_unknown": False,
                        }
                    ],
                }
            ]
            cls.cohort_def_str = json.dumps(cls.cohort_def)

            cls.testuser2 = {
                "dataset_name": cls.DS2_STORED,
                "username": "testuser",
                "access_level": "phi",
            }

        def check_stats_ont(
            self, oDataset, concept_id, datafile_name, prefilter_value=None, data={}
        ):
            """
            Checks responses of specific ontology actions
            """

            url = reverse(
                "chiron:api_v2:concepts-list", kwargs={"dataset_string": "dataset2_stored"}
            ) + "{}/cohort_def_callback/".format(concept_id)

            response = self.client.get(url, data=data)
            self.assertEqual(response.status_code, 200)
            output = response.json()

            with open("{}{}".format(self.expected_stat_dir, datafile_name), encoding="utf-8") as f:
                expected = json.load(f)
            self.assertEqual(len(output["action_results"]), len(expected["action_results"]))

        def test_stats(self):
            """
            tests roots response
            """
            oChironUser = self.setup_user(**self.testuser2)
            oDataset = oChironUser.dataset
            self.check_stats_ont(oDataset, "FYLER", "ontologystat1.json")

        def test_child(self):
            """
            tests child display navigation
            """
            oChironUser = self.setup_user(**self.testuser2)
            oDataset = oChironUser.dataset
            data = {"ontology_class": "Cardiovascular_diagnoses", "ontology_action": "children"}
            self.check_stats_ont(oDataset, "FYLER", "ontologystat2.json", data=data)

        def test_parent(self):
            """
            tests parent display navigation
            """
            oChironUser = self.setup_user(**self.testuser2)
            oDataset = oChironUser.dataset
            data = {"ontology_class": "Cardiovascular_diagnoses", "ontology_action": "parent"}
            self.check_stats_ont(oDataset, "FYLER", "ontologystat3.json", data=data)

        def test_filter_data_exists(self):
            """
            tests data exists display
            """
            oChironUser = self.setup_user(**self.testuser2)
            oDataset = oChironUser.dataset
            data = {"filter_data_exists": False}
            self.check_stats_ont(oDataset, "FYLER", "ontologystat4.json", data=data)

        def test_search(self):
            """
            tests data exists display
            """
            oChironUser = self.setup_user(**self.testuser2)
            oDataset = oChironUser.dataset
            data = {"search": "death"}
            self.check_stats_ont(oDataset, "FYLER", "ontologystat5.json", data=data)

        def test_roots_cohort_defined(self):
            """
            tests that show_all_data responds correctly
            """
            oChironUser = self.setup_user(**self.testuser2)
            oDataset = oChironUser.dataset
            data = {}
            data["cohort_def"] = self.cohort_def_str
            data["show_all_data"] = False
            self.check_stats_ont(oDataset, "FYLER", "ontologystat6.json", data=data)

        def test_cohort_def_include_unknown(self):
            """
            tests simple cohort def
            """
            oChironUser = self.setup_user(**self.testuser2)
            oDataset = oChironUser.dataset
            url = reverse("chiron:apiv2:cohort_def-list", kwargs={"dataset_string": str(oDataset)})
            data = {
                "transformation": {
                    "chiron_ontology_field_selection": ["Family history"],
                    "concept_id": "FYLER",
                    "type": "add_entry",
                    "exclude_selected": False,
                    "include_ontology_unknown": True,
                    "prefilter_value": "",
                    "ignore_warnings": False,
                }
            }
            response = self.client.post(url, data, format="json")
            self.assertEqual(response.status_code, 200)
            output = response.json()
            datafile_name = "ontologystat7.json"
            with open("{}{}".format(self.expected_stat_dir, datafile_name), encoding="utf-8") as f:
                expected = json.load(f)
            self.assertEqual(output["describe"], expected["describe"])

        def test_cohort_def(self):
            """
            tests simple cohort def
            """
            oChironUser = self.setup_user(**self.testuser2)
            oDataset = oChironUser.dataset
            url = reverse("chiron:apiv2:cohort_def-list", kwargs={"dataset_string": str(oDataset)})
            data = {
                "transformation": {
                    "chiron_ontology_field_selection": ["Family history"],
                    "concept_id": "FYLER",
                    "type": "add_entry",
                    "exclude_selected": False,
                    "include_ontology_unknown": False,
                    "prefilter_value": "",
                    "ignore_warnings": False,
                }
            }
            response = self.client.post(url, data, format="json")
            self.assertEqual(response.status_code, 200)
            output = response.json()
            datafile_name = "ontologystat8.json"
            with open("{}{}".format(self.expected_stat_dir, datafile_name), encoding="utf-8") as f:
                expected = json.load(f)
            self.assertEqual(output["describe"], expected["describe"])

else:
    if not apps.is_installed("ontologies"):
        warnings.warn(
            "The ontology app is not in INSTALLED_APPS for your test settings, skipping "
            "ontology tests",
            UserWarning,
        )
    if chiron_settings.CHIRON_TREAT_ONTOLOGY_CONCEPTS_AS_TEXT:
        warnings.warn(
            "CHIRON_TREAT_ONTOLOGY_CONCEPTS_AS_TEXT=True in your test settings, skipping "
            "ontology tests",
            UserWarning,
        )

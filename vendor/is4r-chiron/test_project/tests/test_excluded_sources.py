# from django.test import TestCase
from rest_framework.reverse import reverse

from .utils.base_testcase import BaseTestCase
from chiron.models import Source, Concept


class DjangoEtlTest(BaseTestCase):
    """
    Tests autocreate and ETL for some django models
    """

    @classmethod
    def setUpTestData(cls):
        # populate patient data tables that will be used as sources
        cls.load_patient_model_app_data()

        # create data dictionary for some other datasets
        # This is just to make sure having multiple datasets doesn't break any of our tests.
        cls.initialize_chiron()

        # create and load the data dictionary but not the actual research data
        oDataset = cls.load_dataset_dd("dataset3_autocreated_copy2")

        # set one of the sources in the dataset excluded
        Source.objects.filter(collection__dataset=oDataset, name="ManyToManySubCollection").update(
            exclude_from_etl=True
        )

        # run the etl
        cls.load_dataset(oDataset.unique_id)

        # define user for this set of tests
        cls.testuser = {
            "dataset_name": cls.DS3_AUTO_C2,
            "username": "testuser",
        }

    def test_django_source_not_loaded(self):
        oChironUser = self.setup_user(**self.testuser)
        dataset = oChironUser.dataset

        excluded_source = Source.objects.get(
            collection__dataset=dataset, name="ManyToManySubCollection"
        )

        # check to see if data from the excluded source is present
        excluded_concepts = Concept.objects.filter(
            collection__dataset=dataset.id, source=excluded_source
        )
        for concept in excluded_concepts:
            url = reverse("chiron:api:concepts-list") + "{}/cohort_def_callback/".format(
                concept.permanent_id
            )
            response = self.client.get(url, {})
            self.assertEqual(response.status_code, 200)
            output = response.json()
            print(concept.concept_handler.name, output)
            match concept.concept_handler.name:
                case "TextHandler":
                    self.assertEqual(0, output.get("count"))
                case "BooleanHandler" | "CategoryHandler":
                    self.assertEqual(0, len(output.get("values")))
                case _:
                    self.assertEqual(0, output.get("stats", {}).get("unique_patients"))

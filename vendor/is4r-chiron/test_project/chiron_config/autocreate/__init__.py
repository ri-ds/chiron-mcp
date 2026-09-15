import copy

from chiron.data_dictionary.csv_autocreate import CsvFileAutocreate
from chiron.data_dictionary.django_autocreate import DjangoOrmAutocreate

dataset2_autocreated = {
    "autocreate_tool": CsvFileAutocreate,
    "defaults": {"dataset": "dataset2_autocreated"},
    "list": [
        {
            "unique_source_id": "d2_patients",
            "filename": "source_data/patients2.csv",
            "load_to_root": True,
            "subject_id_field": "Id",
            "add_subject_ids": [
                {
                    "source_id_field": "SSN",
                    "destination_id_field": "ssn",
                },
                {
                    "source_id_field": "PASSPORT",
                    "destination_id_field": "passport_number",
                },
            ],
        },
        {
            "unique_source_id": "d2_encounters",
            "filename": "source_data/encounters2.csv",
            "subject_id_field": "PATIENT",
            "collection_id_field": "Id",
            "subject_matching": {
                "source_id_field": "PASSPORT",
                "destination_id_field": "passport_number",
                "if_no_match": "skip",
            },
        },
    ],
}

dataset3_autocreated = {
    "autocreate_tool": DjangoOrmAutocreate,
    "defaults": {
        "dataset": "dataset3_autocreated",
        "app": "patient_models",
    },
    "list": [
        {
            "model": "Subject",
            "load_to_root": True,
            "subject_id_field": "id",
            "add_subject_ids": [
                {"source_id_field": "alt_subject_id1", "destination_id_field": "alt1"},
                {"source_id_field": "alt_subject_id2", "destination_id_field": "alt2"},
            ],
            "join_models": [
                {
                    "model": "OneToManyCollection",
                    "join_path": "onetomanycollection_set",
                },
                {
                    "model": "SecondOneToManyCollection",
                    "join_path": "onetomanycollection_set__secondonetomanycollection_set",
                },
                {
                    "model": "OneToOneCollection",
                    "join_path": "onetoonecollection",
                },
                {
                    "model": "ReverseOneToOneCollection",
                    "join_path": "one_to_one",
                },
                {
                    "model": "ManyToManyCollection",
                    "join_path": "manytomanycollection_set",
                },
                {
                    "model": "ReverseManyToManyCollection",
                    "join_path": "many_to_many",
                },
            ],
        },
        {
            "model": "SubCollection",
            "load_to_root": False,
            "subject_id_field": "subject.id",
            "collection_id_field": "id",
        },
        {
            "model": "ManyToManySubCollection",
            "load_to_root": False,
            "subject_id_field": "m2m_subjects.id",  # m2m relationships can return >1 subject
            "collection_id_field": "id",
        },
        {
            "model": "SubColComplexSubjectMatching",
            "load_to_root": False,
            "collection_id_field": "id",
            "subject_matching": {
                "source_id_field": "alt_subject_id",
                "destination_id_field": "alt1",
                "if_no_match": "skip",
            },
        },
        {
            "model": "M2MSubColComplexSubjectMatching",
            "load_to_root": False,
            # "subject_id_field": "m2m_subjects.id",  # m2m relationships can return >1 subject
            "collection_id_field": "id",
            "subject_matching": {
                "source_id_field": "m2m_alt_subjects.alt_subject_id2",
                "destination_id_field": "alt2",
                "if_no_match": "skip",
            },
        },
        # TODO: File causes an error because autocreate makes a select_related arg when it
        #   needs a prefetch_related arg for subject_id
        # {
        #     "model": "Sample",
        #     "load_to_root": False,
        #     "subject_id_field": "subject__id",
        #     "collection_id_field": "sample_id",
        # },
        # {
        #     "model": "File",
        #     "load_to_root": False,
        #     "subject_id_field": "subjects__id",
        #     "collection_id_field": "file_id",
        # },
    ],
}

# create a second identical dataset to test for problems with name clashes
dataset3_autocreated_copy2 = copy.deepcopy(dataset3_autocreated)
dataset3_autocreated_copy2["defaults"]["dataset"] = "dataset3_autocreated_copy2"

dataset3_autocreated_copy3 = copy.deepcopy(dataset3_autocreated)
dataset3_autocreated_copy3["defaults"]["dataset"] = "dataset3_autocreated_copy3"

autocreate_source_lists = {
    # stored datasets are loaded from fixtures and should only have autocreate run if new models or
    # fields are added (stored_dataset1 was built manually and doesn't have an autocreate def)
    "dataset2_autocreated": dataset2_autocreated,
    "dataset3_autocreated": dataset3_autocreated,
    "dataset3_autocreated_copy2": dataset3_autocreated_copy2,
    "dataset3_autocreated_copy3": dataset3_autocreated_copy3,
}

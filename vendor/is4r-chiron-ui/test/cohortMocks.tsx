import type {
  CategoryConceptValue,
  CategoryConceptDetailedData,
  TextConceptDetailedData,
  AgeConceptDetailedData,
  DateConceptDetailedData,
  CriteriaSetEntry,
  //ConceptData,
  //CategoryOrTextValues,
  //NumberValues,
  //DateValues,
  //AgeValues,
  //CriteriaSet,
  //NumberConceptDetailedData,
  //NumberConceptDetailedData,
} from "../src/store/cohortSlice";

export const AGE_CONCEPT_DETAILEDDATA: AgeConceptDetailedData = {
  count_missing_values: 0,
  count_subjects_with_missing_values: 0,
  histogram_data: [
    ["1", 100],
    ["2", 200],
    ["3", 180],
  ],
  is_callback: false,
  permanent_id: "age_concept",
  stats: {
    count_non_null: 0,
    unique_patients: 3000,
    avg_day: 150,
    avg_year: 50,
    max_day: 365,
    min_day: 0,
    max_year: 99,
    min_year: 0,
  },
};

export const CATEGORIES_MOCKS: CategoryConceptValue[] = [
  {
    category: "Category1",
    count: 13396,
    uniquePatientCount: 13396,
  },
  {
    category: "Category2",
    count: 5689,
    uniquePatientCount: 5689,
  },
  {
    category: "Category3",
    count: 234,
    uniquePatientCount: 234,
  },
];

export const CATEGORY_CONCEPT_DETAILEDDATA: CategoryConceptDetailedData = {
  count_missing_values: 10,
  count_subjects_with_missing_values: 10,
  is_callback: true,
  max_count: 2300,
  permanent_id: "gender",
  values: CATEGORIES_MOCKS,
};

export const DATE_CONCEPT_DETAILEDDATA: DateConceptDetailedData = {
  count_subjects_with_missing_values: 0,
  count_missing_values: 0,
  is_callback: true,
  permanent_id: "birthdate",
  stats: {
    count_non_null: 40000,
    unique_patients: 40000,
    max: "2023-10-30",
    min: "1923-11-01",
  },
  histogram_data: [
    ["1923", 100],
    ["1950", 200],
    ["2020", 180],
  ],
};

export const TEXT_CONCEPT_DETAILEDDATA: TextConceptDetailedData = {
  count: 690,
  count_subjects_with_missing_values: 0,
  count_missing_values: 0,
  is_callback: true,
  permanent_id: "first_name",
  paginated_results: [
    { unique_values: "TestValue1" },
    { unique_values: "TestValue2" },
    { unique_values: "OtherTestValue3" },
    { unique_values: "OtherTestValue4" },
  ],
  paginator: {
    first_index: 1,
    last_index: 10,
    current_page: 1,
    previous_page: null,
    next_page: 2,
    last_page: 69,
    total_records: 690,
  },
};

export const CRITERIA_SET_MOCK: CriteriaSetEntry = {
  permanent_id: "admission",
  name: "admission",
  get_name_plural: "admissions",
  is_root_collection: false,
  has_event: true,
};
export const CRITERIA_SET_MOCK_2: CriteriaSetEntry = {
  permanent_id: "diagnosis",
  name: "diagnosis",
  get_name_plural: "diagnoses",
  is_root_collection: false,
  has_event: true,
};

export const CRITERIA_SETS_MOCK: CriteriaSetEntry[] = [
  CRITERIA_SET_MOCK,
  CRITERIA_SET_MOCK_2,
];

export const CONCEPT_CATEGORY_MOCK_RSLT = {
  category_id: 1,
  categories: [],
  concepts: [
    {
      permanent_id: "first_name",
      concept_type: "text",
      name: "first name",
      get_name_plural: "first names",
      description: "",
      collection: "subject",
      collection_name: "subject",
      collection_name_plural: "subjects",
      source: 1,
      concept_for_prefilter: null,
      prefilter_mode: "required",
      category_hierarchy: [
        {
          id: 1,
          name: "demographics",
          parent_id: null,
          get_level: 0,
        },
      ],
      order: 1,
      published: true,
      include_in_cohort_def: true,
      include_in_table_def: true,
      include_in_analysis_def: true,
      has_phi: false,
    },
  ],
};

export const CONCEPT_SEARCH_RSLT = {
  count: 1,
  next: null,
  previous: null,
  results: [
    {
      permanent_id: "first_name",
      concept_type: "text",
      name: "first name",
      get_name_plural: "first names",
      description: "",
      collection: "subject",
      collection_name: "subject",
      collection_name_plural: "subjects",
      source: 1,
      concept_for_prefilter: null,
      prefilter_mode: "required",
      category_hierarchy: "demographics",
      order: 1,
      published: true,
      include_in_cohort_def: true,
      include_in_table_def: true,
      include_in_analysis_def: true,
      has_phi: false,
    },
  ],
};

export const CONCEPT_COHORT_MOCK_RSLT = {
  category_id: "top",
  categories: [
    {
      id: 1,
      name: "demographics",
      parent_id: null,
      get_level: 0,
    },
  ],
  concepts: [
    {
      permanent_id: "patient_id",
      concept_type: "text",
      name: "patient ID",
      get_name_plural: "patient IDs",
      description: "",
      collection: "subject",
      collection_name: "subject",
      collection_name_plural: "subjects",
      source: 1,
      concept_for_prefilter: null,
      prefilter_mode: "required",
      category_hierarchy: [],
      order: 1,
      published: true,
      include_in_cohort_def: true,
      include_in_table_def: true,
      include_in_analysis_def: true,
      has_phi: false,
    },
  ],
};

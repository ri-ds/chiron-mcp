import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { APIRequest } from "../api";
import { type Category } from "../components/Concepts";
import { convertDateFormatForTextField } from "../lib/utils";
import { resetTableStatus } from "./tableSlice";
import { resetAggState } from "./aggregateSlice";
import { isNull } from "lodash";

export type CategoryConceptValue = {
  count: number;
  category: string;
  uniquePatientCount: number;
};

export type Collection = {
  get_name_plural: string;
  has_event: boolean;
  is_root_collection: boolean;
  name: string;
  permanent_id: string;
};

export type CategoryConceptDetailedData = {
  count_missing_values: number;
  count_subjects_with_missing_values: number;
  is_callback: boolean;
  max_count: number;
  perf: object;
  permanent_id: string;
  values: CategoryConceptValue[];
};

export type TextConceptDetailedData = {
  count: number;
  count_missing_values: number;
  count_subjects_with_missing_values: number;
  is_callback: boolean;
  paginated_results: { unique_values: string }[];
  paginator: {
    first_index: number;
    last_index: number;
    current_page: number;
    previous_page: number | null;
    next_page: number | null;
    last_page: number;
    total_records: number;
  };
  searchTerm?: string;
};

export type NumberConceptDetailedData = {
  count_missing_values: number;
  count_subjects_with_missing_values: number;
  histogram_data: [string, number][];
  is_callback: boolean;
  permanent_id: string;
  stats: {
    count_non_null: number;
    unique_patients: number;
    avg: number;
    max: number;
    min: number;
  };
  values: CategoryConceptValue[];
};

export type AgeConceptDetailedData = {
  count_missing_values: number;
  count_subjects_with_missing_values: number;
  histogram_data: [string, number][];
  is_callback: boolean;
  permanent_id: string;
  stats: {
    count_non_null: number;
    unique_patients: number;
    avg_day: number;
    avg_year: number;
    max_day: number;
    min_day: number;
    max_year: number;
    min_year: number;
  };
};

export type OntologyConceptDetailedData = {
  count: number;
  count_subjects_with_missing_values: number;
  count_missing_values: number;
  count_unknown_ontology_values: { count: number; uniqueSubjectCount: number };
  action_results: {
    label: string;
    code: string;
    leaf?: number;
    count?: number;
    uniqueSubjectCount?: number;
    hasDescendants?: boolean;
  }[];
  parents: {
    label: string;
    code: string;
    leaf?: number;
    count?: number;
    uniqueSubjectCount?: number;
  }[];
  permanent_id: string;
  term?: {
    label: string;
    code: string;
    leaf?: number;
    count?: number;
    uniqueSubjectCount?: number;
  };
};

export type DateConceptDetailedData = {
  count_missing_values: number;
  count_subjects_with_missing_values: number;
  histogram_data: [string, number][];
  is_callback: boolean;
  permanent_id: string;
  stats: {
    count_non_null: number;
    unique_patients: number;
    max: string;
    min: string;
  };
};

export type ConceptData = {
  permanent_id: string;
  concept_type: string;
  name: string;
  get_name_plural: string;
  description: string;
  collection: string;
  collection_name: string;
  collection_name_plural: string;
  source: number;
  concept_for_prefilter?: {
    id: number;
    name: string;
    permanent_id: string;
  };
  prefilter_mode: string;
  prefilter_value: string;
  category_hierarchy: Category[];
  order: number;
  published: boolean;
  include_in_cohort_def: boolean;
  include_in_table_def: boolean;
  include_in_analysis_def: boolean;
  has_phi: boolean;
  pk?: number;
  cohort_def_options: {
    include_null_and_missing: boolean;
    exclude_selected: boolean;
    existing_min?: string;
    existing_max?: string;
    all_values?: string[];
    ontology_filter_data_exists?: boolean;
    query_type?: string;
    days_ago?: string;
    term_labels?: string[];
  };
};

export type OntologyValue = { label: string; code: string };

export type CategoryOrTextValues = string[];
export type OntologyValues = OntologyValue[];
export type NumberValues = {
  existing_max: number;
  existing_min: number;
  values: string[];
};
export type DateValues = {
  existing_max: Date;
  existing_min: Date;
  query_type: string;
  days_ago: number;
};
export type AgeValues = {
  existing_min_year: number;
  existing_max_year: number;
  existing_min_day: number;
  existing_max_day: number;
};

export interface CohortState {
  showDescribeFilters: boolean;
  showEditCriteriaSet: boolean;
  extended_cohort_def: CriteriaSet[];
  cohortState: string;
  describe: string;
  warnings?: string[];
  errors?: string[];
  snapshot_id?: number;
  previous_snapshot_id?: number;
  next_snapshot_id?: number;
  count?: number;
  countState: string;
  queryConcept?: string;
  queryConceptData?: ConceptData;
  conceptState: string;
  showDataType: string;
  queryConceptDetailedData?: CategoryConceptDetailedData &
    TextConceptDetailedData &
    NumberConceptDetailedData &
    DateConceptDetailedData &
    AgeConceptDetailedData &
    OntologyConceptDetailedData;
  queryConceptValues?:
    | CategoryOrTextValues
    | NumberValues
    | DateValues
    | AgeValues
    | OntologyValues;
  queryConceptEditing?: string;
  queryConceptCriteriaEditing?: string;
  queryConceptEditingPrefilterValue: string | number | boolean;
  queryConceptExclude: boolean;
  queryConceptExcludeOntology: boolean;
  queryConceptIncludeOntologyUnknown?: boolean;
  criteriaSets?: Collection[];
  showCriteriaSets: boolean;
  transformationErrors: string[];
  transformationWarnings: string[];
  addingFilters: boolean;
  cohortPage?: "report" | "result" | "query";
}

export type CriteriaSet = {
  entry_type: string;
  entry_id: string;
  collection_id: string;
  alias: string;
  criteria_set_name: string;
  label: string;
  is_root_collection: boolean;
  collection_name: string;
  subcol_count_restriction?: string; // do we need this?
  has_event_field: boolean;
  event_rule_label: string;
  entries: CriteriaSetEntry[];
};

export type CriteriaSetEntry = {
  entry_id: string;
  concept_id: string;
  prefilter_value: string | number | boolean;
  label: string;
  abbreviated_label: string;
  exclude_selected: boolean;
  include_ontology_unknown?: boolean;
  values: string[];
};

export const initialState: CohortState = {
  showDescribeFilters: false,
  showEditCriteriaSet: false,
  extended_cohort_def: [],
  cohortState: "idle",
  describe: "",
  warnings: undefined,
  errors: undefined,
  snapshot_id: undefined,
  previous_snapshot_id: undefined,
  next_snapshot_id: undefined,
  count: undefined,
  countState: "idle",
  conceptState: "idle",
  queryConcept: undefined,
  queryConceptData: undefined,
  queryConceptValues: undefined,
  queryConceptEditing: undefined,
  queryConceptEditingPrefilterValue: "",
  queryConceptCriteriaEditing: undefined,
  queryConceptExclude: false,
  queryConceptExcludeOntology: true,
  showDataType: "all",
  criteriaSets: [],
  showCriteriaSets: false,
  transformationErrors: [],
  transformationWarnings: [],
  addingFilters: false,
};

// The function below is called a thunk and allows us to perform async logic. It
// can be dispatched like a regular action: `dispatch(incrementAsync(10))`. This
// will call the thunk with the `dispatch` function as the first argument. Async
// code can then be executed and other actions can be dispatched. Thunks are
// typically used to make async requests.
export const countSubjects = createAsyncThunk(
  "cohort/countSubjects",
  async (properties: { dataset: string }) => {
    const response = await APIRequest(
      "GET",
      `/api/v2/${properties.dataset}/query_tools/count/`
    );
    return { count: response.count, countState: "done" };
  }
);

export const setCurrentCohortDef = createAsyncThunk(
  "cohort/setCurrentCohortDef",
  async (
    properties: {
      dataset: string;
      data?:
        | undefined
        | { extended_cohort_def: CriteriaSet[]; describe: string };
    },
    thunkApi
  ) => {
    let response;
    if (properties.data == undefined) {
      response = await APIRequest(
        "GET",
        `/api/v2/${properties.dataset}/cohort_def/`
      );
      await thunkApi.dispatch(countSubjects({ dataset: properties.dataset }));
    } else {
      response = properties.data;
    }
    return {
      ...response,
      // queryConceptEditing: undefined,
      // queryConceptValues: undefined,
      cohortState: "done",
    };
  }
);

export const setCohortDef = createAsyncThunk(
  "cohort/setCohortDef",
  async (
    properties: { dataset: string; snapshotId: number | undefined },
    thunkApi
  ) => {
    if (!properties.snapshotId) {
      return;
    }
    const response = await APIRequest(
      "GET",
      `/api/v2/${properties.dataset}/cohort_def/${properties.snapshotId}/?set_to_active=true`
    );
    await thunkApi.dispatch(countSubjects({ dataset: properties.dataset }));
    thunkApi.dispatch(resetTableStatus());
    thunkApi.dispatch(resetAggState());
    return {
      ...response,
      queryConceptData: undefined,
      queryConceptEditing: undefined,
      queryConceptCriteriaEditing: undefined,
      queryConceptValues: undefined,
    };
  }
);

export const clearCohortDef = createAsyncThunk(
  "cohort/clearCohortDef",
  async (properties: { dataset: string }, thunkApi) => {
    const response = await APIRequest(
      "POST",
      `/api/v2/${properties.dataset}/cohort_def/`,
      {
        transformation: { type: "clear_all" },
      }
    );
    await thunkApi.dispatch(countSubjects({ dataset: properties.dataset }));
    thunkApi.dispatch(resetTableStatus());
    thunkApi.dispatch(resetAggState());
    return {
      ...response,
      queryConceptEditing: undefined,
      queryConceptCriteriaEditing: undefined,
    };
  }
);

export const removeCriteriaSet = createAsyncThunk(
  "cohort/removeCriteriaSet",
  async (
    properties: {
      dataset: string;
      entryId: string;
      queryConceptCriteriaEditing: string | undefined;
    },
    thunkApi
  ) => {
    const response = await APIRequest(
      "POST",
      `/api/v2/${properties.dataset}/cohort_def/`,
      {
        transformation: {
          type: "delete_criteria_set",
          entry_id: properties.entryId,
        },
      }
    );
    await thunkApi.dispatch(countSubjects({ dataset: properties.dataset }));
    thunkApi.dispatch(resetTableStatus());
    thunkApi.dispatch(resetAggState());
    if (properties.entryId == properties.queryConceptCriteriaEditing) {
      return {
        ...response,
        queryConceptEditing: undefined,
        queryConceptCriteriaEditing: undefined,
      };
    }
    return response;
  }
);

export const reorderCriteriaSetEntry = createAsyncThunk(
  "cohort/reorderCriteriaSetEntry",
  async (properties: {
    entryIds: string[];
    criteriaSetId: string;
    dataset: string;
  }) => {
    const response = await APIRequest(
      "POST",
      `/api/v2/${properties.dataset}/cohort_def/`,
      {
        transformation: {
          type: "sort_cd_entries",
          entry_id: properties.criteriaSetId,
          child_ids: properties.entryIds,
        },
      }
    );
    return response;
  }
);

export const removeCriteriaSetEntry = createAsyncThunk(
  "cohort/removeCriteriaSetEntry",
  async (
    properties: {
      dataset: string;
      entry?: CriteriaSetEntry;
      queryEditingId: string | undefined;
      conceptId: string;
      showDataType: string;
    },
    thunkApi
  ) => {
    const response = await APIRequest(
      "POST",
      `/api/v2/${properties.dataset}/cohort_def/`,
      {
        transformation: {
          type: "delete_entry",
          entry_id: properties.entry?.entry_id,
          remove_empty_criteria_sets: false,
        },
      }
    );
    await thunkApi.dispatch(countSubjects({ dataset: properties.dataset }));
    thunkApi.dispatch(resetTableStatus());
    thunkApi.dispatch(resetAggState());
    thunkApi.dispatch(
      loadConceptDisplay({
        dataset: properties.dataset,
        conceptId: properties.conceptId,
        showDataType: properties.showDataType,
        entry: properties.entry,
      })
    );
    if (properties.entry?.entry_id == properties.queryEditingId) {
      return {
        ...response,
        queryConceptEditing: undefined,
        queryConceptCriteriaEditing: undefined,
      };
    }
    return response;
  }
);

export const loadConceptDisplay = createAsyncThunk(
  "cohort/loadConceptDisplay",
  async (
    {
      dataset,
      conceptId,
      showDataType,
      entry,
      prefilterValue,
    }: {
      dataset: string;
      conceptId: string;
      showDataType: string;
      entry?: CriteriaSetEntry;
      prefilterValue?: string | number | boolean;
    },
    thunkApi
  ) => {
    const queryStrings = [
      `cohort_def_entry_id=${entry?.entry_id}`,
      "include_cohort_def_options=true",
      `prefilter_value=${prefilterValue ?? ""}`,
      `show_all_data=${showDataType === "cohort" ? false : true}`,
    ];
    const response = await APIRequest(
      "GET",
      `/api/v2/${dataset}/concepts/${conceptId}/?${queryStrings.join("&")}`
    );

    let values: any = {};
    switch (response.concept_type) {
      case "category":
      case "boolean":
        values = response.cohort_def_options.selected_values;
        response.cohort_def_options.include_null_and_missing =
          response.cohort_def_options.selected_values.some((v: string | null) =>
            isNull(v)
          );
        break;
      case "ontology":
        values = response.cohort_def_options.terms
          ? response.cohort_def_options.terms.map((t: OntologyValue) => t.label)
          : [];
        break;
      case "text":
        values = response.cohort_def_options.terms?.split("\n") || [];
        break;

      case "date":
        values = {
          days_ago: response.cohort_def_options.days_ago,
          query_type: response.cohort_def_options.query_type,
          existing_min: response.cohort_def_options.existing_min
            ? convertDateFormatForTextField(
                response.cohort_def_options.existing_min
              )
            : undefined,
          existing_max: response.cohort_def_options.existing_max
            ? convertDateFormatForTextField(
                response.cohort_def_options.existing_max
              )
            : undefined,
        };
        break;
      case "number":
      case "number_with_categories":
        values = {
          existing_min: response.cohort_def_options.existing_min,
          existing_max: response.cohort_def_options.existing_max,
          values: response.cohort_def_options.selected_values ?? [],
        };
        break;
      case "age":
        values = {
          existing_min_year: response.cohort_def_options.existing_min_year,
          existing_max_year: response.cohort_def_options.existing_max_year,
          existing_min_day: response.cohort_def_options.existing_min_day,
          existing_max_day: response.cohort_def_options.existing_max_day,
        };
        break;
      default:
        values = {};
    }

    if (!response.concept_for_prefilter) {
      thunkApi.dispatch(
        loadConceptDetailedData({ dataset, conceptId, showDataType })
      );
    }
    return {
      queryConceptData: response,
      queryConceptExclude: entry?.exclude_selected,
      queryConceptIncludeOntologyUnknown:
        response.cohort_def_options.include_ontology_unknown,
      queryConceptValues: values,
      transformationWarnings: [],
      transformationErrors: [],
    };
  }
);

export const loadConceptDetailedData = createAsyncThunk(
  "cohort/loadConceptDetailedData",
  async ({
    dataset,
    conceptId,
    showDataType,
    prefilterValue,
  }: {
    dataset: string;
    conceptId: string;
    showDataType: string;
    prefilterValue?: string | number | boolean;
  }) => {
    const queryStrings = [
      `concept_id=${conceptId}`,
      "entry_id=",
      `prefilter_value=${encodeURIComponent(prefilterValue ?? "")}`,
      `show_all_data=${showDataType === "cohort" ? false : true}`,
    ];
    const response = await APIRequest(
      "GET",
      `/api/v2/${dataset}/concepts/${conceptId}/cohort_def_callback/?${queryStrings.join(
        "&"
      )}`
    );

    return {
      queryConceptDetailedData: response,
    };
  }
);

export const conceptOntologyAction = createAsyncThunk(
  "cohort/conceptOntologyAction",
  async ({
    dataset,
    conceptId,
    classId,
    ontologyAction,
    showDataType,
    queryConceptExcludeOntology,
  }: {
    dataset: string;
    conceptId: string;
    classId: string;
    ontologyAction: string;
    showDataType: string;
    queryConceptExcludeOntology: boolean;
  }) => {
    const queryStrings = [
      `ontology_class=${classId}`,
      `ontology_action=${ontologyAction}`,
      "prefilter_value=",
      `show_all_data=${showDataType === "cohort" ? false : true}`,
      `filter_data_exists=${queryConceptExcludeOntology}`,
    ];
    const response = await APIRequest(
      "GET",
      `/api/v2/${dataset}/concepts/${conceptId}/cohort_def_callback/?${queryStrings.join(
        "&"
      )}`
    );
    return {
      queryConceptDetailedData: response,
    };
  }
);

export const conceptGotoSearchPage = createAsyncThunk(
  "cohort/conceptGotoSearchPage",
  async ({
    dataset,
    conceptId,
    searchTerm,
    page = 1,
    showDataType,
    queryConceptExcludeOntology,
  }: {
    dataset: string;
    conceptId: string;
    searchTerm: string;
    page: number;
    showDataType: string;
    queryConceptExcludeOntology?: boolean;
  }) => {
    const queryStrings = [
      `search=${searchTerm}`,
      `page=${page}`,
      "prefilter_value=",
      `show_all_data=${showDataType === "cohort" ? false : true}`,
      `records_per_page=${searchTerm != "" ? 3000 : 10}`,
      `filter_data_exists=${queryConceptExcludeOntology ? true : false}`,
    ];

    const response = await APIRequest(
      "GET",
      `/api/v2/${dataset}/concepts/${conceptId}/cohort_def_callback/?${queryStrings.join(
        "&"
      )}`
    );
    return {
      queryConceptDetailedData: { ...response, searchTerm: searchTerm },
    };
  }
);

export const verifyQueryConceptEntries = createAsyncThunk(
  "cohort/verifyQueryConceptEntries",
  async ({
    dataset,
    conceptId,
    values,
  }: {
    dataset: string;
    conceptId: string;
    values: object;
  }) => {
    const response = await APIRequest(
      "POST",
      `/api/v2/${dataset}/cohort_def/`,
      {
        transformation: {
          ...values,
          concept_id: conceptId,
          type: "add_entry",
          validate_only: true,
          ignore_warnings: false,
        },
      }
    );

    return {
      transformationErrors: response.transformation_errors,
      transformationWarnings: response.transformation_warnings,
    };
  }
);

export const addQueryConceptToFilters = createAsyncThunk(
  "cohort/addQueryConceptToFilters",
  async (
    {
      dataset,
      conceptId,
      values,
      entry,
      exclude,
      include_null_and_missing,
      ignoreWarnings = false,
      include_ontology_unknown,
      prefilterValue,
    }: {
      dataset: string;
      conceptId: string;
      values: object;
      entry?: string;
      exclude: boolean;
      include_null_and_missing?: boolean;
      ignoreWarnings: boolean;
      include_ontology_unknown?: boolean;
      prefilterValue?: string | number | boolean;
    },
    thunkApi
  ) => {
    const response = await APIRequest(
      "POST",
      `/api/v2/${dataset}/cohort_def/`,
      {
        transformation: {
          ...values,
          concept_id: conceptId,
          type: "add_entry",
          entry_id: entry,
          include_null_and_missing: include_null_and_missing
            ? "include"
            : undefined,
          exclude_selected: exclude || false,
          include_ontology_unknown: include_ontology_unknown
            ? include_ontology_unknown
            : false,
          prefilter_value: prefilterValue ?? "",
          ignore_warnings: ignoreWarnings,
        },
      }
    );
    if (response.transformation_successful) {
      thunkApi.dispatch(countSubjects({ dataset: dataset }));
      await thunkApi.dispatch(resetTableStatus());
      await thunkApi.dispatch(resetAggState());
      return {
        addingFilters: false,
        extended_cohort_def: response.extended_cohort_def,
        describe: response.describe,
        transformationWarnings: response.warnings,
        transformationErrors: response.errors,
        snapshot_id: response.snapshot_id,
        previous_snapshot_id: response.previous_snapshot_id,
        next_snapshot_id: response.next_snapshot_id,
        queryConceptEditing: response.entry_id,
        queryConceptCriteriaEditing: response.entry_id,
      };
    } else {
      return {
        addingFilters: false,
        transformationErrors: response.transformation_errors,
        transformationWarnings: response.transformation_warnings,
      };
    }
  }
);

export const getCriteriaSets = createAsyncThunk(
  "cohort/getCriteriaSets",
  async (data: { dataset: string }) => {
    const response = await APIRequest(
      "GET",
      `/api/v2/${data.dataset}/collections/`
    );
    return { criteriaSets: response, showCriteriaSets: true };
  }
);

export const switchDataType = createAsyncThunk(
  "cohort/switchDataType",
  async (
    {
      dataset,
      conceptId,
      showDataType,
      hasPrefilter,
      prefilterValue,
    }: {
      dataset: string;
      conceptId: string;
      showDataType: string;
      hasPrefilter: boolean;
      prefilterValue: string | number | boolean;
    },
    thunkApi
  ) => {
    if (showDataType === null) {
      return;
    }

    if (hasPrefilter) {
      setPrefetchValue(prefilterValue);
      thunkApi.dispatch(
        loadConceptDisplay({
          dataset: dataset,
          conceptId: conceptId,
          showDataType,
          prefilterValue,
        })
      );
    }
    thunkApi.dispatch(
      loadConceptDetailedData({
        dataset,
        conceptId,
        showDataType,
        prefilterValue,
      })
    );

    return { showDataType };
  }
);

export const addCriteriaSet = createAsyncThunk(
  "cohort/addCriteriaSet",
  async (
    { dataset, collection }: { dataset: string; collection: string },
    thunkApi
  ) => {
    const response = await APIRequest(
      "POST",
      `/api/v2/${dataset}/cohort_def/`,
      {
        transformation: {
          type: "add_criteria_set",
          collection_id: collection,
        },
      }
    );
    thunkApi.dispatch(toggleCriteriaSets());
    await thunkApi.dispatch(countSubjects({ dataset }));
    thunkApi.dispatch(resetAggState());
    thunkApi.dispatch(resetTableStatus());

    return {
      extended_cohort_def: response.extended_cohort_def,
      describe: response.describe,
      warnings: response.warnings,
      errors: response.errors,
      snapshot_id: response.snapshot_id,
      previous_snapshot_id: response.previous_snapshot_id,
      next_snapshot_id: response.next_snapshot_id,
    };
  }
);

export const cohortSlice = createSlice({
  name: "cohort",
  initialState,
  // The `reducers` field lets us define reducers and generate associated actions
  reducers: {
    toggleDescribeFilters(state) {
      state.showDescribeFilters = !state.showDescribeFilters;
    },
    resetTransformationAlerts(state) {
      state.transformationWarnings = [];
      state.transformationErrors = [];
    },
    setCohortPage(state, action) {
      state.cohortPage = action.payload.page;
    },
    selectQueryConcept(state, action) {
      state.queryConceptValues = undefined;
      state.queryConceptEditing = action.payload.edit;
      state.queryConceptEditingPrefilterValue = action.payload.prefilterValue;
      state.queryConceptCriteriaEditing = action.payload.criteriaSetId;
      state.queryConcept = action.payload.conceptId;
      state.queryConceptDetailedData = undefined;
      state.queryConceptData = undefined;
    },
    updateConceptValues(state, action) {
      state.queryConceptValues = action.payload;
    },
    cancelQueryConceptEditing(state) {
      state.queryConceptEditing = undefined;
      state.queryConceptCriteriaEditing = undefined;
      state.queryConceptValues = undefined;
      state.queryConceptIncludeOntologyUnknown = undefined;
      state.queryConceptExclude = false;
      state.queryConceptValues = [];
    },
    toggleExclude(state) {
      state.queryConceptExclude = !state.queryConceptExclude;
    },
    toggleIncludeOntologyUnknown(state) {
      state.queryConceptIncludeOntologyUnknown =
        !state.queryConceptIncludeOntologyUnknown;
    },
    toggleIncludeNullAndMissing(state) {
      if (state.queryConceptData) {
        const b =
          !state.queryConceptData.cohort_def_options.include_null_and_missing;
        state.queryConceptData.cohort_def_options.include_null_and_missing = b;
      }
    },
    toggleExistsInOntology(state, action) {
      if (action.payload) {
        state.queryConceptExcludeOntology = action.payload;
      } else {
        state.queryConceptExcludeOntology = !state.queryConceptExcludeOntology;
      }
    },
    toggleCriteriaSets(state) {
      state.showCriteriaSets = !state.showCriteriaSets;
    },
    resetStatuses(state) {
      state.cohortState = "idle";
      state.conceptState = "idle";
      state.countState = "idle";
      state.queryConceptValues = undefined;
      state.queryConceptDetailedData = undefined;
      state.queryConceptData = undefined;
    },
    setPrefetchValue(state, action) {
      if (state.queryConceptData) {
        state.queryConceptData.prefilter_value = action.payload;
      }
      state.queryConceptEditingPrefilterValue = action.payload;
    },
  },
  extraReducers: (builder) => {
    // show loading for fetching the current cohort def only
    builder
      .addCase(setCurrentCohortDef.pending, (state) => {
        state.cohortState = "loading";
      })
      .addCase(countSubjects.pending, (state) => {
        state.countState = "loading";
      })
      .addCase(countSubjects.fulfilled, (state, action) => {
        state.countState = "done";
        state.count = action.payload.count;
      })
      .addCase(countSubjects.rejected, (state) => {
        state.countState = "error";
        state.count = undefined;
      });

    // for all actions, handle the done and errored states
    [
      setCurrentCohortDef,
      setCohortDef,
      clearCohortDef,
      reorderCriteriaSetEntry,
      removeCriteriaSet,
      removeCriteriaSetEntry,
      loadConceptDisplay,
      loadConceptDetailedData,
      addQueryConceptToFilters,
      getCriteriaSets,
      addCriteriaSet,
      conceptOntologyAction,
      conceptGotoSearchPage,
      verifyQueryConceptEntries,
      switchDataType,
    ].forEach((thunk) => {
      builder
        .addCase(thunk.fulfilled, (state, action) => {
          return {
            ...state,
            ...action.payload,
            errors: [],
            cohortState: "done",
            conceptState: "done",
          };
        })
        .addCase(thunk.rejected, (state, action) => {
          state.conceptState = "error";
          state.errors =
            action.error && action.error.message
              ? [action.error.message]
              : ["Concept failed to load"];
        });
    });
    builder.addCase(loadConceptDetailedData.pending, (state) => {
      return {
        ...state,
        queryConceptDetailedData: undefined,
        conceptState: "loading",
      };
    });
    builder.addCase(loadConceptDisplay.pending, (state) => {
      return {
        ...state,
        conceptState: "loading",
      };
    });
    builder.addCase(conceptOntologyAction.pending, (state) => {
      return { ...state, conceptState: "loading" };
    });
    builder.addCase(addQueryConceptToFilters.pending, (state) => {
      return { ...state, addingFilters: true };
    });
  },
});

export const {
  toggleDescribeFilters,
  resetTransformationAlerts,
  selectQueryConcept,
  updateConceptValues,
  cancelQueryConceptEditing,
  toggleExclude,
  toggleExistsInOntology,
  toggleIncludeOntologyUnknown,
  toggleIncludeNullAndMissing,
  toggleCriteriaSets,
  setCohortPage,
  resetStatuses,
  setPrefetchValue,
} = cohortSlice.actions;

export default cohortSlice.reducer;

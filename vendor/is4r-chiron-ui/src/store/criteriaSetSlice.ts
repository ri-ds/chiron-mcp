import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { APIRequest } from "../api";
import { setCurrentCohortDef } from "./cohortSlice";

export type CriteriaSetOption = {
  transformation: string;
  option_id: string;
  label: string;
  allowed: boolean;
  type?: string;
  value?: number;
  alias?: string;
};

export type CriteriaSetEditState = {
  type?: "edit" | "event";
  permanent_id?: string;
  name?: string;
  get_name_plural?: string;
  is_root_collection?: boolean;
  has_event?: boolean;
  criteria_set_options?: CriteriaSetOption[];
  criteria_set_entry_id?: string;
  criteria_set_event_options?: {
    event_options: CriteriaSetEventOption[];
    selected_event_option: string;
  };
};

type CriteriaSetOtherEvent = {
  criteria_set_entry_id: string;
  criteria_set_name: string;
  event_type: string;
};

export type CriteriaSetEventOption = {
  option_id: string;
  label: string;
  transformation: string;
  django_template: string;
  allowed: boolean;
  date_start_min?: string;
  date_start_max?: string;
  date_end_min?: string;
  date_end_max?: string;
  days_ago_options?: [number, string];
  start_date_days_ago?: string;
  end_date_days_ago?: string;
  other_events: CriteriaSetOtherEvent[];
  collection_event_type: string;
  existing_event_rule: {
    range_end_days_from_target: number;
    range_end_target: string;
    range_start_days_from_target: number;
    range_start_target: string;
    reference_date: string;
    target_entry_id: string;
    type: string;
  };
  date_options: [number, string][];
};

export type UpdateEventProps = {
  entry_id: string;
  option_type?: string;
  reference_date?: string;
  start_date_days_ago?: string;
  end_date_days_ago?: string;
  date_start_min?: string;
  date_start_max?: string;
  date_end_min?: string;
  date_end_max?: string;
  range_start_days_from_target?: number;
  range_end_days_from_target?: number;
};

const initialState: CriteriaSetEditState = {};

// The function below is called a thunk and allows us to perform async logic. It
// can be dispatched like a regular action: `dispatch(incrementAsync(10))`. This
// will call the thunk with the `dispatch` function as the first argument. Async
// code can then be executed and other actions can be dispatched. Thunks are
// typically used to make async requests.

export const loadCriteraSetOptions = createAsyncThunk(
  "criteriaSet/loadCriteraSetOptions",
  async (data: {
    dataset: string;
    type: "event" | "edit";
    entryId: string;
    collection: string;
  }) => {
    let response = null;
    if (data.type == "event") {
      response = await APIRequest(
        "GET",
        `/api/v2/${data.dataset}/collections/${data.collection}/?include_criteria_set_event_options=true&criteria_set_entry_id=${data.entryId}`
      );
    } else {
      response = await APIRequest(
        "GET",
        `/api/v2/${data.dataset}/collections/${data.collection}/?include_criteria_set_options=true&criteria_set_entry_id=${data.entryId}`
      );
    }
    // The value we return becomes the `fulfilled` action payload
    return { ...response, type: data.type };
  }
);

export const enableEventFilters = createAsyncThunk(
  "criteriaSet/enableEventFilters",
  async (data: { dataset: string; entryId: string }, thunkApi) => {
    const response = await APIRequest(
      "POST",
      `/api/v2/${data.dataset}/cohort_def/`,
      {
        transformation: {
          entry_id: data.entryId,
          type: "create_event_rule",
        },
      }
    );

    thunkApi.dispatch(
      setCurrentCohortDef({
        dataset: data.dataset,
      })
    );
    // The value we return becomes the `fulfilled` action payload
    return response;
  }
);

export const clearEventFilters = createAsyncThunk(
  "criteriaSet/clearEventFilters",
  async (data: { dataset: string; entryId: string }, thunkApi) => {
    const response = await APIRequest(
      "POST",
      `/api/v2/${data.dataset}/cohort_def/`,
      {
        transformation: {
          entry_id: data.entryId,
          type: "delete_event_rule",
        },
      }
    );

    thunkApi.dispatch(
      setCurrentCohortDef({
        dataset: data.dataset,
      })
    );
    // The value we return becomes the `fulfilled` action payload
    return response;
  }
);

export const loadCriteraSetEventOptions = createAsyncThunk(
  "criteriaSet/loadCriteraSetEventOptions",
  async (data: { dataset: string; entryId: string; collection: string }) => {
    const response = await APIRequest(
      "GET",
      `/api/v2/${data.dataset}/collections/${data.collection}/?include_criteria_set_event_options=true&criteria_set_entry_id=${data.entryId}`
    );
    // The value we return becomes the `fulfilled` action payload
    return response;
  }
);

export const updateCriteriaSet = createAsyncThunk(
  "criteriaSet/updateCriteriaSet",
  async (
    data: { dataset: string; transformation: UpdateEventProps },
    thunkApi
  ) => {
    const response = await APIRequest(
      "POST",
      `/api/v2/${data.dataset}/cohort_def/`,
      {
        transformation: { ...data.transformation },
      }
    );

    thunkApi.dispatch(
      setCurrentCohortDef({
        dataset: data.dataset,
      })
    );
    // The value we return becomes the `fulfilled` action payload
    return response;
  }
);

export const criteriaSetSlice = createSlice({
  name: "criteriaSet",
  initialState,
  // The `reducers` field lets us define reducers and generate associated actions
  reducers: {
    clearCriteriaSetOptions() {
      return initialState;
    },
  },
  extraReducers: (builder) => {
    // show loading for fetching the current cohort def only
    builder.addCase(loadCriteraSetOptions.fulfilled, (state, action) => {
      return { ...state, ...action.payload };
    });
  },
});

export const { clearCriteriaSetOptions } = criteriaSetSlice.actions;

export default criteriaSetSlice.reducer;

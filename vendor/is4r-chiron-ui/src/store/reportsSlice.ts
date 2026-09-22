import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { APIRequest } from "../api";
// import _ from "lodash";

export type ReportsResult = {
  id: number;
  name: string;
  project: number;
  project_name: string;
  description: string;
  creator: number;
  created: string;
  type: string;
  definition: string;
  creator_name: string;
  public: boolean;
  starred: boolean;
  share_with: number[];
  sharing_description: string;
};

export type ReportsList = {
  count: number;
  next?: number;
  previous?: number;
  results: ReportsResult[];
};

export type ReportCategory = {
  label: string;
  pk: number;
  count: number;
  state: string;
};

export type ReportCategories = {
  current_page: string;
  qProject: ReportCategory[];
  custom_report_categories: ReportCategory[];
};

export type ReportsState = {
  errors: string[];
  warnings: string[];
  count?: number;
  previous?: number;
  next?: number;
  results?: ReportsResult[];
  filteredCategory?: string | number;
  filteredState?: string;
  reportCategories?: ReportCategories;
  reportsStatus: "idle" | "loading" | "failed" | "done";
};

const initialState: ReportsState = {
  errors: [],
  warnings: [],
  reportsStatus: "idle",
  filteredCategory: "",
  filteredState: "all",
};

export const flagReport = createAsyncThunk(
  "report/flag",
  async (
    properties: {
      dataset: string;
      report: number;
      add: boolean;
      selectedCategory?: string | number | undefined;
      selectedState?: string | undefined;
    },
    thunkApi
  ) => {
    const postData = {
      add_or_remove: properties.add == true ? "add" : "remove",
    };
    await APIRequest(
      "POST",
      `/api/v2/${properties.dataset}/reports/${properties.report}/flag/`,
      postData
    );

    thunkApi.dispatch(
      loadReportsDef({
        dataset: properties.dataset,
        project_id: properties.selectedCategory?.toString(),
        state: properties.selectedState,
      })
    );
  }
);

export const loadReportsDef = createAsyncThunk(
  "report/loadReportsDef",
  async ({
    dataset,
    project_id = "",
    state = "",
  }: {
    dataset: string;
    project_id?: string;
    state?: string;
  }) => {
    const queryStrings = [`project_id=${project_id}`, `state=${state}`];
    const response = await APIRequest(
      "GET",
      `/api/v2/${dataset}/reports/?${queryStrings.join("&")}`
    );
    return {
      errors: response.errors,
      warnings: response.warnings,
      results: response.results,
      reportsStatus: "done",
      filteredCategory: project_id,
      filteredState: state == "" && project_id == "" ? "all" : state,
    };
  }
);

export const loadReportCategories = createAsyncThunk(
  "report/loadViewableReports",
  async (properties: { dataset: string }, thunkApi) => {
    const response = await APIRequest(
      "GET",
      `/api/v2/${properties.dataset}/reports/viewable_reports/`
    );
    thunkApi.dispatch(loadReportsDef({ dataset: properties.dataset }));
    return {
      errors: response.errors,
      warnings: response.warnings,
      reportCategories: {
        current_page: response.current_page,
        qProject: response.qProject,
        custom_report_categories: response.custom_report_categories,
      },
      reportsStatus: "done",
    };
  }
);

export const reportsSlice = createSlice({
  name: "reports",
  initialState,
  reducers: {
    resetReportsStatus(state) {
      state.reportsStatus = "idle";
      state.errors = [];
    },
  },
  extraReducers: (builder) => {
    [loadReportsDef, loadReportCategories].forEach((thunk) => {
      builder
        .addCase(thunk.pending, (state) => {
          state.reportsStatus = "loading";
        })
        .addCase(thunk.fulfilled, (state, action) => {
          return { ...state, ...action.payload, reportsStatus: "done" };
        })
        .addCase(thunk.rejected, (state) => {
          state.reportsStatus = "failed";
          state.errors = ["Reports List failed to load"];
          state.warnings = [];
        });
    });
  },
});

export const { resetReportsStatus } = reportsSlice.actions;

export default reportsSlice.reducer;

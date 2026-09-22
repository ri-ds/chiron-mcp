import { TableDef } from "../store/tableSliceTypes";
import { APIRequest } from "../api";
import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { loadTableDef } from "./tableSlice";
import { setCurrentCohortDef } from "./cohortSlice";

export type CheckedUser = {
  username: string;
  user_id: number;
  checked: boolean;
};

export type ReportFormData = {
  overwrite_query_def_with_active?: "yes" | "no";
  share_with?: CheckedUser[];
  project?: string | number | undefined;
  project_other?: string | undefined;
  description?: string | undefined;
  dataset?: number | undefined;
  newName?: string;
  public?: string | undefined;
  publicBool?: boolean;
};

export type SelectProjectItem = {
  label: string;
  value?: number;
};

export type ReportState = {
  errors: string[];
  warnings: string[];
  record_count?: number;
  subject_count?: number;
  paginator?: string;
  extended_table_def?: number[];
  reportTableStatus: "idle" | "loading" | "failed" | "done";
  reportCriteriaStatus: "idle" | "loading" | "failed" | "done";
  selectedReport: number;
  tableData?: TableDef;
  name?: string;
  public?: boolean;
  creator?: string;
  created?: string;
  description?: string;
  id?: number;
  showShareDialog: boolean;
  showReportSaveSuccessDialog: boolean;
  sharedUsers: CheckedUser[];
  fullUrl?: string;
  sharingDescription?: string;
  starred?: boolean;
  formTitle?: string;
  project?: string;
  projectId?: number;
  projectSelect: SelectProjectItem[];
  createReportMethod?: string;
  overWriteReportOptions: SelectProjectItem[];
};

export const loadReportCriteriaDef = createAsyncThunk(
  "report/loadReportCriteriaDef",
  async (
    properties: { dataset: string; report_id: number | undefined },
    thunkApi
  ) => {
    if (properties.dataset == "") {
      return initialState;
    }
    const response = await APIRequest(
      "GET",
      `/api/v2/${properties.dataset}/reports/get_report/?report_id=${properties.report_id}`
    );
    thunkApi.dispatch(
      setCurrentCohortDef({
        dataset: properties.dataset,
        data: {
          extended_cohort_def: response.extended_cohort_def,
          describe: response.cohort_description,
        },
      })
    );

    return {
      errors: response.errors,
      warnings: response.warnings,
      reportCriteriaStatus: "done",
      sharingDescription: response.oReport.public,
      name: response.oReport.name,
      creator: response.oReport.creator,
      created: response.oReport.created,
      description: response.oReport.description,
      selectedReport: response.oReport.id,
    };
  }
);
export const loadReportTableDef = createAsyncThunk(
  "report/loadReportTableDef",
  async (
    properties: {
      dataset: string;
      report_id: number | undefined;
      page: number;
      page_size: number;
    },
    thunkApi
  ) => {
    const queryStrings = [
      `output_type=json`,
      `page=${properties.page}`,
      `records_per_page=${properties.page_size}`,
      `sort_field=`,
      `sort_direction=1`,
    ];
    const response = await APIRequest(
      "GET",
      `/api/v2/${properties.dataset}/report_tools/${properties.report_id}/preview/?${queryStrings.join("&")}`
    );
    thunkApi.dispatch(
      loadTableDef({
        dataset: properties.dataset,
        data: response,
        pageSize: properties.page_size,
      })
    );

    return {
      errors: response.errors,
      warnings: response.warnings,
      reportTableStatus: "done",
      tableData: response,
    };
  }
);

export const sortReportColumn = createAsyncThunk(
  "report/sortColumn",
  async (
    properties: {
      dataset: string;
      entryId: string;
      report_id: number | undefined;
      sort_direction: number;
    },
    thunkApi
  ) => {
    const queryStrings = [
      `output_type=json`,
      `page=1`,
      `records_per_page=25`,
      `sort_field=${properties.entryId}`,
      `sort_direction=${properties.sort_direction}`,
    ];

    const response = await APIRequest(
      "GET",
      `/api/v2/${properties.dataset}/report_tools/${properties.report_id}/preview/?${queryStrings.join("&")}`
    );
    thunkApi.dispatch(
      loadTableDef({ dataset: properties.dataset, data: response })
    );
    return {
      errors: response.errors,
      warnings: response.warnings,
      reportTableStatus: "done",
      tableData: response,
    };
  }
);

export const loadReportToResults = createAsyncThunk(
  "report/loadAsActive",
  async (properties: { dataset: string; reportId: number | undefined }) => {
    const response = await APIRequest(
      "POST",
      `/api/v2/${properties.dataset}/report_tools/${properties.reportId}/load_as_active/`
    );

    return {
      errors: response.errors.filter((e: string) => e.length > 0),
      warnings: response.warnings,
    };
  }
);

export const createReport = createAsyncThunk(
  "report/createReport",
  async (properties: {
    dataset: string;
    reportId?: number | undefined;
    postData?: ReportFormData | undefined;
  }) => {
    let response;

    if (properties.postData == undefined) {
      response = await APIRequest(
        "GET",
        `/api/v2/${properties.dataset}/reports/create_form/`
      );
      return {
        sharedUsers: response.data.fForm.shared_options,
        formTitle: response.title,
        project: "--- create new ---",
        projectId: -1,
        public: false,
        selectedReport: -1,
        name: "---select a report---",
        description: "",
        projectSelect: response.data.fForm.project_selection,
        overWriteReportOptions: response.data.oReports,
        createReportMethod: "all",
        errors: response.errors.filter((e: string) => e.length > 0),
      };
    } else {
      const cleanedPostData = {
        ...properties.postData,
        share_with: properties.postData.share_with
          ?.filter((u) => u.checked)
          .map((u) => u.user_id),
        name: properties.postData.newName,
      };
      if (cleanedPostData.publicBool) {
        cleanedPostData.public = "on";
      }
      delete cleanedPostData.publicBool;
      delete cleanedPostData.newName;
      response = await APIRequest(
        "POST",
        `/api/v2/${properties.dataset}/reports/create_form/`,
        cleanedPostData
      );
      return {
        errors: response.errors.filter((e: string) => e.length > 0),
        warnings: response.warnings,
      };
    }
  }
);

export const editReport = createAsyncThunk(
  "report/editReport",
  async (properties: {
    dataset: string;
    reportId: number | undefined;
    postData?: ReportFormData | undefined;
  }) => {
    let response;
    if (properties.postData == undefined) {
      response = await APIRequest(
        "GET",
        `/api/v2/${properties.dataset}/reports/${properties.reportId}/edit_form/?output_type=json`
      );
      return {
        sharedUsers: response.data.fForm.shared_options,
        formTitle: response.title,
        description: response.data.oReport.description,
        name: response.data.oReport.name,
        project: response.data.oReport.project,
        projectId: response.data.oReport.project_id,
        public: response.data.oReport.public,
        projectSelect: response.data.fForm.project_selection,
        errors: response.errors.filter((e: string) => e.length > 0),
      };
    } else {
      const cleanedPostData = {
        ...properties.postData,
        share_with: properties.postData.share_with
          ?.filter((u) => u.checked)
          .map((u) => u.user_id),
        name: properties.postData.newName,
      };
      if (cleanedPostData.publicBool) {
        cleanedPostData.public = "on";
      }
      delete cleanedPostData.publicBool;
      delete cleanedPostData.newName;
      response = await APIRequest(
        "POST",
        `/api/v2/${properties.dataset}/reports/${properties.reportId}/edit_form/`,
        cleanedPostData
      );
      return {
        errors: response.errors.filter((e: string) => e.length > 0),
        warnings: response.warnings,
      };
    }
  }
);

export const deleteReport = createAsyncThunk(
  "report/deleteReport",
  async (properties: {
    dataset: string;
    reportId: number | undefined;
    postData?: ReportFormData;
  }) => {
    let response;
    if (properties.postData == undefined) {
      response = await APIRequest(
        "GET",
        `/api/v2/${properties.dataset}/reports/${properties.reportId}/delete_form/`
      );
      return {
        name: response.data.oReport,
        formTitle: response.title,
        errors: response.errors.filter((e: string) => e.length > 0),
        warnings: response.warnings,
      };
    } else {
      const response = await APIRequest(
        "POST",
        `/api/v2/${properties.dataset}/reports/${properties.reportId}/delete_form/`
      );
      return {
        errors: response.errors.filter((e: string) => e.length > 0),
        warnings: response.warnings,
      };
    }
  }
);

export const shareReport = createAsyncThunk(
  "report/shareReport",
  async (properties: {
    dataset: string;
    reportId: number | undefined;
    postData?: ReportFormData | undefined;
  }) => {
    let response;

    if (properties.postData == undefined) {
      response = await APIRequest(
        "GET",
        `/api/v2/${properties.dataset}/reports/${properties.reportId}/share_form/?output_type=json`
      );
      return {
        sharedUsers: response.data.fForm.shared_options,
        fullUrl: response.data.full_url,
        formTitle: response.title,
        errors: response.errors.filter((e: string) => e.length > 0),
      };
    } else {
      const cleanedPostData = {
        share_with: properties.postData.share_with
          ?.filter((u) => u.checked)
          .map((u) => u.user_id),
      };

      response = await APIRequest(
        "POST",
        `/api/v2/${properties.dataset}/reports/${properties.reportId}/share_form/`,
        cleanedPostData
      );
      return {
        errors: response.errors.filter((e: string) => e.length > 0),
        warnings: response.warnings,
      };
    }
  }
);

const initialState: ReportState = {
  errors: [],
  warnings: [],
  reportTableStatus: "idle",
  reportCriteriaStatus: "idle",
  selectedReport: -1,
  showShareDialog: false,
  showReportSaveSuccessDialog: false,
  sharedUsers: [],
  projectSelect: [],
  overWriteReportOptions: [],
};

export const reportSlice = createSlice({
  name: "report",
  initialState,
  reducers: {
    updateSelectedReport(state, action) {
      state.selectedReport = action.payload;
      state.reportTableStatus = "loading";
    },
    resetReportStatus(state) {
      state.reportTableStatus = "idle";
      state.reportCriteriaStatus = "idle";
      state.errors = [];
    },
    toggleShareDialog(state) {
      state.showShareDialog = !state.showShareDialog;
    },
    toggleReportSaveSuccessDialog(state) {
      state.showReportSaveSuccessDialog = !state.showReportSaveSuccessDialog;
    },
    updateShareUsers(state, action) {
      const updatedUserIds = action.payload.map(
        (user: CheckedUser) => user.user_id
      );
      state.sharedUsers = state.sharedUsers.map((user) => ({
        ...user,
        checked: updatedUserIds.includes(user.user_id),
      }));
    },
    updateReportProject(state, action) {
      state.project = action.payload.label;
      state.projectId = action.payload.value;
    },
    toggleReportPublic(state) {
      state.public = !state.public;
    },
    updateReportName(state, action) {
      state.name = action.payload;
    },
    updateReportDescription(state, action) {
      state.description = action.payload;
    },
    toggleCreateReportMethod(state, action) {
      state.createReportMethod = action.payload;
    },
    resetReportData(state) {
      state.errors = [];
      state.warnings = [];
      state.reportTableStatus = "idle";
      state.reportCriteriaStatus = "idle";
      state.selectedReport = -1;
      state.showShareDialog = false;
      state.sharedUsers = [];
      state.projectSelect = [];
      state.description = undefined;
      state.name = undefined;
      state.created = undefined;
      state.project = undefined;
      state.projectId = undefined;
      state.createReportMethod = undefined;
      state.tableData = undefined;
    },
  },
  extraReducers: (builder) => {
    [
      loadReportTableDef,
      loadReportCriteriaDef,
      sortReportColumn,
      shareReport,
      editReport,
      deleteReport,
      createReport,
    ].forEach((thunk) => {
      builder
        .addCase(thunk.pending, (state) => {
          state.reportTableStatus = "loading";
          // state.reportCriteriaStatus = "loading";
        })
        .addCase(thunk.fulfilled, (state, action) => {
          return {
            ...state,
            ...action.payload,
            reportTableStatus: "done",
            reportCriteriaStatus: "done",
          };
        })
        .addCase(thunk.rejected, (state) => {
          state.reportTableStatus = "failed";
          state.errors = ["Report failed to load"];
          state.warnings = [];
        });
    });
  },
});

export const {
  updateSelectedReport,
  resetReportStatus,
  toggleShareDialog,
  toggleReportSaveSuccessDialog,
  updateShareUsers,
  updateReportProject,
  updateReportName,
  updateReportDescription,
  toggleReportPublic,
  resetReportData,
  toggleCreateReportMethod,
} = reportSlice.actions;

export default reportSlice.reducer;

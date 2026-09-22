import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { APIRequest, APIFileRequest } from "../api";
import _ from "lodash";
import { CohortState } from "./cohortSlice";
import {
  TableState,
  TableDef,
  SortDef,
  ColumnDef,
  TableColumn,
  Transformation,
} from "./tableSliceTypes";

const initialState: TableState = {
  errors: [],
  warnings: [],
  tableStatus: "idle",
  pageSize: 25,
};

function translateTableDefToColumns(tableDef: TableDef["extended_table_def"]) {
  // build sorting lookups,
  const sorting: { [k: string]: number } = {};
  tableDef.sort.forEach(
    (sort: SortDef) => (sorting[sort.entry_id] = sort.direction)
  );
  if (tableDef.fields.length) {
    return tableDef.fields.map((item: ColumnDef) => ({
      entryId: item.entry_id,
      conceptId: item.concept_id,
      name: item.label,
      categories: item.categories,
      canDelete: item.can_delete,
      canSort: item.can_sort,
      hasErrors: item.has_errors,
      isAggregate: item.aggregate,
      aggregationColumnText: item.aggregation_method?.replace("_", " "),
      aggregationMethod: _.startCase(
        item.aggregation_method?.replace("_", " ")
      ),
      alias: item.alias ?? undefined,
      categorize: item.categorize,
      sortDirection: sorting[item.entry_id] ?? undefined,
    }));
  }
  return [];
}

export const loadTableDef = createAsyncThunk(
  "table/loadTableDef",
  async ({
    dataset,
    page = 1,
    pageSize = 25,
    data = undefined,
  }: {
    dataset: string;
    page?: number;
    pageSize?: number;
    data?: undefined | TableDef;
  }) => {
    const queryStrings = [`page=${page}`, `records_per_page=${pageSize}`];

    let response;
    if (data == undefined) {
      try {
        response = await APIRequest(
          "GET",
          `/api/v2/${dataset}/query_tools/preview/?${queryStrings.join("&")}`
        );
      } catch (e: any) {
        return {
          errors: [e.message],
        };
      }
    } else {
      response = data;
    }

    return {
      errors: response.errors,
      warnings: response.warnings,
      columns: translateTableDefToColumns(response.extended_table_def),
      tableDef: response.extended_table_def,
      firstIndex: response.paginator.first_index,
      lastIndex: response.paginator.last_index,
      currentPage: response.paginator.current_page,
      pageSize: pageSize,
      lastPage: response.paginator.last_page,
      results: response.data,
      recordCount: response.record_count,
      subjectCount: response.subject_count,
      tableStatus: "done",
    };
  }
);

export const loadColumnInformation = createAsyncThunk(
  "table/loadColumnInformation",
  async ({
    dataset,
    column,
    refresh,
  }: {
    dataset: string;
    column: TableColumn;
    refresh: boolean;
  }) => {
    const response = await APIRequest(
      "GET",
      `/api/v2/${dataset}/concepts/${column.conceptId}/?include_table_def_options=true&table_def_entry_id=${column.entryId}`
    );

    return {
      editColumn: {
        ...response.table_def_options,
        concept: response.name,
        conceptId: response.permanent_id,
        aggregateOptions: undefined,
        refresh: refresh,
      },
    };
  }
);

export const loadAggregateOptions = createAsyncThunk(
  "table/loadAggregateOptions",
  async ({ url, search }: { url: string; search: string }) => {
    const finalUrl = `${url}${search}`;
    const response = await APIRequest("GET", finalUrl);
    return {
      aggregateOptions: response.results,
    };
  }
);

export const downloadCsvFile = createAsyncThunk(
  "table/downloadCsvFile",
  async (payload: {
    dataset: string;
    cohort_def: CohortState["extended_cohort_def"];
    table_def?: TableDef["extended_table_def"];
    report_id?: number;
  }) => {
    const urlString = !payload.report_id
      ? `query_tools`
      : `report_tools/${payload.report_id}`;

    if (!payload.report_id) {
      await APIFileRequest(
        "POST",
        `/api/v2/${payload.dataset}/${urlString}/export_csv/`,
        "results_export.csv",
        payload
      );
    } else {
      await APIFileRequest(
        "GET",
        `/api/v2/${payload.dataset}/${urlString}/export_csv/`,
        "results_export.csv"
      );
    }
  }
);

export const applyTransformation = createAsyncThunk(
  "table/applyTransformation",
  async (
    payload: {
      transformation: Transformation;
      dataset: string;
      refresh: boolean;
    },
    thunkApi
  ) => {
    if (
      payload.transformation.type === "resort_columns" &&
      typeof payload.transformation.src == "number" &&
      typeof payload.transformation.dest == "number"
    ) {
      const rslt = await APIRequest(
        "GET",
        `/api/v2/${payload.dataset}/table_def`
      );
      const entryIdList = rslt.extended_table_def.fields.map(
        (t: Transformation) => t.entry_id
      );

      // remove entry at src
      const [entry] = entryIdList.splice(payload.transformation.src, 1);

      // insert removed entry at dest
      entryIdList.splice(payload.transformation.dest, 0, entry);

      payload.transformation.entry_ids = entryIdList;
      delete payload.transformation.src;
      delete payload.transformation.dest;
    }
    const rslt = await APIRequest(
      "POST",
      `/api/v2/${payload.dataset}/table_def/`,
      {
        transformation: payload.transformation,
      }
    );
    // only update data on the reset action and sort actions
    if (payload.refresh) {
      return await thunkApi.dispatch(
        loadTableDef({ dataset: payload.dataset })
      );
    } else {
      return {
        columns: translateTableDefToColumns(rslt.extended_table_def),
        tableDef: rslt.extended_table_def,
        results: [],
        errors: rslt.errors,
        warnings: rslt.warnings,
      };
    }
  }
);

export const tableSlice = createSlice({
  name: "cohort",
  initialState,
  // The `reducers` field lets us define reducers and generate associated actions
  reducers: {
    resetTableStatus(state) {
      state.tableStatus = "idle";
    },
    setTablePage(state, action) {
      state.tablePage = action.payload.page;
    },
    clearColumnInformation(state) {
      state.editColumn = undefined;
    },
    clearAggregateOptions(state) {
      state.aggregateOptions = [];
    },
    openModal(state) {
      state.closeModal = false;
      state.openModal = true;
    },
    closeModal(state) {
      state.closeModal = true;
      state.openModal = false;
    },
  },
  extraReducers: (builder) => {
    [
      loadTableDef,
      loadColumnInformation,
      loadAggregateOptions,
      applyTransformation,
    ].forEach((thunk) => {
      builder
        .addCase(thunk.pending, (state) => {
          state.tableStatus = "loading";
        })
        .addCase(thunk.fulfilled, (state, action) => {
          return { ...state, ...action.payload, tableStatus: "done" };
        })
        .addCase(thunk.rejected, (state, action) => {
          state.tableStatus = "failed";
          state.errors =
            action.error && action.error.message
              ? [action.error.message]
              : ["Report failed to load"];
          state.warnings = [];
          state.results = undefined;
          state.columns = undefined;
        });
    });
  },
});

export const {
  resetTableStatus,
  clearColumnInformation,
  clearAggregateOptions,
  setTablePage,
  openModal,
  closeModal,
} = tableSlice.actions;

export default tableSlice.reducer;

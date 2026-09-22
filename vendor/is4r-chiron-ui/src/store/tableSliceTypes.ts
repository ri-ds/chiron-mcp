/* Table type definitions */

// open this issue to see if we can fix the icon type
// https://github.com/backstage/backstage/issues/18018
export type MenuButton = {
  label: string;
  onClick: () => void;
  icon: any;
  dataField?: string;
  disabled?: boolean;
};

export type TableColumn = {
  entryId: string;
  conceptId: string;
  name: string;
  categories: string[];
  canDelete: boolean;
  hasErrors: boolean;
  isAggregate: boolean;
  aggregationColumnText?: string;
  aggregationMethod?: string;
  alias?: string /* do we need? */;
  categorize: boolean;
  sortDirection?: number;
};

export type AggregationOptionInput = {
  id: string;
  label: string;
  type: string;
  options_callback?: string;
  selected: string | string[];
  options: string[];
};

export type AggregationOption = {
  id: string;
  group: string;
  label: string;
  selected: boolean;
  inputs: AggregationOptionInput[];
};

export type EditColumn = {
  aggregation_options: AggregationOption[];
  entry_id: string;
  concept: string;
  conceptId: string;
  // criteria_set_options: {};
  // selected_aggregation_criteria_set?: {};
  entry_alias?: string;
  refresh: boolean;
};

export type TableResult = string[] | number[];

export type AggregationOptionTypeahead = {
  id: string | number;
  text: string;
};

export type Transformation = {
  [key: string]: number | string | string[] | undefined;
};

export type TableState = {
  errors: string[];
  warnings: string[];
  firstIndex?: number;
  lastIndex?: number;
  currentPage?: number;
  lastPage?: number;
  pageSize: number;
  recordCount?: number;
  subjectCount?: number;
  results?: TableResult[];
  columns?: TableColumn[];
  tableDef?: TableDef["extended_table_def"];
  editColumn?: EditColumn;
  aggregateOptions?: AggregationOptionTypeahead[];
  tablePage?: "report" | "results";
  tableStatus: "idle" | "loading" | "failed" | "done";
  openModal?: boolean;
  closeModal?: boolean;
};

/**
 * The following types are to represent what comes back from the API
 */

export type SortDef = {
  entry_id: string;
  direction: number;
  label: string;
};

export type ColumnDef = {
  entry_id: string;
  concept_name: string;
  concept_id: string;
  categories: string[];
  label: string;
  can_delete: boolean;
  can_sort: boolean;
  has_errors: boolean;
  aggregate: boolean;
  aggregation_method?: string;
  alias?: string;
  categorize: boolean;
};

export type TableDef = {
  warnings: string[];
  errors: string[];
  record_count: number;
  subject_count: number;
  report_id?: number;
  paginator: {
    first_index: number;
    last_index: number;
    current_page: number;
    previous_page?: number;
    next_page?: number;
    total_records: number;
  };
  extended_table_def: {
    fields: ColumnDef[];
    table_type: "string";
    sort: SortDef[];
  };
  data: TableResult[];
};

import { grey, red } from "@mui/material/colors";
import {
  Paper,
  TableContainer,
  Table,
  TableHead,
  TableCell,
  TableRow,
  TableBody,
  Typography,
  Box,
  Select,
  MenuItem,
  Pagination,
  SelectChangeEvent,
  IconButton,
  Alert,
  AlertTitle,
} from "@mui/material";

import { useAppDispatch, useAppSelector } from "../../store/hooks";
import {
  applyTransformation,
  loadColumnInformation,
  loadTableDef,
} from "../../store/tableSlice";
import { loadReportTableDef, sortReportColumn } from "../../store/reportSlice";
import {
  Remove as RemoveIcon,
  ArrowDropUp as ArrowDropUpIcon,
  ArrowDropDown as ArrowDropDownIcon,
  SortByAlpha as SortByAlphaIcon,
  Edit,
} from "@mui/icons-material";
import FormatCell from "./FormatCell";
import EditColumn from "./EditColumn";
import EditTable from "./EditTable";

export default function ResultsTable({
  currentViewPage = "results",
}: {
  currentViewPage: "report" | "results";
}) {
  const recordCount = useAppSelector((state) => state.table.recordCount);
  const columns = useAppSelector((state) => state.table.columns);
  const currentPage = useAppSelector((state) => state.table.currentPage);
  const firstIndex = useAppSelector((state) => state.table.firstIndex);
  const lastIndex = useAppSelector((state) => state.table.lastIndex);
  const lastPage = useAppSelector((state) => state.table.lastPage);
  const results = useAppSelector((state) => state.table.results);
  const columnInformation = useAppSelector((state) => state.table.editColumn);
  const report_id = useAppSelector((state) => state.report.selectedReport);
  const tableStatus = useAppSelector((state) => state.table.tableStatus);
  const dispatch = useAppDispatch();
  const pageSize = useAppSelector((state) => state.table.pageSize);
  const showEditTable = currentViewPage == "report" ? false : true;
  const dataset = useAppSelector((state) => state.auth.dataset?.unique_id);

  return (
    <>
      <EditTable />
      <Paper sx={{ width: "100%", overflow: "hidden" }}>
        {tableStatus == "done" && dataset ? (
          columns && columns.length > 0 ? (
            <TableContainer sx={{ maxHeight: 540 }}>
              <Table stickyHeader aria-label="sticky table">
                <TableHead>
                  <TableRow>
                    {columns?.map((column, index) => (
                      <TableCell
                        key={column.entryId}
                        style={{
                          position:
                            index == 1 && showEditTable ? "sticky" : undefined,
                          left: index == 0 && showEditTable ? 0 : "",
                          zIndex: index == 0 && showEditTable ? 1 : 0,
                          backgroundColor:
                            index == 0 && showEditTable ? "white" : "",
                          minWidth: 200,
                          border: "1px solid",
                          borderColor: grey[300],
                          borderRight:
                            index == 0 && columns?.length > 1 && showEditTable
                              ? "1px solid #E0E0E0"
                              : "",
                          borderCollapse: "collapse",
                          padding: "0.25rem 0.5rem",
                        }}
                      >
                        {column.canDelete && showEditTable ? (
                          <IconButton
                            onClick={() =>
                              dispatch(
                                applyTransformation({
                                  transformation: {
                                    type: "delete_entry",
                                    entry_id: column.entryId,
                                  },
                                  dataset: dataset,
                                  refresh: true,
                                })
                              )
                            }
                            sx={{
                              position: "absolute",
                              borderRadius: "100%",
                              top: "0.5rem",
                              right: "0.5rem",
                              height: "1rem",
                              width: "1rem",
                              bgcolor: red[600],
                              color: "white",
                              ":hover": {
                                bgcolor: red[700],
                                cursor: "pointer",
                              },
                            }}
                          >
                            <RemoveIcon color="inherit" fontSize="small" />
                          </IconButton>
                        ) : null}
                        <Box
                          sx={{ paddingTop: "15px" }}
                          display="flex"
                          alignItems="center"
                          gap={1}
                        >
                          <Typography fontWeight="bold">
                            {column.alias
                              ? column.alias
                              : column.name.replace(
                                  `(${column.aggregationColumnText})`,
                                  ""
                                )}
                          </Typography>
                          <IconButton
                            size="small"
                            onClick={() =>
                              showEditTable
                                ? dispatch(
                                    applyTransformation({
                                      dataset: dataset,
                                      transformation: {
                                        entry_id: column.entryId,
                                        type: "add_sort_entry",
                                      },
                                      refresh: true,
                                    })
                                  )
                                : dispatch(
                                    sortReportColumn({
                                      dataset: dataset,
                                      entryId: column.entryId,
                                      report_id: report_id,
                                      sort_direction:
                                        column.sortDirection == undefined
                                          ? 1
                                          : column.sortDirection * -1,
                                    })
                                  )
                            }
                          >
                            {column.sortDirection === 1 ? (
                              <ArrowDropUpIcon
                                fontSize="small"
                                color="primary"
                              />
                            ) : column.sortDirection === -1 ? (
                              <ArrowDropDownIcon
                                fontSize="small"
                                color="primary"
                              />
                            ) : (
                              <SortByAlphaIcon
                                fontSize="small"
                                color="primary"
                              />
                            )}
                          </IconButton>
                        </Box>
                        <Box mt={-1} display="flex" alignItems="center" gap={1}>
                          <Typography variant="caption">
                            {column.categories.join(" / ")}
                          </Typography>
                        </Box>

                        <Box
                          display="flex"
                          alignItems="center"
                          justifyContent="flex-start"
                          gap={0.5}
                        >
                          <Typography variant="caption">
                            Aggregation:{" "}
                          </Typography>
                          <Typography
                            variant="caption"
                            color="primary"
                            fontWeight="bold"
                          >
                            {column.isAggregate
                              ? column.aggregationMethod
                              : "Stack"}
                          </Typography>
                          {showEditTable ? (
                            <IconButton
                              size="small"
                              color="primary"
                              onClick={() =>
                                dispatch(
                                  loadColumnInformation({
                                    dataset: dataset,
                                    column: column,
                                    refresh: true,
                                  })
                                )
                              }
                            >
                              <Edit fontSize="small" />
                            </IconButton>
                          ) : null}
                        </Box>
                      </TableCell>
                    ))}
                  </TableRow>
                </TableHead>

                {columnInformation ? (
                  <EditColumn column={columnInformation} />
                ) : null}

                <TableBody>
                  {results?.map((row, idx) => {
                    return (
                      <TableRow
                        hover
                        role="checkbox"
                        tabIndex={-1}
                        key={`row-${idx}`}
                      >
                        {row.map((item, itemIdx) => (
                          <TableCell
                            style={{
                              position:
                                itemIdx == 0 && showEditTable
                                  ? "sticky"
                                  : undefined,
                              left: itemIdx == 0 && showEditTable ? 0 : "",
                              backgroundColor:
                                itemIdx == 0 && showEditTable ? "white" : "",
                              borderRight:
                                itemIdx == 0 &&
                                columns?.length > 1 &&
                                showEditTable
                                  ? "1px solid #E0E0E0"
                                  : "",
                            }}
                            size="small"
                            key={`cell-${itemIdx}`}
                          >
                            <FormatCell item={item} />
                          </TableCell>
                        ))}
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          ) : (
            <Alert severity="warning">
              <AlertTitle>No columns selected</AlertTitle>
              Please set a default concept for this dataset
            </Alert>
          )
        ) : null}
      </Paper>
      {columns && columns.length > 0 ? (
        <Box
          display="flex"
          justifyContent="space-between"
          alignItems="center"
          p={1.5}
        >
          <Box display="flex" alignItems="center" gap={1}>
            <Typography>
              Showing {firstIndex}-{lastIndex} of {recordCount}
            </Typography>
            <Select
              size="small"
              autoWidth
              margin="dense"
              value={pageSize?.toString()}
              onChange={(event: SelectChangeEvent) => {
                const pageSize = Number(event.target.value);
                if (showEditTable) {
                  dispatch(
                    loadTableDef({
                      dataset: dataset ? dataset : "",
                      page: 1,
                      pageSize,
                    })
                  );
                } else {
                  dispatch(
                    loadReportTableDef({
                      dataset: dataset ? dataset : "",
                      report_id: report_id,
                      page: 1,
                      page_size: pageSize,
                    })
                  );
                }
              }}
            >
              <MenuItem value={25}>Show 25</MenuItem>
              <MenuItem value={50}>Show 50</MenuItem>
              <MenuItem value={75}>Show 75</MenuItem>
              <MenuItem value={100}>Show 100</MenuItem>
            </Select>
          </Box>
          <Box>
            <Pagination
              count={lastPage}
              color="primary"
              size="small"
              page={currentPage || 1}
              onChange={(_, value: number) =>
                showEditTable
                  ? dispatch(
                      loadTableDef({
                        dataset: dataset ? dataset : "",
                        page: Number(value),
                        pageSize,
                      })
                    )
                  : dispatch(
                      loadReportTableDef({
                        dataset: dataset ? dataset : "",
                        report_id: report_id,
                        page: Number(value),
                        page_size: pageSize,
                      })
                    )
              }
            />
          </Box>
        </Box>
      ) : null}
    </>
  );
}

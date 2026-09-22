import { grey, red } from "@mui/material/colors";
import {
  Paper,
  TableContainer,
  Table,
  TableHead,
  TableCell,
  TableRow,
  TableBody,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import StarIcon from "@mui/icons-material/Star";

import { useAppSelector, useAppDispatch } from "../../store/hooks";
import { flagReport } from "../../store/reportsSlice";
import type { ReportsResult } from "../../store/reportsSlice";
import {
  deleteReport,
  editReport,
  toggleShareDialog,
  updateSelectedReport,
} from "../../store/reportSlice";
import config from "../../config";

export default function ReportsTable() {
  const reports = useAppSelector((state) => state.reports.results);
  const chironUserId = useAppSelector(
    (state) => state.auth.dataset?.chironUserId
  );
  const dispatch = useAppDispatch();
  const dataset = useAppSelector((state) => state.auth.dataset?.unique_id);
  const filteredCategory = useAppSelector(
    (state) => state.reports.filteredCategory
  );
  const filteredState = useAppSelector((state) => state.reports.filteredState);

  //defining columns for table and values from reportList type
  const columns = [
    { label: "Star", val: "star" },
    { label: "ID", val: "id" },
    { label: "Name", val: "name" },
    { label: "Created By", val: "creator_name" },
    { label: "Creation Date", val: "created" },
    { label: "Sharing", val: "sharing_description" },
    { label: "Description", val: "description" },
    { label: "", val: "edit" },
  ];

  return (
    <>
      <Paper sx={{ overflow: "auto", m: 2 }}>
        <TableContainer>
          <Table stickyHeader aria-label="sticky table">
            <TableHead>
              <TableRow>
                {columns?.map((column) => (
                  <TableCell
                    key={column.val}
                    style={{
                      minWidth: 150,
                      border: "1px solid",
                      borderColor: grey[300],
                      borderCollapse: "collapse",
                      padding: "0.25rem 0.5rem",
                      backgroundColor: config.table.secondaryHeaderColor[100],
                    }}
                  >
                    {column.label}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>

            <TableBody>
              {reports?.map((row: ReportsResult) => {
                return (
                  <TableRow
                    hover
                    tabIndex={-1}
                    key={`row-${row.id}`}
                    sx={{ cursor: "pointer" }}
                  >
                    {columns.map((column, itemIdx: number) => (
                      <TableCell
                        size="small"
                        key={`cell-${itemIdx}`}
                        onClick={() => {
                          if (column.val == "edit") {
                            return;
                          }
                          if (column.val == "star") {
                            dispatch(
                              flagReport({
                                dataset: dataset ? dataset : "",
                                report: row.id,
                                add: !row.starred,
                                selectedCategory: filteredCategory,
                                selectedState:
                                  filteredState == "all" ? "" : filteredState,
                              })
                            );
                          } else {
                            window.location.href = `/${dataset}/reports/${row.id}`;
                          }
                        }}
                      >
                        {column.val == "star" ? (
                          <StarIcon
                            sx={{
                              color:
                                row.starred == true
                                  ? config.table.conceptHeaderColor[400]
                                  : grey[200],
                            }}
                          ></StarIcon>
                        ) : column.val == "created" ? (
                          row[column.val].split("T")[0]
                        ) : column.val != "edit" ? (
                          row[column.val as keyof ReportsResult]
                        ) : row.creator == chironUserId ? (
                          <>
                            <EditIcon
                              sx={{
                                color: config.table.aggHeaderColor[600],
                              }}
                              onClick={function () {
                                dispatch(updateSelectedReport(row.id));
                                dispatch(
                                  editReport({
                                    dataset: dataset ? dataset : "",
                                    reportId: row.id,
                                  })
                                );
                                dispatch(toggleShareDialog());
                              }}
                            ></EditIcon>
                            <DeleteIcon
                              sx={{
                                color: red[600],
                              }}
                              onClick={() => {
                                dispatch(updateSelectedReport(row.id));
                                dispatch(toggleShareDialog());
                                dispatch(
                                  deleteReport({
                                    dataset: dataset ? dataset : "",
                                    reportId: row.id,
                                  })
                                );
                              }}
                            ></DeleteIcon>
                          </>
                        ) : null}
                      </TableCell>
                    ))}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>
    </>
  );
}

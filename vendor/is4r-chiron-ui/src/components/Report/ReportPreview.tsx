import { Box, Paper, Skeleton } from "@mui/material";
import ResultsTable from "../Results/Table";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import { loadReportTableDef } from "../../store/reportSlice";
import { setTablePage } from "../../store/tableSlice";

export default function ReportPreview() {
  const dispatch = useAppDispatch();
  const dataset = useAppSelector((state) => state.auth.dataset?.unique_id);
  const selectedReport = useAppSelector((state) => state.report.selectedReport);
  const tableStatus = useAppSelector((state) => state.report.reportTableStatus);
  const tablePage = useAppSelector((state) => state.table.tablePage);
  const currentPage = "report";

  if (
    dataset &&
    selectedReport != -1 &&
    (tableStatus === "idle" || tablePage != currentPage)
  ) {
    dispatch(setTablePage({ page: currentPage }));
    dispatch(
      loadReportTableDef({
        dataset: dataset,
        report_id: selectedReport,
        page: 1,
        page_size: 25,
      })
    );
  }
  return (
    <Box p={2} pb={8}>
      {tableStatus == "done" ? (
        <ResultsTable currentViewPage={currentPage} />
      ) : (
        <Paper sx={{ width: "100%", overflow: "hidden" }}>
          <Skeleton variant="rounded" height={400} />
        </Paper>
      )}
    </Box>
  );
}

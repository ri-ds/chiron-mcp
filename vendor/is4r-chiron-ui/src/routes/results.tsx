import { Box } from "@mui/material";
import ResultsHeader from "../components/Results/Header";
import ResultsTable from "../components/Results/Table";
import Filters from "../components/Filters";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { loadTableDef, setTablePage } from "../store/tableSlice";
import ResultReportModal from "../components/Report/Modals/ResultReportModal";
import { resetReportStatus } from "../store/reportSlice";
import ReportSavedModal from "../components/Report/EditReport/ReportSavedModal";

export default function ResultsRoute() {
  const dispatch = useAppDispatch();
  const tablePage = "results";
  const tableStatus = useAppSelector((state) => state.table.tableStatus);
  const currentPage = useAppSelector((state) => state.table.tablePage);
  const dataset = useAppSelector((state) => state.auth.dataset?.unique_id);
  if (dataset && (tableStatus === "idle" || currentPage != tablePage)) {
    dispatch(setTablePage({ page: tablePage }));
    dispatch(loadTableDef({ dataset: dataset }));
    dispatch(resetReportStatus());
  }

  return (
    <Box display="flex">
      <Box flexGrow={1} overflow={"scroll"}>
        <ResultReportModal></ResultReportModal>
        <ReportSavedModal></ReportSavedModal>
        <ResultsHeader currentViewPage={tablePage} />
        <Box p={2} minWidth={200}>
          <ResultsTable currentViewPage={tablePage} />
        </Box>
      </Box>
      <Box>
        <Filters resultsDisplay />
      </Box>
    </Box>
  );
}

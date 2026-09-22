import { Box, Typography } from "@mui/material";
import { useParams } from "react-router-dom";
import ReportDetails from "../components/Report/ReportDetails";
import ReportPreview from "../components/Report/ReportPreview";
import ResultsHeader from "../components/Results/Header";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { loadReportCriteriaDef } from "../store/reportSlice";
import ReportViewModal from "../components/Report/Modals/ReportViewModal";
import { useEffect } from "react";

export default function ReportRoute() {
  const dispatch = useAppDispatch();
  const { report_id } = useParams();
  const dataset = useAppSelector((state) => state.auth.dataset);

  useEffect(() => {
    dispatch(
      loadReportCriteriaDef({
        dataset: dataset?.unique_id ?? "",
        report_id: Number(report_id),
      })
    );
  }, [report_id, dataset, dispatch]);

  const selectedReport = useAppSelector((state) => state.report.selectedReport);
  const reportName = useAppSelector((state) => state.report.name);

  return (
    <Box
      sx={{
        display: "flex",
      }}
    >
      <Box>
        <ReportDetails></ReportDetails>
      </Box>
      <Box flexGrow={1} overflow={"scroll"}>
        <Typography variant="h4" sx={{ p: 2 }}>
          {selectedReport != -1
            ? `Report ${selectedReport}: ${reportName}`
            : ""}
        </Typography>
        <ReportViewModal></ReportViewModal>
        <ResultsHeader currentViewPage={"report"} reportId={selectedReport} />
        <ReportPreview></ReportPreview>
      </Box>
    </Box>
  );
}

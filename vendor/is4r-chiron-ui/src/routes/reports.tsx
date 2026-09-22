import { Alert, AlertTitle, Box, Typography } from "@mui/material";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { loadReportCategories } from "../store/reportsSlice";
import ReportsCategories from "../components/Reports/ReportsCategories";
import ReportsTable from "../components/Reports/ReportsTable";
import ReportsListModal from "../components/Report/Modals/ReportsListModal";

export default function ReportsRoute() {
  const dispatch = useAppDispatch();

  const reportsStatus = useAppSelector((state) => state.reports.reportsStatus);
  const reportsErrors = useAppSelector((state) => state.reports.errors);
  const dataset = useAppSelector((state) => state.auth.dataset);
  if (reportsStatus === "idle" && dataset) {
    dispatch(loadReportCategories({ dataset: dataset.unique_id }));
  }
  return (
    <Box display="flex">
      <Box width="100%">
        <Box>
          <Typography variant="h4" sx={{ p: 2 }}>
            Reports
          </Typography>
          {reportsErrors?.length > 0
            ? reportsErrors.map((err) => (
                <Alert severity="error">
                  <AlertTitle>Error</AlertTitle>
                  {err}
                </Alert>
              ))
            : null}
          <ReportsListModal></ReportsListModal>
          <ReportsCategories />
          <ReportsTable />
        </Box>
      </Box>
    </Box>
  );
}

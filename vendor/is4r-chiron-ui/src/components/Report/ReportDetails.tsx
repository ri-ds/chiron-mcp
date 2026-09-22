import { Typography, Box, Button, Collapse, Skeleton } from "@mui/material";
import { Link } from "react-router-dom";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import Filters from "../../components/Filters";
import { loadReportCriteriaDef } from "../../store/reportSlice";
import { setCohortPage } from "../../store/cohortSlice";
import { useState } from "react";
import { ChevronRight, ChevronLeft } from "@mui/icons-material";
import { grey } from "@mui/material/colors";
export default function ReportDetails() {
  const dispatch = useAppDispatch();
  const dataset = useAppSelector((state) => state.auth.dataset?.unique_id);
  const selectedReport = useAppSelector((state) => state.report.selectedReport);
  const reportCriteriaStatus = useAppSelector(
    (state) => state.report.reportCriteriaStatus
  );
  const currentPage = "report";

  const cohortPage = useAppSelector((state) => state.cohort.cohortPage);

  if (
    dataset &&
    selectedReport != -1 &&
    (reportCriteriaStatus === "idle" || cohortPage != currentPage)
  ) {
    dispatch(setCohortPage({ page: currentPage }));
    dispatch(
      loadReportCriteriaDef({ dataset: dataset, report_id: selectedReport })
    );
  }

  const reportName = useAppSelector((state) => state.report.name);
  const reportCreator = useAppSelector((state) => state.report.creator);
  const reportCreated = useAppSelector((state) => state.report.created);
  const reportDescription = useAppSelector((state) => state.report.description);
  const [checked, setChecked] = useState(true);

  const handleChange = () => {
    setChecked((prev) => !prev);
  };

  return (
    <Box sx={{ p: 2 }} borderRight={1} borderColor={grey[300]} maxWidth={400}>
      <Collapse orientation="horizontal" in={checked}>
        <Link to={`/${dataset}/reports/`} reloadDocument>
          <Button fullWidth variant="contained">
            Back to report list
          </Button>
        </Link>
        {reportCriteriaStatus == "done" ? (
          <>
            <Typography variant="h6">{reportName}</Typography>
            <p>{reportCreator}</p>
            <p>{reportDescription}</p>
            <p>Date Created : {reportCreated?.split("T")[0]}</p>
            <Box sx={{ overflowY: "scroll", height: "30rem" }}>
              <Filters
                resultsDisplay={true}
                currentPage={currentPage}
              ></Filters>
            </Box>
          </>
        ) : (
          <Box pt={1}>
            <Typography>
              <Skeleton variant="rounded" height={50} width={350} />
            </Typography>
            <p>
              <Skeleton variant="rounded" height={50} width={350} />
            </p>
            <Box>
              <Skeleton variant="rounded" height={250} width={300} />
            </Box>
          </Box>
        )}
      </Collapse>
      <Box pt={1} pb={5}>
        <Button
          size="small"
          onClick={handleChange}
          startIcon={checked ? <ChevronLeft /> : <ChevronRight />}
          sx={{ minWidth: "unset" }}
        >
          {checked ? "Hide" : ""}
        </Button>
      </Box>
    </Box>
  );
}

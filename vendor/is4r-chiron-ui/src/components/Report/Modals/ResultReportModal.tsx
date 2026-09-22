import { Box, FormControl, InputLabel, MenuItem, Select } from "@mui/material";

import { useAppDispatch, useAppSelector } from "../../../store/hooks";
import { editReport, updateSelectedReport } from "../../../store/reportSlice";
import OverWriteNewToggle from "./OverWriteNewToggle";
import ReportModal from "../EditReport/ReportModal";
import EditReportForm from "../EditReport/EditReportForm";
import ReportSubmitButton from "../EditReport/ReportSubmitButton";
export default function ResultReportModal() {
  const currentReport = useAppSelector((state) => state.report);
  const dataset = useAppSelector((state) => state.auth.dataset?.unique_id);
  const dispatch = useAppDispatch();
  return (
    <>
      {currentReport.createReportMethod == "overwrite" ? (
        <ReportModal
          formInfo={
            <Box>
              <OverWriteNewToggle></OverWriteNewToggle>

              <FormControl fullWidth sx={{ mt: 2 }}>
                <InputLabel id="report-select-label" size="small">
                  Select the Report to Overwrite
                </InputLabel>
                <Select
                  labelId="report-select-label"
                  id="project-select"
                  value={currentReport.selectedReport}
                  label={currentReport.name}
                  size="small"
                >
                  {currentReport.overWriteReportOptions.map((p) => (
                    <MenuItem
                      key={p.value}
                      value={p.value}
                      onClick={() => {
                        dispatch(updateSelectedReport(p.value));
                        if (p.value != -1) {
                          dispatch(
                            editReport({
                              dataset: dataset ? dataset : "",
                              reportId: p.value,
                            })
                          );
                        }
                      }}
                    >
                      {p.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              {currentReport.selectedReport != -1 ? (
                <EditReportForm></EditReportForm>
              ) : null}
            </Box>
          }
          editActions={
            <ReportSubmitButton reportAction="Overwrite"></ReportSubmitButton>
          }
        ></ReportModal>
      ) : (
        <ReportModal
          formInfo={
            <Box>
              <OverWriteNewToggle></OverWriteNewToggle>
              <EditReportForm></EditReportForm>
            </Box>
          }
          editActions={
            <ReportSubmitButton reportAction="Create"></ReportSubmitButton>
          }
        ></ReportModal>
      )}
    </>
  );
}

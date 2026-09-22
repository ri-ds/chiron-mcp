import {
  Alert,
  AlertTitle,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
} from "@mui/material";

import { useAppDispatch, useAppSelector } from "../../../store/hooks";
import { toggleReportSaveSuccessDialog } from "../../../store/reportSlice";
import { NavLink } from "react-router-dom";

export default function ReportSavedModal() {
  const showShareDialog = useAppSelector(
    (state) => state.report.showReportSaveSuccessDialog
  );
  const currentDataset = useAppSelector((state) => state.auth.dataset);

  const dispatch = useAppDispatch();
  function handleClose() {
    dispatch(toggleReportSaveSuccessDialog());
  }

  return (
    <Dialog onClose={handleClose} open={showShareDialog} maxWidth="lg">
      <DialogContent>
        <Alert severity="success">
          <AlertTitle>Report Saved Successfully</AlertTitle>
        </Alert>
      </DialogContent>
      <DialogActions>
        <NavLink to={`/${currentDataset?.unique_id}/reports/`} reloadDocument>
          <Button variant="contained">Go to Reports Page</Button>
        </NavLink>
      </DialogActions>
    </Dialog>
  );
}

import {
  Alert,
  AlertTitle,
  Box,
  Dialog,
  DialogActions,
  DialogContent,
  Typography,
} from "@mui/material";
import Divider from "@mui/material/Divider";

import { useAppDispatch, useAppSelector } from "../../../store/hooks";
import { toggleShareDialog } from "../../../store/reportSlice";
import { ReactNode } from "react";

export default function ReportModal(props: {
  formInfo: ReactNode;
  editActions: ReactNode;
}) {
  const showShareDialog = useAppSelector(
    (state) => state.report.showShareDialog
  );
  const formTitle = useAppSelector((state) => state.report.formTitle);
  const reportErrors = useAppSelector((state) => state.report.errors);
  const dispatch = useAppDispatch();
  function handleClose() {
    dispatch(toggleShareDialog());
  }

  return reportErrors.length > 0 && !showShareDialog ? (
    reportErrors.map((err) => (
      <Alert severity="error">
        <AlertTitle>Error</AlertTitle>
        {err}
      </Alert>
    ))
  ) : (
    <Dialog
      onClose={handleClose}
      open={showShareDialog}
      maxWidth="lg"
      sx={{
        "& .MuiDialog-container": {
          "& .MuiPaper-root": {
            width: "100%",
            maxWidth: "80%",
          },
        },
      }}
    >
      <DialogContent>
        {reportErrors.length > 0 && showShareDialog
          ? reportErrors.map((err) => (
              <Alert severity="error">
                <AlertTitle>Error</AlertTitle>
                {err}
              </Alert>
            ))
          : null}
        <Box>
          <Box>
            <Typography variant="h6">{formTitle}</Typography>
          </Box>
          <Divider></Divider>
          {props.formInfo}
        </Box>
      </DialogContent>
      <DialogActions>{props.editActions}</DialogActions>
    </Dialog>
  );
}

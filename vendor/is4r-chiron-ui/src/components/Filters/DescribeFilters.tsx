import {
  Dialog,
  DialogTitle,
  DialogContent,
  IconButton,
  Button,
} from "@mui/material";
import { Close as CloseIcon } from "@mui/icons-material";
import { Interweave } from "interweave";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import { toggleDescribeFilters } from "../../store/cohortSlice";

export default function DescribeFilters({
  disabled,
  description,
}: {
  disabled: boolean;
  description: string;
}) {
  const dispatch = useAppDispatch();
  const open = useAppSelector((state) => state.cohort.showDescribeFilters);

  function handleClickOpen() {
    dispatch(toggleDescribeFilters());
  }

  function handleClose() {
    dispatch(toggleDescribeFilters());
  }

  return (
    <>
      <Button
        fullWidth
        size="small"
        variant="outlined"
        sx={{ my: 1 }}
        onClick={handleClickOpen}
        disabled={disabled}
      >
        Describe Filters
      </Button>
      <Dialog
        onClose={handleClose}
        aria-labelledby="describe-cohort-modal"
        open={open}
        maxWidth="xl"
      >
        <DialogTitle sx={{ m: 0, p: 2 }} id="describe-cohort-modal">
          Cohort Description
        </DialogTitle>
        <IconButton
          aria-label="close"
          onClick={handleClose}
          sx={{
            position: "absolute",
            right: 8,
            top: 8,
            color: (theme) => theme.palette.grey[500],
          }}
        >
          <CloseIcon />
        </IconButton>
        <DialogContent dividers sx={{ minWidth: 800 }}>
          <Interweave content={description} />
        </DialogContent>
      </Dialog>
    </>
  );
}

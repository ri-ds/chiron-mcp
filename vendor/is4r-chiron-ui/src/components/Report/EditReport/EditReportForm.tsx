import {
  Box,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Checkbox,
  FormControlLabel,
  Typography,
} from "@mui/material";
import {
  toggleReportPublic,
  updateReportDescription,
  updateReportName,
  updateReportProject,
} from "../../../store/reportSlice";
import ShareUsersToggle from "./ShareUsers";
import { useAppDispatch, useAppSelector } from "../../../store/hooks";

export default function EditReportForm() {
  const currentReport = useAppSelector((state) => state.report);
  const dispatch = useAppDispatch();
  return (
    <Box component="form" sx={{ p: 2 }}>
      <TextField
        fullWidth
        required
        id="name-required"
        label="Name"
        defaultValue={
          currentReport.name == "---select a report---"
            ? ""
            : currentReport.name
        }
        aria-required
        key={currentReport.name}
        size="small"
        sx={{ mt: 2 }}
        onBlur={(e) => dispatch(updateReportName(e.target.value))}
      />
      <FormControl fullWidth sx={{ mt: 2 }}>
        <InputLabel required id="project-select-label" size="small">
          Project
        </InputLabel>
        <Select
          labelId="project-select-label"
          id="project-select"
          aria-required
          required
          value={currentReport.projectId}
          label={currentReport.project}
          size="small"
        >
          {currentReport.projectSelect.map((p) => (
            <MenuItem
              key={p.value}
              value={p.value}
              onClick={() => {
                dispatch(
                  updateReportProject({ value: p.value, label: p.label })
                );
              }}
            >
              {p.label}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      {currentReport.projectId == -1 ? (
        <TextField
          fullWidth
          id="new-project-required"
          label="New Project Name"
          sx={{ mt: 2 }}
          size="small"
          onBlur={(e) =>
            dispatch(updateReportProject({ value: -1, label: e.target.value }))
          }
        />
      ) : null}
      <TextField
        fullWidth
        id="description-required"
        label="Description"
        defaultValue={currentReport.description}
        key={currentReport.description}
        multiline
        rows={4}
        sx={{ mt: 2 }}
        size="small"
        onBlur={(e) => dispatch(updateReportDescription(e.target.value))}
      />

      {!currentReport.public ? (
        <Box py={1}>
          <Typography>Share With</Typography>
          <ShareUsersToggle></ShareUsersToggle>
        </Box>
      ) : null}
      <FormControlLabel
        sx={{ p: 2 }}
        control={<Checkbox checked={currentReport.public} />}
        label={"Public (share with everyone)"}
        onChange={() => {
          dispatch(toggleReportPublic());
        }}
      />
    </Box>
  );
}

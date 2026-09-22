import {
  Dialog,
  DialogTitle,
  DialogContent,
  IconButton,
  Box,
  Tabs,
  Tab,
} from "@mui/material";
import { Close as CloseIcon } from "@mui/icons-material";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import { clearCriteriaSetOptions } from "../../store/criteriaSetSlice";
import { useState, SyntheticEvent } from "react";
import EditCriteriaSetForm from "./EditCriteriaSetForm";
import CountRule from "./EditForms/CountRule";
import Alias from "./EditForms/Alias";
import DateRange from "./EventForms/DateRange";
import NoRestriction from "./EventForms/NoRestriction";
import RelativeToToday from "./EventForms/RelativeToToday";
import RelativeToOtherEvent from "./EventForms/RelativeToOtherEvent";
import AgeDaysRange from "./EventForms/AgeDaysRange";
import IntervalDateRange from "./EventForms/IntervalDateRage";
import IntervalRelativeToToday from "./EventForms/IntervalRelativeToToday";

const formLookup: any = {
  add_criteria_set_count_rule: CountRule,
  set_criteria_set_alias: Alias,
  date_range: DateRange,
  interval_date_range: IntervalDateRange,
  no_restriction: NoRestriction,
  relative_to_today: RelativeToToday,
  interval_relative_to_today: IntervalRelativeToToday,
  relative_to_other_event: RelativeToOtherEvent,
  age_in_days_range: AgeDaysRange,
};

export default function EditCriteriaSet() {
  const dispatch = useAppDispatch();
  const data = useAppSelector((state) => state.criteriaSet);
  const [value, setValue] = useState(0);

  const handleChange = (_: SyntheticEvent, newValue: number) => {
    setValue(newValue);
  };

  function handleClose() {
    dispatch(clearCriteriaSetOptions());
  }

  const options =
    data.type == "event"
      ? data.criteria_set_event_options?.event_options
      : data.criteria_set_options;

  return (
    <Dialog
      onClose={handleClose}
      aria-labelledby="edit-criteria-set-dialog"
      open={data.criteria_set_entry_id !== undefined}
      maxWidth="xl"
    >
      <DialogTitle sx={{ m: 0, p: 2 }} id="edit-criteria-set-dialog">
        Edit {data.name} Filter Set
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
        <Box sx={{ width: "100%" }}>
          <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
            <Tabs
              value={value}
              onChange={handleChange}
              aria-label="basic tabs example"
            >
              {options?.map((option, idx) => (
                <Tab
                  disabled={!option.allowed}
                  key={`tab-${idx}`}
                  label={option.label}
                  id={`tab-${idx}`}
                  aria-controls={`tabpanel-${idx}`}
                />
              ))}
            </Tabs>
          </Box>
          {options?.map((option, idx) => {
            const formId =
              data.type == "edit" ? option.transformation : option.option_id;
            const fData = { ...option, get_name_plural: data.get_name_plural };
            return value == idx ? (
              <EditCriteriaSetForm
                key={`panel-${idx}`}
                data={{
                  formData: fData,
                  index: idx,
                  type: data.type || "",
                  entryId: data.criteria_set_entry_id || "",
                  form: formLookup[formId],
                }}
              />
            ) : null;
          })}
        </Box>
      </DialogContent>
    </Dialog>
  );
}

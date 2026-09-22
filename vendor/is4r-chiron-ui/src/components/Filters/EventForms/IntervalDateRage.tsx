import { Box, FormGroup, FormLabel, TextField } from "@mui/material";
import { convertDateFormatForTextField } from "../../../lib/utils";

type DateRangeProps = {
  option_id: string;
  label: string;
  allowed: boolean;
  date_start_min: string;
  date_start_max: string;
  date_end_min: string;
  date_end_max: string;
};

export default function IntervalDateRange({ data }: { data: DateRangeProps }) {
  return (
    <Box pt={6}>
      <input type="hidden" name="type" value="modify_event_rule" />
      <input type="hidden" name="option_type" value={data.option_id} />
      <Box display="flex" justifyContent="space-evenly" py={1}>
        <FormGroup>
          <FormLabel>Min Start Date (inclusive)</FormLabel>
          <TextField
            type="date"
            name="date_start_min"
            defaultValue={convertDateFormatForTextField(data.date_start_min)}
          />
        </FormGroup>
        <FormGroup>
          <FormLabel>Max Start Date (inclusive)</FormLabel>
          <TextField
            type="date"
            name="date_start_max"
            defaultValue={convertDateFormatForTextField(data.date_start_max)}
          />
        </FormGroup>
      </Box>
      <Box display="flex" justifyContent="space-evenly" py={1}>
        <FormGroup>
          <FormLabel>Min End Date(inclusive)</FormLabel>
          <TextField
            type="date"
            name="date_end_min"
            defaultValue={convertDateFormatForTextField(data.date_end_min)}
          />
        </FormGroup>
        <FormGroup>
          <FormLabel>Max End Date(inclusive)</FormLabel>
          <TextField
            type="date"
            name="date_end_max"
            defaultValue={convertDateFormatForTextField(data.date_end_max)}
          />
        </FormGroup>
      </Box>
    </Box>
  );
}

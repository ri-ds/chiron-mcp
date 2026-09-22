import { Box, FormGroup, FormLabel, TextField } from "@mui/material";
import { convertDateFormatForTextField } from "../../../lib/utils";

type DateRangeProps = {
  option_id: string;
  label: string;
  allowed: boolean;
  date_min: string;
  date_max: string;
};

export default function DateRange({ data }: { data: DateRangeProps }) {
  return (
    <Box display="flex" justifyContent="space-evenly" py={5}>
      <input type="hidden" name="type" value="modify_event_rule" />
      <input type="hidden" name="option_type" value={data.option_id} />
      <FormGroup>
        <FormLabel>Min (inclusive)</FormLabel>
        <TextField
          type="date"
          name="date_min"
          defaultValue={convertDateFormatForTextField(data.date_min)}
        />
      </FormGroup>
      <FormGroup>
        <FormLabel>Max (inclusive)</FormLabel>
        <TextField
          type="date"
          name="date_max"
          defaultValue={convertDateFormatForTextField(data.date_max)}
        />
      </FormGroup>
    </Box>
  );
}

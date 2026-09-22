import { Box, FormGroup, FormLabel, TextField } from "@mui/material";

type DateRangeProps = {
  option_id: string;
  label: string;
  allowed: boolean;
  age_min: number;
  age_max: number;
};

export default function AgeRange({ data }: { data: DateRangeProps }) {
  return (
    <Box display="flex" justifyContent="space-evenly" py={5}>
      <input type="hidden" name="type" value="modify_event_rule" />
      <input type="hidden" name="option_type" value={data.option_id} />
      <FormGroup>
        <FormLabel>Min (inclusive)</FormLabel>
        <TextField type="number" name="age_min" defaultValue={data.age_min} />
      </FormGroup>
      <FormGroup>
        <FormLabel>Max (inclusive)</FormLabel>
        <TextField type="number" name="age_max" defaultValue={data.age_max} />
      </FormGroup>
    </Box>
  );
}

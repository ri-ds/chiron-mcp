import { FormGroup, FormLabel, MenuItem, Select } from "@mui/material";

type DaysAgoOption = [number, string];

type NoRestrictionsProps = {
  data: {
    option_id: string;
    label: string;
    allowed: boolean;
    days_ago: number;
    days_ago_options: DaysAgoOption[];
  };
};

export default function RelativeToToday({ data }: NoRestrictionsProps) {
  return (
    <FormGroup sx={{ p: 5 }}>
      <input type="hidden" name="type" value="modify_event_rule" />
      <input type="hidden" name="option_type" value={data.option_id} />
      <FormLabel>Any time in the last</FormLabel>
      <Select name="days_ago" defaultValue={data.days_ago}>
        {data.days_ago_options.map((option) => (
          <MenuItem key={option[0]} value={option[0]}>
            {option[1]}
          </MenuItem>
        ))}
      </Select>
    </FormGroup>
  );
}

import { Box, FormGroup, FormLabel, MenuItem, Select } from "@mui/material";

type DaysAgoOption = [number, string];

type NoRestrictionsProps = {
  data: {
    option_id: string;
    label: string;
    allowed: boolean;
    start_date_days_ago: number;
    end_date_days_ago: number;
    days_ago_options: DaysAgoOption[];
  };
};

export default function RelativeToToday({ data }: NoRestrictionsProps) {
  return (
    <Box display="flex" justifyContent="space-evenly">
      <FormGroup sx={{ py: 4 }}>
        <input type="hidden" name="type" value="modify_event_rule" />
        <input type="hidden" name="option_type" value={data.option_id} />
        <FormLabel>Event started any time in the last</FormLabel>
        <Select
          name="start_date_days_ago"
          defaultValue={data.start_date_days_ago}
        >
          {data.days_ago_options.map((option) => (
            <MenuItem key={option[0]} value={option[0]}>
              {option[1]}
            </MenuItem>
          ))}
        </Select>
      </FormGroup>
      <FormGroup sx={{ py: 4 }}>
        <FormLabel>Event ended any time in the last</FormLabel>
        <Select name="end_date_days_ago" defaultValue={data.end_date_days_ago}>
          {data.days_ago_options.map((option) => (
            <MenuItem key={option[0]} value={option[0]}>
              {option[1]}
            </MenuItem>
          ))}
        </Select>
      </FormGroup>
    </Box>
  );
}

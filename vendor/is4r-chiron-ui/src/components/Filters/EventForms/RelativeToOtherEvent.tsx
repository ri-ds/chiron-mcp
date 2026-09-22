import {
  Box,
  FormGroup,
  FormLabel,
  MenuItem,
  Select,
  SelectChangeEvent,
  Typography,
} from "@mui/material";
import { grey } from "@mui/material/colors";
import { useState } from "react";

type DaysAgoOption = [number, string];

type OtherEvent = {
  criteria_set_name: string;
  event_type: string;
  criteria_set_entry_id: string;
};

type RelativeToOtherEventProps = {
  data: {
    option_id: string;
    label: string;
    collection_event_type: string;
    allowed: boolean;
    existing_event_rule: {
      range_start_days_from_target: number;
      range_end_days_from_target: number;
      target_entry_id: string;
      type: string;
    };
    date_options: DaysAgoOption[];
    other_events: OtherEvent[];
  };
};

export default function RelativeToOtherEvent({
  data,
}: RelativeToOtherEventProps) {
  const [selectedEvent, setSelectedEvent] = useState<string>(
    data.existing_event_rule.target_entry_id || "-1"
  );

  if (data.other_events.length === 0) {
    return (
      <Typography
        textAlign="center"
        sx={{ p: 8 }}
        variant="h6"
        color={grey[700]}
        gutterBottom
      >
        There are not any other events defined for this cohort.
      </Typography>
    );
  }
  const eventNames: { [k: string]: string } = {};
  for (const event of data.other_events) {
    eventNames[event.criteria_set_entry_id] = event.criteria_set_name;
  }

  return (
    <FormGroup sx={{ p: 5 }}>
      <input type="hidden" name="type" value="modify_event_rule" />
      <input type="hidden" name="option_type" value={data.option_id} />
      <FormLabel>Any time in the last</FormLabel>
      <Select
        value={selectedEvent}
        name="target_entry_id"
        onChange={(e: SelectChangeEvent) =>
          setSelectedEvent(e.target.value as string)
        }
      >
        <MenuItem value="-1">Select an Event</MenuItem>
        {data.other_events.map((event) => (
          <MenuItem
            key={event.criteria_set_entry_id}
            value={event.criteria_set_entry_id}
          >
            {event.criteria_set_name}
          </MenuItem>
        ))}
      </Select>

      {selectedEvent !== "-1" ? (
        <Box pt={4}>
          <Select
            name={`range_start_days_from_target_${selectedEvent}`}
            defaultValue={
              data.existing_event_rule.range_start_days_from_target || 0
            }
            sx={{ mx: 1 }}
          >
            {data.date_options.map((option) => (
              <MenuItem value={option[0]}>{option[1]}</MenuItem>
            ))}
          </Select>
          {eventNames[selectedEvent]} and
          <Select
            name={`range_end_days_from_target_${selectedEvent}`}
            defaultValue={
              data.existing_event_rule.range_end_days_from_target || 0
            }
            sx={{ mx: 1 }}
          >
            {data.date_options.map((option) => (
              <MenuItem value={option[0]}>{option[1]}</MenuItem>
            ))}
          </Select>
          {eventNames[selectedEvent]}
        </Box>
      ) : null}
    </FormGroup>
  );
}

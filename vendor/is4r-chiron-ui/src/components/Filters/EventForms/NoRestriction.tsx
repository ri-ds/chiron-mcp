import { Typography } from "@mui/material";
import { grey } from "@mui/material/colors";

export default function NoRestriction() {
  return (
    <>
      <input type="hidden" name="type" value="modify_event_rule" />
      <input type="hidden" name="option_type" value="no_restriction" />
      <Typography
        textAlign="center"
        sx={{ p: 8 }}
        variant="h6"
        color={grey[700]}
        gutterBottom
      >
        Create event with no restriction (allow any date/age)
      </Typography>
    </>
  );
}

import { Box, Select, TextField, Typography, MenuItem } from "@mui/material";

type CountRuleProps = {
  data: {
    value: string;
    type: string;
    get_name_plural: string;
  };
};

export default function CountRule({ data }: CountRuleProps) {
  return (
    <Box p={4} textAlign="center">
      <input type="hidden" name="type" value="add_criteria_set_count_rule" />
      <Box mt={2} mb={9}>
        <Typography component="span">Subject has</Typography>
        <Select
          size="small"
          labelId="select-type-label"
          id="select-type"
          name="rule_operator"
          defaultValue={data.type}
          sx={{ ml: 1 }}
        >
          <MenuItem value="at least">at least</MenuItem>
          <MenuItem value="at most">at most</MenuItem>
          <MenuItem value="exactly">exactly</MenuItem>
        </Select>
        <TextField
          size="small"
          type="number"
          name="rule_count"
          defaultValue={data.value}
          sx={{ mr: 1, width: 100 }}
        />
        <Typography component="span">
          matching {data.get_name_plural}
        </Typography>
      </Box>
    </Box>
  );
}

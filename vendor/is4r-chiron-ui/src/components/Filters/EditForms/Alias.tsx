import { TextField } from "@mui/material";
type AliasProps = {
  data: {
    alias: string;
  };
};
export default function Alias({ data }: AliasProps) {
  return (
    <>
      <input type="hidden" name="type" value="set_criteria_set_alias" />
      <TextField
        sx={{ my: 2 }}
        defaultValue={data.alias}
        fullWidth
        name="alias"
        label="Set a custom name for this filter set:"
        helperText="Set to blank to use the default filter set name "
      />
    </>
  );
}

import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  TextField,
  type SelectChangeEvent,
  Box,
  Typography,
} from "@mui/material";
import { useAppDispatch, useAppSelector } from "../../../store/hooks";
import {
  applyTransformation,
  clearColumnInformation,
} from "../../../store/tableSlice";
import {
  type EditColumn,
  type AggregationOption as AggregationOptionType,
  type AggregationOptionInput,
} from "../../../store/tableSliceTypes";
import AggregationOption from "./AggregationOption";
import { grey } from "@mui/material/colors";
import _ from "lodash";
import { SyntheticEvent, useState } from "react";

function parseColumnInformation(column: EditColumn) {
  const displayData: { [k: string]: AggregationOptionType[] } = {};
  const inputLookups: { [k: string]: AggregationOptionInput[] } = {};

  let defaultSelected: string = "stack";
  column.aggregation_options.forEach((option) => {
    const group = _.startCase(option.group.replace("_", " "));
    if (!displayData[group]) {
      displayData[group] = [];
    }

    displayData[group].push(option);

    // check for selection
    if (option.selected) {
      defaultSelected = option.id;
    }

    if (option.inputs.length) {
      inputLookups[option.id] = option.inputs;
    }
  });

  return {
    displayData,
    inputLookups,
    defaultSelected,
  };
}

export default function EditColumn({ column }: { column: EditColumn }) {
  const dispatch = useAppDispatch();
  const dataset = useAppSelector((state) => state.auth.dataset?.unique_id);
  const { displayData, inputLookups, defaultSelected } =
    parseColumnInformation(column);
  const [selected, setSelected] = useState(defaultSelected);

  function handleSubmit(e: SyntheticEvent<HTMLFormElement>) {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const data: { [k: string]: any } = {};
    const arrayFields: string[] = ["values", "values_text"];

    for (const pair of formData.entries()) {
      if (arrayFields.includes(pair[0])) {
        if (!data[pair[0]]) {
          data[pair[0]] = [];
        }
        data[pair[0]].push(pair[1]);
      } else {
        data[pair[0] as string] = pair[1] as string;
      }
    }
    dispatch(
      applyTransformation({
        dataset: dataset ? dataset : "",
        transformation: { ...data, type: "add_entry" },
        refresh: column.refresh,
      })
    );
    dispatch(clearColumnInformation());
  }

  function handleChange(e: SelectChangeEvent<typeof selected>) {
    setSelected(e.target.value);
  }

  return (
    <Dialog
      onClose={() => dispatch(clearColumnInformation())}
      open={Boolean(column)}
      maxWidth="xl"
    >
      <form action="POST" onSubmit={handleSubmit}>
        <DialogTitle sx={{ m: 0, p: 2 }}>
          How do you want to handle multiple values for{" "}
          <strong>{column.concept}</strong>?
        </DialogTitle>
        <DialogContent>
          <TextField
            name="entry_alias"
            fullWidth
            size="small"
            margin="dense"
            label="Alias"
            defaultValue={column.entry_alias}
            placeholder="[use default value]"
          />
          <Divider sx={{ my: 2 }} />
          <FormControl fullWidth sx={{ my: 2 }}>
            <InputLabel htmlFor="grouped-select">Aggregation Method</InputLabel>
            <Select
              value={selected}
              size="small"
              label="Aggregation Method"
              name="aggregation_method"
              onChange={handleChange}
            >
              <MenuItem value="stack">Stack (one row per data point)</MenuItem>

              {displayData.List.map((item: AggregationOptionType) => (
                <MenuItem key={item.id} value={item.id}>
                  {_.startCase(item.label.replace("_", " "))}
                </MenuItem>
              ))}

              {displayData.Aggregate.map((item: AggregationOptionType) => (
                <MenuItem key={item.id} value={item.id}>
                  {_.startCase(item.label.replace("_", " "))}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <input type="hidden" name="concept_id" value={column.conceptId} />
          <input type="hidden" name="entry_id" value={column.entry_id} />

          {inputLookups[selected] ? (
            <Box my={2}>
              <Typography
                variant="h6"
                sx={{ borderBottom: "1px solid", borderColor: grey[300] }}
              >
                Aggregation Options
              </Typography>
              {inputLookups[selected].map((option) => (
                <AggregationOption key={option.id} data={option} />
              ))}
            </Box>
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button type="submit" fullWidth variant="contained" color="primary">
            Save Changes
          </Button>
          <Button
            type="button"
            fullWidth
            variant="contained"
            color="inherit"
            onClick={() => dispatch(clearColumnInformation())}
          >
            Discard Changes
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}

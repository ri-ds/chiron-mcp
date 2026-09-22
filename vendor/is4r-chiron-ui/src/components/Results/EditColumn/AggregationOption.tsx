import {
  FormControl,
  FormGroup,
  InputLabel,
  MenuItem,
  Select,
  debounce,
} from "@mui/material";
import { type AggregationOptionInput } from "../../../store/tableSliceTypes";
import AsyncSelect from "react-select/async";
import { APIRequest } from "../../../api";

type OptionResult = {
  value: string;
  label: string;
};

export default function AggregationOption({
  data,
}: {
  data: AggregationOptionInput;
}) {
  /**
   * This is the function that handles searching the values, it needs to be
   * non async so that the AsyncSelect properly passes Typescript validation
   *
   * @param search The search term to find
   * @param callback the function to apply the changes
   * @returns
   */
  function searchValues(
    search: string,
    callback: (options: OptionResult[]) => void
  ) {
    if (!search || search.length < 2) {
      return;
    }
    const url = data.options_callback;
    APIRequest("GET", `${url}${search}`).then((response) => {
      const responseData = response.results || response.paginated_results;
      callback(
        responseData.map((option: { id: string; text: string }) => ({
          value: option.id,
          label: option.text,
        }))
      );
    });
  }
  const debouncedSearch = debounce(searchValues, 300);

  let defaultValue: OptionResult[] = [];
  if (data.type == "ajax_multiselect") {
    defaultValue = (data.selected as string[]).map((item) => ({
      value: item,
      label: item,
    }));
  }

  switch (data.type) {
    case "select":
    case "multiselect":
      return (
        <FormControl fullWidth sx={{ my: 2 }}>
          <InputLabel>{data.label}</InputLabel>
          <Select
            size="small"
            multiple={data.type === "multiselect"}
            defaultValue={
              data.type === "multiselect"
                ? data.selected === ""
                  ? []
                  : data.selected
                : data.selected
            }
            label={data.label}
            name={data.id}
          >
            {data.options.map((option) => (
              <MenuItem key={option[0]} value={option[0]}>
                {option[1]}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      );
    case "ajax_multiselect":
      return (
        <FormGroup sx={{ my: 2 }}>
          <InputLabel>{data.label}</InputLabel>
          <FormControl fullWidth sx={{ zIndex: 10000 }}>
            <AsyncSelect
              isMulti
              name={data.id}
              placeholder={`Start typing for ${data.label}`}
              cacheOptions
              defaultOptions
              defaultValue={defaultValue}
              loadOptions={debouncedSearch}
            />
          </FormControl>
        </FormGroup>
      );
    default:
      return null;
  }
}

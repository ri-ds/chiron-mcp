import {
  Box,
  Checkbox,
  FormControlLabel,
  InputAdornment,
  Pagination,
  TextField,
  Typography,
} from "@mui/material";
import CheckIcon from "@mui/icons-material/Check";
import AddIcon from "@mui/icons-material/Add";
import {
  type TextConceptDetailedData,
  addQueryConceptToFilters,
  type CategoryOrTextValues,
  updateConceptValues,
  conceptGotoSearchPage,
  verifyQueryConceptEntries,
  resetTransformationAlerts,
} from "../../store/cohortSlice";
import { grey, yellow } from "@mui/material/colors";
import { type SyntheticEvent, useState, useEffect } from "react";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import QueryConceptAddOrUpdateButton from "../QueryConceptAddOrUpdateButton";
import { Search } from "@mui/icons-material";
import ReportProblem from "@mui/icons-material/ReportProblem";
import debounce from "lodash/debounce";
import truncate from "lodash/truncate";
import { AppDispatch } from "../../store";
import QueryConceptExcludeSwitch from "../QueryConceptExcludeSwitch";
import FilterTextArea from "./FilterComponents/TextArea";
import SelectedValuesArea from "./FilterComponents/SelectedValuesArea";
import config from "../../config";

/**
 * Handles the searching through the the values to return a subset of all the
 * values
 *
 * @param dispatch the dispatch function
 * @param conceptId the concepts permanent id
 * @param searchTerm the search term to use
 * @param showDataType what data to query against
 */
function handleSearchAction(
  dispatch: AppDispatch,
  dataset: string,
  conceptId: string,
  searchTerm: string,
  showDataType: string
) {
  dispatch(
    conceptGotoSearchPage({
      dataset,
      conceptId,
      searchTerm,
      page: 1,
      showDataType,
    })
  );
}

/**
 * The debounced version of the function
 */
const debouncedHandleSearchAction = debounce(handleSearchAction, 500);

export default function Text({ data }: { data: TextConceptDetailedData }) {
  const dispatch = useAppDispatch();
  const values = useAppSelector(
    (state) => state.cohort.queryConceptValues as CategoryOrTextValues
  );
  const dataset = useAppSelector((state) => state.auth.dataset?.unique_id);
  const queryConceptData = useAppSelector(
    (state) => state.cohort.queryConceptData
  );
  const queryConceptEditing = useAppSelector(
    (state) => state.cohort.queryConceptEditing
  );
  const queryConceptExclude = useAppSelector(
    (state) => state.cohort.queryConceptExclude
  );
  const queryConceptEditingPrefilterValue = useAppSelector(
    (state) => state.cohort.queryConceptEditingPrefilterValue
  );
  const showDataType = useAppSelector((state) => state.cohort.showDataType);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<string[]>(values || []);

  /**
   * Either removes or adds the value to the values list,
   * updates in Redux and runs the validation
   * @param value the item to add or remove
   */
  function handleSelectValue(value: string) {
    const newValues = [...selected];
    if (newValues.includes(value)) {
      // remove the value
      newValues.splice(newValues.indexOf(value), 1);
    } else {
      // add the value
      newValues.push(value);
    }
    setSelected(newValues);
  }

  const [open, setOpen] = useState(false);

  const handleClickOpen = () => {
    setOpen(true);
    dispatch(resetTransformationAlerts());
  };

  const [textValue, setTextValue] = useState("");

  useEffect(() => {
    if (selected === values) {
      return;
    }
    setSelected(values);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [values]);

  function handleSubmit(e: SyntheticEvent<HTMLFormElement>) {
    e.preventDefault();
    dispatch(
      addQueryConceptToFilters({
        dataset: dataset ? dataset : "",
        conceptId: queryConceptData?.permanent_id || "",
        values: {
          chiron_text_field_selection: selected.join("\n"),
        },
        include_null_and_missing:
          queryConceptData?.cohort_def_options.include_null_and_missing,
        entry: queryConceptEditing,
        exclude: queryConceptExclude,
        ignoreWarnings: false,
        prefilterValue: queryConceptEditingPrefilterValue,
      })
    );
  }

  function allResultsInSelected(left: string[], right: string[]) {
    let retBool = true;
    left.forEach((element) => {
      if (right.indexOf(element) < 0) {
        retBool = false;
      }
    });
    return retBool;
  }

  function not(a: readonly string[], b: readonly string[]) {
    return a.filter((value) => b.indexOf(value) === -1);
  }

  function union(a: readonly string[], b: readonly string[]) {
    return [...a, ...not(b, a)];
  }

  function handleSelectAll() {
    const values = data.paginated_results.map((item) => item.unique_values);
    if (allResultsInSelected(values, selected)) {
      setSelected(not(selected, values));
    } else {
      // add all values
      setSelected(union(selected, values));
    }
  }

  const handleClose = () => {
    setOpen(false);
  };

  function handleClearAll() {
    dispatch(updateConceptValues([]));
    setSelected([]);
    dispatch(
      verifyQueryConceptEntries({
        dataset: dataset ? dataset : "",
        conceptId: queryConceptData?.permanent_id || "",
        values: {
          chiron_text_field_selection: "",
        },
      })
    ).then(() => {
      dispatch(resetTransformationAlerts());
    });
  }

  return (
    <>
      <Box display="flex" justifyContent="space-around" gap={1}>
        <Box width="100%" p={2}>
          <Typography fontWeight={"bold"} pb={1}>
            Browse Data
          </Typography>
          <TextField
            value={search}
            onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
              setSearch(event.target.value);
              debouncedHandleSearchAction(
                dispatch,
                dataset ? dataset : "",
                queryConceptData?.permanent_id || "",
                event.target.value,
                showDataType
              );
            }}
            margin="none"
            size="small"
            label="Search values ..."
            type="search"
            InputLabelProps={{
              sx: { color: config.table.conceptHeaderColor[800] },
            }}
            InputProps={{
              endAdornment: (
                <InputAdornment
                  position="end"
                  sx={{
                    cursor: "pointer",
                    color: config.table.conceptHeaderColor[800],
                  }}
                  onClick={() =>
                    dispatch(
                      conceptGotoSearchPage({
                        dataset: dataset ? dataset : "",
                        conceptId: queryConceptData?.permanent_id || "",
                        searchTerm: search,
                        page: 1,
                        showDataType,
                      })
                    )
                  }
                >
                  <Search />
                </InputAdornment>
              ),
            }}
          />{" "}
          <FormControlLabel
            control={
              <Checkbox
                data-id="sresults-selectall"
                checked={allResultsInSelected(
                  data.paginated_results.map((item) => item.unique_values),
                  selected
                )}
                onClick={handleSelectAll}
              />
            }
            disabled={!search}
            label="Select All"
          />
          <Box
            width="100%"
            minHeight="11rem"
            maxHeight="23rem"
            p={1}
            mt={1}
            border="1px solid"
            borderColor={grey[300]}
            overflow={"scroll"}
          >
            {data.paginated_results.length ? (
              data.paginated_results.map((item) => (
                <FormControlLabel
                  disableTypography={true}
                  key={`left-${item.unique_values}`}
                  sx={{
                    width: "100%",
                    pl: 1,
                    zIndex: 100,
                    ".MuiFormControlLabel-label": {
                      display: "block",
                      zIndex: 100,
                      color: "black",
                      width: "100%",
                      pt: ".2rem",
                      height: "1.8rem",
                    },
                  }}
                  control={
                    <Checkbox
                      sx={{
                        p: 0,
                        mx: 0.75,
                      }}
                      checkedIcon={<CheckIcon />}
                      icon={<AddIcon />}
                      onClick={() => handleSelectValue(item.unique_values)}
                      checked={selected.includes(item.unique_values)}
                      size="small"
                    />
                  }
                  label={truncate(item.unique_values, {
                    length: 55,
                    separator: " ",
                  })}
                />
              ))
            ) : (
              <Box display="flex" flexDirection="column" textAlign="center">
                <ReportProblem
                  sx={{ color: yellow[800], mt: 6, mx: "auto" }}
                  fontSize="large"
                />
                <Typography variant="h5" color="GrayText">
                  No data was found for <strong>{search}</strong>
                </Typography>
              </Box>
            )}
          </Box>
          <Box
            display="flex"
            flexWrap="nowrap"
            alignItems="center"
            justifyContent="space-between"
            pt={1}
          >
            <Typography sx={{ flexGrow: 1 }} fontSize="small">
              Showing{" "}
              {data.paginator?.total_records === 0
                ? "0"
                : data.paginator.first_index}
              -{data.paginator.last_index} of {data.paginator.total_records}
            </Typography>
            <Pagination
              count={data.paginator.last_page}
              color="primary"
              size="small"
              page={data.paginator.current_page}
              onChange={(_, value: number) =>
                dispatch(
                  conceptGotoSearchPage({
                    dataset: dataset ? dataset : "",
                    conceptId: queryConceptData?.permanent_id || "",
                    searchTerm: search,
                    page: value,
                    showDataType,
                  })
                )
              }
            />
          </Box>
          <FilterTextArea
            data={selected}
            open={open}
            onClose={handleClose}
            handleClickOpen={handleClickOpen}
            conceptId={queryConceptData?.permanent_id || ""}
            textValue={textValue}
            setTextValue={setTextValue}
            textOrOntology="text"
          />
        </Box>

        <Box width="80%">
          <Box
            ml={-2}
            component="form"
            onSubmit={handleSubmit}
            sx={{ display: { sm: "", md: "flex" } }}
            justifyContent="space-between"
            py={1}
          >
            <QueryConceptExcludeSwitch />
            <QueryConceptAddOrUpdateButton />
          </Box>
          <Typography marginBottom={2.5} fontWeight={"bold"}>
            Selected Data
          </Typography>
          <SelectedValuesArea
            selected={selected}
            handleSelectValue={handleSelectValue}
            handleClearAll={handleClearAll}
          ></SelectedValuesArea>
        </Box>
      </Box>
    </>
  );
}

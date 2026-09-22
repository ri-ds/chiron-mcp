import {
  Box,
  Button,
  InputAdornment,
  TextField,
  Typography,
  CircularProgress,
  FormControlLabel,
  Checkbox,
  Switch,
} from "@mui/material";
import {
  type OntologyConceptDetailedData,
  addQueryConceptToFilters,
  updateConceptValues,
  conceptGotoSearchPage,
  conceptOntologyAction,
  verifyQueryConceptEntries,
  resetTransformationAlerts,
  toggleExistsInOntology,
  toggleIncludeOntologyUnknown,
} from "../../store/cohortSlice";
import { grey, yellow } from "@mui/material/colors";
import { type SyntheticEvent, useState, useEffect } from "react";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import QueryConceptAddOrUpdateButton from "../QueryConceptAddOrUpdateButton";
import { Info, Search } from "@mui/icons-material";

import CheckIcon from "@mui/icons-material/Check";
import AddIcon from "@mui/icons-material/Add";
import SubdirectoryArrowLeftIcon from "@mui/icons-material/SubdirectoryArrowLeft";
import ReportProblem from "@mui/icons-material/ReportProblem";
import debounce from "lodash/debounce";
import truncate from "lodash/truncate";
import { AppDispatch } from "../../store";
import QueryConceptExcludeSwitch from "../QueryConceptExcludeSwitch";
import finalConfig from "../../config";
import LightTooltip from "../LightTooltip";
import FilterTextArea from "./FilterComponents/TextArea";
import SelectedValuesArea from "./FilterComponents/SelectedValuesArea";
import { pluralizeCount } from "../../lib/utils";

/**
 * Handles loading of children/parent navigation
 *
 * @param dispatch the dispatch function
 * @param conceptId the concepts permanent id
 * @param searchTerm the search term to use
 * @param showDataType what data to query against
 * @param queryConceptExcludeOntology passed boolean to count/filter by whether the item exists in the dataset
 */

function handleOntologyAction(
  dispatch: AppDispatch,
  dataset: string,
  conceptId: string,
  classId: string,
  ontologyAction: string,
  showDataType: string,
  queryConceptExcludeOntology: boolean
) {
  dispatch(
    conceptOntologyAction({
      dataset: dataset,
      conceptId,
      classId,
      ontologyAction,
      showDataType,
      queryConceptExcludeOntology,
    })
  );
}

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
  showDataType: string,
  queryConceptExcludeOntology: boolean
) {
  dispatch(
    conceptGotoSearchPage({
      dataset: dataset,
      conceptId,
      searchTerm,
      page: 1,
      showDataType,
      queryConceptExcludeOntology,
    })
  );
}

/**
 * The debounced version of the function
 */
const debouncedHandleSearchAction = debounce(handleSearchAction, 1000);

export default function Ontology({
  data,
}: {
  data: OntologyConceptDetailedData;
}) {
  const dispatch = useAppDispatch();
  const values = useAppSelector(
    (state) => state.cohort.queryConceptValues as string[]
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
  const queryConceptIncludeOntologyUnknown = useAppSelector(
    (state) => state.cohort.queryConceptIncludeOntologyUnknown
  );
  const queryConceptEditingPrefilterValue = useAppSelector(
    (state) => state.cohort.queryConceptEditingPrefilterValue
  );

  const queryConceptExcludeOntology = useAppSelector(
    (state) => state.cohort.queryConceptExcludeOntology
  );

  const queryConceptOntologyUnknownCounts = useAppSelector(
    (state) =>
      state.cohort.queryConceptDetailedData?.count_unknown_ontology_values
  );
  const [search, setSearch] = useState("");
  const showDataType = useAppSelector((state) => state.cohort.showDataType);
  const conceptState = useAppSelector((state) => state.cohort.conceptState);
  const [selected, setSelected] = useState<string[]>(values || []);

  let unknownItemString = "";
  if (queryConceptOntologyUnknownCounts) {
    unknownItemString = `(${pluralizeCount(
      queryConceptOntologyUnknownCounts.uniqueSubjectCount,
      "subject"
    )})`;
  }
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

  const handleClose = () => {
    setOpen(false);
  };

  const [textValue, setTextValue] = useState("");

  function handleClearAll() {
    dispatch(updateConceptValues([]));
    setSelected([]);
    dispatch(
      verifyQueryConceptEntries({
        dataset: dataset ? dataset : "",
        conceptId: queryConceptData?.permanent_id || "",
        values: {
          chiron_ontology_field_selection: [],
        },
      })
    ).then(() => {
      dispatch(resetTransformationAlerts());
    });
  }

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
          chiron_ontology_field_selection: selected.filter(
            (item) => item !== ""
          ),
        },
        include_null_and_missing:
          queryConceptData?.cohort_def_options.include_null_and_missing,
        entry: queryConceptEditing,
        exclude: queryConceptExclude,
        include_ontology_unknown: queryConceptIncludeOntologyUnknown,
        ignoreWarnings: false,
        prefilterValue: queryConceptEditingPrefilterValue,
      })
    );
  }

  return (
    <>
      <Box
        ml={-2}
        component="form"
        onSubmit={handleSubmit}
        sx={{ display: "flex" }}
        justifyContent="right"
        py={1}
      >
        <Box mr={3}>
          <QueryConceptExcludeSwitch />
        </Box>
        <QueryConceptAddOrUpdateButton />
      </Box>
      <Box display="flex" justifyContent="space-around" gap={1}>
        <Box width="100%" p={2}>
          <Typography fontWeight={"bold"}>Browse Data</Typography>
          <Box display="flex" alignItems="center" pb={1}>
            <FormControlLabel
              control={
                <Switch
                  checked={queryConceptExcludeOntology}
                  onChange={() => {
                    dispatch(toggleExistsInOntology(undefined));
                    if (search) {
                      dispatch(
                        conceptGotoSearchPage({
                          dataset: dataset ? dataset : "",
                          conceptId: queryConceptData?.permanent_id || "",
                          searchTerm: search,
                          page: 1,
                          showDataType,
                          queryConceptExcludeOntology:
                            !queryConceptExcludeOntology,
                        })
                      );
                    } else {
                      handleOntologyAction(
                        dispatch,
                        dataset ? dataset : "",
                        queryConceptData?.permanent_id || "",
                        data.term ? data.term.code : "",
                        "children",
                        showDataType,
                        !queryConceptExcludeOntology
                      );
                    }
                  }}
                />
              }
              label={`Display only items that exist in data`}
            />
            <LightTooltip
              title="When inactive, display values will show values
             that exist in the ontology whether or not they exist in the dataset"
            >
              <Info color="primary" />
            </LightTooltip>
          </Box>
          <TextField
            fullWidth
            value={search}
            onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
              setSearch(event.target.value);
              debouncedHandleSearchAction(
                dispatch,
                dataset ? dataset : "",
                queryConceptData?.permanent_id || "",
                event.target.value,
                showDataType,
                queryConceptExcludeOntology
              );
            }}
            margin="none"
            size="small"
            label="Search values ..."
            type="search"
            InputProps={{
              endAdornment: (
                <InputAdornment
                  position="end"
                  sx={{ cursor: "pointer" }}
                  onClick={() =>
                    dispatch(
                      conceptGotoSearchPage({
                        dataset: dataset ? dataset : "",
                        conceptId: queryConceptData?.permanent_id || "",
                        searchTerm: search,
                        page: 1,
                        showDataType,
                        queryConceptExcludeOntology,
                      })
                    )
                  }
                >
                  <Search />
                </InputAdornment>
              ),
            }}
          />
          <Box
            // display="flex"
            alignItems="center"
            justifyContent="space-between"
            aria-details="parent buttons"
          >
            <Button
              onClick={() => {
                handleOntologyAction(
                  dispatch,
                  dataset ? dataset : "",
                  queryConceptData?.permanent_id || "",
                  "",
                  "parent",
                  showDataType,
                  queryConceptExcludeOntology
                );
              }}
              size="small"
            >
              <SubdirectoryArrowLeftIcon sx={{ transform: "rotate(90deg)" }} />
              Ontology Roots
            </Button>
            {data.parents.length > 0
              ? data.parents.map((p) => (
                  <Button
                    onClick={() => {
                      handleOntologyAction(
                        dispatch,
                        dataset ? dataset : "",
                        queryConceptData?.permanent_id || "",
                        p.code,
                        "parent",
                        showDataType,
                        queryConceptExcludeOntology
                      );
                    }}
                    size="small"
                  >
                    <SubdirectoryArrowLeftIcon
                      sx={{ transform: "rotate(90deg)" }}
                    />
                    {p.label}
                  </Button>
                ))
              : null}
          </Box>
          <Box>
            {data.term ? (
              <Typography pb={1}>
                <b>{data.term.label} </b>
                <span style={{ color: finalConfig.table.aggHeaderColor[600] }}>
                  {data.term.count && data.term.uniqueSubjectCount
                    ? `: Count: ${data.term.count} (Subjects: ${data.term.uniqueSubjectCount})`
                    : ""}
                </span>
              </Typography>
            ) : null}
          </Box>
          <Box
            width="100%"
            height="12rem"
            p={1}
            border="1px solid"
            borderColor={grey[300]}
            sx={{ overflow: "auto" }}
          >
            {conceptState == "loading" ? (
              <CircularProgress size={25} />
            ) : data.action_results.length ? (
              data.action_results.map((item) => (
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    textTransform: "none",
                  }}
                  key={item.code}
                >
                  <Button
                    startIcon={
                      <SubdirectoryArrowLeftIcon
                        color="primary"
                        sx={{
                          transform: "scaleX(-1) rotate(270deg)",
                          visibility:
                            item.leaf == 1
                              ? "hidden"
                              : item.hasDescendants != undefined &&
                                  item.hasDescendants == false
                                ? "hidden"
                                : "visible",
                        }}
                      />
                    }
                    onClick={() => {
                      if (
                        item.leaf != 1 &&
                        (item.hasDescendants == undefined ||
                          item.hasDescendants == true)
                      ) {
                        handleOntologyAction(
                          dispatch,
                          dataset ? dataset : "",
                          queryConceptData?.permanent_id || "",
                          item.code,
                          "children",
                          showDataType,
                          queryConceptExcludeOntology
                        );
                      }
                    }}
                  >
                    {
                      <Typography
                        color="textPrimary"
                        textTransform={"none"}
                        textAlign={"left"}
                      >
                        <span>
                          {truncate(item.label, {
                            length: 55,
                            separator: " ",
                          })}
                        </span>
                        <span
                          style={{
                            justifyContent: "right",
                          }}
                        ></span>
                        <span
                          style={{
                            color: finalConfig.table.aggHeaderColor[600],
                          }}
                        >
                          {item.count && item.uniqueSubjectCount
                            ? ` - ${item.count} (${item.uniqueSubjectCount})`
                            : ""}
                        </span>
                      </Typography>
                    }
                  </Button>
                  <FormControlLabel
                    disableTypography={true}
                    control={
                      <Checkbox
                        sx={{
                          p: 0,
                          mx: 0.75,
                          mr: 4,
                        }}
                        checkedIcon={<CheckIcon />}
                        icon={<AddIcon />}
                        onClick={() => handleSelectValue(item.label)}
                        checked={selected.includes(item.label)}
                      />
                    }
                    label=""
                    labelPlacement={"start"}
                  ></FormControlLabel>
                </Box>
              ))
            ) : (
              <Box display="flex" flexDirection="column" textAlign="center">
                <ReportProblem
                  sx={{ color: yellow[800], mt: 6, mx: "auto" }}
                  fontSize="large"
                />
                <Typography variant="h5" color="GrayText">
                  No data was found for{" "}
                  <strong>{data.parents.map((p) => p.label)}</strong>
                </Typography>
              </Box>
            )}
          </Box>
          <FilterTextArea
            data={selected}
            open={open}
            onClose={handleClose}
            handleClickOpen={handleClickOpen}
            conceptId={queryConceptData?.permanent_id || ""}
            textValue={textValue}
            setTextValue={setTextValue}
            textOrOntology="ontology"
          />
        </Box>
        <Box width="80%" p={2}>
          <Typography fontWeight={"bold"}>Selected Data</Typography>
          <Box display="flex" alignItems="center">
            <FormControlLabel
              control={
                <Switch
                  checked={queryConceptIncludeOntologyUnknown}
                  onChange={() => {
                    dispatch(toggleIncludeOntologyUnknown());
                  }}
                />
              }
              label={
                <>Include unrecognized ontology codes {unknownItemString} </>
              }
            />
            <LightTooltip
              title="These are ontology codes from the source system 
              that didn't match any codes in the copy of the ontology used by this
              website. This can happen if a code is typed incorrectly, a different 
             code format is used, or there is a mismatch between ontology versions used
              by the source system vs this website. Contact your site administrator
               to report problems"
            >
              <Info color="primary" />
            </LightTooltip>
          </Box>
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

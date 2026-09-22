import { Box, Checkbox, Button, LinearProgress } from "@mui/material";
import {
  type CategoryConceptDetailedData,
  type CategoryConceptValue,
  addQueryConceptToFilters,
  type CategoryOrTextValues,
  updateConceptValues,
} from "../../store/cohortSlice";
import { type SyntheticEvent } from "react";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import QueryConceptAddOrUpdateButton from "../QueryConceptAddOrUpdateButton";
import QueryConceptExcludeSwitch from "../QueryConceptExcludeSwitch";

export default function CategoryOrBoolean({
  data,
}: {
  data: CategoryConceptDetailedData;
}) {
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
  if (!data.values) {
    return null;
  }

  /**
   * Add or remove the item into the values array
   *
   * @param e HTML Event
   * @param item the item to add/remove
   */
  function handleCheck(
    e: SyntheticEvent<HTMLButtonElement>,
    item: CategoryConceptValue
  ) {
    e.preventDefault();
    // new array without the item
    const newSelected =
      values?.filter((value) => value !== item.category) || [];

    // add it in if the original did not include it
    if (!values?.includes(item.category)) {
      newSelected.push(item.category);
    }

    // update the state
    dispatch(updateConceptValues(newSelected));
  }

  /**
   * Add the values into the filters
   *
   * @param e HTML Event
   */
  function handleSubmit(e: SyntheticEvent<HTMLFormElement>) {
    e.preventDefault();

    const newValues: (string | null)[] = [...values];
    if (newValues.indexOf(null) > 0) {
      newValues.splice(newValues.indexOf(null), 1);
    }
    if (queryConceptData?.cohort_def_options.include_null_and_missing) {
      newValues.push("");
    }
    dispatch(
      addQueryConceptToFilters({
        dataset: dataset ? dataset : "",
        conceptId: queryConceptData?.permanent_id || "",
        values: {
          selected_categories: newValues,
        },
        entry: queryConceptEditing,
        exclude: queryConceptExclude,
        ignoreWarnings: false,
        prefilterValue: queryConceptEditingPrefilterValue,
      })
    );
  }

  return (
    <Box flexDirection="column" px={2} my={2}>
      <Box
        sx={{ display: { xs: "", md: "flex" } }}
        justifyContent="flex-end"
        alignItems="center"
        py={1}
      >
        <QueryConceptExcludeSwitch />
        <form onSubmit={handleSubmit} style={{ marginLeft: "1rem" }}>
          <QueryConceptAddOrUpdateButton />
        </form>
      </Box>
      {data.values.map((item) => (
        <Box display="flex" alignItems="center" key={item.category}>
          <Button
            startIcon={
              <Checkbox
                onClick={(e) => handleCheck(e, item)}
                checked={values?.includes(item.category) || false}
              />
            }
            fullWidth
            sx={{ py: 0, textTransform: "none" }}
            onClick={(e) => handleCheck(e, item)}
          >
            <Box display="flex" flexDirection="column" width="100%">
              <Box display="flex" justifyContent="space-between">
                <Box textAlign={"left"}>{item.category}</Box>
                <Box>
                  {item.count} entries for {item.uniquePatientCount} subjects
                </Box>
              </Box>
              <LinearProgress
                variant="determinate"
                color={
                  values?.includes(item.category) ? "secondary" : "primary"
                }
                value={(item.count / data.max_count) * 100}
                sx={{ width: "100%", height: 5 }}
              />
            </Box>
          </Button>
        </Box>
      ))}
    </Box>
  );
}

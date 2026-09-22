import {
  Grid,
  FormGroup,
  FormLabel,
  FormControl,
  Box,
  Typography,
  Skeleton,
  Alert,
} from "@mui/material";
import AsyncSelect from "react-select/async";
import { APIRequest } from "../../api";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import { Error as ErrorIcon, ReportProblem } from "@mui/icons-material";
import {
  loadConceptDetailedData,
  setPrefetchValue,
  type ConceptData,
} from "../../store/cohortSlice";

import { componentMap } from "../../lib/utils";
import { yellow } from "@mui/material/colors";
import { useLayoutEffect } from "react";
import { type SingleValue } from "react-select";

type PrefilterCategoryValue = {
  category: string;
};

export default function Prefilter({
  data,
  count,
}: {
  data: ConceptData;
  count: number;
}) {
  const DisplayComponent = componentMap[data.concept_type];
  const dispatch = useAppDispatch();
  const dataset = useAppSelector((state) => state.auth.dataset);
  const queryConceptDetailedData = useAppSelector(
    (state) => state.cohort.queryConceptDetailedData
  );
  const queryConceptEditingPrefilterValue = useAppSelector(
    (state) => state.cohort.queryConceptEditingPrefilterValue
  );
  const errors = useAppSelector((state) => state.cohort.transformationErrors);
  const warnings = useAppSelector(
    (state) => state.cohort.transformationWarnings
  );

  async function loadPrefilterOptions(value: string) {
    const conceptId = data.concept_for_prefilter?.permanent_id;
    const queryStrings = [
      "page=1",
      "search=",
      "show_all_data=true",
      "cohort_def=[]",
      "records_per_page=1000",
      "include_statistics=true",
    ];
    const response = await APIRequest(
      "GET",
      `/api/v2/${dataset?.unique_id}/concepts/${conceptId}/?${queryStrings.join("&")}`
    );

    if (data.prefilter_mode == "optional") {
      dispatch(
        loadConceptDetailedData({
          dataset: dataset?.unique_id ?? "",
          conceptId: data.permanent_id,
          showDataType: "all",
          prefilterValue: queryConceptEditingPrefilterValue,
        })
      );
    }

    if (response.statistics.error) {
      return [
        {
          label: "Prefilter is configured incorrectly",
          value: "-1",
        },
      ];
    }

    if (response.concept_type == "category") {
      return response.statistics.values
        .filter((item: PrefilterCategoryValue) => item.category.includes(value))
        .map((item: PrefilterCategoryValue) => ({
          label: item.category,
          value: item.category,
        }));
    } else if (response.concept_type == "text") {
      return response.statistics.values
        .filter((item: string) => item.includes(value))
        .map((item: string) => ({
          label: item,
          value: item,
        }));
    } else {
      return [
        {
          label: "Only category and text concepts are allowed for prefilter",
          value: "-1",
        },
      ];
    }
  }
  type PrefilterSelectType = {
    label: typeof queryConceptEditingPrefilterValue;
    value: typeof queryConceptEditingPrefilterValue;
  };

  async function handleOnChange(value: SingleValue<PrefilterSelectType>) {
    if (value == null) {
      dispatch(setPrefetchValue(""));
      return;
    }
    if (queryConceptEditingPrefilterValue !== value?.value) {
      dispatch(setPrefetchValue(value?.value ?? ""));
    }
    await dispatch(
      loadConceptDetailedData({
        dataset: dataset?.unique_id ?? "",
        conceptId: data.permanent_id,
        showDataType: "all",
        prefilterValue: value?.value,
      })
    );
  }

  useLayoutEffect(() => {
    if (queryConceptEditingPrefilterValue) {
      handleOnChange({
        value: queryConceptEditingPrefilterValue,
        label: queryConceptEditingPrefilterValue,
      });
    }
  }, []); // eslint-disable-line

  return (
    <>
      <Grid container justifyContent="center">
        <Grid>
          <FormGroup sx={{ px: 2 }}>
            <FormLabel>
              {data.prefilter_mode == "required" ? "First" : "Optionally"}{" "}
              select a {data.concept_for_prefilter?.name} to filter from
            </FormLabel>
            <FormControl data-testid="prefilter-select">
              <AsyncSelect
                defaultValue={{
                  label: queryConceptEditingPrefilterValue,
                  value: queryConceptEditingPrefilterValue,
                }}
                isClearable
                loadOptions={loadPrefilterOptions}
                defaultOptions
                onChange={handleOnChange}
                menuPosition="fixed"
              />
            </FormControl>
          </FormGroup>
        </Grid>
      </Grid>
      {data.prefilter_mode == "required" && !data.prefilter_value ? (
        <Box
          p={2}
          display="flex"
          flexDirection="column"
          justifyContent="center"
          alignItems="center"
        >
          <ErrorIcon color="error" fontSize="large" />
          <Typography>Please select a value to filter from</Typography>
        </Box>
      ) : !queryConceptDetailedData ? (
        <Box textAlign="center" p={2}>
          <Skeleton variant="rectangular" height="5rem" sx={{ my: 1 }} />
          <Skeleton variant="rectangular" height="25rem" />
        </Box>
      ) : (
        <>
          <Box>
            {errors.length
              ? errors.map((error) => (
                  <Alert key={error} severity="error">
                    {error}
                  </Alert>
                ))
              : null}
            {warnings.length && data.concept_type != "text"
              ? warnings.map((warning) => (
                  <Alert key={warning} severity="warning">
                    {warning}
                  </Alert>
                ))
              : null}
          </Box>
          {/* have to handle case where text/ontology search returns empty results */}
          {count > 1 || queryConceptDetailedData.searchTerm ? (
            <Box pb={10}>
              <DisplayComponent data={queryConceptDetailedData} />
            </Box>
          ) : (
            <Box
              display="flex"
              flexDirection="column"
              mt={2}
              textAlign="center"
            >
              <ReportProblem
                sx={{ color: yellow[800], mx: "auto" }}
                fontSize="large"
              />
              <Typography variant="h5" color="GrayText">
                No data was found for this concept
              </Typography>
            </Box>
          )}
        </>
      )}
    </>
  );
}

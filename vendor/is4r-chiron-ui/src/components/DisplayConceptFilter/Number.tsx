import {
  type NumberConceptDetailedData,
  addQueryConceptToFilters,
  type NumberValues,
  type CategoryConceptValue,
  updateConceptValues,
} from "../../store/cohortSlice";
import Box from "@mui/material/Box";
import { generateHistogramData } from "../../lib/utils";
import {
  Chip,
  Paper,
  TextField,
  Container,
  useMediaQuery,
  Checkbox,
  LinearProgress,
  Button,
} from "@mui/material";
import { grey } from "@mui/material/colors";
import QueryConceptAddOrUpdateButton from "../QueryConceptAddOrUpdateButton";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import { SyntheticEvent } from "react";
import QueryConceptExcludeSwitch from "../QueryConceptExcludeSwitch";

import {
  ChartsTooltip,
  ResponsiveChartContainer,
  ChartsXAxis,
  BarPlot,
  ChartsYAxis,
} from "@mui/x-charts";
import config from "../../config";

function DataDisplay({
  name,
  value,
}: {
  name: string;
  value: string | number;
}) {
  return (
    <div>
      <Chip label={name} sx={{ borderRadius: 0 }} />
      <Chip
        label={Number(value).toLocaleString()}
        sx={{
          fontWeight: "bold",
          background: "inherit",
          border: "1px solid",
          borderColor: grey[300],
          borderRadius: 0,
          borderCollapse: "collapse",
        }}
      />
    </div>
  );
}

export default function NumberDisplay({
  data,
}: {
  data: NumberConceptDetailedData;
}) {
  const translatedData = generateHistogramData(data.histogram_data);
  const dispatch = useAppDispatch();
  const dataset = useAppSelector((state) => state.auth.dataset?.unique_id);

  const values = useAppSelector(
    (state) => state.cohort.queryConceptValues as NumberValues
  );

  const queryConceptData = useAppSelector(
    (state) => state.cohort.queryConceptData
  );

  const queryConceptDetailedData = useAppSelector(
    (state) => state.cohort.queryConceptDetailedData
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
  const isMobile = useMediaQuery("(max-width: 700px)");

  function handleCheck(
    e: SyntheticEvent<HTMLButtonElement>,
    item: CategoryConceptValue
  ) {
    e.preventDefault();

    // new array without the item
    const newSelected =
      values.values.filter((value) => value !== item.category) || [];

    // add it in if the original did not include it
    if (!values.values.includes(item.category)) {
      newSelected.push(item.category);
    }

    // update the state
    dispatch(updateConceptValues({ values: newSelected }));
  }

  /**
   * Adds the values into the filters
   *
   * @param e HTML Event
   */
  function handleSubmit(e: SyntheticEvent<HTMLFormElement>) {
    e.preventDefault();

    const newValues: (string | null)[] = [...values.values];
    if (newValues.indexOf(null) > 0) {
      newValues.splice(newValues.indexOf(null), 1);
    }
    if (queryConceptData?.cohort_def_options.include_null_and_missing) {
      newValues.push("");
    }

    const formData = new FormData(e.currentTarget);
    const min = formData.get("min");
    const max = formData.get("max");

    dispatch(
      addQueryConceptToFilters({
        dataset: dataset ? dataset : "",
        conceptId: queryConceptData?.permanent_id || "",
        values: {
          cd_numeric_min: min || "",
          cd_numeric_max: max || "",
          selected_categories: newValues,
        },
        include_null_and_missing:
          queryConceptData?.cohort_def_options.include_null_and_missing,
        entry: queryConceptEditing,
        exclude: queryConceptExclude,
        prefilterValue: queryConceptEditingPrefilterValue,
        ignoreWarnings: false,
      })
    );
  }

  return (
    <>
      <Box display="flex" flexDirection="column" px={1} my={3}>
        <form onSubmit={handleSubmit}>
          <Box
            sx={{ display: { sm: "", md: "flex" } }}
            justifyContent="space-between"
            alignItems="center"
            p={2}
          >
            <Box display="flex" gap={2}>
              <TextField
                label="Min Value"
                name="min"
                size="small"
                InputLabelProps={{ shrink: true }}
                placeholder={
                  data.stats.min != undefined ? data.stats.min.toString() : ""
                }
                defaultValue={
                  values.existing_min || values.existing_min === 0
                    ? values.existing_min
                    : ""
                }
              />
              <TextField
                label="Max Value"
                name="max"
                size="small"
                InputLabelProps={{ shrink: true }}
                placeholder={data.stats.max ? data.stats.max.toString() : ""}
                defaultValue={
                  values.existing_max || values.existing_max === 0
                    ? values.existing_max
                    : ""
                }
              />
            </Box>
            <Box sx={{ display: { xs: "", sm: "flex" } }} alignItems="center">
              <QueryConceptExcludeSwitch />
              <Box ml={1}>
                <QueryConceptAddOrUpdateButton />
              </Box>
            </Box>
          </Box>
        </form>
        <Box display="flex" justifyContent="center" gap={2} p={2}>
          <DataDisplay name="Entries:" value={data.stats.count_non_null} />
          <DataDisplay name="Min:" value={data.stats.min} />
          <DataDisplay name="Mean:" value={data.stats.avg} />
          <DataDisplay name="Max:" value={data.stats.max} />
        </Box>
      </Box>
      <Container
        sx={{
          display: "flex",
          flexDirection: isMobile ? "column" : "",
          flexWrap: !isMobile ? "wrap" : "",
          justifyContent: !isMobile ? "space-between" : "",
          gap: !isMobile ? 0.5 : "",
          alignItems: isMobile ? "center" : "",
          maxHeight: !isMobile ? "200" : "",
        }}
      >
        {translatedData?.values.length ? (
          <Box
            sx={{
              flex: !isMobile ? 1 : "",
              minWidth: !isMobile ? "60%" : "",
              textAlign: !isMobile ? "center" : "",
              width: isMobile ? "90%" : "",
              marginBottom: isMobile ? 10 : "",
            }}
          >
            <Paper sx={{ height: { sm: 200, md: 500 } }}>
              <ResponsiveChartContainer
                series={[
                  {
                    data: translatedData.values,
                    type: "bar",
                    color: config.table.secondaryColor,
                    yAxisKey: "yAxis",
                  },
                ]}
                xAxis={[
                  {
                    scaleType: "band",
                    data: translatedData.labels,
                    id: "x-axis-id",
                  },
                ]}
                yAxis={[{ scaleType: "linear", id: "yAxis" }]}
              >
                <ChartsTooltip />

                <BarPlot tooltip={{ trigger: "item" }} />
                <ChartsYAxis position="left" axisId="yAxis"></ChartsYAxis>
                <ChartsXAxis
                  label={queryConceptData?.name || "Data"}
                  position="bottom"
                  axisId="x-axis-id"
                />
              </ResponsiveChartContainer>
            </Paper>
          </Box>
        ) : null}
        {queryConceptData?.concept_type &&
        queryConceptData.concept_type == "number_with_categories" ? (
          <Box
            sx={{
              flex: !isMobile ? 1 : "",
              minWidth: !isMobile ? "30%" : "",
              width: isMobile ? "90%" : "",
            }}
          >
            <Box sx={{ fontWeight: 600 }}>Non-numberic-values</Box>
            {queryConceptDetailedData?.values.map((item) => (
              <Box key={item.category}>
                <Button
                  startIcon={
                    <Checkbox
                      onClick={(e) => handleCheck(e, item)}
                      checked={values.values.includes(item.category) || false}
                    />
                  }
                  sx={{ width: "100%", py: 0, textTransform: "none" }}
                  onClick={(e) => handleCheck(e, item)}
                >
                  <Box width="100%">
                    <Box display="flex" justifyContent="space-between">
                      <Box>{item.category}</Box>
                      <Box>
                        {item.count} entries for {item.uniquePatientCount}{" "}
                        subjects
                      </Box>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={
                        (item.count / queryConceptDetailedData.max_count) * 100
                      }
                      sx={{ width: "100%", height: 5 }}
                    />
                  </Box>
                </Button>
              </Box>
            ))}
          </Box>
        ) : null}
      </Container>
    </>
  );
}

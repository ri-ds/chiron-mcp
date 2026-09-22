import {
  type AgeConceptDetailedData,
  addQueryConceptToFilters,
  type AgeValues,
} from "../../store/cohortSlice";
import Box from "@mui/material/Box";
import { generateHistogramData } from "../../lib/utils";
import { Chip, Paper, TextField } from "@mui/material";
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
        label={value}
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

export default function AgeDisplay({ data }: { data: AgeConceptDetailedData }) {
  const translatedData = generateHistogramData(data.histogram_data);
  const dispatch = useAppDispatch();
  const values = useAppSelector(
    (state) => state.cohort.queryConceptValues as AgeValues
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

  /**
   * Adds the values into the filters
   *
   * @param e HTML Event
   */
  function handleSubmit(e: SyntheticEvent<HTMLFormElement>) {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const min_year = formData.get("min_year");
    const max_year = formData.get("max_year");
    const min_day = formData.get("min_day");
    const max_day = formData.get("max_day");
    const values = {
      cd_age_min_year: min_year || "",
      cd_age_max_year: max_year || "",
      cd_age_min_day: min_day || "",
      cd_age_max_day: max_day || "",
    };
    dispatch(
      addQueryConceptToFilters({
        dataset: dataset ? dataset : "",
        conceptId: queryConceptData?.permanent_id || "",
        values: values,
        entry: queryConceptEditing,
        exclude: queryConceptExclude,
        include_null_and_missing:
          queryConceptData?.cohort_def_options.include_null_and_missing,
        ignoreWarnings: false,
        prefilterValue: queryConceptEditingPrefilterValue,
      })
    );
  }

  return (
    <Box display="flex" flexDirection="column" px={2} my={2}>
      <form onSubmit={handleSubmit}>
        <Box
          display="flex"
          justifyContent="space-between"
          alignItems="center"
          p={2}
        >
          <Box gap={2} sx={{ display: { xs: "", md: "flex" } }}>
            <TextField
              label="Min Year"
              name="min_year"
              size="small"
              type="number"
              InputLabelProps={{ shrink: true }}
              placeholder={data.stats.min_year.toString() || ""}
              defaultValue={
                values.existing_min_year || values.existing_min_year === 0
                  ? values.existing_min_year
                  : ""
              }
              sx={{ p: 2 }}
            />
            <TextField
              label="Min Day"
              name="min_day"
              size="small"
              type="number"
              InputLabelProps={{ shrink: true }}
              placeholder={data.stats.min_day.toString() || ""}
              defaultValue={
                values.existing_min_day || values.existing_min_day === 0
                  ? values.existing_min_day
                  : ""
              }
              sx={{ p: 2 }}
            />
            <TextField
              label="Max Year"
              name="max_year"
              size="small"
              type="number"
              InputLabelProps={{ shrink: true }}
              placeholder={data.stats.max_year.toString() || ""}
              defaultValue={
                values.existing_max_year || values.existing_max_year === 0
                  ? values.existing_max_year
                  : ""
              }
              sx={{ p: 2 }}
            />
            <TextField
              label="Max Day"
              name="max_day"
              size="small"
              type="number"
              InputLabelProps={{ shrink: true }}
              placeholder={data.stats.max_day.toString() || ""}
              defaultValue={
                values.existing_max_day || values.existing_max_day === 0
                  ? values.existing_max_day
                  : ""
              }
              sx={{ p: 2 }}
            />
          </Box>
          <Box
            sx={{ display: { xs: "unset", md: "flex" } }}
            alignItems="center"
          >
            <QueryConceptExcludeSwitch />
            <Box ml={1}>
              <QueryConceptAddOrUpdateButton />
            </Box>
          </Box>
        </Box>
      </form>
      <Box
        sx={{ display: { xs: "", sm: "flex" } }}
        justifyContent="center"
        gap={2}
        p={2}
      >
        <DataDisplay name="Entries:" value={data.stats.count_non_null} />
        <DataDisplay
          name="Mean:"
          value={`${data.stats.avg_year}Y ${data.stats.avg_day}D`}
        />
        <DataDisplay
          name="Min:"
          value={`${data.stats.min_year}Y ${data.stats.min_day}D`}
        />
        <DataDisplay
          name="Max:"
          value={`${data.stats.max_year}Y ${data.stats.max_day}D`}
        />
      </Box>
      <Paper sx={{ height: { sm: 200, md: 500 }, minWidth: 200 }}>
        <ResponsiveChartContainer
          series={[
            {
              data: translatedData?.values,
              type: "bar",
              color: config.table.secondaryColor,
              yAxisKey: "yAxis",
            },
          ]}
          xAxis={[
            {
              scaleType: "band",
              data: translatedData?.labels,
              id: "x-axis-id",
            },
          ]}
          yAxis={[{ scaleType: "linear", id: "yAxis" }]}
        >
          <ChartsTooltip />

          <BarPlot tooltip={{ trigger: "item" }} />
          <ChartsYAxis position="left" axisId={"yAxis"}></ChartsYAxis>
          <ChartsXAxis
            label={queryConceptData?.name || "Data"}
            position="bottom"
            axisId="x-axis-id"
          />
        </ResponsiveChartContainer>
      </Paper>
    </Box>
  );
}

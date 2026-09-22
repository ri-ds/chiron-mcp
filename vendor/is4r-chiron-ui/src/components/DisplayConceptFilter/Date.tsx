import {
  type DateConceptDetailedData,
  addQueryConceptToFilters,
  type DateValues,
} from "../../store/cohortSlice";
import Box from "@mui/material/Box";
import { generateHistogramData } from "../../lib/utils";
import {
  Chip,
  MenuItem,
  Paper,
  Select,
  Tab,
  Tabs,
  TextField,
} from "@mui/material";
import { grey } from "@mui/material/colors";
import QueryConceptAddOrUpdateButton from "../QueryConceptAddOrUpdateButton";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import { SyntheticEvent, useEffect, useState } from "react";
import QueryConceptExcludeSwitch from "../QueryConceptExcludeSwitch";
import config from "../../config.tsx";
import {
  ChartsTooltip,
  ResponsiveChartContainer,
  ChartsXAxis,
  BarPlot,
  ChartsYAxis,
} from "@mui/x-charts";

const days_ago_otions = [
  { id: 1, label: "1 day (today)" },
  { id: 2, label: "2 days" },
  { id: 3, label: "3 days" },
  { id: 4, label: "4 days" },
  { id: 5, label: "5 days" },
  { id: 6, label: "6 days" },
  { id: 7, label: "7 days" },
  { id: 8, label: "8 days" },
  { id: 9, label: "9 days" },
  { id: 10, label: "10 days" },
  { id: 14, label: "14 days" },
  { id: 30, label: "30 days" },
  { id: 60, label: "60 days" },
  { id: 180, label: "180 days" },
  { id: 365, label: "1 years" },
  { id: 730, label: "2 years" },
  { id: 1095, label: "3 years" },
];

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

export default function DateDisplay({
  data,
}: {
  data: DateConceptDetailedData;
}) {
  const translatedData = generateHistogramData(data.histogram_data);
  const dispatch = useAppDispatch();
  const values = useAppSelector(
    (state) => state.cohort.queryConceptValues as DateValues
  );
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
  const [tabValue, setTabValue] = useState("date_range");
  const dataset = useAppSelector((state) => state.auth.dataset?.unique_id);
  /**
   * This is to pre-select the correct tab, it only watches one
   * key to accomplish this.
   */
  useEffect(() => {
    if (tabValue !== values?.query_type) {
      setTabValue(values?.query_type || "date_range");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [values?.query_type]);

  /**
   * Adds the values into the filters
   *
   * @param e HTML Event
   */
  function handleSubmit(e: SyntheticEvent<HTMLFormElement>) {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const min = formData.get("min");
    const max = formData.get("max");
    const query_type = formData.get("query_type");
    const days_ago = formData.get("days_ago");

    dispatch(
      addQueryConceptToFilters({
        dataset: dataset ? dataset : "",
        conceptId: queryConceptData?.permanent_id || "",
        values: {
          days_ago,
          query_type,
          cd_numeric_min: min || "",
          cd_numeric_max: max || "",
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

  /**
   * Handles the switching of the tab
   *
   * @param _e HTML Event
   * @param newValue The value to use
   */
  const handleChangeTab = (_e: SyntheticEvent, newValue: string) => {
    setTabValue(newValue);
  };

  return (
    <Box display="flex" flexDirection="column" px={2} my={2}>
      <form onSubmit={handleSubmit}>
        <Box
          justifyContent="space-between"
          alignItems="center"
          p={2}
          sx={{ display: { xs: "", md: "flex" } }}
        >
          <Box textAlign="center">
            <Tabs
              value={tabValue}
              onChange={handleChangeTab}
              sx={{ pb: 2 }}
              variant="fullWidth"
            >
              <Tab label="Filter by date range" value="date_range" />
              <Tab label="Filter relative to today" value="relative_to_today" />
            </Tabs>
            <input type="hidden" name="query_type" value={tabValue} />
            {tabValue == "date_range" ? (
              <Box
                role="tabpanel"
                display="flex"
                gap={1}
                justifyContent="center"
              >
                <TextField
                  label="Min (inclusive)"
                  name="min"
                  type="date"
                  size="small"
                  InputLabelProps={{ shrink: true }}
                  placeholder={data.stats.min || ""}
                  defaultValue={values?.existing_min || ""}
                />
                <TextField
                  label="Max (inclusive)"
                  name="max"
                  type="date"
                  size="small"
                  InputLabelProps={{ shrink: true }}
                  placeholder={data.stats.max || ""}
                  defaultValue={values?.existing_max || ""}
                />
              </Box>
            ) : tabValue === "relative_to_today" ? (
              <div role="tabpanel">
                <Select
                  name="days_ago"
                  size="small"
                  defaultValue={values?.days_ago || "1"}
                >
                  {days_ago_otions.map((option) => (
                    <MenuItem key={option.id} value={option.id}>
                      {option.label}
                    </MenuItem>
                  ))}
                </Select>
              </div>
            ) : null}
          </Box>
          <Box display="flex" alignItems="center">
            <QueryConceptExcludeSwitch />
            <Box ml={1}>
              <QueryConceptAddOrUpdateButton />
            </Box>
          </Box>
        </Box>
      </form>
      <Box
        sx={{ display: { xs: "unset", sm: "flex" } }}
        justifyContent="center"
        gap={2}
        p={2}
      >
        <DataDisplay name="Entries:" value={data.stats.count_non_null} />
        <DataDisplay
          name="Unique Subjects:"
          value={data.stats.unique_patients}
        />
        <DataDisplay name="Min:" value={data.stats.min} />
        <DataDisplay name="Max:" value={data.stats.max} />
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

import {
  Box,
  ToggleButtonGroup,
  ToggleButton,
  Typography,
} from "@mui/material";
import { Error as ErrorIcon } from "@mui/icons-material";
import { loadReportsDef } from "../../store/reportsSlice";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import { AppDispatch } from "../../store";
import config from "../../config";

export default function ReportsCategories() {
  const reportsStatus = useAppSelector((state) => state.reports.reportsStatus);
  const categories = useAppSelector((state) => state.reports.reportCategories);
  const dataset = useAppSelector((state) => state.auth.dataset);
  const dispatch = useAppDispatch();

  const filteredCategory = useAppSelector(
    (state) => state.reports.filteredCategory
  );
  const filteredState = useAppSelector((state) => state.reports.filteredState);

  /**
   * Handles filtering of reports list
   *
   * @param dispatch the dispatch function
   * @param project_id the reports permanent id if it is not a spcecial category
   * @param state either "all" or "starred" for special categories
   */

  function handleCategoryAction(
    dispatch: AppDispatch,
    parameterObject: {
      dataset: string;
      project_id: string;
      state: string;
    }
  ) {
    dispatch(loadReportsDef(parameterObject));
  }

  const handleCategoryChange = (
    _: React.MouseEvent<HTMLElement>,
    newSetting: string | number
  ) => {
    newSetting = newSetting == "all" ? "" : newSetting;
    const parameterObject = {
      dataset: dataset ? dataset.unique_id : "",
      project_id: typeof newSetting == "number" ? newSetting.toString() : "",
      state: typeof newSetting == "string" ? newSetting.toString() : "",
    };
    handleCategoryAction(dispatch, parameterObject);
  };

  return (
    <Box
      px={2}
      display="flex"
      justifyContent="space-between"
      alignItems="center"
      sx={{ overflow: "auto" }}
    >
      {reportsStatus == "failed" ? (
        <Box display="flex" alignItems="center" gap={1}>
          <ErrorIcon color="error" />{" "}
          <Typography variant="h5" color="error">
            Could not load results
          </Typography>
        </Box>
      ) : (
        <ToggleButtonGroup
          value={
            filteredCategory == ""
              ? filteredState
              : filteredCategory == undefined
                ? ""
                : +filteredCategory
          }
          sx={{
            backgroundColor: config.table.aggHeaderColor[100],
            "& .Mui-selected": {
              backgroundColor: config.table.secondaryHeaderColor[300],
            },
          }}
          exclusive={true}
          onChange={handleCategoryChange}
        >
          {categories?.custom_report_categories.map((category) => (
            <ToggleButton value={category.state} key={category.state}>
              {category.label} [{category.count}]
            </ToggleButton>
          ))}
          {categories?.qProject.map((category) => (
            <ToggleButton value={category.pk} key={category.pk}>
              {category.label} [{category.count}]
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      )}
      <Box display="flex" gap={2} alignItems="center"></Box>
    </Box>
  );
}

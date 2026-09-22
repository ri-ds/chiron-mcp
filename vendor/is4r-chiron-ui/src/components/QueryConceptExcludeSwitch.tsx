import { Box, Switch, FormControlLabel } from "@mui/material";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { toggleExclude } from "../store/cohortSlice";
import InfoIcon from "@mui/icons-material/Info";
import LightTooltip from "./LightTooltip";

export default function QueryConceptExcludeSwitch() {
  const dispatch = useAppDispatch();
  const queryConceptData = useAppSelector(
    (state) => state.cohort.queryConceptData
  );
  const queryConceptExclude = useAppSelector(
    (state) => state.cohort.queryConceptExclude
  );

  return queryConceptData?.concept_type !== "boolean" ? (
    <Box display="flex" alignItems="center">
      <FormControlLabel
        sx={{ mr: 0 }}
        labelPlacement="start"
        control={
          <Switch
            checked={queryConceptExclude}
            onChange={() => dispatch(toggleExclude())}
          />
        }
        label="Exclude Filter"
      />
      <LightTooltip title="Excluded filters will be applied to Filters panel as 'not equal to'">
        <InfoIcon color="primary" />
      </LightTooltip>
    </Box>
  ) : null;
}

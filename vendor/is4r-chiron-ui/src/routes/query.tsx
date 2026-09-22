import {
  Alert,
  Box,
  Breadcrumbs,
  Button,
  FormControlLabel,
  Switch,
  Tooltip,
  Typography,
} from "@mui/material";
import Concepts from "../components/Concepts";
import Filters from "../components/Filters";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  cancelQueryConceptEditing,
  switchDataType,
  toggleIncludeNullAndMissing,
} from "../store/cohortSlice";
import DisplayConceptFilter from "../components/DisplayConceptFilter";
import { pluralizeCount } from "../lib/utils";
import { Info } from "@mui/icons-material";
import LightTooltip from "../components/LightTooltip";
import truncate from "lodash/truncate";
import LockIcon from "@mui/icons-material/Lock";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import ConstructionIcon from "@mui/icons-material/Construction";
import { NavLink } from "react-router-dom";
import config from "../config";
import { ConceptFilterSkeleton } from "../components/DisplayConceptFilter/Skeleton";
export default function QueryRoute() {
  const dispatch = useAppDispatch();
  const queryConceptData = useAppSelector(
    (state) => state.cohort.queryConceptData
  );

  const isStaff = useAppSelector((state) => state.auth.user?.isStaff);
  const showDataType = useAppSelector((state) => state.cohort.showDataType);
  const dataset = useAppSelector((state) => state.auth.dataset?.unique_id);
  const canViewWorkspace = useAppSelector(
    (state) => state.auth.dataset?.canViewWorkspace
  );
  const accessLevel = useAppSelector(
    (state) => state.auth.dataset?.accessLevel
  );
  const queryConceptDetailedData = useAppSelector(
    (state) => state.cohort.queryConceptDetailedData
  );

  const queryConceptStatus = useAppSelector(
    (state) => state.cohort.conceptState
  );

  const queryConceptEditing = useAppSelector(
    (state) => state.cohort.queryConceptEditing
  );

  let missingSubjectsString = "";
  if (queryConceptDetailedData) {
    missingSubjectsString = `(${pluralizeCount(
      queryConceptDetailedData.count_subjects_with_missing_values,
      "subject"
    )})`;
  }

  //This is the only workspace page that doesn't make data call to return auth error,
  //Seemed simpler than having to extract error state from concept
  if (
    (canViewWorkspace != undefined && !canViewWorkspace) ||
    accessLevel == "agg"
  ) {
    return (
      <Box>
        <Alert severity="error">
          The chiron user doesn't have permission to access to workspace
          functionality.
        </Alert>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        display: "flex",
      }}
    >
      <Box>
        <Concepts conceptType="cohort" />
      </Box>
      <Box flexGrow={1} overflow={"scroll"}>
        {queryConceptData ? (
          <>
            <Box p={2}>
              <Box
                sx={{
                  display: { md: "unset", lg: "grid" },
                  gridTemplateColumns: "repeat(2, 1fr)",
                }}
              >
                <Box sx={{ display: { sm: "", md: "" } }}>
                  <Breadcrumbs
                    maxItems={2}
                    aria-label="breadcrumb showing concept hierarchy"
                    slots={{
                      CollapsedIcon: () => {
                        const toolTipText = queryConceptData?.category_hierarchy
                          .map((item) => item.name)
                          .join("-> ");

                        return (
                          <Tooltip
                            title={`${toolTipText}-> ${queryConceptData.name}`}
                          >
                            <MoreHorizIcon fontSize="medium"></MoreHorizIcon>
                          </Tooltip>
                        );
                      },
                    }}
                  >
                    {queryConceptData?.category_hierarchy.map((item) => (
                      <Box key={item.name}>
                        <Typography
                          variant="h5"
                          fontWeight="100"
                          key={item.name}
                        >
                          {truncate(item.name)}
                        </Typography>
                        <Typography
                          variant="h4"
                          color="GrayText"
                          fontWeight="100"
                          sx={{ mx: 1 }}
                        ></Typography>
                      </Box>
                    ))}

                    <Box key={queryConceptData.name}>
                      <Typography variant="h5" fontWeight="bold">
                        {truncate(queryConceptData.name)}
                      </Typography>
                    </Box>
                  </Breadcrumbs>
                  {isStaff ? (
                    <NavLink
                      to={`${config.apiBaseUrl}${config.header.adminLink}chiron/concept/${queryConceptData.pk}`}
                      reloadDocument={true}
                    >
                      <Button variant="outlined">
                        <ConstructionIcon></ConstructionIcon>
                        Edit Concept
                      </Button>
                    </NavLink>
                  ) : null}
                </Box>
                <Box px={2} display="flex" flexDirection="column">
                  <Box display="flex" alignItems="center">
                    <FormControlLabel
                      labelPlacement="end"
                      control={
                        <Switch
                          checked={showDataType === "cohort"}
                          data-testid="active-cohort-switch"
                          onChange={() =>
                            dispatch(
                              switchDataType({
                                dataset: dataset ? dataset : "",
                                conceptId: queryConceptData.permanent_id,
                                hasPrefilter: Boolean(
                                  queryConceptData.concept_for_prefilter
                                ),
                                prefilterValue:
                                  queryConceptData.prefilter_value,
                                showDataType:
                                  showDataType === "all" ? "cohort" : "all",
                              })
                            )
                          }
                        />
                      }
                      label="Show data for active cohort only"
                    />
                    <LightTooltip title="When active, all data displayed in this panel will be from the active cohort only">
                      <Info color="primary" />
                    </LightTooltip>
                  </Box>
                  <Box display="flex" alignItems="center">
                    <FormControlLabel
                      control={
                        <Switch
                          checked={
                            queryConceptData.cohort_def_options
                              .include_null_and_missing == true
                          }
                          onChange={() =>
                            dispatch(toggleIncludeNullAndMissing())
                          }
                        />
                      }
                      label={`Include null or missing values in filter ${missingSubjectsString}`}
                    />
                    <LightTooltip title="When active, null and missing values will be included in the filters">
                      <Info color="primary" />
                    </LightTooltip>
                  </Box>
                </Box>
              </Box>
              {queryConceptData.description ? (
                <div
                  style={{ fontWeight: 300 }}
                  dangerouslySetInnerHTML={{
                    __html: queryConceptData.description,
                  }}
                />
              ) : null}
              {queryConceptData.has_phi ? (
                <Alert
                  severity="info"
                  sx={{
                    alignItems: "center",
                    width: "100%",
                    ".MuiAlert-message": {
                      width: "100%",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                    },
                  }}
                  icon={<LockIcon></LockIcon>}
                >
                  <Typography>This field may include PHI</Typography>
                </Alert>
              ) : null}
              {queryConceptEditing ? (
                <Alert
                  severity="info"
                  sx={{
                    alignItems: "center",
                    width: "100%",
                    ".MuiAlert-message": {
                      width: "100%",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                    },
                  }}
                >
                  <Typography>Editing Concept Filter...</Typography>
                  <Button
                    size="small"
                    variant="outlined"
                    color="inherit"
                    sx={{ mr: 1 }}
                    onClick={() => dispatch(cancelQueryConceptEditing())}
                  >
                    Cancel Editing
                  </Button>
                </Alert>
              ) : null}
            </Box>
            <Box maxHeight={200}>
              <DisplayConceptFilter type={queryConceptData.concept_type} />
            </Box>
          </>
        ) : queryConceptStatus == "done" ? (
          <Box p={3} mt={5} maxHeight={200}>
            <Typography variant="h5" sx={{ mb: 3, ml: 2.5 }}>
              Quick Start Guide
            </Typography>
            <ol>
              <li>
                <Typography fontWeight="normal" gutterBottom sx={{ mb: 3 }}>
                  <strong>Search</strong> or <strong>Browse</strong> data
                  categories on the left. Selecting a data set will display
                  descriptive information, distribution charts (for numerical
                  data), and various statistics.
                </Typography>
              </li>
              <li>
                <Typography fontWeight="normal" gutterBottom sx={{ mb: 3 }}>
                  <strong>Make selections</strong> from the displayed data set
                  and click "apply new filter" to add a subject filter to the
                  right side. Multiple filters may be applied.
                </Typography>
              </li>
              <li>
                <Typography fontWeight="normal" gutterBottom sx={{ mb: 3 }}>
                  <strong>Add additional filters</strong> to further refine
                  data. Click the "add filter set" button on the right, then
                  select a set from the list that appears. Multiple filters may
                  be applied.
                </Typography>
              </li>
              <li>
                <Typography fontWeight="normal" gutterBottom sx={{ mb: 3 }}>
                  <strong>Click "View Results"</strong> to analyze filtered
                  data. Results can be downloaded or save to your user profile
                  for future use.
                </Typography>
              </li>
            </ol>
          </Box>
        ) : (
          <ConceptFilterSkeleton></ConceptFilterSkeleton>
        )}
      </Box>
      <Box>
        <Filters resultsDisplay={false} />
      </Box>
    </Box>
  );
}

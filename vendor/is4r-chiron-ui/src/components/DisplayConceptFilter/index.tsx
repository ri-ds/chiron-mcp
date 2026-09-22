import { useAppSelector } from "../../store/hooks";
import { Alert, Box, Skeleton, Typography } from "@mui/material";
import ReportProblem from "@mui/icons-material/ReportProblem";
import { yellow } from "@mui/material/colors";
import Prefilter from "./PreFilter";
import { componentMap } from "../../lib/utils";

export default function DisplayConceptFilter({ type }: { type: string }) {
  const queryConceptDetailedData = useAppSelector(
    (state) => state.cohort.queryConceptDetailedData
  );
  const queryConceptData = useAppSelector(
    (state) => state.cohort.queryConceptData
  );
  const showDataType = useAppSelector((state) => state.cohort.showDataType);
  const cohortDef = useAppSelector((state) => state.cohort.extended_cohort_def);
  const errors = useAppSelector((state) => state.cohort.transformationErrors);
  const conceptErrors = useAppSelector((state) => state.cohort.errors);
  const warnings = useAppSelector(
    (state) => state.cohort.transformationWarnings
  );

  if (conceptErrors && conceptErrors.length > 0) {
    return (
      <Box display="flex" flexDirection="column" mt={2} textAlign="center">
        <ReportProblem
          sx={{ color: yellow[800], mx: "auto" }}
          fontSize="large"
        />
        {conceptErrors.map((e) => (
          <Typography variant="h5" color="GrayText" key={e}>
            {e}
          </Typography>
        ))}
      </Box>
    );
  }

  if (!queryConceptDetailedData && !queryConceptData?.concept_for_prefilter) {
    return (
      <Box textAlign="center" p={2}>
        <Skeleton variant="rectangular" height="5rem" sx={{ my: 1 }} />
        <Skeleton variant="rectangular" height="25rem" />
      </Box>
    );
  }

  if (type in componentMap) {
    const DisplayComponent = componentMap[type];

    let dataCount = 0;
    switch (type) {
      case "category":
      case "boolean":
        dataCount = queryConceptDetailedData?.values?.length ?? 0;
        break;
      case "number_with_categories":
      case "number":
      case "age":
      case "date":
        dataCount = queryConceptDetailedData?.histogram_data?.length ?? 0;
        break;
      case "text":
        dataCount = queryConceptDetailedData?.paginated_results?.length ?? 0;
        break;
      default:
        dataCount = 1;
        break;
    }

    if (
      !queryConceptData?.concept_for_prefilter &&
      (dataCount > 0 ||
        (type == "text" &&
          (queryConceptDetailedData?.paginated_results.length ||
            queryConceptDetailedData?.searchTerm)))
    ) {
      return (
        <Box display="flex" flexDirection="column" ml={2} mr={2}>
          <Box>
            {errors.length
              ? errors.map((error) => (
                  <Alert key={error} severity="error">
                    {error}
                  </Alert>
                ))
              : null}
            {warnings.length && type != "text"
              ? warnings.map((warning) => (
                  <Alert key={warning} severity="warning">
                    {warning}
                  </Alert>
                ))
              : null}
          </Box>

          <DisplayComponent data={queryConceptDetailedData} />
        </Box>
      );
    } else if (queryConceptData?.concept_for_prefilter) {
      return <Prefilter data={queryConceptData} count={dataCount} />;
    } else {
      return (
        <Box display="flex" flexDirection="column" mt={2} textAlign="center">
          <ReportProblem
            sx={{ color: yellow[800], mx: "auto" }}
            fontSize="large"
          />
          {showDataType == "cohort" && cohortDef.length ? (
            <Box>
              <Typography variant="h5" color="GrayText">
                No data was found for this concept in your cohort.
              </Typography>
              <Typography variant="body1">
                {" "}
                You might try to turn off "Show data for active cohort only" so
                that you can see data for all subjects.
              </Typography>
            </Box>
          ) : (
            <Box>
              <Typography variant="h5" color="GrayText">
                No data was found for this concept.
              </Typography>
              <Typography variant="body1">
                {" "}
                This could mean that there is no data for this concept in the
                source system we are pulling data from, or it could indicate
                there was a problem with the data pull. If you think there
                should be data here, contact the administrator for this website.
              </Typography>
            </Box>
          )}
        </Box>
      );
    }
  }

  return (
    <Box>
      <Typography variant="h5">Could not load display for `{type}`</Typography>
    </Box>
  );
}

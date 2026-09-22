import {
  Box,
  Typography,
  Button,
  Skeleton,
  Collapse,
  List,
  useMediaQuery,
  IconButton,
} from "@mui/material";
import { styled } from "@mui/material/styles";
import { Replay, Add, ChevronLeft, ChevronRight } from "@mui/icons-material";
import Count from "./Count";
import { grey } from "@mui/material/colors";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import {
  setCurrentCohortDef,
  setCohortDef,
  clearCohortDef,
  getCriteriaSets,
  toggleCriteriaSets,
  addCriteriaSet,
  setCohortPage,
  reorderCriteriaSetEntry,
} from "../../store/cohortSlice";
import CriteriaSet from "./CriteriaSet";
import DescribeFilters from "./DescribeFilters";
import EditCriteriaSet from "./EditCriteriaSet";
import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import config from "../../config";
import { DragDropContext, DropResult } from "@hello-pangea/dnd";

const SlimButton = styled(Button)(() => ({
  minWidth: 35,
  marginRight: 6,
  padding: "0.25rem",
}));

export default function Filters({
  resultsDisplay = false,
  currentPage = "query",
}: {
  resultsDisplay: boolean;
  currentPage?: "query" | "results" | "report";
}) {
  const dispatch = useAppDispatch();
  const filters = useAppSelector((state) => state.cohort);
  const cohortPage = useAppSelector((state) => state.cohort.cohortPage);
  const dataset = useAppSelector((state) => state.auth.dataset?.unique_id);
  const datasetPermissions = useAppSelector(
    (state) => state.auth.dataset?.accessLevel
  );
  const reportDisplay = currentPage == "report";
  const panelWidth =
    useMediaQuery("(min-width: 1201px)") && currentPage != "report" ? 320 : 240;

  if (dataset && (filters.cohortState == "idle" || cohortPage != currentPage)) {
    dispatch(setCohortPage({ page: currentPage }));
    dispatch(setCurrentCohortDef({ dataset: dataset ? dataset : "" }));
  }

  function onDragEnd(result: DropResult) {
    //convenience function for matching collection entry ids
    function findCriteriaCollection(dragId: string) {
      for (let i = 0; i < filters.extended_cohort_def.length; i++) {
        const f = filters.extended_cohort_def[i];
        if (f.entry_id == dragId) {
          return {
            collectionId: f.collection_id,
            entryId: f.entry_id,
            index: i,
          };
        }
      }

      //should never reach here
      throw "No collection id found, reset filters";
    }
    // dropped outside the list
    if (!result.destination) {
      return;
    }
    //this assumes ids are formatted exactly as in the criteriaSet id `criteria-entry-list-${criteriaSet.entry_id}`
    const destinationEntryId = result.destination.droppableId.split("-")[3];
    const sourceEntryId = result.source.droppableId.split("-")[3];
    const destinationCollection = findCriteriaCollection(destinationEntryId);
    const sourceCollection = findCriteriaCollection(sourceEntryId);

    //returns if collection ids are different, dragging between not allowed
    if (sourceCollection.collectionId != destinationCollection.collectionId) {
      return;
    }
    const criteriaSet =
      filters.extended_cohort_def[destinationCollection.index];
    const newItems = criteriaSet.entries
      ? [...criteriaSet.entries.map((item) => item.entry_id)]
      : [];
    //if collection entry ids are identical, then were sorting so we remove original index
    if (sourceCollection.entryId == destinationCollection.entryId) {
      // TODO: removed [0] as it didn't seem to do anything useful - check it
      newItems.splice(result.source.index, 1);
    }
    //insert new item
    newItems.splice(result.destination.index, 0, result.draggableId);

    dispatch(
      reorderCriteriaSetEntry({
        entryIds: newItems,
        criteriaSetId: criteriaSet.entry_id,
        dataset: dataset ? dataset : "",
      })
    );
  }

  const [checked, setChecked] = useState(window.innerWidth > 1200);
  useEffect(() => {
    function handleResize() {
      setChecked(window.innerWidth > 1200);
    }

    window.addEventListener("resize", handleResize);

    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const handleChange = () => {
    setChecked((prev) => !prev);
  };
  if (datasetPermissions == "agg") {
    return null;
  }

  return (
    <Box borderLeft={1} borderColor={grey[300]}>
      <Collapse orientation="horizontal" in={checked}>
        <Box flexDirection="column" height="80vh" p={1} pb={8} display="flex">
          {!resultsDisplay ? (
            <>
              <Count />
              <Link to={`/${dataset}/results`}>
                <Button
                  variant="contained"
                  size="small"
                  color="primary"
                  fullWidth
                >
                  View Results
                </Button>
              </Link>
            </>
          ) : null}

          <Box
            width={panelWidth}
            display="flex"
            flexDirection="column"
            borderBottom={1}
            borderTop={1}
            py={2}
            borderColor={grey[300]}
            alignItems="flex-start"
            height="100vh"
            sx={{ overflowY: "auto" }}
          >
            {filters.cohortState === "loading" ? (
              <Box display="flex" flexDirection="column" width="100%">
                <Skeleton
                  variant="text"
                  width="100%"
                  sx={{ fontSize: "1.75rem" }}
                />
                <Skeleton
                  variant="text"
                  width="100%"
                  sx={{ fontSize: "1.75rem" }}
                />
                <Skeleton variant="rectangular" height={120} sx={{ my: 1 }} />
                <Skeleton variant="rectangular" height={120} sx={{ my: 1 }} />
                <Skeleton variant="rectangular" height={120} sx={{ my: 1 }} />
                <Skeleton variant="rectangular" height={120} sx={{ my: 1 }} />
              </Box>
            ) : filters.cohortState === "done" ? (
              <>
                <Box width="100%">
                  <Box
                    display="flex"
                    alignItems="center"
                    justifyContent="space-between"
                  >
                    <Typography variant="h5">Filters</Typography>
                    {resultsDisplay ? (
                      !reportDisplay ? (
                        <SlimButton
                          sx={{ marginRight: 0 }}
                          variant="outlined"
                          color="primary"
                          title="Clear Filters"
                          onClick={() =>
                            dispatch(
                              clearCohortDef({
                                dataset: dataset ? dataset : "",
                              })
                            )
                          }
                          disabled={filters?.extended_cohort_def?.length === 0}
                        >
                          Clear All
                        </SlimButton>
                      ) : null
                    ) : null}
                  </Box>
                  {!resultsDisplay ? (
                    <>
                      <SlimButton
                        variant="outlined"
                        color="primary"
                        title="Previous Snapshot"
                        onClick={() =>
                          dispatch(
                            setCohortDef({
                              dataset: dataset ? dataset : "",
                              snapshotId: filters.previous_snapshot_id,
                            })
                          )
                        }
                        disabled={!filters?.previous_snapshot_id}
                      >
                        <Replay sx={{ transform: "rotate(-50deg)" }} />
                      </SlimButton>
                      <SlimButton
                        variant="outlined"
                        color="primary"
                        title="Next Snapshot"
                        onClick={() =>
                          dispatch(
                            setCohortDef({
                              dataset: dataset ? dataset : "",
                              snapshotId: filters.next_snapshot_id,
                            })
                          )
                        }
                        disabled={!filters?.next_snapshot_id}
                      >
                        <Replay
                          sx={{ transform: "scaleX(-1) rotate(-50deg)" }}
                        />
                      </SlimButton>
                      <SlimButton
                        variant="outlined"
                        color="primary"
                        title="Clear Filters"
                        onClick={() =>
                          dispatch(
                            clearCohortDef({ dataset: dataset ? dataset : "" })
                          )
                        }
                        disabled={filters?.extended_cohort_def?.length === 0}
                      >
                        Clear All
                      </SlimButton>
                    </>
                  ) : null}
                  <DescribeFilters
                    description={filters?.describe}
                    disabled={filters?.extended_cohort_def?.length === 0}
                  />
                </Box>

                <Box width="100%">
                  <DragDropContext onDragEnd={onDragEnd}>
                    <List className={`filter-droppable`}>
                      {filters.extended_cohort_def.map((criteriaSet) => (
                        <CriteriaSet
                          key={criteriaSet.entry_id}
                          criteriaSet={criteriaSet}
                          editable={!reportDisplay}
                        />
                      ))}
                    </List>
                  </DragDropContext>
                </Box>
                <EditCriteriaSet />
              </>
            ) : (
              <Box width="100%" pt={4}>
                <Typography variant="h6" textAlign="center" color={grey[500]}>
                  No filters are set
                </Typography>
              </Box>
            )}

            <Box width="100%">
              {!reportDisplay ? (
                <Button
                  fullWidth
                  variant="outlined"
                  onClick={() => {
                    if (filters.criteriaSets?.length) {
                      dispatch(toggleCriteriaSets());
                    } else {
                      dispatch(
                        getCriteriaSets({ dataset: dataset ? dataset : "" })
                      );
                    }
                  }}
                >
                  Add Filter Set
                </Button>
              ) : null}

              {filters.showCriteriaSets
                ? filters.criteriaSets?.map((criteriaSet) => (
                    <Button
                      variant="outlined"
                      fullWidth
                      size="small"
                      startIcon={<Add />}
                      sx={{ my: 0.5, justifyContent: "space-between" }}
                      key={criteriaSet.name}
                      onClick={() =>
                        dispatch(
                          addCriteriaSet({
                            dataset: dataset ? dataset : "",
                            collection: criteriaSet.permanent_id,
                          })
                        )
                      }
                    >
                      <Box
                        sx={{ wordBreak: "break-word" }}
                        textAlign="center"
                        flexGrow={1}
                      >
                        {criteriaSet.name}
                      </Box>
                    </Button>
                  ))
                : null}
            </Box>
          </Box>
        </Box>
      </Collapse>
      {currentPage != "report" ? (
        <Box
          position="absolute"
          top={140}
          sx={{ transition: "right ease 0.3s" }}
          right={checked ? panelWidth + 12 : -10}
        >
          <IconButton
            size="small"
            title={checked ? "Hide Filter Sets" : "Show Filter Sets"}
            sx={{
              border: "1px solid",
              borderRadius: "100%",
              backgroundColor: "white",
              "&:hover": {
                backgroundColor: config.table.conceptHeaderColor,
                color:
                  config.table.conceptHeaderShade == "dark" ? "white" : "black",
              },
            }}
            onClick={handleChange}
          >
            {checked ? <ChevronRight /> : <ChevronLeft />}
          </IconButton>
        </Box>
      ) : null}
    </Box>
  );
}

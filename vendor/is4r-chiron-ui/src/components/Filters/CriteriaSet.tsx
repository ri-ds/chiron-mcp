import { grey, red } from "@mui/material/colors";
import {
  removeCriteriaSet,
  removeCriteriaSetEntry,
  type CriteriaSet,
  selectQueryConcept,
  loadConceptDisplay,
  type CriteriaSetEntry,
} from "../../store/cohortSlice";
import { Typography, Box, IconButton, List } from "@mui/material";
import { styled } from "@mui/material/styles";
import {
  CalendarMonth,
  Edit,
  Close,
  Event,
  Remove,
  DragIndicator,
} from "@mui/icons-material";
import { Interweave, Node } from "interweave";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import {
  clearEventFilters,
  enableEventFilters,
  loadCriteraSetOptions,
} from "../../store/criteriaSetSlice";
import { useNavigate } from "react-router-dom";
import config from "../../config";
type PropTypes = {
  criteriaSet: CriteriaSet;
  editable: boolean;
};
import { Droppable, Draggable } from "@hello-pangea/dnd";

const ActionButtons = styled(Box)(() => ({
  textAlign: "right",
  minWidth: 75,
}));

const ActionButtonEdit = styled(IconButton)(() => ({
  color: config.table.conceptHeaderColor[700],
  marginRight: 5,
  padding: 0,
  ":hover": {
    color: config.table.conceptHeaderColor[800],
  },
  ":last-child": {
    marginRight: 0,
  },
}));
const ActionButtonRemove = styled(IconButton)(() => ({
  backgroundColor: red[700],
  color: "white",
  padding: 0,
  marginRight: 5,
  ":hover": {
    backgroundColor: red[800],
  },
}));

export default function CriteriaSet({ criteriaSet, editable }: PropTypes) {
  const dispatch = useAppDispatch();
  const showDataType = useAppSelector((state) => state.cohort.showDataType);
  const dataset = useAppSelector((state) => state.auth.dataset?.unique_id);
  const queryConceptEditing = useAppSelector(
    (state) => state.cohort.queryConceptEditing
  );
  const queryCriteriaEditing = useAppSelector(
    (state) => state.cohort.queryConceptCriteriaEditing
  );

  function WrapperComponent({ children }: { children: React.ReactNode }) {
    return (
      <Typography
        title={children as string}
        whiteSpace={"nowrap"}
        overflow={"hidden"}
        textOverflow={"ellipsis"}
        fontWeight="bold"
        maxWidth="230px"
      >
        {children}
      </Typography>
    );
  }

  // The transform function to intercept and replace nodes
  function transformer(
    node: HTMLElement,
    children: Node[]
  ): React.ReactNode | undefined {
    // Check if the node is a <strong> tag
    if (node.tagName === "STRONG") {
      // Return your custom component with the original children inside
      return <WrapperComponent>{children}</WrapperComponent>;
    }
    // For all other tags, return undefined to use the default interweave rendering
    return undefined;
  }

  const navigate = useNavigate();
  async function handleEditConcept(entry: CriteriaSetEntry) {
    dispatch(
      selectQueryConcept({
        conceptId: entry.concept_id,
        edit: entry.entry_id,
        prefilterValue: entry.prefilter_value,
        criteriaSetId: criteriaSet.entry_id,
      })
    );
    dispatch(
      loadConceptDisplay({
        dataset: dataset ? dataset : "",
        conceptId: entry.concept_id,
        showDataType,
        entry: entry,
        prefilterValue: entry.prefilter_value,
      })
    );
  }

  const displayName = criteriaSet.alias
    ? criteriaSet.alias
    : criteriaSet.criteria_set_name;
  return (
    <Box my={2} border="1px solid" borderColor={grey[400]} borderRadius="3px">
      {displayName ? (
        <Typography
          variant="h6"
          fontSize={14}
          py="2px"
          px={1}
          fontWeight="bold"
        >
          {displayName}
        </Typography>
      ) : null}
      <Box
        bgcolor={grey[200]}
        color={grey[900]}
        padding="0.25rem"
        display="flex"
        justifyContent="space-between"
        alignItems="center"
        sx={{
          borderTopLeftRadius: displayName ? 0 : "3px",
          borderTopRightRadius: displayName ? 0 : "3px",
        }}
      >
        <Interweave content={criteriaSet.label} transform={transformer} />
        {editable ? (
          <ActionButtons>
            {!criteriaSet.is_root_collection ? (
              <ActionButtonEdit
                aria-label="edit"
                onClick={() => {
                  dispatch(
                    loadCriteraSetOptions({
                      dataset: dataset ? dataset : "",
                      type: "edit",
                      entryId: criteriaSet.entry_id,
                      collection: criteriaSet.collection_id,
                    })
                  );
                }}
              >
                <Edit fontSize="small" />
              </ActionButtonEdit>
            ) : null}
            {criteriaSet.has_event_field && !criteriaSet.event_rule_label ? (
              <ActionButtonEdit
                aria-label="event"
                onClick={() =>
                  dispatch(
                    enableEventFilters({
                      dataset: dataset ? dataset : "",
                      entryId: criteriaSet.entry_id,
                    })
                  )
                }
              >
                <Event fontSize="small" />
              </ActionButtonEdit>
            ) : null}

            <ActionButtonRemove
              aria-label="delete"
              onClick={function () {
                //have to deal with initial case after concept add, where these two are identical
                const editingId =
                  queryConceptEditing == queryCriteriaEditing
                    ? criteriaSet.entry_id
                    : queryCriteriaEditing;
                dispatch(
                  removeCriteriaSet({
                    dataset: dataset ? dataset : "",
                    entryId: criteriaSet.entry_id,
                    queryConceptCriteriaEditing: editingId,
                  })
                );
              }}
            >
              <Remove fontSize="small" />
            </ActionButtonRemove>
          </ActionButtons>
        ) : null}
      </Box>
      {criteriaSet.event_rule_label ? (
        <Box
          bgcolor={grey[300]}
          display="flex"
          justifyContent="space-between"
          alignItems="center"
          fontWeight="semibold"
          p={1}
        >
          <Box display="flex" alignItems="center">
            <CalendarMonth fontSize="medium" sx={{ pr: 1 }} />
            <Interweave content={criteriaSet.event_rule_label} />
          </Box>
          {editable ? (
            <ActionButtons>
              <ActionButtonEdit
                aria-label="event"
                onClick={() =>
                  dispatch(
                    loadCriteraSetOptions({
                      dataset: dataset ? dataset : "",
                      type: "event",
                      entryId: criteriaSet.entry_id,
                      collection: criteriaSet.collection_id,
                    })
                  )
                }
              >
                <Event fontSize="small" />
              </ActionButtonEdit>
              <ActionButtonRemove
                aria-label="delete"
                onClick={() =>
                  dispatch(
                    clearEventFilters({
                      dataset: dataset ? dataset : "",
                      entryId: criteriaSet.entry_id,
                    })
                  )
                }
              >
                <Close fontSize="small" />
              </ActionButtonRemove>
            </ActionButtons>
          ) : null}
        </Box>
      ) : null}
      <Box
        sx={{
          borderCollapse: "collapse",
          ":last-child": {
            borderBottomLeftRadius: "3px",
            borderBottomRightRadius: "3px",
          },
        }}
      >
        <Droppable droppableId={`criteria-entry-list-${criteriaSet.entry_id}`}>
          {(provided) => (
            <List
              className={`criteria-entry-list-${criteriaSet.entry_id}`}
              {...provided.droppableProps}
              ref={provided.innerRef}
            >
              {criteriaSet.entries.map((entry, idx) => (
                <Draggable
                  key={entry.entry_id}
                  draggableId={entry.entry_id}
                  index={idx}
                >
                  {(provided) => (
                    <div
                      key={idx}
                      ref={provided.innerRef}
                      {...provided.dragHandleProps}
                      {...provided.draggableProps}
                    >
                      <Box
                        key={entry.entry_id}
                        display="flex"
                        justifyContent="space-between"
                        alignItems="center"
                        py={0.5}
                        px={1}
                        border="1px solid"
                        borderColor={grey[200]}
                        sx={{
                          borderBottomLeftRadius: "3px",
                          borderBottomRightRadius: "3px",
                        }}
                      >
                        <Interweave content={entry.abbreviated_label} />
                        {editable ? (
                          <ActionButtons>
                            <ActionButtonEdit
                              aria-label="filter-edit"
                              onClick={() => {
                                handleEditConcept(entry);
                                navigate(`/${dataset}/query`);
                              }}
                            >
                              <Edit fontSize="small" />
                            </ActionButtonEdit>
                            <ActionButtonRemove
                              aria-label="filter-delete"
                              onClick={function () {
                                dispatch(
                                  removeCriteriaSetEntry({
                                    dataset: dataset ? dataset : "",
                                    entry: entry,
                                    queryEditingId: queryConceptEditing,
                                    conceptId: entry.concept_id,
                                    showDataType: showDataType,
                                  })
                                );
                              }}
                            >
                              <Remove fontSize="small" />
                            </ActionButtonRemove>
                            <ActionButtonEdit>
                              <DragIndicator fontSize="small" display="none" />
                            </ActionButtonEdit>
                          </ActionButtons>
                        ) : null}
                      </Box>
                    </div>
                  )}
                </Draggable>
              ))}
            </List>
          )}
        </Droppable>

        {criteriaSet.entries.length === 0 ? (
          <Typography
            sx={{
              py: 0.5,
              px: 1,
              border: "1px solid",
              borderColor: grey[200],
              borderRadius: "1px",
              fontStyle: "italic",
            }}
          >
            All
          </Typography>
        ) : null}
      </Box>
    </Box>
  );
}

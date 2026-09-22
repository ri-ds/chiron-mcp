import {
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  IconButton,
  List,
  Typography,
} from "@mui/material";
import Concepts from "../../Concepts";
import { styled } from "@mui/material/styles";
import { useAppDispatch, useAppSelector } from "../../../store/hooks";
import { red } from "@mui/material/colors";

import {
  DragDropContext,
  Droppable,
  Draggable,
  DropResult,
} from "@hello-pangea/dnd";

import {
  Remove as RemoveIcon,
  DragIndicator as DragIndicatorIcon,
  Edit,
} from "@mui/icons-material";
import {
  applyTransformation,
  loadColumnInformation,
  closeModal,
  loadTableDef,
} from "../../../store/tableSlice";
import config from "../../../config";

const ColumnBar = styled(Box)(() => ({
  border: "1px solid",
  borderColor: config.table.conceptHeaderColor[400],
  backgroundColor: config.table.conceptHeaderColor[50],
  padding: "0.25rem 0.25rem 0.25rem 0.75rem",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginTop: 4,
}));

export default function EditTable() {
  const columns = useAppSelector((state) => state.table.columns);
  const dataset = useAppSelector((state) => state.auth.dataset?.unique_id);
  const tableStatus = useAppSelector((state) => state.table.tableStatus);
  const openModal = useAppSelector((state) => state.table.openModal);

  const dispatch = useAppDispatch();

  function handleClose() {
    dispatch(loadTableDef({ dataset: dataset || "" }));
    dispatch(closeModal());
  }

  function onDragEnd(result: DropResult) {
    // dropped outside the list
    if (!result.destination) {
      return;
    }
    dispatch(
      applyTransformation({
        transformation: {
          type: "resort_columns",
          src: result.source.index,
          dest: result.destination.index,
        },
        dataset: dataset ? dataset : "",
        refresh: false,
      })
    );
  }
  return (
    <Dialog
      onClose={handleClose}
      open={openModal ?? false}
      maxWidth="lg"
      sx={{
        "& .MuiDialog-container": {
          "& .MuiPaper-root": {
            width: "100%",
            maxWidth: "80%",
          },
        },
      }}
    >
      <DialogContent>
        <Box display="flex" width="100%">
          <Box height="100%">
            <Concepts conceptType="table" />
          </Box>
          <Box width="100%" p={2} overflow="auto">
            <Typography variant="h6">Selected Columns</Typography>
            {tableStatus == "done" ? (
              <DragDropContext onDragEnd={onDragEnd}>
                <Droppable droppableId={`aggregate-modal_ResultsCols`}>
                  {(provided) => (
                    <List
                      className={`aggregate-modal_ResultsCols`}
                      {...provided.droppableProps}
                      ref={provided.innerRef}
                    >
                      {columns?.map((item, idx) => (
                        <Draggable
                          key={
                            item.entryId
                              ? item.entryId
                              : item.conceptId + "-" + idx
                          }
                          draggableId={
                            item.entryId
                              ? item.entryId
                              : item.conceptId + "-" + idx
                          }
                          index={idx}
                        >
                          {(provided) => (
                            <div
                              key={idx}
                              ref={provided.innerRef}
                              {...provided.dragHandleProps}
                              {...provided.draggableProps}
                            >
                              <ColumnBar>
                                <Typography>{item.name}</Typography>
                                <Box>
                                  <IconButton
                                    size="small"
                                    color="primary"
                                    onClick={() =>
                                      dispatch(
                                        loadColumnInformation({
                                          dataset: dataset || "",
                                          column: item,
                                          refresh: false,
                                        })
                                      )
                                    }
                                  >
                                    <Edit fontSize="small" />
                                  </IconButton>
                                  <IconButton
                                    size="small"
                                    sx={{
                                      bgcolor: red[600],
                                      color: "white",
                                      p: 0,
                                      ":hover": { bgcolor: red[400] },
                                    }}
                                    onClick={() =>
                                      dispatch(
                                        applyTransformation({
                                          transformation: {
                                            type: "delete_entry",
                                            entry_id: item.entryId,
                                          },
                                          dataset: dataset ? dataset : "",
                                          refresh: false,
                                        })
                                      )
                                    }
                                  >
                                    <RemoveIcon fontSize="small" />
                                  </IconButton>
                                  <IconButton size="small" color="inherit">
                                    <DragIndicatorIcon fontSize="small" />
                                  </IconButton>
                                </Box>
                              </ColumnBar>
                            </div>
                          )}
                        </Draggable>
                      ))}
                      {provided.placeholder}
                    </List>
                  )}
                </Droppable>
              </DragDropContext>
            ) : (
              <CircularProgress size={50} />
            )}
          </Box>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button
          variant="contained"
          onClick={() => {
            handleClose();
          }}
        >
          Update
        </Button>
      </DialogActions>
    </Dialog>
  );
}

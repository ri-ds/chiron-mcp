import {
  Paper,
  TableContainer,
  Table,
  TableHead,
  TableRow,
  TableCell,
  IconButton,
} from "@mui/material";
import { Add as AddIcon } from "@mui/icons-material";
import { aggItemsForEditing } from "../../store/aggregateSlice";
import { useAppDispatch } from "../../store/hooks";
import config from "../../config";

export default function EmptyAggregateTable() {
  const dispatch = useAppDispatch();
  return (
    <Paper sx={{ width: "100%", overflow: "hidden" }}>
      <TableContainer>
        <Table stickyHeader aria-label="sticky table">
          <TableHead>
            <TableRow>
              <TableCell></TableCell>
              <TableCell
                variant="head"
                sx={{
                  backgroundColor: config.table.backgroundColor,
                }}
                onClick={() => dispatch(aggItemsForEditing("Columns"))}
              >
                <IconButton>
                  <AddIcon></AddIcon>
                </IconButton>
                Add Columns
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell
                variant="head"
                sx={{
                  backgroundColor: config.table.backgroundColor,
                }}
                onClick={() => dispatch(aggItemsForEditing("Rows"))}
              >
                <IconButton>
                  <AddIcon></AddIcon>
                </IconButton>
                Add Rows
              </TableCell>
              <TableCell></TableCell>
            </TableRow>
          </TableHead>
        </Table>
      </TableContainer>
    </Paper>
  );
}

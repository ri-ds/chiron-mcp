import Button from "@mui/material/Button";
import EditIcon from "@mui/icons-material/Edit";
import AddIcon from "@mui/icons-material/Add";
import { useAppSelector } from "../store/hooks";
import { CircularProgress } from "@mui/material";

export default function QueryConceptAddOrUpdateButton() {
  const queryConceptEditing = useAppSelector(
    (state) => state.cohort.queryConceptEditing
  );
  const addingFilters = useAppSelector((state) => state.cohort.addingFilters);
  const queryConceptData = useAppSelector(
    (state) => state.cohort.queryConceptData
  );

  if (!queryConceptData) {
    return null;
  }

  return (
    <Button
      size="small"
      type="submit"
      color={"success"}
      variant="contained"
      startIcon={
        addingFilters ? (
          <CircularProgress size={16} />
        ) : queryConceptEditing ? (
          <EditIcon />
        ) : (
          <AddIcon />
        )
      }
      disabled={addingFilters}
    >
      {queryConceptEditing ? "Update" : "Apply new"} filter
    </Button>
  );
}

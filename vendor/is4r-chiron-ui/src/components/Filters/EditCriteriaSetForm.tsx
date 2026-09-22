import { Box, Button } from "@mui/material";
import {
  UpdateEventProps,
  clearCriteriaSetOptions,
  updateCriteriaSet,
} from "../../store/criteriaSetSlice";
import { Edit as EditIcon } from "@mui/icons-material";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import { FC, SyntheticEvent } from "react";

type EditCriteriaSetFormProps = {
  data: {
    formData: any;
    index: number;
    type: string;
    entryId: string;
    form: FC<{ data: any }>;
  };
};

export default function EditCriteriaSetForm({
  data,
}: EditCriteriaSetFormProps) {
  const dispatch = useAppDispatch();
  const dataset = useAppSelector((state) => state.auth.dataset?.unique_id);
  async function onSubmit(e: SyntheticEvent<HTMLFormElement>) {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);

    if (!data.entryId) {
      return;
    }

    const postData: UpdateEventProps & { [k: string]: string } = {
      entry_id: data.entryId,
    };
    for (const entry of formData.entries()) {
      postData[entry[0]] = entry[1] as string;
    }

    await dispatch(
      updateCriteriaSet({
        dataset: dataset ? dataset : "",
        transformation: postData,
      })
    );
    dispatch(clearCriteriaSetOptions());
  }

  return (
    <Box
      role="tabpanel"
      id={`tabpanel-${data.index}`}
      aria-labelledby={`tab-${data.index}`}
      minHeight={250}
    >
      <Box component="form" onSubmit={onSubmit}>
        {data.form ? <data.form data={data.formData} /> : null}
        <Box textAlign="center" mt={6}>
          <Button variant="outlined" type="submit" startIcon={<EditIcon />}>
            Update cohort definition
          </Button>
          <Button
            color="inherit"
            sx={{ ml: 2 }}
            onClick={() => dispatch(clearCriteriaSetOptions())}
          >
            Cancel
          </Button>
        </Box>
      </Box>
    </Box>
  );
}

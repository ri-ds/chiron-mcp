import { Alert, Box, Button, Typography } from "@mui/material";
import { useAppDispatch, useAppSelector } from "../../../store/hooks";
import { grey } from "@mui/material/colors";
import { ChangeEvent } from "react";
import {
  resetTransformationAlerts,
  updateConceptValues,
  verifyQueryConceptEntries,
} from "../../../store/cohortSlice";
import LightTooltip from "../../LightTooltip";
import { ChevronRight, Info } from "@mui/icons-material";

export default function FilterTextArea({
  data,
  open,
  onClose,
  handleClickOpen,
  conceptId,
  textValue,
  setTextValue,
  textOrOntology = "text",
}: {
  data: string[];
  open: boolean;
  onClose: () => void;
  handleClickOpen: () => void;
  conceptId: string;
  textValue: string;
  setTextValue: (input: string) => void;
  textOrOntology: "text" | "ontology";
}) {
  const dataset = useAppSelector((state) => state.auth.dataset?.unique_id);
  const warnings = useAppSelector(
    (state) => state.cohort.transformationWarnings
  );
  const dispatch = useAppDispatch();

  function handleTextValuesUpdate(event: ChangeEvent<HTMLTextAreaElement>) {
    setTextValue(event.currentTarget.value);
  }
  function handleRemoveInvalidEntries(warnings: string[]) {
    const valuesToRemove = warnings.map((warn) =>
      warn.slice(6, warn.indexOf("not found") - 1)
    );
    setTextValue(valuesToRemove.join("\n"));
    const newValues = textValue
      .split("\n")
      .filter((item) => {
        if (item == "") {
          return false;
        }
        return !valuesToRemove.includes(item.trim());
      })
      .concat(data);
    dispatch(updateConceptValues([...new Set(newValues)]));
  }

  return (
    <Box pt={1}>
      <Box>
        <Box display={"flex"} gap={1} pb={1}>
          <Typography fontWeight={"bold"}>Paste Data </Typography>
          <LightTooltip title="Copy/paste custom data from csv or other source">
            <Info color="primary" />
          </LightTooltip>
        </Box>
      </Box>
      <Box display={warnings.length > 0 ? "unset" : "none"}>
        <Alert key="paste warning" severity="warning">
          Remaining entries are invalid
        </Alert>
      </Box>
      <Box display={"flex"}>
        <textarea
          style={{
            height: "8.6rem",
            overflow: "auto",
            borderColor: grey[300],
            width: "100%",
            fontFamily: "inherit",
            color: !open && warnings.length > 0 ? "#e65100" : "inherit",
            fontSize: "1rem",
          }}
          onFocus={handleClickOpen}
          onChange={handleTextValuesUpdate}
          value={textValue}
        />
        <Box mt={5} ml={2} display={open ? "unset" : "none"}>
          <Button
            size="small"
            variant="outlined"
            color="primary"
            onClick={() => {
              if (textValue.length > 0) {
                const valObj =
                  textOrOntology == "text"
                    ? {
                        chiron_text_field_selection: textValue,
                      }
                    : {
                        chiron_ontology_field_selection: textValue,
                      };

                dispatch(
                  verifyQueryConceptEntries({
                    dataset: dataset ? dataset : "",
                    conceptId: conceptId,
                    values: valObj,
                  })
                )
                  .then(function (value: any) {
                    handleRemoveInvalidEntries(
                      value.payload.transformationWarnings
                    );
                  })
                  .then(() => {
                    onClose();
                  });
              } else {
                dispatch(resetTransformationAlerts());
              }
            }}
            data-testid="add-button"
          >
            <ChevronRight fontSize="large" />
          </Button>
        </Box>
      </Box>
    </Box>
  );
}

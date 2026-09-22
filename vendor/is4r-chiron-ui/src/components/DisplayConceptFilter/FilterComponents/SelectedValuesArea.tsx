import {
  Box,
  Button,
  Checkbox,
  FormControlLabel,
  Typography,
} from "@mui/material";
import { grey } from "@mui/material/colors";
import { truncate } from "lodash";
import RemoveCircleIcon from "@mui/icons-material/RemoveCircle";

export default function SelectedValuesArea({
  selected,
  handleSelectValue,
  handleClearAll,
}: {
  selected: string[];
  handleClearAll: () => void;
  handleSelectValue: (input: string) => void;
}) {
  return (
    <>
      <Box
        width="100%"
        height="27rem"
        p={1}
        mt={1}
        border="1px solid"
        borderColor={grey[300]}
        overflow={"scroll"}
      >
        {selected
          ? selected.map((selectedItem) =>
              selectedItem != "" ? (
                <FormControlLabel
                  disableTypography={true}
                  key={`right-${selectedItem}`}
                  sx={{
                    width: "100%",
                    pl: 1,
                    zIndex: 100,
                    ".MuiFormControlLabel-label": {
                      display: "block",
                      zIndex: 100,
                      color: "black",
                      width: "100%",
                      pt: ".2rem",
                      height: "1.8rem",
                    },
                  }}
                  control={
                    <Checkbox
                      sx={{
                        p: 0,
                        mx: 0.75,
                        visibility: selected.includes(selectedItem)
                          ? "visible"
                          : "hidden",
                      }}
                      checkedIcon={
                        <RemoveCircleIcon color="error" fontSize="small" />
                      }
                      onClick={() => handleSelectValue(selectedItem)}
                      checked={selected.includes(selectedItem)}
                    />
                  }
                  label={truncate(selectedItem, {
                    length: 55,
                    separator: " ",
                  })}
                />
              ) : null
            )
          : null}
      </Box>
      <Box display="flex" justifyContent="space-between" p={1}>
        <Typography>{selected.length} Selected</Typography>
        <Button onClick={handleClearAll} size="small" variant="outlined">
          Clear All
        </Button>
      </Box>
    </>
  );
}

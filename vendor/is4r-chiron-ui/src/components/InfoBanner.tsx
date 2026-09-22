import { Box } from "@mui/material";
import { red } from "@mui/material/colors";

export default function InfoBanner() {
  return (
    <Box bgcolor={red[700]} color="white" textAlign="center" p={0.5}>
      This is a <strong>DEV/TEST</strong> system, do not rely on the
      information.
    </Box>
  );
}

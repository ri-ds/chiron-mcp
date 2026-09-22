import { Box, Typography, CircularProgress } from "@mui/material";
import config from "../../config";
import { useAppSelector } from "../../store/hooks";
import { Error } from "@mui/icons-material";

export default function Count() {
  const count = useAppSelector((state) => state.cohort.count);
  const countState = useAppSelector((state) => state.cohort.countState);

  const countDisplay =
    !count || isNaN(count) ? null : Number(count).toLocaleString();

  return (
    <Box
      display="flex"
      mb={1}
      justifyContent="space-between"
      alignItems="center"
    >
      <Typography variant="h6">{config.query.countLabel}</Typography>
      {countState == "loading" || countDisplay === null ? (
        <CircularProgress size={25} />
      ) : countState == "failed" ? (
        <Error color="error" />
      ) : (
        <Typography variant="h6" fontWeight="bold" color="primary">
          {countDisplay}
        </Typography>
      )}
    </Box>
  );
}

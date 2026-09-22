import { Box, Skeleton } from "@mui/material";

export function ConceptFilterSkeleton() {
  return (
    <>
      <Box display="flex" justifyContent="space-between" py={1}>
        <Skeleton variant="rectangular" height="2rem" width="30rem" />
        <Skeleton variant="rectangular" height="2rem" width="20rem" />
      </Box>
      <Box display="flex" justifyContent="space-between" py={1}>
        <Skeleton variant="rectangular" height="3rem" width="40rem" />
      </Box>
      <Skeleton variant="rectangular" height="1.5rem" />
      <Box display="flex" justifyContent="space-between" py={1}>
        <Skeleton variant="rectangular" height="2rem" width="10rem" />
        <Skeleton variant="rectangular" height="2rem" width="10rem" />
      </Box>
      <Skeleton variant="rectangular" height="5rem" sx={{ my: 1 }} />
      <Skeleton variant="rectangular" height="25rem" />
    </>
  );
}

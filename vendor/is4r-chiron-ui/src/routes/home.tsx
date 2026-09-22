import {
  Typography,
  Box,
  Container,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
  Skeleton,
} from "@mui/material";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { useNavigate } from "react-router-dom";
import { getDatasets, resetDatasetStates } from "../store/authSlice";
import { useEffect } from "react";
import config from "../config";

export default function HomeRoute() {
  const datasets = useAppSelector((state) => state.auth.datasets);
  const datasetId = useAppSelector((state) => state.auth.dataset?.id);
  const authState = useAppSelector((state) => state.auth.authStatus);
  const dispatch = useAppDispatch();
  const navigate = useNavigate();

  if (!datasets && authState != "loading" && authState != "failed") {
    dispatch(getDatasets());
  }

  useEffect(() => {
    if (datasets?.length == 1) {
      // since there is only one, navigate directly to the dataset

      dispatch(resetDatasetStates());
      navigate(`/dataset/${datasets[0].unique_id}`);
    }
  }, [datasets, dispatch, navigate]);

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        minHeight: "100vh",
        pb: 10,
      }}
    >
      {authState == "loading" ? (
        <Container sx={{ mt: 8, mb: 2 }} maxWidth="lg">
          <Skeleton variant="rounded" width={650} height={200} />
        </Container>
      ) : datasets != undefined ? (
        <Container sx={{ mt: 8, mb: 2 }}>
          <Typography
            variant="h4"
            sx={{
              fontWeight: "bold",
            }}
            gutterBottom
          >
            Select a Dataset
          </Typography>

          <TableContainer component={Paper}>
            <Table sx={{ minWidth: 650 }} aria-label="simple table">
              <TableHead>
                <TableRow
                  sx={{
                    backgroundColor: config.table.backgroundColor,
                  }}
                >
                  <TableCell key="name">Dataset Name</TableCell>
                  <TableCell align="right">Description</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {datasets.map((row) => (
                  <TableRow
                    key={row.name}
                    sx={{ "&:last-child td, &:last-child th": { border: 0 } }}
                  >
                    <TableCell component="th" scope="row">
                      {row.name}
                    </TableCell>
                    <TableCell align="right">{row.description}</TableCell>

                    <TableCell align="right">
                      {row.selectable || row.selectable == undefined ? (
                        <Button
                          onClick={function () {
                            if (row.id != datasetId) {
                              dispatch(resetDatasetStates());
                            }
                            navigate(`/dataset/${row.unique_id}`);
                          }}
                          data-field="dataset-button"
                        >
                          View Dataset
                        </Button>
                      ) : row.contactEmail ? (
                        <Button
                          color="secondary"
                          component="a"
                          href={`mailto:${row.contactEmail}?subject=${row.name} permission request&body=Hi, I would like to request permission to the Chiron ${row.name} dataset.`}
                        >
                          Request permission
                        </Button>
                      ) : (
                        <Button disabled>You do not have access</Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Container>
      ) : (
        <Container>
          <Typography variant="h4">Please Log in</Typography>
        </Container>
      )}
    </Box>
  );
}

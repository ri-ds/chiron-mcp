import {
  Typography,
  Box,
  Container,
  Card,
  CardContent,
  CardHeader,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableRow,
  Skeleton,
  Button,
} from "@mui/material";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import config from "../config";
import { setCurrentDataset } from "../store/authSlice";
import { NavLink, useParams } from "react-router-dom";
import { ArrowBack } from "@mui/icons-material";

export default function DatasetHomeRoute() {
  const dispatch = useAppDispatch();
  const dataset = useAppSelector((state) => state.auth.dataset);
  const authStatus = useAppSelector((state) => state.auth.authStatus);
  const dataset_param = useParams();
  const numDatasets =
    useAppSelector((state) => state.auth.datasets?.length) || 0;
  const authState = useAppSelector((state) => state.auth.authStatus);

  if (!dataset && authState != "loading" && authState != "failed") {
    dispatch(
      setCurrentDataset({
        dataset: dataset_param.dataset_id ? dataset_param.dataset_id : "",
      })
    );
  }

  const summaryKeys = {
    lastImport: "Date of last import",
    subjectCount: "Total subjects in system",
    accessLevelLabel: "Your Access Level",
  };

  // if the home page is set override it here
  if (config.routes.homepage) {
    return config.routes.homepage;
  }

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        minHeight: "100vh",
      }}
    >
      {authStatus == "loading" ? (
        <Container sx={{ mt: 8, mb: 2 }} maxWidth="lg">
          <Skeleton variant="rounded" height={300} />
        </Container>
      ) : dataset != undefined ? (
        <Container sx={{ mt: 8, mb: 2 }} maxWidth="lg">
          <Box>
            <Typography>Active Dataset</Typography>
            <Typography
              variant="h4"
              sx={{
                fontWeight: "bold",
              }}
              gutterBottom
            >
              {dataset.name}
            </Typography>
            <Typography>{dataset.description}</Typography>
            <Grid container alignItems="flex-end" pt={3} minHeight={300}>
              <Grid key={"extools"} size="grow">
                <Card>
                  <CardHeader
                    title="Data Summary"
                    subheader={`Statistics for ${dataset.name}`}
                    sx={{
                      backgroundColor: config.table.backgroundColor,
                    }}
                  />
                  <CardContent>
                    <Table size="small">
                      <TableBody>
                        {Object.keys(summaryKeys).map((k) => {
                          return (
                            <TableRow key={k}>
                              <TableCell
                                key="date"
                                sx={{
                                  fontWeight: "bold",
                                  color: config.table.textColor,
                                }}
                              >
                                {summaryKeys[k as keyof typeof summaryKeys]}
                              </TableCell>
                              <TableCell>
                                {dataset[k as keyof typeof summaryKeys]}
                              </TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>
                {numDatasets > 1 && (
                  <Grid pt={4}>
                    <NavLink to="/" reloadDocument>
                      <Button>
                        <ArrowBack />
                        <Typography pl={"5px"}>
                          Select a different dataset
                        </Typography>
                      </Button>
                    </NavLink>
                  </Grid>
                )}
              </Grid>
            </Grid>
          </Box>
        </Container>
      ) : null}
    </Box>
  );
}

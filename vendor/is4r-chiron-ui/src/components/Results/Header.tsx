import {
  Replay as ReplayIcon,
  ViewColumn as ViewColumnIcon,
  Download as DownloadIcon,
  Save as SaveIcon,
  Error as ErrorIcon,
} from "@mui/icons-material";
import GroupIcon from "@mui/icons-material/Group";
import EditNoteIcon from "@mui/icons-material/EditNote";
import {
  Box,
  Button,
  CircularProgress,
  LinearProgress,
  Menu,
  Typography,
} from "@mui/material";
import { styled } from "@mui/material/styles";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import MenuIcon from "@mui/icons-material/Menu";
import {
  applyTransformation,
  downloadCsvFile,
  resetTableStatus,
  openModal,
} from "../../store/tableSlice";
import {
  createReport,
  loadReportToResults,
  resetReportData,
  shareReport,
  toggleShareDialog,
} from "../../store/reportSlice";
import config from "../../config";
import React from "react";
import { MenuButton as MenuButtonType } from "../../store/tableSliceTypes";
const MenuButton = styled(Button)(() => ({
  width: 80,
  display: "flex",

  flexDirection: "column",
}));
const MenuButtonText = styled(Typography)(() => ({
  textTransform: "none",
  fontWeight: "bold",
  fontSize: "0.75rem",
}));

export default function ResultsHeader({
  currentViewPage = "results",
  reportId,
}: {
  currentViewPage: "report" | "results";
  reportId?: number;
}) {
  const tableStatus = useAppSelector((state) =>
    currentViewPage == "results"
      ? state.table.tableStatus
      : state.report.reportTableStatus
  );
  const tableErrors = useAppSelector((state) =>
    currentViewPage == "results" ? state.table.errors : state.report.errors
  );
  const [anchorElRes, setAnchorElRes] = React.useState<null | HTMLElement>(
    null
  );
  const [csvLoading, setCsvLoading] = React.useState(false);
  const handleOpenResMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorElRes(event.currentTarget);
  };
  const handleCloseResMenu = () => {
    setAnchorElRes(null);
  };
  const showEditTable = currentViewPage == "report" ? false : true;
  const records = useAppSelector((state) => state.table.recordCount);
  const subjects = useAppSelector((state) => state.table.subjectCount);
  const cohortDef = useAppSelector((state) => state.cohort.extended_cohort_def);
  const tableDef = useAppSelector((state) => state.table.tableDef);
  const dataset = useAppSelector((state) => state.auth.dataset?.unique_id);
  const canViewWorkspace = useAppSelector(
    (state) => state.auth.dataset?.canViewWorkspace
  );
  const dispatch = useAppDispatch();
  const tableErrorMsg = useAppSelector((state) => state.table.errors);

  const menuButtons: MenuButtonType[] = [];
  if (tableErrors.length > 0) {
    if (showEditTable) {
      menuButtons.push({
        label: "Reset Columns",
        icon: (
          <ReplayIcon fontSize="medium" sx={{ transform: "rotate(-50deg)" }} />
        ),
        onClick: () => {
          handleCloseResMenu();
          dispatch(
            applyTransformation({
              dataset: dataset ? dataset : "",
              transformation: {
                type: "resort_columns",
                entry_ids: [],
              },
              refresh: true,
            })
          );
        },
      });
    }
  } else if (showEditTable) {
    menuButtons.push({
      label: "Reset Columns",
      icon: (
        <ReplayIcon fontSize="medium" sx={{ transform: "rotate(-50deg)" }} />
      ),
      onClick: () => {
        handleCloseResMenu();
        dispatch(
          applyTransformation({
            dataset: dataset ? dataset : "",
            transformation: {
              type: "resort_columns",
              entry_ids: [],
            },
            refresh: true,
          })
        );
      },
    });
    menuButtons.push({
      label: "Edit Columns",
      icon: <ViewColumnIcon fontSize="medium" />,
      onClick: () => {
        handleCloseResMenu();
        dispatch(openModal());
      },
    });
    menuButtons.push({
      label: "Save Query",
      icon: <SaveIcon fontSize="medium" />,
      onClick: function () {
        handleCloseResMenu();
        dispatch(resetReportData());
        dispatch(createReport({ dataset: dataset ? dataset : "" }));
        dispatch(toggleShareDialog());
      },
    });
  } else {
    menuButtons.push({
      label: "Share",
      icon: <GroupIcon fontSize="medium" />,
      onClick: async function () {
        handleCloseResMenu();
        await dispatch(
          shareReport({ dataset: dataset ? dataset : "", reportId: reportId })
        );
        dispatch(toggleShareDialog());
      },
    });
    if (canViewWorkspace)
      menuButtons.push({
        label: "Load Into Workspace",
        icon: <EditNoteIcon fontSize="medium" />,
        onClick: async function () {
          handleCloseResMenu();
          await dispatch(
            loadReportToResults({
              dataset: dataset ? dataset : "",
              reportId: reportId,
            })
          );
          dispatch(resetTableStatus());
          window.location.href = `/${dataset}/results/`;
        },
      });
  }
  if (tableErrors.length == 0) {
    menuButtons.push({
      label: "Download CSV",
      icon: (
        <>
          {csvLoading ? (
            <CircularProgress></CircularProgress>
          ) : (
            <DownloadIcon fontSize="medium" />
          )}
        </>
      ),
      onClick: () => {
        handleCloseResMenu();
        setCsvLoading(true);
        dispatch(
          downloadCsvFile({
            dataset: dataset ? dataset : "",
            cohort_def: cohortDef,
            table_def: tableDef,
            report_id: reportId,
          })
        )
          .unwrap()
          .catch(() => {
            alert(
              "Download Error: The CSV download has timed out after one minute. " +
                "Please try again. " +
                "If the issue persists, use the Save Query feature and then click Help to report the issue. " +
                "Please include the name of the query you were trying to run. " +
                "Our support team can help diagnose the issue and provide query recommendations."
            );
          })
          .finally(() => setCsvLoading(false));
      },
    });
  }

  return (
    <>
      <Box
        bgcolor={config.table.backgroundColor}
        px={2}
        display="flex"
        justifyContent="space-between"
        alignItems="center"
      >
        {!dataset ? null : tableStatus == "failed" &&
          tableErrorMsg.length > 0 ? (
          <Box display="flex" alignItems="center" gap={1}>
            <ErrorIcon color="error" />{" "}
            <Typography variant="h5" color="error">
              {tableErrorMsg[0]}
            </Typography>
          </Box>
        ) : tableStatus == "loading" ? (
          <Typography variant="h5">Loading...</Typography>
        ) : (
          <>
            <Typography variant="h5">
              <strong>{records?.toLocaleString()}</strong> record(s) for{" "}
              <strong>{subjects?.toLocaleString()}</strong> subject(s)
            </Typography>
            <Box sx={{ display: { xs: "flex", md: "none" } }}>
              <MenuButton
                size="large"
                aria-label="results table edit choices"
                aria-controls="menu-appbar"
                aria-haspopup="true"
                onClick={handleOpenResMenu}
              >
                <MenuIcon />
              </MenuButton>
              <Menu
                id="menu-appbar"
                anchorEl={anchorElRes}
                anchorOrigin={{
                  vertical: "bottom",
                  horizontal: "left",
                }}
                keepMounted
                transformOrigin={{
                  vertical: "top",
                  horizontal: "left",
                }}
                open={Boolean(anchorElRes)}
                onClose={handleCloseResMenu}
                sx={{
                  display: { xs: "block", md: "none" },
                }}
              >
                {menuButtons.map((mb, i) => {
                  return (
                    <MenuButton
                      onClick={mb.onClick}
                      key={`result-header-menu-${i}`}
                    >
                      {mb.icon}
                      <MenuButtonText>{mb.label}</MenuButtonText>
                    </MenuButton>
                  );
                })}
              </Menu>
            </Box>

            <Box
              sx={{ display: { xs: "none", md: "flex" } }}
              gap={2}
              alignItems="center"
            >
              {menuButtons.map((mb, i) => {
                return (
                  <MenuButton onClick={mb.onClick} key={`result-header-${i}`}>
                    {mb.icon}
                    <MenuButtonText>{mb.label}</MenuButtonText>
                  </MenuButton>
                );
              })}
            </Box>
          </>
        )}
        {tableStatus === "loading" || tableStatus === "failed" ? (
          <Box>
            <MenuButton sx={{ visibility: "hidden" }}>
              <ReplayIcon
                fontSize="medium"
                sx={{ transform: "rotate(-50deg)" }}
              />{" "}
              <MenuButtonText>keep same</MenuButtonText>
            </MenuButton>
          </Box>
        ) : null}
      </Box>
      {tableStatus === "loading" ? <LinearProgress /> : <Box height={4}></Box>}
    </>
  );
}

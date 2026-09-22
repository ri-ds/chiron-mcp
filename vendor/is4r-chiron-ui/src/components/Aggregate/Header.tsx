import {
  Replay as ReplayIcon,
  ViewColumn as ViewColumnIcon,
  Download as DownloadIcon,
  Error as ErrorIcon,
  TableRows as TableRowsIcon,
  SwapHoriz as SwapHorizIcon,
  Backspace as BackSpaceIcon,
} from "@mui/icons-material";
import MenuIcon from "@mui/icons-material/Menu";
import { Box, Button, LinearProgress, Menu, Typography } from "@mui/material";
import { styled } from "@mui/material/styles";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import config from "../../config";
import { MenuButton as MenuButtonType } from "../../store/tableSliceTypes";

import {
  applyTransformation,
  downloadCsvFile,
  aggItemsForEditing,
} from "../../store/aggregateSlice";
import React from "react";

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

export default function AggregateHeader() {
  const [anchorElAgg, setAnchorElAgg] = React.useState<null | HTMLElement>(
    null
  );
  const handleOpenAggMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorElAgg(event.currentTarget);
  };
  const handleCloseAggMenu = () => {
    setAnchorElAgg(null);
  };
  const aggStatus = useAppSelector((state) => state.aggregate.aggStatus);
  const dataset = useAppSelector((state) => state.auth.dataset?.unique_id);
  const columns = useAppSelector((state) => state.aggregate.columns);
  const rows = useAppSelector((state) => state.aggregate.rows);
  const aggErrorMsg = useAppSelector((state) => state.aggregate.errors);
  const dispatch = useAppDispatch();

  const menuButtons: MenuButtonType[] = [
    {
      label: "Edit Columns",
      icon: <ViewColumnIcon fontSize="medium" />,
      onClick: () => {
        handleCloseAggMenu();
        dispatch(aggItemsForEditing("Columns"));
      },
    },
    {
      label: "Edit Rows",
      icon: <TableRowsIcon fontSize="medium" />,
      onClick: () => {
        handleCloseAggMenu();
        dispatch(aggItemsForEditing("Rows"));
      },
    },
    {
      label: "Swap Rows & Columns",
      icon: <SwapHorizIcon fontSize="medium" />,
      dataField: "swap-cols-button",
      onClick: () => {
        handleCloseAggMenu();
        dispatch(
          applyTransformation({
            dataset: dataset ? dataset : "",
            transformation: { type: "swap_rows_and_cols" },
          })
        );
      },
    },
    {
      label: "Clear All",
      icon: <BackSpaceIcon fontSize="medium" />,
      onClick: () => {
        handleCloseAggMenu();
        dispatch(
          applyTransformation({
            dataset: dataset ? dataset : "",
            transformation: { type: "clear_all" },
          })
        );
      },
    },
    {
      label: "Download CSV",
      icon: <DownloadIcon fontSize="medium" />,
      onClick: () => {
        handleCloseAggMenu();
        dispatch(downloadCsvFile({ dataset: dataset ? dataset : "" }));
      },
      dataField: "download-csv-button",
      disabled: columns.length == 0 && rows.length == 0 ? true : false,
    },
  ];

  return (
    <>
      <Box
        bgcolor={config.table.backgroundColor}
        px={2}
        display="flex"
        justifyContent="space-between"
        alignItems="center"
      >
        {aggStatus == "failed" ? (
          <Box display="flex" alignItems="center" gap={1}>
            <ErrorIcon color="error" />{" "}
            <Typography variant="h5" color="error">
              {aggErrorMsg[0]}
            </Typography>
            <Box display="flex" gap={2} alignItems="center">
              <MenuButton
                onClick={() => {
                  dispatch(
                    applyTransformation({
                      dataset: dataset ? dataset : "",
                      transformation: { type: "clear_all" },
                    })
                  );
                }}
              >
                <BackSpaceIcon fontSize="medium" />
                <MenuButtonText>Clear All</MenuButtonText>
              </MenuButton>
            </Box>
          </Box>
        ) : aggStatus == "loading" || aggStatus == "idle" ? (
          <Typography variant="h5">Loading...</Typography>
        ) : (
          <>
            <Typography variant="h5">
              <strong>Aggregate Data View</strong>
            </Typography>
            <Box sx={{ display: { xs: "flex", md: "none" } }}>
              <MenuButton
                size="large"
                aria-label="Open the aggregate edit options"
                aria-controls="menu-appbar"
                aria-haspopup="true"
                onClick={handleOpenAggMenu}
              >
                <MenuIcon />
              </MenuButton>
              <Menu
                id="menu-appbar"
                anchorEl={anchorElAgg}
                anchorOrigin={{
                  vertical: "bottom",
                  horizontal: "left",
                }}
                keepMounted
                transformOrigin={{
                  vertical: "top",
                  horizontal: "left",
                }}
                open={Boolean(anchorElAgg)}
                onClose={handleCloseAggMenu}
                sx={{
                  display: { xs: "block", md: "none" },
                }}
              >
                {menuButtons.map((mb, i) => {
                  return (
                    <MenuButton
                      onClick={mb.onClick}
                      data-field={mb.dataField}
                      disabled={mb.disabled}
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
                  <MenuButton
                    onClick={mb.onClick}
                    key={`result-header-${i}`}
                    data-field={mb.dataField}
                    disabled={mb.disabled}
                  >
                    {mb.icon}
                    <MenuButtonText>{mb.label}</MenuButtonText>
                  </MenuButton>
                );
              })}
            </Box>
          </>
        )}
        {aggStatus === "loading" || aggStatus === "idle" ? (
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
      {aggStatus === "loading" ? <LinearProgress /> : <Box height={4}></Box>}
    </>
  );
}

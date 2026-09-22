import * as React from "react";
import {
  Logout as LogoutIcon,
  Login as LoginIcon,
  ArrowDropDown as ArrowDropDown,
  AccountCircle as AccountCircleIcon,
  Info as InfoIcon,
} from "@mui/icons-material";
import {
  AppBar,
  Toolbar,
  Box,
  Button,
  Menu,
  MenuItem,
  Divider,
  IconButton,
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import { darken, styled } from "@mui/material/styles";
import config from "../config";
import { NavLink as routerNavLink } from "react-router-dom";
import { useAppSelector } from "../store/hooks";
import { AuthDatasetType } from "../store/authSlice";

export type NavItem = {
  label: string;
  link: string;
  icon?: React.ReactNode;
};

// The reused element and css for header links
const NavLink = styled(routerNavLink)(() => ({
  color: "inherit",
  display: "flex",
  textDecoration: "none",
}));
const FullWidthMenuItem = styled(MenuItem)(() => ({
  width: "100%",
}));
const StyledMenu = styled(Menu)(() => ({
  ".MuiList-root": {
    padding: 0,
  },
}));

export default function Header() {
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const [anchorElMenu, setAnchorElMenu] = React.useState<null | HTMLElement>(
    null
  );
  const user = useAppSelector((state) => state.auth.user);
  const dataset = useAppSelector((state) => state.auth.dataset);
  const siteTitle = useAppSelector(
    (state) => state.auth.dataset?.siteTitle ?? "Chiron"
  );
  const numDatasets =
    useAppSelector((state) => state.auth.datasets?.length) || 0;

  const handleOpenNavMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorElMenu(event.currentTarget);
  };
  const handleCloseMenu = () => {
    setAnchorElMenu(null);
  };

  const handleMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  function headerLinkPermissions(ds: AuthDatasetType, item: NavItem) {
    if (
      ds.accessLevel == "agg" &&
      ["/results", "/reports", "/query"].includes(item.link)
    ) {
      return false;
    }
    if (
      !ds.canViewWorkspace &&
      ["/results", "/query", "/aggregate"].includes(item.link)
    ) {
      return false;
    }
    return true;
  }

  const headerLink = dataset?.unique_id
    ? "/dataset/" + dataset?.unique_id
    : "/";

  return (
    <AppBar position="static" elevation={0}>
      <Toolbar
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          color: config.header.textColor,
          bgcolor: config.header.backgroundColor,
          borderBottom: "2px solid",
          borderBottomColor: darken(config.header.backgroundColor, 0.1),
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center" }}>
          <NavLink to={headerLink} sx={{ ml: 2, mr: 4 }} title={siteTitle}>
            {dataset?.logoUrl ? (
              <img
                src={dataset?.logoUrl}
                alt={`${dataset?.name} logo`}
                height={40}
              />
            ) : config.header.logo ? (
              <img src={config.header.logo} alt={siteTitle} height={40} />
            ) : (
              siteTitle
            )}
          </NavLink>
          {dataset != undefined ? (
            <NavLink
              sx={{
                display: { xs: "none", md: "flex", ml: 2, mr: 4 },
                fontSize: config.header.titleFontSize,
              }}
              to={`/dataset/${dataset?.unique_id}`}
              title={dataset?.name}
            >
              {dataset?.name}
            </NavLink>
          ) : null}
        </Box>
        {user && dataset ? (
          <Box sx={{ flexGrow: 1, display: { xs: "flex", md: "none" } }}>
            <IconButton
              size="large"
              aria-label="account of current user"
              aria-controls="menu-appbar"
              aria-haspopup="true"
              onClick={handleOpenNavMenu}
              color="inherit"
            >
              <MenuIcon />
            </IconButton>
            <StyledMenu
              id="menu-appbar"
              anchorEl={anchorElMenu}
              anchorOrigin={{
                vertical: "bottom",
                horizontal: "left",
              }}
              keepMounted
              transformOrigin={{
                vertical: "top",
                horizontal: "left",
              }}
              open={Boolean(anchorElMenu)}
              onClose={handleCloseMenu}
              MenuListProps={{ sx: { paddingTop: 0 } }}
              sx={{
                display: { xs: "block", md: "none" },
              }}
            >
              {config.header.nav.map((item: NavItem) => {
                if (headerLinkPermissions(dataset, item)) {
                  return (
                    <NavLink
                      key={item.link}
                      to={
                        item.link != `/dataset`
                          ? `${dataset?.unique_id}${item.link}/`
                          : `/dataset/${dataset?.unique_id}`
                      }
                    >
                      <Button
                        fullWidth
                        disableRipple
                        startIcon={item.icon}
                        sx={{ color: "inherit", mx: "auto" }}
                        disableElevation
                      >
                        {item.label}
                      </Button>
                    </NavLink>
                  );
                }
                return null;
              })}
              {dataset?.extraHeaderLinks &&
                Object.entries(dataset?.extraHeaderLinks).map(
                  ([key, value]) => {
                    return (
                      <NavLink key={key} to={value}>
                        <Button
                          fullWidth
                          disableRipple
                          startIcon={<InfoIcon />}
                          sx={{ color: "inherit", mx: "auto" }}
                          disableElevation
                        >
                          {key}
                        </Button>
                      </NavLink>
                    );
                  }
                )}
            </StyledMenu>
          </Box>
        ) : null}
        <Box
          sx={{
            alignItems: "center",
            justifyContent: "center",
            display: { xs: "none", md: "flex" },
          }}
        >
          {user &&
            dataset &&
            config.header.nav.map((item: NavItem) => {
              if (headerLinkPermissions(dataset, item)) {
                return (
                  <NavLink
                    key={item.link}
                    to={
                      item.link != `/dataset`
                        ? `${dataset?.unique_id}${item.link}/`
                        : `/dataset/${dataset?.unique_id}`
                    }
                  >
                    {({ isActive }) => (
                      <Button
                        disableRipple
                        sx={{
                          color: "inherit",
                          textDecoration: isActive ? "underline" : "",
                          mx: "auto",
                        }}
                        disableElevation
                        startIcon={item.icon}
                      >
                        {item.label}
                      </Button>
                    )}
                  </NavLink>
                );
              }
              return null;
            })}
          {dataset?.extraHeaderLinks &&
            Object.entries(dataset?.extraHeaderLinks).map(([key, value]) => {
              return (
                <NavLink key={key} to={value}>
                  <Button
                    disableRipple
                    startIcon={<InfoIcon />}
                    sx={{ color: "inherit", mx: "auto" }}
                    disableElevation
                  >
                    {key}
                  </Button>
                </NavLink>
              );
            })}
        </Box>
        <Box sx={{ display: "flex", alignItems: "center" }}>
          {config.header.rightNav.map((item: NavItem) => (
            <NavLink key={item.link} to={item.link}>
              <Button
                disableRipple
                color="inherit"
                sx={{ mx: 0.5 }}
                startIcon={item.icon}
              >
                {item.label}
              </Button>
            </NavLink>
          ))}
          {user ? (
            <div>
              <Button
                aria-label="auth menu"
                aria-controls="menu-appbar"
                aria-haspopup="true"
                startIcon={<AccountCircleIcon />}
                disableRipple
                onClick={handleMenu}
                color="inherit"
              >
                {user.name} <ArrowDropDown />
              </Button>
              <StyledMenu
                id="menu-appbar"
                anchorEl={anchorEl}
                anchorOrigin={{
                  vertical: 50,
                  horizontal: "right",
                }}
                keepMounted
                transformOrigin={{
                  vertical: "top",
                  horizontal: "right",
                }}
                sx={{ pt: 0 }}
                open={Boolean(anchorEl)}
                onClose={handleClose}
              >
                {config.header.userNav.map((item: NavItem) => (
                  <NavLink to={item.link}>
                    <FullWidthMenuItem key={item.link} onClick={handleClose}>
                      {item.icon} <Box sx={{ ml: 1 }}>{item.label}</Box>
                    </FullWidthMenuItem>
                  </NavLink>
                ))}
                {/* select dataset button */}
                {numDatasets > 1 && (
                  <NavLink to="/" reloadDocument>
                    <FullWidthMenuItem>Switch Dataset</FullWidthMenuItem>
                  </NavLink>
                )}
                {user.isStaff && (
                  <div>
                    <Divider />
                    <NavLink
                      to={`${config.apiBaseUrl}${config.header.adminLink}`}
                      reloadDocument={true}
                    >
                      <FullWidthMenuItem>Django Admin</FullWidthMenuItem>
                    </NavLink>

                    <NavLink
                      to={`${config.apiBaseUrl}/backend/etl_logs`}
                      reloadDocument={true}
                    >
                      <FullWidthMenuItem>ETL Logs</FullWidthMenuItem>
                    </NavLink>
                    <NavLink
                      to={`${config.apiBaseUrl}/backend/query_troubleshooting`}
                      reloadDocument={true}
                    >
                      <FullWidthMenuItem>
                        Query Troubleshooting
                      </FullWidthMenuItem>
                    </NavLink>
                    <NavLink
                      to={`${config.apiBaseUrl}/backend/user_report`}
                      reloadDocument={true}
                    >
                      <FullWidthMenuItem>User Report</FullWidthMenuItem>
                    </NavLink>
                  </div>
                )}
                <Divider />

                <FullWidthMenuItem
                  onClick={() => {
                    window.location.href = config.header.logoutLink;
                  }}
                >
                  <LogoutIcon />
                  <Box sx={{ ml: 1 }}>Logout</Box>
                </FullWidthMenuItem>
              </StyledMenu>
            </div>
          ) : (
            <div>
              <a style={{ color: "black" }} href={config.header.loginLink}>
                <Button
                  disableRipple
                  color="inherit"
                  sx={{ mx: 0.5 }}
                  startIcon={<LoginIcon />}
                >
                  <Box sx={{ ml: 1 }}>Login</Box>
                </Button>
              </a>
            </div>
          )}
        </Box>
      </Toolbar>
    </AppBar>
  );
}

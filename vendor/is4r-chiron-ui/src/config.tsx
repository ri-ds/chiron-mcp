import { deepMerge } from "./lib/utils";
import { grey, purple, teal, green } from "@mui/material/colors";
import theme from "./theme";
import {
  Home as HomeIcon,
  Search as SearchIcon,
  TableChart as TableChartIcon,
  FileCopy as FileCopyIcon,
  Addchart as AddChartIcon,
} from "@mui/icons-material";
import type { NavItem } from "./components/Header";
import type { NonIndexRouteObject } from "react-router-dom";
import { createTheme, type Theme } from "@mui/material/styles";

// update this file for overriding configs
import { overrideConfig } from "./overrideConfig";

export type HeaderConfig = {
  backgroundColor: string;
  textColor: string;
  logo?: React.ReactNode;
  logoutLink: string;
  loginLink: string;
  adminLink: string;
  nav: NavItem[];
  rightNav?: NavItem[];
  userNav?: NavItem[];
  titleFontSize: string;
};

export type TableConfig = {
  backgroundColor: string;
  secondaryColor: string;
  textColor: string;
  aggHeaderColor: { [key: number]: string };
  conceptHeaderColor: string;
  conceptHeaderShade: "dark" | "light";
  secondaryHeaderColor: { [key: number]: string };
  aggregateRowHeight?: number;
};
export type FooterConfig = {
  backgroundColor: string;
  textColor: string;
  leftContent?: React.ReactNode;
  middleContent?: React.ReactNode;
  rightContent?: React.ReactNode;
  paddingForContent: number;
};

export type RoutesConfig = {
  homepage: React.ReactNode;
  more: NonIndexRouteObject[];
  datasetMore: NonIndexRouteObject[];
};

export type QueryPageConfig = {
  countLabel: string;
};

export type AppConfig = {
  theme: Theme;
  apiBaseUrl: string;
  routes: RoutesConfig;
  table: TableConfig;
  header: HeaderConfig;
  footer: FooterConfig;
  query: QueryPageConfig;
  idleTimeOut: number;
};

/* tslint:disable-next-line allow for incomplete object for themes */
let finalThemeConfig = deepMerge({}, theme);
if ("theme" in overrideConfig) {
  finalThemeConfig = deepMerge({}, theme, overrideConfig.theme);
}
export const finalTheme = createTheme(finalThemeConfig);

const defaultConfig: AppConfig = {
  theme: finalTheme,
  // only matters in dev or when the API is not served on the same domain
  apiBaseUrl: "",
  routes: {
    homepage: null,
    more: [],
    // these will be prepended with the dataset id
    datasetMore: [],
  },
  table: {
    backgroundColor: teal[50],
    secondaryColor: green[300],
    textColor: grey[600],
    aggHeaderColor: teal,
    conceptHeaderColor: teal[700],
    conceptHeaderShade: "dark",
    secondaryHeaderColor: green,
    aggregateRowHeight: 30,
  },
  header: {
    backgroundColor: grey[100],
    textColor: purple[900],
    logo: "/vite.svg",
    logoutLink: "/sso/?logout",
    loginLink: "/login/",
    adminLink: "/admin/",
    nav: [
      { label: "Dataset Home", link: "/dataset", icon: <HomeIcon /> },
      { label: "Query", link: "/query", icon: <SearchIcon /> },
      { label: "Results", link: "/results", icon: <TableChartIcon /> },
      { label: "Reports", link: "/reports", icon: <FileCopyIcon /> },
      { label: "Aggregate", link: "/aggregate", icon: <AddChartIcon /> },
    ],
    rightNav: [],
    userNav: [],
    titleFontSize: "1.5rem",
  },
  query: {
    countLabel: "Subject Count",
  },
  footer: {
    backgroundColor: grey[100],
    textColor: teal[900],
    leftContent: undefined,
    middleContent: undefined,
    rightContent: undefined,
    paddingForContent: 5,
  },
  //1 hour idle timeout
  idleTimeOut: 1000 * (60 * 60), //number of milliseconds of inactivity before navigate to logout url
};

// Combine the overrides with the defaults
const finalConfig = deepMerge({}, defaultConfig, overrideConfig);
export default finalConfig;

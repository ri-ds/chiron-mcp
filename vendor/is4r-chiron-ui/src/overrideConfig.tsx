// For local development, uncomment the apiBaseUrl setting

import {
  Home as HomeIcon,
  Search as SearchIcon,
  TableChart as TableChartIcon,
  FileCopy as FileCopyIcon,
  Addchart as AddChartIcon,
  QuestionAnswer as AskIcon,
} from "@mui/icons-material";
import { useParams } from "react-router-dom";

// Where the "Ask Chiron" server is running (python -m chiron_mcp.webapp).
const ASK_URL = "http://localhost:8900";

/**
 * Natural-language question box for the current dataset.
 *
 * Rendered as an iframe so the chat, its markdown rendering and its charts live in
 * the Ask Chiron server, and this file stays a small mergeable override rather than
 * a fork of the UI.
 */
function AskRoute() {
  const { dataset_id } = useParams();
  return (
    <iframe
      title="Ask Chiron"
      src={`${ASK_URL}/?dataset=${encodeURIComponent(dataset_id ?? "")}`}
      style={{
        width: "100%",
        height: "calc(100vh - 160px)",
        minHeight: 480,
        border: 0,
        display: "block",
      }}
    />
  );
}

// deepMerge replaces arrays wholesale (lib/utils.ts isObject excludes arrays), so
// the nav has to be restated in full, not just appended to.
export const overrideConfig = {
  // apiBaseUrl: "http://localhost:8000",
  routes: {
    datasetMore: [{ path: "ask", element: <AskRoute /> }],
  },
  header: {
    // Chiron's default is "/login/", which Django does not serve; the real form is
    // at /accounts/login/. Without this, the LOGIN button goes nowhere and every API
    // call 403s, which the UI reports as "Could not load the page".
    loginLink: "/accounts/login/",
    nav: [
      { label: "Dataset Home", link: "/dataset", icon: <HomeIcon /> },
      { label: "Query", link: "/query", icon: <SearchIcon /> },
      { label: "Results", link: "/results", icon: <TableChartIcon /> },
      { label: "Reports", link: "/reports", icon: <FileCopyIcon /> },
      { label: "Aggregate", link: "/aggregate", icon: <AddChartIcon /> },
      { label: "Ask", link: "/ask", icon: <AskIcon /> },
    ],
  },
};

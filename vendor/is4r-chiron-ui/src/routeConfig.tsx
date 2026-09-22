import { lazy } from "react";

import { Navigate, useRouteError } from "react-router-dom";
import App, { ErrorDisplay } from "./App";
import config from "./config";
import { useAppSelector } from "./store/hooks";
const LoginRoute = lazy(() => import("./routes/login"));
import type { AllError } from "./App";
const AggregateRoute = lazy(() => import("./routes/aggregate"));
const DatasetHomeRoute = lazy(() => import("./routes/dataset"));
const HomeRoute = lazy(() => import("./routes/home"));
const QueryRoute = lazy(() => import("./routes/query"));
const ResultsRoute = lazy(() => import("./routes/results"));
const ReportsRoute = lazy(() => import("./routes/reports"));
const ReportRoute = lazy(() => import("./routes/report"));

export const ProtectedRoute = ({ children }: { children: JSX.Element }) => {
  const user = useAppSelector((state) => state.auth.user);
  const status = useAppSelector((state) => state.auth.authStatus);
  if (status === "done" && !user) {
    // user is not authenticated
    return <Navigate to="/" />;
  }
  return children;
};

const routesConfig = [
  { path: "admin" },
  { path: "backend" },
  {
    path: "/",
    element: <App />,
    children: [
      {
        path: "",
        element: <HomeRoute />,
      },
      {
        path: "login",
        element: (
          <ProtectedRoute>
            <LoginRoute />
          </ProtectedRoute>
        ),
      },
      {
        path: "dataset/:dataset_id",
        element: (
          <ProtectedRoute>
            <DatasetHomeRoute />
          </ProtectedRoute>
        ),
      },
      {
        exact: true,
        path: ":dataset_id/reports/:report_id",
        element: (
          <ProtectedRoute>
            <ReportRoute />
          </ProtectedRoute>
        ),
      },
      {
        path: ":dataset_id",
        children: [
          {
            path: "query",
            element: (
              <ProtectedRoute>
                <QueryRoute />
              </ProtectedRoute>
            ),
          },
          {
            path: "results",
            element: (
              <ProtectedRoute>
                <ResultsRoute />
              </ProtectedRoute>
            ),
          },
          {
            path: "reports",
            element: (
              <ProtectedRoute>
                <ReportsRoute />
              </ProtectedRoute>
            ),
          },
          {
            path: "aggregate",
            element: (
              <ProtectedRoute>
                <AggregateRoute />
              </ProtectedRoute>
            ),
          },
        ].concat(config.routes.datasetMore),
      },
    ].concat(config.routes.more),
    errorElement: <RouteError></RouteError>,
  },
];

function RouteError() {
  const error = useRouteError() as AllError;
  return <ErrorDisplay error={error}></ErrorDisplay>;
}

// eslint-disable-next-line react-refresh/only-export-components
export default routesConfig;

import { Suspense } from "react";
import { ErrorBoundary } from "react-error-boundary";
import Footer from "./components/Footer";
import Header from "./components/Header";
import { Outlet, ScrollRestoration, useParams } from "react-router-dom";
import {
  Alert,
  AlertTitle,
  Box,
  Button,
  LinearProgress,
  Typography,
} from "@mui/material";
import { useAppSelector, useAppDispatch } from "./store/hooks";
import { setCurrentUser } from "./store/authSlice";
import { grey } from "@mui/material/colors";
import InfoBanner from "./components/InfoBanner";
import { LicenseInfo } from "@mui/x-license";
import config from "./config";
import { useIdleTimer } from "react-idle-timer";
import finalConfig from "./config";
LicenseInfo.setLicenseKey(import.meta.env.VITE_MUI_KEY);
import { useEffect } from "react";
import { useLocation } from "react-router-dom";

// REQUIRED TO USE MATOMO ANALYTICS
// MATOMO_DOMAIN - matomo endpoint url with no slashes
// MATOMO_SITE_ID - numerical site ID
const MATOMO_DOMAIN = import.meta.env.VITE_MATOMO_DOMAIN || "";
const MATOMO_SITE_ID = import.meta.env.VITE_MATOMO_SITE_ID || "";
// OPTIONS FOR MATOMO TRACKER
// MATOMO_TRACKER_OPTIONS - a list of matomo tracker options as a string 
const MATOMO_TRACKER_OPTIONS =
  import.meta.env.VITE_MATOMO_TRACKER_OPTIONS || "";

declare global {
  interface Window {
    _paq: any[];
  }
}

export type AllError = Error & { data: string; statusText: string };

export function ErrorDisplay({ error }: { error: AllError }) {
  // Call resetErrorBoundary() to reset the error boundary and retry the render.
  return (
    <>
      <Header />
      <Box role="alert" maxWidth={600} mx="auto" marginTop="15%">
        <Typography textAlign="center" variant="h4" gutterBottom>
          Something went wrong
        </Typography>

        <Box
          bgcolor={grey[100]}
          border="1px solid"
          borderColor={grey[300]}
          borderRadius={2}
          padding={2}
          maxHeight={200}
          overflow={"scroll"}
        >
          {import.meta.env.DEV ? (
            <>
              <Typography color="error">{error.message}</Typography>
              <Typography>{error.stack}</Typography>
              <Typography color="error">{error.statusText}</Typography>
              <Typography>{error.data}</Typography>
            </>
          ) : (
            <>
              <Typography color="error">Refused to fetch</Typography>
              <Typography>
                You may have been logged out, or the api may be experiencing
                issues
              </Typography>
            </>
          )}
        </Box>

        <Box alignItems={"center"} pt={2}>
          <Button
            variant="contained"
            component="button"
            onClick={() => {
              window.location.href = "/";
            }}
            sx={{ m: 2 }}
          >
            Go to home page
          </Button>
          <Button
            variant="contained"
            component="button"
            onClick={() => {
              window.location.reload();
            }}
          >
            Reload Page
          </Button>
        </Box>
      </Box>
      <Footer />
    </>
  );
}

function App() {
  const dispatch = useAppDispatch();
  const authStatus = useAppSelector((state) => state.auth.authStatus);
  const authErrors = useAppSelector((state) => state.auth.errors);
  const dataset = useAppSelector((state) => state.auth.dataset);
  const { dataset_id } = useParams();
  if (authStatus == "idle") {
    dispatch(
      setCurrentUser({
        dataset_id: dataset_id,
        current_dataset: dataset,
      })
    );
  }

  const onIdle = () => {
    window.location.href = config.header.logoutLink;
  };
  useIdleTimer({ onIdle, timeout: finalConfig.idleTimeOut });

  const location = useLocation();

  useEffect(() => {
    const _paq = (window._paq = window._paq || []);
    if (MATOMO_TRACKER_OPTIONS != "") {
      try {
        JSON.parse(MATOMO_TRACKER_OPTIONS).forEach((option: any) => {
          _paq.push(option);
        });
      } catch (e) {
        console.log("Unable to parse Matomo options", e);
      }
    }

    if (MATOMO_DOMAIN != "" && MATOMO_SITE_ID != "") {
      try {
        (function () {
          const u = "//" + MATOMO_DOMAIN + "/";
          _paq.push(["setTrackerUrl", u + "matomo.php"]);
          _paq.push(["setSiteId", MATOMO_SITE_ID]);
          const d = document,
            g = d.createElement("script"),
            s = d.getElementsByTagName("script")[0];
          if (s.parentNode) {
            g.async = true;
            g.src = u + "matomo.js";
            s.parentNode.insertBefore(g, s);
          }
        })();
      } catch (e) {
        console.log("Error connecting to Matomo", e);
      }
    }
  }, []);

  useEffect(() => {
    const _paq = (window._paq = window._paq || []);
    _paq.push(["setCustomUrl", location.pathname + location.search]);
    _paq.push(["trackPageView"]);
  }, [location]);

  return (
    <>
      <ErrorBoundary FallbackComponent={ErrorDisplay}>
        {import.meta.env.VITE_SHOW_INFO_BAR ? <InfoBanner /> : null}

        <Header />
        {authErrors?.length > 0 ? (
          authErrors.map((err) => {
            return (
              <Alert severity="error" key={err}>
                <AlertTitle>Error</AlertTitle>
                {err}
              </Alert>
            );
          })
        ) : (
          <Suspense fallback={<LinearProgress />}>
            <Box pb={config.footer.paddingForContent} mb={1}>
              <Outlet />
            </Box>
          </Suspense>
        )}
        <Footer />
      </ErrorBoundary>
      <ScrollRestoration />
    </>
  );
}

export default App;

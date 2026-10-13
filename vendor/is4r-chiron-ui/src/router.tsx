import { createBrowserRouter } from "react-router-dom";
import routesConfig from "./routeConfig";
// BASE_URL is "/" unless the build sets a path prefix (vite.config.ts `base`).
const router = createBrowserRouter(routesConfig, {
  basename: import.meta.env.BASE_URL,
});

export default router;

import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";

export default defineConfig(({ mode }) => {
  process.env = { ...process.env, ...loadEnv(mode, process.cwd()) };

  // The bundled demo Chiron runs on 8001 (scripts/serve_chiron.py). Point at your
  // own deployment with CHIRON_API=http://host:port.
  const api = process.env.CHIRON_API || "http://127.0.0.1:8001";

  // Served under a path prefix (e.g. /chiron) when VITE_BASE_PATH is set; the
  // deployment's Dockerfile.web passes it through from BASE_PATH. Unset: the site root.
  const basePath = (process.env.VITE_BASE_PATH || "").replace(/\/+$/, "");

  return {
    base: `${basePath}/`,
    plugins: [react()],
    server: {
      port: Number(process.env.CHIRON_UI_PORT || 5173),
      headers: {
        "Access-Control-Allow-Origin": "*",
      },
      proxy: {
        "/admin": api,
        "/api": api,
        "/accounts": api,
        "/backend": api,
        "/ajax": api,
        "/static": api,
      },
    },
    optimizeDeps: {
      include: [
        "@mui/icons-material",
        "@mui/material",
        "@emotion/react",
        "@emotion/styled",
      ],
    },
  };
});

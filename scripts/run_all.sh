#!/usr/bin/env bash
# Start everything: Chiron, the Ask chat server, and the Chiron UI with the Ask tab.
#
#   ./scripts/run_all.sh
#
# Ctrl-C stops all three.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"

if [ ! -f demo/chiron_demo.sqlite3 ]; then
  echo "No demo database yet. Run these first:"
  echo "  docker compose up -d"
  echo "  .venv/bin/python scripts/bootstrap_demo.py"
  exit 1
fi

export CHIRON_MCP_METADATA_DB="${CHIRON_MCP_METADATA_DB:-$ROOT/demo/chiron_demo.sqlite3}"
export CHIRON_MCP_WAREHOUSE_URL="${CHIRON_MCP_WAREHOUSE_URL:-postgresql://chiron:chiron@localhost:55432/chiron}"
export CHIRON_MCP_USERNAME="${CHIRON_MCP_USERNAME:-demouser}"
export CHIRON_MCP_ALLOW_SAVE="${CHIRON_MCP_ALLOW_SAVE:-1}"
export CHIRON_MCP_UI_URL="${CHIRON_MCP_UI_URL:-http://localhost:5173}"

pids=()
cleanup() { echo; echo "stopping..."; for p in "${pids[@]}"; do kill "$p" 2>/dev/null || true; done; }
trap cleanup EXIT INT TERM

echo "[1/3] Chiron            http://localhost:8001"
.venv/bin/python scripts/serve_chiron.py > /tmp/chiron-demo.log 2>&1 &
pids+=($!)

echo "[2/3] Ask Chiron        http://localhost:8900"
.venv/bin/python -m chiron_mcp.webapp > /tmp/chiron-ask.log 2>&1 &
pids+=($!)

UI="$ROOT/vendor/is4r-chiron-ui"
if [ ! -d "$UI/node_modules" ]; then
  echo "[3/3] installing UI dependencies (first run only, a few minutes)..."
  # --legacy-peer-deps: the UI pins eslint 9 while eslint-config-react-app wants
  # eslint 8. It is a lint-only conflict that does not affect the built app.
  (cd "$UI" && npm install --legacy-peer-deps --no-audit --no-fund \
      > /tmp/chiron-ui-install.log 2>&1) \
    || { echo "npm install failed, see /tmp/chiron-ui-install.log"; exit 1; }
fi
echo "[3/3] Chiron UI         http://localhost:5173   <- open this one"
(cd "$UI" && npm run dev > /tmp/chiron-ui.log 2>&1) &
pids+=($!)

sleep 6
echo
echo "Ready. Open http://localhost:5173 and click a login button (no password needed)"
echo "The 'Ask' tab is in the header, next to Aggregate."
echo "Logs: /tmp/chiron-demo.log /tmp/chiron-ask.log /tmp/chiron-ui.log"
echo "Ctrl-C to stop."
wait

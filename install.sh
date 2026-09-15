#!/usr/bin/env bash
# Set up chiron-mcp. Chiron itself is vendored at vendor/is4r-chiron, so this needs
# nothing but python3.12+.
set -euo pipefail
cd "$(dirname "$0")"

CHIRON_SRC="${CHIRON_MCP_CHIRON_SRC:-$PWD/vendor/is4r-chiron}"
if [ ! -f "$CHIRON_SRC/chiron/__init__.py" ]; then
  echo "Chiron source not found at: $CHIRON_SRC"
  echo "The bundled copy should be at vendor/is4r-chiron. If you removed it, set"
  echo "CHIRON_MCP_CHIRON_SRC to your own is4r-chiron checkout."
  exit 1
fi
echo "Chiron source: $CHIRON_SRC"

python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
echo "Installing dependencies (takes a minute)..."
.venv/bin/pip install -q "mcp>=2.0.0" -r "$CHIRON_SRC/requirements/base.txt"

echo
echo "Done. For a working demo with data, run:"
echo "  docker compose up -d"
echo "  .venv/bin/python scripts/bootstrap_demo.py"
echo
echo "That builds a metadata database, runs a real ETL into Postgres, creates demo"
echo "accounts, and prints the exact Claude config block to paste."

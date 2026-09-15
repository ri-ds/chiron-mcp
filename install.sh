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

# Find a Python 3.12+. The system python3 on macOS is 3.9, which cannot install mcp.
PY=""
for c in python3.14 python3.13 python3.12 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)' 2>/dev/null; then
    PY="$c"; break
  fi
done
if [ -z "$PY" ]; then
  echo
  echo "No Python 3.12 or newer found (found: $(python3 -V 2>&1))."
  echo "Install one, then re-run:"
  echo "  macOS    brew install python@3.12"
  echo "  Ubuntu   sudo apt install python3.12 python3.12-venv"
  exit 1
fi
echo "Python: $($PY -V) at $(command -v $PY)"

rm -rf .venv
"$PY" -m venv .venv
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

#!/usr/bin/env bash
# Set up chiron-mcp. Needs python3.12+ and a Chiron checkout.
set -euo pipefail
cd "$(dirname "$0")"

CHIRON_SRC="${CHIRON_MCP_CHIRON_SRC:-$(cd .. && pwd)/is4r-chiron-develop}"
if [ ! -f "$CHIRON_SRC/chiron/__init__.py" ]; then
  echo "Chiron source not found at: $CHIRON_SRC"
  echo "Clone is4r-chiron next to this project, or set CHIRON_MCP_CHIRON_SRC."
  exit 1
fi
echo "Chiron source: $CHIRON_SRC"

python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
echo "Installing dependencies (this takes a minute)..."
.venv/bin/pip install -q "mcp>=2.0.0" -r "$CHIRON_SRC/requirements/base.txt"

echo
echo "Done. Next:"
echo "  1. cp .env.example .env   and set CHIRON_MCP_USERNAME"
echo "  2. CHIRON_MCP_USERNAME=<user> .venv/bin/python scripts/harness.py"
echo "     -> confirms Chiron imports, the databases resolve, and which datasets that user can reach"
echo "  3. add the block from claude_mcp_config.example.json to your Claude config"

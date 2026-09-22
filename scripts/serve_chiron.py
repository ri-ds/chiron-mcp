"""Run the bundled Chiron web app against the demo databases.

Gives you a real Chiron website (login, workspace, reports) to pair with the MCP
server and the Ask page, without needing any external deployment.

    .venv/bin/python scripts/serve_chiron.py        # http://localhost:8001

Uses the demo metadata database and warehouse that scripts/bootstrap_demo.py built.
"""

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

PORT = os.environ.get("CHIRON_DEMO_PORT", "8001")
os.environ.setdefault("CHIRON_MCP_METADATA_DB", str(HERE / "demo" / "chiron_demo.sqlite3"))
os.environ.setdefault(
    "CHIRON_MCP_WAREHOUSE_URL", "postgresql://chiron:chiron@localhost:55432/chiron"
)
os.environ.setdefault("CHIRON_MCP_USERNAME", "demo")

from chiron_mcp.bootstrap import ensure_django  # noqa: E402
from chiron_mcp.config import CONFIG  # noqa: E402

if not Path(os.environ["CHIRON_MCP_METADATA_DB"]).exists():
    sys.exit(
        "No demo database yet. Run this first:\n"
        "  docker compose up -d\n"
        "  .venv/bin/python scripts/bootstrap_demo.py"
    )

ensure_django()

from django.core.management import call_command  # noqa: E402

print(f"Chiron at http://localhost:{PORT}   (log in as demo / demo)")
print(f"  metadata : {CONFIG.metadata_db}")
os.chdir(CONFIG.project_dir)
call_command("runserver", f"0.0.0.0:{PORT}", use_reloader=False)

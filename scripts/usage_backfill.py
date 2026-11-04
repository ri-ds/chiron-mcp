"""Fill the usage ledger from call-log lines: the answers given before the ledger existed.

Reads the lines from stdin, or from the files named. An answer's `request` line gives its
start, its `answer` line everything else. Rows the ledger already has are kept, so this
is safe to run again. In the deploy bundle, where the ledger lives in the ask container:

    docker compose logs --no-log-prefix ask | docker compose exec -T ask python /app/scripts/usage_backfill.py

Elsewhere, with the same CHIRON_MCP_USAGE_DB / CHIRON_MCP_STATE_DIR as the server:

    python scripts/usage_backfill.py /var/log/ask.log
"""

import fileinput
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chiron_mcp import usage  # noqa: E402

if usage.path() is None:
    sys.exit("The usage ledger is switched off (CHIRON_MCP_USAGE_DB).")
out = usage.backfill(fileinput.input(files=sys.argv[1:] or ("-",)))
print(f"{out['answers']} answers in the log: {out['written']} written, {out['kept']} already "
      f"in {usage.path()}")

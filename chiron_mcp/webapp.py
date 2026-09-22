"""A small web server that puts a chat box in front of the Chiron MCP tools.

Each question is answered by running Claude Code headless (`claude -p`) with this
project's MCP server loaded, so it uses the operator's existing Claude subscription
rather than an API key. Progress and the final answer stream back over SSE.

    .venv/bin/python -m chiron_mcp.webapp

Then open http://localhost:8900, or embed that URL in the Chiron UI (see
docs/chiron-ui-integration.md).

Standard library only, so it adds no dependencies to the MCP server itself.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from chiron_mcp.config import CONFIG

HERE = Path(__file__).resolve().parent
WEBUI = HERE / "webui"
PORT = int(os.environ.get("CHIRON_MCP_WEB_PORT", "8900"))

# Only the read-only analysis tools are offered by default. The hand-off tool is
# included so "open this in Chiron" works, but it is itself gated on
# CHIRON_MCP_ALLOW_SAVE inside the server.
TOOLS = [
    "chiron_datasets",
    "chiron_find_concepts",
    "chiron_describe_concept",
    "chiron_concept_values",
    "chiron_edit_cohort",
    "chiron_event_rule_options",
    "chiron_count_cohort",
    "chiron_run_table",
    "chiron_crosstab",
    "chiron_saved_reports",
    "chiron_run_saved_report",
    "chiron_open_in_ui",
]

SYSTEM_PROMPT = """You are a research data analyst helping someone explore a Chiron dataset.

Use the chiron tools to answer. Never invent numbers: every figure you state must come
from a tool result.

How to work:
- Call chiron_describe_concept before building any filter. It tells you the exact field
  names that concept's filter takes; guessing them fails.
- Check counts with chiron_count_cohort before pulling rows.
- Values in this data are often recorded with case and spelling variants. When counting a
  category, check chiron_concept_values first and include the variants, saying so.
- Combining filters from two different collections often fails with a SQL error. That is a
  known Chiron defect, not your mistake. If it happens, filter on one collection and put
  the other variable in the columns instead, and tell the user why.

How to answer:
- Lead with the number or the answer. Be brief.
- Use a markdown table whenever you have more than two rows of figures.
- To draw a chart, emit a fenced block tagged `chart` containing JSON:
  {"type":"bar","label":"Patients","data":[{"x":"Asthma","y":838},{"x":"COPD","y":199}]}
  Types: bar, line, doughnut. Use one when comparing categories or showing a trend, not
  for a single number.
- When the user wants to keep working in Chiron, call chiron_open_in_ui and give them the
  link it returns. Use mode="workspace" only if they ask to load it into their workspace,
  and warn that it replaces what they currently have open.
"""


def mcp_config_path() -> Path:
    """Write the MCP config this server runs Claude with, mirroring our own env."""
    env = {
        "CHIRON_MCP_CHIRON_SRC": CONFIG.chiron_src,
        "CHIRON_MCP_USERNAME": CONFIG.username,
        "CHIRON_MCP_MAX_ACCESS_LEVEL": CONFIG.max_access_level,
        "CHIRON_MCP_UI_URL": CONFIG.ui_url,
    }
    if CONFIG.metadata_db:
        env["CHIRON_MCP_METADATA_DB"] = CONFIG.metadata_db
    if CONFIG.warehouse_url:
        env["CHIRON_MCP_WAREHOUSE_URL"] = CONFIG.warehouse_url
    if CONFIG.allow_save:
        env["CHIRON_MCP_ALLOW_SAVE"] = "1"
    if CONFIG.operator:
        env["CHIRON_MCP_OPERATOR"] = "1"

    console = Path(sys.executable).parent / "chiron-mcp"
    cfg = {"mcpServers": {"chiron": {"command": str(console), "env": env}}}
    path = HERE / ".mcp-web.json"
    path.write_text(json.dumps(cfg, indent=2))
    return path


# Tools whose cohort_def input is the query that produced a figure the user sees.
_RESULT_TOOLS = {
    "chiron_count_cohort", "chiron_run_table", "chiron_crosstab", "chiron_export_table",
    "chiron_open_in_ui",
}


class _CohortTracker:
    """Watch the tool traffic and remember the cohort behind the answer.

    The model holds the working cohort_def and passes it to every tool, so the last
    definition it counted, tabulated or handed off is the one the answer is about.  A
    successful chiron_edit_cohort also yields one in its *result*, which matters when
    the model builds a filter and answers from the edit alone.
    """

    def __init__(self):
        self.state: dict | None = None
        self._names: dict[str, str] = {}  # tool_use_id -> tool name

    def tool_use(self, block: dict) -> None:
        name = block.get("name", "").replace("mcp__chiron__", "")
        args = block.get("input") or {}
        self._names[block.get("id", "")] = name
        if name in _RESULT_TOOLS and args.get("cohort_def"):
            self.state = {
                "dataset_id": args.get("dataset_id"),
                "cohort_def": args["cohort_def"],
                "columns": [c for c in (args.get("columns") or []) if isinstance(c, dict)],
            }

    def tool_result(self, block: dict) -> None:
        if self._names.get(block.get("tool_use_id", "")) != "chiron_edit_cohort":
            return
        content = block.get("content")
        if isinstance(content, list):
            content = "".join(c.get("text", "") for c in content if isinstance(c, dict))
        try:
            data = json.loads(content or "")
        except (TypeError, ValueError):
            return
        if isinstance(data, dict) and data.get("successful") and data.get("cohort_def"):
            prev = self.state or {}
            self.state = {
                "dataset_id": prev.get("dataset_id"),
                "cohort_def": data["cohort_def"],
                "columns": prev.get("columns", []),
            }


def ask_stream(question: str, dataset: str | None):
    """Run Claude headless and yield (event, payload) tuples as it works.

    Events: step, thinking, cohort (the cohort_def behind the answer, once, just
    before the answer), answer, error.
    """
    claude = shutil.which("claude") or os.path.expanduser("~/.local/bin/claude")
    if not Path(claude).exists():
        yield "error", "Claude Code CLI not found. Install it, or put `claude` on PATH."
        return

    prompt = question if not dataset else f"[dataset: {dataset}]\n\n{question}"
    cmd = [
        claude, "-p", prompt,
        "--mcp-config", str(mcp_config_path()),
        "--allowed-tools", ",".join(f"mcp__chiron__{t}" for t in TOOLS),
        "--append-system-prompt", SYSTEM_PROMPT,
        "--output-format", "stream-json",
        "--verbose",
    ]
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL, text=True, bufsize=1,
    )
    tracker = _CohortTracker()
    try:
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue

            kind = ev.get("type")
            if kind == "assistant":
                for block in ev.get("message", {}).get("content", []):
                    if block.get("type") == "tool_use":
                        raw = block.get("name", "")
                        # Only surface Chiron work. Claude's own housekeeping tools
                        # (ToolSearch and friends) are noise to a researcher.
                        if not raw.startswith("mcp__chiron__"):
                            continue
                        tracker.tool_use(block)
                        yield "step", raw.replace("mcp__chiron__chiron_", "")
                    elif block.get("type") == "text" and block.get("text", "").strip():
                        yield "thinking", block["text"][:300]
            elif kind == "user":
                for block in ev.get("message", {}).get("content", []) or []:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        tracker.tool_result(block)
            elif kind == "result":
                if ev.get("is_error"):
                    yield "error", ev.get("result") or "Claude returned an error."
                else:
                    if tracker.state and tracker.state.get("dataset_id"):
                        yield "cohort", tracker.state
                    yield "answer", ev.get("result", "")
        proc.wait(timeout=10)
        if proc.returncode not in (0, None):
            err = (proc.stderr.read() or "").strip()
            if err:
                yield "error", err[:500]
    finally:
        if proc.poll() is None:
            proc.kill()


def session_username(cookie_header: str | None) -> str | None:
    """The Django user behind a browser's Chiron session cookie, if any.

    Chiron and this server are reached on the same host (the UI proxies one and
    iframes the other), and cookies ignore the port, so the browser sends Chiron's
    `sessionid` here too.  Resolving it lets "use this as my query" land in the
    workspace of the person who clicked rather than in CHIRON_MCP_USERNAME's.
    """
    if not cookie_header:
        return None
    from http.cookies import SimpleCookie

    jar = SimpleCookie()
    try:
        jar.load(cookie_header)
    except Exception:  # noqa: BLE001
        return None
    if "sessionid" not in jar:
        return None
    try:
        from chiron_mcp import server as S  # noqa: F401  (boots Django)
        from django.contrib.auth import get_user_model
        from django.contrib.sessions.models import Session
        from django.utils import timezone

        sess = Session.objects.filter(
            session_key=jar["sessionid"].value, expire_date__gt=timezone.now()
        ).first()
        if not sess:
            return None
        uid = sess.get_decoded().get("_auth_user_id")
        user = get_user_model().objects.filter(pk=uid, is_active=True).first()
        return user.username if user else None
    except Exception:  # noqa: BLE001
        return None


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # keep the console quiet
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        url = urlparse(self.path)

        if url.path in ("/", "/index.html"):
            return self._file(WEBUI / "index.html", "text/html; charset=utf-8")
        if url.path == "/health":
            return self._json({"ok": True, "identity": CONFIG.username})
        if url.path == "/datasets":
            return self._datasets()
        if url.path == "/ask":
            return self._ask(parse_qs(url.query))

        self.send_error(404)

    def do_POST(self):
        url = urlparse(self.path)
        if url.path == "/load":
            return self._load()
        self.send_error(404)

    def _file(self, path: Path, ctype: str):
        if not path.exists():
            return self.send_error(404)
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _datasets(self):
        """List datasets directly, so the picker fills instantly instead of waiting on Claude."""
        try:
            from chiron_mcp import server as S

            info = S.chiron_datasets()
            rows = [
                {"id": d["dataset_id"], "name": d.get("name") or d["dataset_id"]}
                for d in info.get("datasets", [])
                if d.get("accessible")
            ]
            return self._json({
                "datasets": rows,
                "identity": info.get("identity"),
                "browser_user": session_username(self.headers.get("Cookie")),
            })
        except Exception as exc:  # noqa: BLE001
            return self._json({"datasets": [], "error": str(exc)})

    def _load(self):
        """Replace the browser user's live Chiron query with a cohort from an answer.

        Body: {"dataset_id", "cohort_def", "columns"?}.  Writes to the workspace of the
        Chiron user behind the request's session cookie, falling back to
        CHIRON_MCP_USERNAME when there is none.  Same guards as chiron_open_in_ui:
        CHIRON_MCP_ALLOW_SAVE must be on, and an errored definition is refused.
        """
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, TypeError):
            return self._json({"error": "Body must be JSON."})
        dataset_id = body.get("dataset_id")
        cohort_def = body.get("cohort_def")
        if not dataset_id or not isinstance(cohort_def, list) or not cohort_def:
            return self._json({"error": "dataset_id and a non-empty cohort_def are required."})

        from chiron_mcp import server as S

        who = session_username(self.headers.get("Cookie"))
        result = S.open_in_ui(
            dataset_id, cohort_def, body.get("columns") or [], mode="workspace", username=who
        )
        result["browser_user"] = who
        return self._json(result)

    def _ask(self, params):
        question = (params.get("q") or [""])[0].strip()
        dataset = (params.get("dataset") or [None])[0]
        if not question:
            return self.send_error(400, "missing q")

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self._cors()
        self.end_headers()

        def send(event, data):
            chunk = f"event: {event}\ndata: {json.dumps(data)}\n\n"
            self.wfile.write(chunk.encode())
            self.wfile.flush()

        try:
            for event, payload in ask_stream(question, dataset):
                send(event, payload)
            send("done", "")
        except (BrokenPipeError, ConnectionResetError):
            pass  # the browser navigated away


def main() -> int:
    if not CONFIG.username:
        print("CHIRON_MCP_USERNAME is required.", file=sys.stderr)
        return 1
    WEBUI.mkdir(exist_ok=True)
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Chiron Ask running at http://localhost:{PORT}")
    print(f"  identity : {CONFIG.username} (ceiling {CONFIG.max_access_level})")
    print(f"  chiron ui: {CONFIG.ui_url}")
    print("  Ctrl-C to stop")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

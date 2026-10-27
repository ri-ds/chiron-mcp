"""Django settings for the MCP server process.

Inherits the host project's real settings (so CHIRON_* behaviour, the processor
module list and the concept registry are identical to the deployment) and then
overrides only the two storage locations and the debug posture.

`chiron_mcp.bootstrap` puts the project directory on sys.path before Django
imports this module, which is what makes the star-import below resolve.
"""

import os

from chiron_mcp.config import CONFIG

# The host project's settings module, e.g. test_project/project/settings.py
_base = __import__(CONFIG.base_settings, fromlist=["*"])
for _name in dir(_base):
    if _name.isupper():
        globals()[_name] = getattr(_base, _name)

# --- overrides ---------------------------------------------------------------

# Metadata DB. Only overridden when CHIRON_MCP_METADATA_DB is set; otherwise the host
# project's own DATABASES setting is inherited untouched, which is what a fresh checkout
# wants. Point it at a different file to read a deployment's live metadata, or at a
# postgresql:// URL. Postgres is the safe choice whenever Chiron and this server run in
# different places (say Chiron in Docker, this on the host): SQLite's file locks do not
# cross that boundary, and concurrent writers then corrupt reads.
def _database_from_url(url: str) -> dict:
    from urllib.parse import unquote, urlparse

    u = urlparse(url)
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(u.path.lstrip("/")),
        "USER": unquote(u.username or ""),
        "PASSWORD": unquote(u.password or ""),
        "HOST": u.hostname or "localhost",
        "PORT": str(u.port or 5432),
    }


if CONFIG.metadata_db:
    if CONFIG.metadata_db.startswith(("postgres://", "postgresql://")):
        DATABASES = {"default": _database_from_url(CONFIG.metadata_db)}
    else:
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": CONFIG.metadata_db,
            }
        }

# Warehouse: reached only through SQLAlchemy, never the Django ORM. Same rule.
#
# Two Postgres settings ride on every warehouse connection (libpq "options"):
# - client_connection_check_interval: when a question is stopped, its Chiron MCP process
#   dies, and Postgres cancels that process's running query within seconds instead of
#   finishing a minutes-long scan nobody will read. Such leftovers used to pile up and
#   fill Postgres's shared memory, so the next questions failed.
# - statement_timeout: one query never runs past CHIRON_MCP_STATEMENT_TIMEOUT (seconds,
#   default 240, inside Ask's answer limit), so a too-slow step fails with an error the
#   model can report instead of silently using up the whole answer.
# A connection string that already sets "options" is left alone.


def _statement_timeout_ms() -> int:
    return int(float(os.environ.get("CHIRON_MCP_STATEMENT_TIMEOUT", "240")) * 1000)


def _check_interval_ms() -> int:
    """How often Postgres checks that the client is still there, in ms. A Postgres on
    macOS refuses any value but 0 ("platforms that lack POLLRDHUP"), so a warehouse on a
    Mac needs CHIRON_MCP_PG_CHECK_INTERVAL=0; the Linux stacks keep the default."""
    return int(float(os.environ.get("CHIRON_MCP_PG_CHECK_INTERVAL", "2000")))


def _with_pg_options(url: str) -> str:
    from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

    if not url.startswith(("postgres://", "postgresql://", "postgresql+")):
        return url
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    if "options" in query:
        return url
    query["options"] = (f"-c client_connection_check_interval={_check_interval_ms()} "
                        f"-c statement_timeout={_statement_timeout_ms()}")
    return urlunsplit(parts._replace(query=urlencode(query, quote_via=quote)))


if CONFIG.warehouse_url:
    CHIRON_SQL_ALCHEMY_CONNECTION_STRING = _with_pg_options(CONFIG.warehouse_url)

# The URL's "options" reach only our own connections (chiron_mcp.query's engine). Chiron
# builds an engine per dataset with libpq options of its own (the schema's search_path plus
# CHIRON_PG_CONN_OPTIONS_SITE), and those replace the URL's, so without this Chiron's
# queries ran under its default statement_timeout of 30 minutes: a stopped question's
# query kept running for minutes after the question was gone. Site connections are the
# ones Chiron MCP and Ask use; the MGMT setting (Chiron's own management commands, i.e. an
# ETL) keeps Chiron's default, because an ETL step may legitimately take longer.
CHIRON_PG_CONN_OPTIONS_SITE = {
    "statement_timeout": _statement_timeout_ms(),
    "client_connection_check_interval": _check_interval_ms(),
}

# Never leak tracebacks through tool output.
DEBUG = False

# DEBUG=False makes Django require this. Local hosts only: scripts/serve_chiron.py
# runs a development server for the bundled demo, not a public deployment.
ALLOWED_HOSTS = list(dict.fromkeys(
    list(globals().get("ALLOWED_HOSTS", [])) + ["localhost", "127.0.0.1", "0.0.0.0", "[::1]"]
))

# The UI dev server runs on a different origin (5173) from Chiron (8001) and proxies
# to it. A browser sends Origin: http://localhost:5173 on the login POST, and Django
# rejects it unless the origin is listed here. Without this, logging in through the UI
# fails with "CSRF verification failed" while the same request via curl succeeds,
# because curl sends no Origin header.
_ui_origins = [
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:3000", "http://127.0.0.1:3000",
    "http://localhost:8001", "http://127.0.0.1:8001",
]
if CONFIG.ui_url and CONFIG.ui_url not in _ui_origins:
    _ui_origins.append(CONFIG.ui_url)
CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(
    list(globals().get("CSRF_TRUSTED_ORIGINS", [])) + _ui_origins
))

# QueryTool/StatTool compile SQL with literal_binds and hand the string to
# helpers.print_query_info, which would put filter values (i.e. PHI) into logs.
CHIRON_GET_QUERY_PERFORMANCE = False

"""Django settings for the MCP server process.

Inherits the host project's real settings (so CHIRON_* behaviour, the processor
module list and the concept registry are identical to the deployment) and then
overrides only the two storage locations and the debug posture.

`chiron_mcp.bootstrap` puts the project directory on sys.path before Django
imports this module, which is what makes the star-import below resolve.
"""

from chiron_mcp.config import CONFIG

# The host project's settings module, e.g. test_project/project/settings.py
_base = __import__(CONFIG.base_settings, fromlist=["*"])
for _name in dir(_base):
    if _name.isupper():
        globals()[_name] = getattr(_base, _name)

# --- overrides ---------------------------------------------------------------

# Metadata DB. Only overridden when CHIRON_MCP_METADATA_DB is set; otherwise the host
# project's own DATABASES setting is inherited untouched, which is what a fresh checkout
# wants. Point it at a different file to read a deployment's live metadata.
if CONFIG.metadata_db:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": CONFIG.metadata_db,
        }
    }

# Warehouse: reached only through SQLAlchemy, never the Django ORM. Same rule.
if CONFIG.warehouse_url:
    CHIRON_SQL_ALCHEMY_CONNECTION_STRING = CONFIG.warehouse_url

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

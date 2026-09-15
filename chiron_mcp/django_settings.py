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

# QueryTool/StatTool compile SQL with literal_binds and hand the string to
# helpers.print_query_info, which would put filter values (i.e. PHI) into logs.
CHIRON_GET_QUERY_PERFORMANCE = False

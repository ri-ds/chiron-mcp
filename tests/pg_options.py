"""Every warehouse connection, Chiron's own included, carries the statement timeout and the
client connection check (chiron_mcp/django_settings.py).

Chiron builds an engine per dataset with libpq options of its own, which replace the ones
on the connection URL; so the settings must also be in CHIRON_PG_CONN_OPTIONS_SITE, or
Chiron's queries run under its 30-minute default. The first checks are offline; the last
ones need the warehouse (a SHOW on one connection) and a user with access to synthea-100k,
from the usual CHIRON_MCP_* settings. With chiron-benchmark's:

    CHIRON_BENCH_USER=bench-toolcheck PYTHONPATH=../chiron-benchmark .venv/bin/python -c \
      "from bench import config; config.setup(); import runpy; runpy.run_path('tests/pg_options.py', run_name='__main__')"

Exit code 0 means every check held.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("CHIRON_MCP_USERNAME", "tester")
os.environ["CHIRON_MCP_STATEMENT_TIMEOUT"] = "7"

fails: list[str] = []


def check(name: str, ok: bool, detail="") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:200])
    if not ok:
        fails.append(name)


from chiron_mcp.bootstrap import ensure_django  # noqa: E402

ensure_django()
from django.conf import settings  # noqa: E402

from chiron_mcp import django_settings as DS  # noqa: E402

from urllib.parse import parse_qs, urlsplit  # noqa: E402

url_options = parse_qs(urlsplit(DS._with_pg_options("postgresql://u@h/db")).query).get("options", [""])[0]
check("the URL options carry the timeout and the check interval",
      url_options == "-c client_connection_check_interval=2000 -c statement_timeout=7000", url_options)
check("a URL that sets its own options is left alone",
      DS._with_pg_options("postgresql://u@h/db?options=-c%20x%3D1") == "postgresql://u@h/db?options=-c%20x%3D1")
check("Chiron's site connection options carry the same two settings",
      settings.CHIRON_PG_CONN_OPTIONS_SITE == {"statement_timeout": 7000, "client_connection_check_interval": 2000},
      str(settings.CHIRON_PG_CONN_OPTIONS_SITE))
check("Chiron's management-command connections keep Chiron's default (an ETL may run long)",
      not hasattr(settings, "CHIRON_PG_CONN_OPTIONS_MGMT"))

# Live: what Postgres reports on a connection from Chiron's own engine for a dataset.
from chiron.models import Dataset  # noqa: E402
from chiron.query_engine.postgres import database  # noqa: E402

ds = Dataset.objects.filter(unique_id="synthea-100k").first()
if ds is None:
    print("SKIP  live checks: no synthea-100k here")
else:
    with database.get_sql_alchemy_db_engine(ds).connect() as c:
        timeout = c.exec_driver_sql("SHOW statement_timeout").scalar()
        interval = c.exec_driver_sql("SHOW client_connection_check_interval").scalar()
        path = c.exec_driver_sql("SHOW search_path").scalar()
    check("Chiron's engine: statement_timeout is ours, not 30 minutes", timeout == "7s", timeout)
    check("Chiron's engine: client_connection_check_interval is 2 s", interval == "2s", interval)
    check("Chiron's engine: the dataset's schema is still the search_path", path == "synthea_100k", path)

print()
print("all passed" if not fails else f"{len(fails)} failed: {fails}")
sys.exit(1 if fails else 0)

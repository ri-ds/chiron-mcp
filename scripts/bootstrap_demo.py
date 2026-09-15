"""Build a complete, self-contained Chiron demo from the bundled source and fixtures.

Creates a metadata database, loads the bundled data dictionary, runs a real ETL over the
bundled CSVs into a Postgres warehouse, and creates demo accounts at each access level.

Needs a running Postgres. The bundled compose file provides one:

    docker compose up -d
    .venv/bin/python scripts/bootstrap_demo.py

Safe to re-run: it rebuilds the demo metadata database from scratch each time. It only ever
touches the demo database, never a real deployment.
"""

import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

DEMO_DB = HERE / "demo" / "chiron_demo.sqlite3"
DEMO_WAREHOUSE = os.environ.get(
    "CHIRON_MCP_WAREHOUSE_URL", "postgresql://chiron:chiron@localhost:55432/chiron"
)

# Accounts created for the demo, one per access level.
DEMO_USERS = [
    ("demo", "deid", False),
    ("demo_agg", "agg", False),
    ("demo_admin", "phi", True),
]


def main() -> int:
    fresh = "--keep" not in sys.argv
    DEMO_DB.parent.mkdir(parents=True, exist_ok=True)
    if fresh and DEMO_DB.exists():
        DEMO_DB.unlink()
        print(f"removed existing {DEMO_DB.name}")

    # Point this process at the demo databases before Django starts.
    os.environ["CHIRON_MCP_METADATA_DB"] = str(DEMO_DB)
    os.environ["CHIRON_MCP_WAREHOUSE_URL"] = DEMO_WAREHOUSE
    os.environ.setdefault("CHIRON_MCP_USERNAME", "demo")

    from chiron_mcp.bootstrap import ensure_django
    from chiron_mcp.config import CONFIG

    print(f"chiron source : {CONFIG.chiron_src}")
    print(f"metadata db   : {DEMO_DB}")
    print(f"warehouse     : {DEMO_WAREHOUSE}")
    print()

    ensure_django()

    from django.core.management import call_command
    from django.db import connections

    from chiron import models

    print("[1/5] creating metadata tables")
    call_command("migrate", verbosity=0, interactive=False)

    print("[2/5] loading the bundled data dictionary")
    # chiron_restore_dd reads CHIRON_DATA_DICT_BACKUP_DIR, relative to the project dir.
    cwd = os.getcwd()
    os.chdir(CONFIG.project_dir)
    try:
        call_command("chiron_restore_dd", verbosity=0)
    finally:
        os.chdir(cwd)
    n_ds = models.Dataset.objects.count()
    n_concepts = models.Concept.objects.count()
    print(f"      {n_ds} dataset(s), {n_concepts} concept(s)")

    print("[3/5] running ETL into the warehouse (this is the slow step)")
    os.chdir(CONFIG.project_dir)
    try:
        for oDataset in models.Dataset.objects.all():
            print(f"      {oDataset.unique_id} ...", flush=True)
            try:
                call_command(
                    "chiron_run_etl",
                    dataset=oDataset.unique_id,
                    force=True,
                    verbosity=0,
                )
            except TypeError:
                # Older signature takes the dataset positionally.
                call_command("chiron_run_etl", oDataset.unique_id, force=True, verbosity=0)
    finally:
        os.chdir(cwd)

    print("[4/5] creating demo accounts")
    from django.contrib.auth import get_user_model

    User = get_user_model()
    for username, level, is_staff in DEMO_USERS:
        user, created = User.objects.get_or_create(
            username=username, defaults={"is_staff": is_staff}
        )
        user.is_staff = is_staff
        user.set_password("demo")
        user.save()
        for oDataset in models.Dataset.objects.all():
            cu, _ = models.ChironUser.objects.get_or_create(user=user, dataset=oDataset)
            cu.access_level = level
            cu.can_view_workspace = True
            cu.can_view_subject_details = False
            cu.save()
            for oDefault in models.DefaultPermissionGroup.objects.filter(dataset=oDataset):
                cu.permission_groups.add(oDefault.permission_group)
        print(f"      {username} ({level}) on {models.Dataset.objects.count()} dataset(s)")

    print("[5/5] verifying the warehouse answers")
    from chiron_mcp import identity
    from chiron.query_engine import get_querytool

    ok = 0
    for oDataset in models.Dataset.objects.all():
        try:
            ident = identity.resolve(oDataset.unique_id)
            count = get_querytool(ident.chironuser, []).get_cohort_count()
            print(f"      {oDataset.unique_id}: {count} subjects")
            ok += 1
        except Exception as exc:  # noqa: BLE001
            print(f"      {oDataset.unique_id}: FAILED - {exc}")

    connections.close_all()

    if not ok:
        print("\nNo dataset returned data. Is Postgres running? (docker compose up -d)")
        return 1

    print(f"""
Demo ready. {ok} dataset(s) queryable.

Add this to your Claude config, then restart the client:

{{
  "mcpServers": {{
    "chiron": {{
      "command": "{HERE}/.venv/bin/chiron-mcp",
      "env": {{
        "CHIRON_MCP_METADATA_DB": "{DEMO_DB}",
        "CHIRON_MCP_WAREHOUSE_URL": "{DEMO_WAREHOUSE}",
        "CHIRON_MCP_USERNAME": "demo",
        "CHIRON_MCP_MAX_ACCESS_LEVEL": "deid"
      }}
    }}
  }}
}}
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

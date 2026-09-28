"""Pack one Chiron dataset into a single file another deployment can import.

The bundle holds the dataset's data dictionary (Chiron's own chiron_backup_dataset) and
its warehouse schema (pg_dump), so the other side needs no source files and no ETL:

    CHIRON_MCP_METADATA_DB=/path/to/chiron_metadata.sqlite3 \\
    CHIRON_MCP_WAREHOUSE_URL=postgresql://user:pass@localhost:5432/chiron \\
    CHIRON_MCP_USERNAME=demouser \\
    .venv/bin/python scripts/export_dataset.py synthea-10k

writes synthea-10k.chiron.tar.gz. Import it with deploy/import-dataset.sh.

Users, access grants and saved reports are not included; the importer grants the demo
accounts. Reads only: nothing in the source deployment changes.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))


def pg_dump_command(url: str, schema: str, out: Path) -> list[str]:
    """A pg_dump at least as new as the server, or the same thing through Docker."""
    import psycopg2

    with psycopg2.connect(url) as conn, conn.cursor() as cur:
        cur.execute("show server_version_num")
        server_major = int(cur.fetchone()[0]) // 10000
    local = shutil.which("pg_dump")
    if local:
        m = re.search(r"(\d+)", subprocess.run([local, "--version"], capture_output=True,
                                               text=True).stdout)
        if m and int(m.group(1)) >= server_major:
            return [local, "--format=custom", "--no-owner", "--no-privileges",
                    f"--schema={schema}", f"--file={out}", url]
    # pg_dump refuses a newer server; a containerised one of the right version does not.
    docker_url = url.replace("@localhost", "@host.docker.internal").replace(
        "@127.0.0.1", "@host.docker.internal")
    return ["docker", "run", "--rm", "-v", f"{out.parent}:/out",
            f"postgres:{max(server_major, 17)}", "pg_dump", "--format=custom",
            "--no-owner", "--no-privileges", f"--schema={schema}",
            f"--file=/out/{out.name}", docker_url]


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    wanted = sys.argv[1]
    out_path = Path(sys.argv[2] if len(sys.argv) > 2 else f"{wanted}.chiron.tar.gz").resolve()

    os.environ.setdefault("CHIRON_MCP_USERNAME", "demouser")
    from chiron_mcp.bootstrap import ensure_django

    ensure_django()
    from django.core.management import call_command

    from chiron import models

    oDataset = models.Dataset.objects.filter(unique_id=wanted).first()
    if not oDataset:
        names = ", ".join(models.Dataset.objects.values_list("unique_id", flat=True))
        print(f"No dataset {wanted!r}. This deployment has: {names}")
        return 1
    from django.conf import settings

    schema = oDataset.get_actual_database_name()
    url = settings.CHIRON_SQL_ALCHEMY_CONNECTION_STRING

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        print(f"[1/3] data dictionary for {wanted}")
        call_command("chiron_backup_dataset", str(oDataset.id), filename=f"{wanted}.json",
                     backup_dir=str(tmp), overwrite=True, verbosity=0)

        print(f"[2/3] warehouse schema {schema} (the slow step)")
        dump = tmp / "warehouse.dump"
        subprocess.run(pg_dump_command(url, schema, dump), check=True)

        from chiron.query_engine import get_querytool
        from chiron_mcp import identity

        try:
            subjects = get_querytool(identity.resolve(wanted).chironuser, []).get_cohort_count()
        except Exception:  # noqa: BLE001  the count is informative only
            subjects = None
        (tmp / "manifest.json").write_text(json.dumps({
            "dataset": wanted, "schema": schema, "subjects": subjects,
            "dictionary": f"{wanted}.json", "warehouse": "warehouse.dump",
        }, indent=2))

        print(f"[3/3] packing {out_path.name}")
        with tarfile.open(out_path, "w:gz") as tar:
            for name in ("manifest.json", f"{wanted}.json", "warehouse.dump"):
                tar.add(tmp / name, arcname=name)

    size = out_path.stat().st_size / 1e6
    print(f"\nWrote {out_path} ({size:.0f} MB, {subjects} subjects).")
    print("Copy it to the other machine and run there:  deploy/import-dataset.sh <file>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

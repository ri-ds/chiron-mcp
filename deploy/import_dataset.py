"""Register an exported dataset's data dictionary and grant the demo accounts.

Runs inside the chiron container, after deploy/import-dataset.sh has restored the
warehouse schema:  python /app/deploy/import_dataset.py /tmp/import/synthea-10k.json

The accounts get the level their names promise (demouser deid, agguser agg, admin phi)
explicitly. Left to Chiron, the first visit would create a grant at the dataset's
auto-access level, which is phi on some datasets.
"""

import re
import sys
from pathlib import Path

from chiron_mcp.bootstrap import ensure_django

ensure_django()

from django.core.management import call_command  # noqa: E402

from chiron import models  # noqa: E402

LEVELS = {"demouser": "deid", "agguser": "agg", "admin": "phi"}


def main() -> int:
    path = Path(sys.argv[1])
    unique_id = path.stem
    if not re.fullmatch(r"[A-Za-z0-9_-]+", unique_id):
        print(f"Refusing: {unique_id!r} is not a plain dataset name.")
        return 1
    replace = "--replace" in sys.argv

    existing = models.Dataset.objects.filter(unique_id=unique_id).first()
    if existing and not replace:
        print(f"      {unique_id} is already registered; kept its data dictionary "
              "(pass --replace to reload it)")
    else:
        call_command("chiron_restore_dataset", path.name, backup_dir=str(path.parent),
                     overwrite=bool(existing), verbosity=0)
        print(f"      registered {unique_id}")
    oDataset = models.Dataset.objects.get(unique_id=unique_id)

    from django.contrib.auth import get_user_model

    for username, level in LEVELS.items():
        user = get_user_model().objects.filter(username=username).first()
        if not user:
            continue
        cu, _ = models.ChironUser.objects.get_or_create(user=user, dataset=oDataset)
        cu.access_level = level
        cu.can_view_workspace = True
        cu.can_view_subject_details = False
        cu.save()
        for oDefault in models.DefaultPermissionGroup.objects.filter(dataset=oDataset):
            cu.permission_groups.add(oDefault.permission_group)
        print(f"      {username}: {level}")

    from chiron.query_engine import get_querytool
    from chiron_mcp import identity

    granted = [u for u in LEVELS if get_user_model().objects.filter(username=u).exists()]
    if not granted:
        print("      no demo accounts yet (the demo builds on Chiron's first start), so "
              "nobody was granted access; run this again once it has")
        return 1
    ident = identity.resolve(unique_id, username=granted[0])
    count = get_querytool(ident.chironuser, []).get_cohort_count()
    print(f"      {unique_id} answers: {count} subjects")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

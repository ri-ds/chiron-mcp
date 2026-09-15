"""Step 1: prove the deployment shape with no MCP in it.

Resolves the bound Django user, then walks every dataset in the metadata DB and
reports what this identity may actually do -- including the datasets it is
deliberately refused.  Run this before debugging anything in the server itself.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chiron_mcp.bootstrap import ensure_django  # noqa: E402

ensure_django()

from chiron import models  # noqa: E402
from chiron_mcp import identity  # noqa: E402
from chiron_mcp.config import CONFIG  # noqa: E402


def main() -> int:
    from django.conf import settings

    print(f"chiron src  : {CONFIG.chiron_src}")
    print(f"project dir : {CONFIG.project_dir}")
    print(f"metadata db : {settings.DATABASES['default']['NAME']}")
    print(f"warehouse   : {settings.CHIRON_SQL_ALCHEMY_CONNECTION_STRING}")
    print(f"username    : {CONFIG.username}")
    print(f"ceiling     : {CONFIG.max_access_level}")
    print(f"operator    : {CONFIG.operator}   allow_save: {CONFIG.allow_save}")
    print()

    try:
        user = identity._django_user()
    except identity.AccessError as exc:
        print(f"FATAL: {exc}")
        return 1
    print(f"django user : {user.username} (staff={user.is_staff}, super={user.is_superuser})")
    print()

    ok = 0
    for oDataset in models.Dataset.objects.all().order_by("unique_id"):
        label = oDataset.unique_id
        try:
            ident = identity.resolve(label)
        except identity.AccessError as exc:
            print(f"  [refused] {label:18} {exc}")
            continue

        raw = ident.chironuser.access_level
        clamp = "" if raw == ident.access_level else f" (clamped from '{raw}')"
        gates = []
        for name, fn in (
            ("subject_level", lambda: identity.require_subject_level(ident)),
            ("workspace", lambda: identity.require_workspace(ident)),
        ):
            try:
                fn()
                gates.append(f"+{name}")
            except identity.AccessError:
                gates.append(f"-{name}")

        print(
            f"  [ok]      {label:18} access={ident.access_level}{clamp}  "
            f"schema={oDataset.get_actual_database_name()}  {' '.join(gates)}"
        )
        ok += 1

    print()
    print(f"{ok} dataset(s) reachable by this identity.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

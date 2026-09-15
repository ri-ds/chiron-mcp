"""Grant (or revoke) a Django user a ChironUser row on datasets.

The MCP server deliberately never autocreates a ChironUser, because Chiron's own
autocreate provisions at `Dataset.auto_access_level` -- which is 'phi' on the
synthea datasets. Access is therefore granted here, deliberately and visibly.

Idempotent. Usage:

    python scripts/grant_access.py --user demouser --datasets synthea-10k --level deid
    python scripts/grant_access.py --user demouser --datasets synthea-10k --revoke
    python scripts/grant_access.py --list
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chiron_mcp.bootstrap import ensure_django  # noqa: E402

ensure_django()

from django.contrib.auth import get_user_model  # noqa: E402

from chiron import models  # noqa: E402


def show():
    print(f"{'chironuser':>10}  {'user':<12} {'dataset':<18} {'level':<6} workspace")
    for cu in models.ChironUser.objects.select_related("user", "dataset").order_by(
        "user__username", "dataset__unique_id"
    ):
        print(
            f"{cu.pk:>10}  {cu.user.username:<12} {cu.dataset.unique_id:<18} "
            f"{cu.access_level:<6} {cu.can_view_workspace}"
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user")
    ap.add_argument("--datasets", help="comma separated Dataset.unique_id values")
    ap.add_argument("--level", default="deid", choices=["phi", "deid", "agg"])
    ap.add_argument("--revoke", action="store_true")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list or not args.user:
        show()
        return 0

    User = get_user_model()
    user = User.objects.filter(username=args.user).first()
    if not user:
        print(f"No Django user {args.user!r}")
        return 1

    for name in [x.strip() for x in (args.datasets or "").split(",") if x.strip()]:
        oDataset = models.Dataset.objects.filter(unique_id=name).first()
        if not oDataset:
            print(f"  ! no dataset {name!r}")
            continue

        existing = models.ChironUser.objects.filter(user=user, dataset=oDataset).first()

        if args.revoke:
            if existing:
                existing.delete()
                print(f"  revoked {args.user} on {name}")
            else:
                print(f"  (nothing to revoke for {args.user} on {name})")
            continue

        if existing:
            existing.access_level = args.level
            existing.can_view_workspace = True
            existing.save()
            print(f"  updated {args.user} on {name} -> {args.level}")
        else:
            cu = models.ChironUser(
                user=user,
                dataset=oDataset,
                access_level=args.level,
                can_view_workspace=True,
                can_view_subject_details=False,
            )
            cu.save()
            # A dataset with PermissionGroup rows hides everything from a user with no
            # group (manage_users.md), so attach the dataset's defaults.
            for oDefault in models.DefaultPermissionGroup.objects.filter(dataset=oDataset):
                cu.permission_groups.add(oDefault.permission_group)
            n = models.PermissionGroup.objects.filter(dataset=oDataset).count()
            note = f"  (dataset has {n} permission group(s))" if n else ""
            print(f"  granted {args.user} on {name} -> {args.level}{note}")

    print()
    show()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

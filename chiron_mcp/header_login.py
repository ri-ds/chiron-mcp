"""Sign-on by request header, for a Chiron behind a gateway that authenticates people.

A gateway such as an access manager or a Shibboleth service provider signs the person in
and forwards every request with headers that say who they are (OBLIX_UID, REMOTE_USER,
eppn, X-Remote-User and the like). With CHIRON_SSO_USER_HEADER naming that header, the
middleware here logs the person into Django on their first request: the account is
created if it is new, with first name, last name and email from the companion headers,
never staff and never a superuser, and a newcomer gets the access CHIRON_SSO_DEFAULT_ACCESS
says (agg by default) on the datasets CHIRON_SSO_DEFAULT_DATASETS lists (all of them by
default), so that everyone can ask and what they get out depends on their rows, which an
administrator raises in Chiron's admin. With the header unset nothing here runs and
Chiron's own login page is the only way in.

The header is believed as it arrives. So this may stand only behind a gateway that
strips the same header from what the client sent, and nothing but that gateway may
reach the web server: /ask/whoami shows a staff account what arrives, and a bogus
header sent from the browser must not show up there. The Ask server trusts only the
Django session this creates, never the header itself.

Settings (read from the environment by deploy/settings_custom.py):

    CHIRON_SSO_USER_HEADER            the header with the username, e.g. OBLIX_UID,
                                      X-Remote-User, eppn; REMOTE_USER means the web
                                      server's own variable
    CHIRON_SSO_FIRST_NAME_HEADER      e.g. OBLIX_FNAME or givenName        (optional)
    CHIRON_SSO_LAST_NAME_HEADER       e.g. OBLIX_LNAME or sn               (optional)
    CHIRON_SSO_DISPLAY_NAME_HEADER    e.g. displayName, split when the two above are
                                      missing                              (optional)
    CHIRON_SSO_EMAIL_HEADER           e.g. OBLIX_EMAIL or mail             (optional)
    CHIRON_SSO_STRIP_DOMAIN           1: abc1de@example.org becomes abc1de
    CHIRON_SSO_DEFAULT_ACCESS         agg (default), deid, phi, or none
    CHIRON_SSO_DEFAULT_DATASETS       comma-separated unique_ids; unset: every dataset
    CHIRON_SSO_LOGOUT_URL             where Chiron's logout sends the browser, so the
                                      gateway's session ends too; unset: the login page
"""

from __future__ import annotations

import sys

from django.conf import settings
from django.contrib.auth.backends import RemoteUserBackend
from django.contrib.auth.middleware import RemoteUserMiddleware

LEVELS = ("agg", "deid", "phi")


def header_key(name: str | None) -> str | None:
    """The request.META key for a header name as written in an HTTP request: X-Remote-User
    is HTTP_X_REMOTE_USER, OBLIX_UID is HTTP_OBLIX_UID. REMOTE_USER and anything already
    spelled HTTP_... are taken as they are."""
    name = (name or "").strip()
    if not name:
        return None
    key = name.upper().replace("-", "_")
    if key == "REMOTE_USER" or key.startswith("HTTP_"):
        return key
    return "HTTP_" + key


def setting(name: str, default: str = "") -> str:
    return str(getattr(settings, name, default) or default).strip()


def meta(request, name: str) -> str:
    key = header_key(setting(name))
    return (request.META.get(key) or "").strip() if key else ""


class HeaderLoginMiddleware(RemoteUserMiddleware):
    """Logs in the person the sign-on header names, and logs out a session whose header
    has gone (the gateway's session ended), so a Django login never outlives the
    gateway's. Inert when CHIRON_SSO_USER_HEADER is unset."""

    @property
    def header(self):  # type: ignore[override]
        return header_key(setting("CHIRON_SSO_USER_HEADER")) or "REMOTE_USER"

    def process_request(self, request):
        if not setting("CHIRON_SSO_USER_HEADER"):
            return None
        # A blank value is no identity: treat it as a missing header, which logs out.
        key = self.header
        value = (request.META.get(key) or "").strip()
        if value:
            request.META[key] = value
        else:
            request.META.pop(key, None)
        return super().process_request(request)


class HeaderLoginBackend(RemoteUserBackend):
    """Creates the account on first sight, fills its names, and grants the default access."""

    create_unknown_user = True

    def authenticate(self, request, remote_user=None):
        if not remote_user or not self.clean_username(remote_user):
            return None  # never an account with an empty name
        return super().authenticate(request, remote_user=remote_user)

    def clean_username(self, username):
        username = (username or "").strip().lower()
        if setting("CHIRON_SSO_STRIP_DOMAIN").lower() in ("1", "true", "yes") and "@" in username:
            username = username.split("@", 1)[0]
        return username

    def configure_user(self, request, user, created=True):
        changed = False
        if created:
            user.is_staff = False
            user.is_superuser = False
            user.set_unusable_password()
            changed = True
        first = meta(request, "CHIRON_SSO_FIRST_NAME_HEADER")
        last = meta(request, "CHIRON_SSO_LAST_NAME_HEADER")
        if not (first or last):
            display = meta(request, "CHIRON_SSO_DISPLAY_NAME_HEADER")
            if display:
                first, _, last = display.partition(" ")
        email = meta(request, "CHIRON_SSO_EMAIL_HEADER")
        # Fill what is empty; never overwrite a name or address someone set by hand.
        if first and not user.first_name:
            user.first_name, changed = first[:150], True
        if last and not user.last_name:
            user.last_name, changed = last[:150], True
        if email and not user.email:
            user.email, changed = email[:254], True
        if changed:
            user.save()
        if created:
            granted = grant_default_access(user)
            print(f"sso: created {user.username!r}" + (f", {granted}" if granted else ", no dataset access"),
                  file=sys.stderr, flush=True)
        return user


def grant_default_access(user) -> str:
    """The rows CHIRON_SSO_DEFAULT_ACCESS and CHIRON_SSO_DEFAULT_DATASETS ask for, made
    deliberately here and nowhere else; what was granted, in words."""
    level = setting("CHIRON_SSO_DEFAULT_ACCESS", "agg").lower()
    if level in ("", "none", "off", "0"):
        return ""
    if level not in LEVELS:
        print(f"sso: CHIRON_SSO_DEFAULT_ACCESS={level!r} is not one of {LEVELS}; granting nothing",
              file=sys.stderr, flush=True)
        return ""
    try:
        from chiron import models
    except Exception:  # noqa: BLE001  (no Chiron in this Django: nothing to grant)
        return ""
    wanted = [x.strip() for x in setting("CHIRON_SSO_DEFAULT_DATASETS").split(",") if x.strip()]
    datasets = models.Dataset.objects.all().order_by("unique_id")
    if wanted:
        datasets = datasets.filter(unique_id__in=wanted)
    made = []
    for ds in datasets:
        if models.ChironUser.objects.filter(user=user, dataset=ds).exists():
            continue
        cu = models.ChironUser(user=user, dataset=ds, access_level=level,
                               can_view_workspace=True, can_view_subject_details=False)
        cu.save()
        for default in models.DefaultPermissionGroup.objects.filter(dataset=ds):
            cu.permission_groups.add(default.permission_group)
        made.append(ds.unique_id)
    return f"{level} on {', '.join(made)}" if made else ""

"""Sign-on by request header (chiron_mcp/header_login.py): the person a gateway names in
a header is logged into Django, created on first sight with names and email and no
rights, kept in step with the header, and left alone when the setting is off.

Offline: a throwaway Django with auth and sessions in memory, no Chiron, no server.

    .venv/bin/python tests/header_login.py

Exit code 0 means every check held.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import django  # noqa: E402
from django.conf import settings  # noqa: E402

settings.configure(
    SECRET_KEY="test-only",
    INSTALLED_APPS=["django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions"],
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
    MIDDLEWARE=[
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "chiron_mcp.header_login.HeaderLoginMiddleware",
    ],
    AUTHENTICATION_BACKENDS=[
        "chiron_mcp.header_login.HeaderLoginBackend",
        "django.contrib.auth.backends.ModelBackend",
    ],
    CHIRON_SSO_USER_HEADER="OBLIX_UID",
    CHIRON_SSO_FIRST_NAME_HEADER="OBLIX_FNAME",
    CHIRON_SSO_LAST_NAME_HEADER="OBLIX_LNAME",
    CHIRON_SSO_DISPLAY_NAME_HEADER="displayName",
    CHIRON_SSO_EMAIL_HEADER="OBLIX_EMAIL",
    CHIRON_SSO_STRIP_DOMAIN="",
    CHIRON_SSO_DEFAULT_ACCESS="agg",
    USE_TZ=True,
)
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.contrib.auth.middleware import AuthenticationMiddleware  # noqa: E402
from django.contrib.sessions.middleware import SessionMiddleware  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.test import RequestFactory  # noqa: E402

from chiron_mcp import header_login as H  # noqa: E402

call_command("migrate", verbosity=0, run_syncdb=True)
User = get_user_model()
fails: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    print(f"{'PASS' if cond else 'FAIL'}  {label}  {str(detail)[:200]}")
    if not cond:
        fails.append(label)


def request(headers: dict | None = None, session_key: str | None = None):
    """A request through the three middlewares, as Django would run them."""
    meta = {f"HTTP_{k.upper().replace('-', '_')}": v for k, v in (headers or {}).items()}
    req = RequestFactory().get("/", **meta)
    if session_key:
        req.COOKIES[settings.SESSION_COOKIE_NAME] = session_key
    noop = lambda r: None  # noqa: E731
    SessionMiddleware(noop).process_request(req)
    AuthenticationMiddleware(noop).process_request(req)
    H.HeaderLoginMiddleware(noop).process_request(req)
    req.session.save()
    return req


# --- header names -------------------------------------------------------------------
check("an HTTP header name becomes its META key",
      H.header_key("X-Remote-User") == "HTTP_X_REMOTE_USER" and H.header_key("OBLIX_UID") == "HTTP_OBLIX_UID"
      and H.header_key("eppn") == "HTTP_EPPN")
check("REMOTE_USER and HTTP_... are taken as they are",
      H.header_key("REMOTE_USER") == "REMOTE_USER" and H.header_key("HTTP_EPPN") == "HTTP_EPPN"
      and H.header_key("") is None)

# --- first sight ----------------------------------------------------------------------
req = request({"OBLIX_UID": "ABC1DE", "OBLIX_FNAME": "Ada", "OBLIX_LNAME": "Lovelace",
               "OBLIX_EMAIL": "ada@example.org"})
u = req.user
check("the person in the header is logged in, username lower-cased",
      u.is_authenticated and u.username == "abc1de", getattr(u, "username", None))
check("names and email come from the companion headers",
      u.first_name == "Ada" and u.last_name == "Lovelace" and u.email == "ada@example.org", (u.first_name, u.last_name, u.email))
check("never staff, never superuser, no usable password",
      not u.is_staff and not u.is_superuser and not u.has_usable_password())
check("one account", User.objects.filter(username="abc1de").count() == 1)
key = req.session.session_key

# --- again, with other names: the account is reused and its names kept --------------
req = request({"OBLIX_UID": "abc1de", "OBLIX_FNAME": "Someone", "OBLIX_LNAME": "Else"}, key)
check("the same person again is the same account, names left alone",
      req.user.username == "abc1de" and req.user.first_name == "Ada" and User.objects.count() == 1,
      (req.user.first_name, User.objects.count()))

# --- the header goes: the gateway's session ended, so Django's does too --------------
req = request({}, key)
check("no header, no login, even with the session cookie of a login", not req.user.is_authenticated)

# --- a different person on the same browser session ---------------------------------
req = request({"OBLIX_UID": "zzz9", "displayName": "Grace Hopper"}, key)
check("another header on the same session switches the login",
      req.user.is_authenticated and req.user.username == "zzz9", getattr(req.user, "username", None))
check("a display name is split when there are no first and last name headers",
      req.user.first_name == "Grace" and req.user.last_name == "Hopper", (req.user.first_name, req.user.last_name))

# --- domain stripping ------------------------------------------------------------------
settings.CHIRON_SSO_STRIP_DOMAIN = "1"
req = request({"OBLIX_UID": "Jane.Doe@Example.org"})
check("with CHIRON_SSO_STRIP_DOMAIN the domain is dropped from the username",
      req.user.username == "jane.doe", getattr(req.user, "username", None))
settings.CHIRON_SSO_STRIP_DOMAIN = ""
req = request({"OBLIX_UID": "Jane.Doe@Example.org"})
check("without it the whole value is the username, lower-cased",
      req.user.username == "jane.doe@example.org", getattr(req.user, "username", None))

# --- a blank value, and the switch off --------------------------------------------------
req = request({"OBLIX_UID": "   "})
check("a blank header logs nobody in", not req.user.is_authenticated)
settings.CHIRON_SSO_USER_HEADER = ""
n = User.objects.count()
req = request({"OBLIX_UID": "newperson"})
check("with the setting off the header is ignored and no account is made",
      not req.user.is_authenticated and User.objects.count() == n)
settings.CHIRON_SSO_USER_HEADER = "OBLIX_UID"

# --- default access without Chiron: nothing to grant, nothing breaks ------------------
check("without Chiron's models the default access step grants nothing and says so",
      H.grant_default_access(User.objects.get(username="abc1de")) == "")
settings.CHIRON_SSO_DEFAULT_ACCESS = "none"
check("CHIRON_SSO_DEFAULT_ACCESS=none grants nothing", H.grant_default_access(User.objects.get(username="abc1de")) == "")

print()
print("ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}")
sys.exit(1 if fails else 0)

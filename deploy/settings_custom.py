"""Chiron settings for the Docker deployment.

The image copies this over test_project/project/settings_custom.py, which Chiron's
settings.py star-imports last. Every value comes from the environment deploy/compose.yml
sets, so nothing here is specific to one machine.
"""

import os
from urllib.parse import unquote, urlparse


def _database(url: str) -> dict:
    u = urlparse(url)
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(u.path.lstrip("/")),
        "USER": unquote(u.username or ""),
        "PASSWORD": unquote(u.password or ""),
        "HOST": u.hostname or "db",
        "PORT": str(u.port or 5432),
        "CONN_MAX_AGE": 60,
    }


# The key in Chiron's settings.py is published in its repository, and Django signs
# session cookies with it, so anyone could forge an admin login. Never run without
# a key of our own.
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = os.environ.get("DJANGO_DEBUG") == "1"

# Metadata in Postgres, not SQLite: Chiron and the Ask server run in separate
# containers, and SQLite's file locks are not shared safely between them.
DATABASES = {"default": _database(os.environ["CHIRON_MCP_METADATA_DB"])}
CHIRON_SQL_ALCHEMY_CONNECTION_STRING = os.environ["CHIRON_MCP_WAREHOUSE_URL"]

# One public address; the proxy in front sends Chiron everything under /api,
# /accounts, /admin, /backend and /ajax (Django's static files it serves itself).
PUBLIC_URL = os.environ.get("CHIRON_PUBLIC_URL", "http://localhost").rstrip("/")
_public = urlparse(PUBLIC_URL)
_host = _public.hostname or "localhost"
ALLOWED_HOSTS = list(dict.fromkeys([_host, "localhost", "127.0.0.1", "chiron"]))
# An origin is scheme and host only; PUBLIC_URL may carry a path (BASE_PATH below).
CSRF_TRUSTED_ORIGINS = [f"{_public.scheme}://{_public.netloc}"]

# Optionally served under a path prefix, e.g. https://example.org/chiron (BASE_PATH in
# deploy/.env). The proxy strips the prefix before Django sees a request;
# FORCE_SCRIPT_NAME puts it back on every URL Django builds, and the settings that hold
# plain paths are prefixed here because Django leaves those as written.
BASE_PATH = "/" + os.environ.get("CHIRON_BASE_PATH", "").strip().strip("/")
if BASE_PATH != "/":
    FORCE_SCRIPT_NAME = BASE_PATH
    STATIC_URL = f"{BASE_PATH}/static/"
    LOGIN_URL = f"{BASE_PATH}/accounts/login/"
    LOGIN_REDIRECT_URL = f"{BASE_PATH}/"
    LOGOUT_REDIRECT_URL = f"{BASE_PATH}/accounts/login/"

# TLS ends at the proxy (or at Cloudflare in front of it), which says so in
# X-Forwarded-Proto.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
if PUBLIC_URL.startswith("https://"):
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# collectstatic writes here; the proxy serves the files from a shared volume.
STATIC_ROOT = "/app/static"

CHIRON_SITE_TITLE = os.environ.get("CHIRON_SITE_TITLE", "Chiron")
CHIRON_INFOBAR = os.environ.get("CHIRON_INFOBAR", "Synthetic demo data only")

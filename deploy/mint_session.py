"""Print a fresh Chiron session id for a user, for deploy/check.py.

Creates the session the way Django's login does, so no password is ever typed or sent.
Run inside the chiron container:  python /app/deploy/mint_session.py demouser
"""

import sys

from chiron_mcp.bootstrap import ensure_django

ensure_django()

from django.contrib.auth import get_user_model  # noqa: E402
from django.contrib.sessions.backends.db import SessionStore  # noqa: E402

user = get_user_model().objects.get(username=sys.argv[1])
s = SessionStore()
s["_auth_user_id"] = str(user.pk)
s["_auth_user_backend"] = "django.contrib.auth.backends.ModelBackend"
s["_auth_user_hash"] = user.get_session_auth_hash()
s.set_expiry(3600)
s.create()
print(s.session_key)

"""OAuth for the HTTP endpoint: sign in as a Chiron user, and every tool call acts as them.

Without this the HTTP endpoint serves every caller as CHIRON_MCP_USERNAME. With
CHIRON_MCP_HTTP_AUTH=oauth the server is its own small OAuth 2.1 authorization server
(dynamic client registration, authorization code with PKCE, refresh tokens), which is the
flow MCP clients such as Claude Code already speak:

    client -> /authorize -> /oauth/login (this module's page) -> client's redirect_uri
    client -> /token -> access token -> /mcp with "Authorization: Bearer ..."

The login page is where an identity becomes a Chiron user. It accepts either of:

  * the Chiron session the browser already has (the `sessionid` cookie, which the
    browser sends here because cookies ignore the port), offered as "Continue as X";
  * a Chiron username and password, checked by Django's own `authenticate()`, so
    whatever authentication backends the deployment configures apply.

Either way the result is the username of an existing, active Django user. It rides in
the token as its subject, `identity.bound_username()` reads it back on each request, and
`identity.resolve()` then finds that user's real ChironUser per dataset. Nothing is ever
provisioned: a person with no ChironUser on a dataset is refused exactly as before.

WHAT IS STORED
--------------
Nothing durable but one signing key. Access tokens, refresh tokens and client
registrations are signed blobs (django.core.signing, HMAC-SHA256) that the server
verifies rather than looks up, so they survive a restart and an unauthenticated
/register cannot fill a table. Pending logins and authorization codes are short-lived
and live in memory.

The key is CHIRON_MCP_OAUTH_SECRET, or a random one created on first use in
CHIRON_MCP_STATE_DIR (default ~/.cache/chiron-mcp/oauth.key, mode 0600). It is
deliberately not Django's SECRET_KEY: the bundled demo project ships a public one, and
anyone who knew the key could mint a token for any user. Deleting the key file signs
everyone out and forgets every registered client.

A token also dies when its user is deactivated or their password changes, because each
one carries a fingerprint of the user's password hash that is re-checked on every
request, the way Django invalidates sessions.

LIMITS
------
Signed tokens cannot be revoked one at a time, so there is no /revoke endpoint and a
used refresh token stays valid until it expires. Access tokens last an hour to bound
that. The endpoint still listens on loopback only, and clients may only register
loopback redirect URIs.
"""

from __future__ import annotations

import hashlib
import hmac
import html
import os
import secrets
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

import anyio.to_thread
from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    AuthorizeError,
    RefreshToken,
    RegistrationError,
    TokenError,
    construct_redirect_uri,
)
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from chiron_mcp import identity
from chiron_mcp.config import CONFIG

SCOPE = "chiron"
ACCESS_TTL = 60 * 60  # seconds an access token works
REFRESH_TTL = 30 * 24 * 60 * 60  # seconds a refresh token works
CODE_TTL = 5 * 60  # seconds to exchange an authorization code
LOGIN_TTL = 10 * 60  # seconds to finish the login page
MAX_PENDING = 500  # unfinished logins held at once
MAX_ATTEMPTS = 5  # wrong passwords before a login is abandoned
MAX_REDIRECT_URIS = 5
LOGIN_PATH = "/oauth/login"

_LOOPBACK = {"localhost", "127.0.0.1", "::1"}


def issuer_url() -> str:
    # Hosted, the sign-in lives beside the endpoint under the public address (the proxy
    # strips <public path>/mcp before this app sees it); locally, at the port's root.
    if CONFIG.hosted:
        return f"{CONFIG.public_url}/mcp"
    return f"http://localhost:{CONFIG.http_port}"


def resource_url() -> str:
    if CONFIG.hosted:
        return f"{CONFIG.public_url}/mcp"
    return f"{issuer_url()}/mcp"


def _login_action() -> str:
    """The sign-in form's target, as the browser sees it (under the issuer's path)."""
    return urlsplit(issuer_url()).path.rstrip("/") + LOGIN_PATH


# --- signing -----------------------------------------------------------------

_KEY: str | None = None


def _state_dir() -> Path:
    d = Path(os.environ.get("CHIRON_MCP_STATE_DIR", Path.home() / ".cache" / "chiron-mcp"))
    d.mkdir(parents=True, exist_ok=True)
    try:
        d.chmod(0o700)
    except OSError:
        pass
    return d


def _key() -> str:
    """The signing key: from the environment, else a random one kept in the state dir."""
    global _KEY
    if _KEY:
        return _KEY
    env = os.environ.get("CHIRON_MCP_OAUTH_SECRET", "").strip()
    if env:
        if len(env) < 32:
            raise SystemExit("CHIRON_MCP_OAUTH_SECRET must be at least 32 characters.")
        _KEY = env
        return _KEY
    path = _state_dir() / "oauth.key"
    try:
        # O_EXCL: two servers starting together cannot both write a key.
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as fh:
            fh.write(secrets.token_hex(32))
    except FileExistsError:
        pass
    _KEY = path.read_text().strip()
    if len(_KEY) < 32:
        raise SystemExit(f"{path} does not hold a usable key. Delete it to make a new one.")
    return _KEY


def _sign(kind: str, payload: dict) -> str:
    from django.core import signing

    blob = signing.dumps(payload, key=_key(), salt=f"chiron-mcp.oauth.{kind}", compress=True)
    # Django joins the parts with ":", which RFC 6750 does not allow in a bearer token.
    # "~" is allowed and never occurs in the parts themselves.
    return blob.replace(":", "~")


def _unsign(kind: str, blob: str, max_age: int | None) -> dict | None:
    from django.core import signing

    try:
        data = signing.loads(
            blob.replace("~", ":"), key=_key(), salt=f"chiron-mcp.oauth.{kind}", max_age=max_age,
            # Without this Django also accepts settings.SECRET_KEY_FALLBACKS, and the
            # point of a separate key is that Django's own are never enough.
            fallback_keys=[],
        )
    except signing.BadSignature:  # includes SignatureExpired
        return None
    except Exception:  # noqa: BLE001  (malformed input must never be a 500)
        return None
    return data if isinstance(data, dict) else None


def _mac(label: str, value: str) -> str:
    return hmac.new(_key().encode(), f"{label}:{value}".encode(), hashlib.sha256).hexdigest()


def _client_tag(client_id: str) -> str:
    """A short stand-in for a client id, which is itself a long signed blob."""
    return hashlib.sha256(client_id.encode()).hexdigest()[:24]


# --- Chiron users (blocking; call through a worker thread) --------------------


def _live_user(username: str):
    """The active Django user of that name, or None."""
    from django.contrib.auth import get_user_model

    return get_user_model().objects.filter(username=username, is_active=True).first()


def _user_stamp(user) -> str:
    """Changes when the user's password does, which invalidates their tokens."""
    return _mac("user", f"{user.pk}:{user.password}")[:16]


def _stamped_user(username: str, stamp: str):
    user = _live_user(username)
    if user is None or not hmac.compare_digest(_user_stamp(user), stamp):
        return None
    return user


def _check_password(username: str, password: str) -> str | None:
    """Django's own credential check, so the deployment's auth backends apply."""
    from django.contrib.auth import authenticate

    user = authenticate(request=None, username=username, password=password)
    return user.username if user is not None and user.is_active else None


def _acceptable(username: str) -> str | None:
    """None if this person may use the server, else why not."""
    try:
        identity._django_user(username, allow_superuser=True)
    except identity.AccessError as exc:
        return str(exc)
    return None


# --- the provider ------------------------------------------------------------


def _is_loopback_redirect(uri) -> bool:
    return uri.scheme == "http" and (uri.host or "").strip("[]") in _LOOPBACK


def _same_resource(requested: str) -> bool:
    """Is `requested` this endpoint, under either spelling of the loopback host?"""
    if CONFIG.hosted:
        return requested.rstrip("/") == resource_url()
    try:
        parts = urlsplit(requested)
        return (
            parts.scheme == "http"
            and (parts.hostname or "") in _LOOPBACK
            and parts.port == CONFIG.http_port
            and parts.path.rstrip("/") == "/mcp"
        )
    except ValueError:
        return False


class ChironOAuthProvider:
    """The MCP library's authorization-server hooks, backed by Chiron's own users."""

    def __init__(self) -> None:
        # Both maps are touched only from the event loop, so they need no lock.
        self._pending: dict[str, dict] = {}  # txn -> an unfinished login
        self._codes: dict[str, AuthorizationCode] = {}

    # -- clients: stateless, the client_id *is* the signed registration --

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        data = _unsign("client", client_id, max_age=None)
        if not data:
            return None
        confidential = data.get("m") != "none"
        return OAuthClientInformationFull(
            client_id=client_id,
            client_secret=_mac("client-secret", client_id) if confidential else None,
            client_secret_expires_at=0 if confidential else None,
            client_id_issued_at=data.get("t"),
            redirect_uris=data.get("r") or [],
            client_name=data.get("n"),
            token_endpoint_auth_method=data.get("m"),
            grant_types=data.get("g") or ["authorization_code", "refresh_token"],
            response_types=["code"],
            scope=SCOPE,
        )

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        uris = client_info.redirect_uris or []
        if not uris or len(uris) > MAX_REDIRECT_URIS:
            raise RegistrationError(
                "invalid_redirect_uri", f"Register between 1 and {MAX_REDIRECT_URIS} redirect URIs."
            )
        for uri in uris:
            if not _is_loopback_redirect(uri):
                raise RegistrationError(
                    "invalid_redirect_uri",
                    "This server is reachable only from the machine it runs on, so "
                    f"redirect URIs must be http://localhost or http://127.0.0.1. Got {uri}.",
                )
        method = client_info.token_endpoint_auth_method or "none"
        # The library reads these back from the same object to build its response, so
        # replacing the id and secret here is what the client receives.
        client_info.scope = SCOPE
        client_info.client_id = _sign("client", {
            "r": [str(u) for u in uris],
            "n": (client_info.client_name or "")[:80],
            "m": method,
            "g": list(client_info.grant_types),
            "t": int(time.time()),
        })
        if client_info.client_secret:
            client_info.client_secret = _mac("client-secret", client_info.client_id)

    # -- authorize: park the request and send the browser to the login page --

    def _prune(self) -> None:
        now = time.time()
        for txn in [t for t, p in self._pending.items() if p["expires"] < now]:
            del self._pending[txn]
        for code in [c for c, a in self._codes.items() if a.expires_at < now]:
            del self._codes[code]

    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        if params.resource and not _same_resource(params.resource):
            raise AuthorizeError(
                "invalid_target", f"This server only issues tokens for {resource_url()}."
            )
        self._prune()
        if len(self._pending) >= MAX_PENDING:
            raise AuthorizeError("temporarily_unavailable", "Too many sign-ins in progress.")
        txn = secrets.token_urlsafe(32)
        self._pending[txn] = {
            "client_id": client.client_id,
            "client_name": client.client_name or "An MCP client",
            "params": params,
            "expires": time.time() + LOGIN_TTL,
            "attempts": 0,
        }
        return f"{issuer_url()}{LOGIN_PATH}?txn={txn}"

    def pending(self, txn: str) -> dict | None:
        self._prune()
        return self._pending.get(txn)

    def abandon(self, txn: str) -> None:
        self._pending.pop(txn, None)

    def issue_code(self, txn: str, username: str) -> str:
        """Finish a login: trade the parked request for an authorization code."""
        entry = self._pending.pop(txn)
        params: AuthorizationParams = entry["params"]
        code = secrets.token_urlsafe(32)
        self._codes[code] = AuthorizationCode(
            code=code,
            scopes=[SCOPE],
            expires_at=time.time() + CODE_TTL,
            client_id=entry["client_id"],
            code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            resource=resource_url(),
            subject=username,
        )
        return code

    # -- tokens --

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        # Popped on first sight: a code is good for one attempt, right or wrong.
        self._prune()
        return self._codes.pop(authorization_code, None)

    def _issue(self, client_id: str, user) -> OAuthToken:
        claims = {"u": user.username, "c": _client_tag(client_id), "h": _user_stamp(user)}
        return OAuthToken(
            access_token=_sign("access", claims),
            refresh_token=_sign("refresh", claims),
            expires_in=ACCESS_TTL,
            scope=SCOPE,
        )

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        user = await anyio.to_thread.run_sync(_live_user, authorization_code.subject or "")
        if user is None:
            raise TokenError("invalid_grant", "That Chiron user no longer exists or is inactive.")
        return self._issue(client.client_id, user)

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        data = _unsign("refresh", refresh_token, max_age=REFRESH_TTL)
        if not data or data.get("c") != _client_tag(client.client_id):
            return None
        return RefreshToken(
            token=refresh_token,
            client_id=client.client_id,
            scopes=[SCOPE],
            resource=resource_url(),
            subject=data.get("u"),
        )

    async def exchange_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: RefreshToken, scopes: list[str]
    ) -> OAuthToken:
        data = _unsign("refresh", refresh_token.token, max_age=REFRESH_TTL) or {}
        user = await anyio.to_thread.run_sync(_stamped_user, data.get("u", ""), data.get("h", ""))
        if user is None:
            raise TokenError(
                "invalid_grant",
                "That Chiron user is gone, inactive, or has changed password. Sign in again.",
            )
        return self._issue(client.client_id, user)

    async def load_access_token(self, token: str) -> AccessToken | None:
        data = _unsign("access", token, max_age=ACCESS_TTL)
        if not data:
            return None
        user = await anyio.to_thread.run_sync(_stamped_user, data.get("u", ""), data.get("h", ""))
        if user is None:
            return None
        return AccessToken(
            token=token,
            client_id=data.get("c", ""),
            scopes=[SCOPE],
            resource=resource_url(),
            subject=user.username,
            claims={"iss": issuer_url()},
        )

    async def revoke_token(self, token) -> None:
        # Signed tokens cannot be revoked individually; see the module docstring.
        return None


PROVIDER = ChironOAuthProvider()


def server_kwargs() -> dict:
    """Constructor arguments that make an MCPServer require a Chiron login."""
    _key()  # fail at startup, not at the first login, if the key cannot be made
    return {
        "auth_server_provider": PROVIDER,
        "auth": AuthSettings(
            issuer_url=issuer_url(),
            resource_server_url=resource_url(),
            validate_token_resource=True,
            required_scopes=[SCOPE],
            client_registration_options=ClientRegistrationOptions(
                enabled=True, valid_scopes=[SCOPE], default_scopes=[SCOPE]
            ),
        ),
    }


# --- the login page ----------------------------------------------------------

# The page may load nothing (Content-Security-Policy: default-src 'none'), so it is
# self-contained: system fonts, inline CSS, and icons drawn as inline SVG markup.
_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>Sign in to Chiron</title>
<style>
  :root { --bg: #f4f2f8; --card: #fff; --text: #1f1d24; --muted: #6b6775;
          --line: #e5e1ec; --field: #fbfaff; --brand: #5b2a86; --brand-hi: #4a2170;
          --brand-soft: #f1eaf8; --on-brand: #fff; --bad: #b3261e; --bad-soft: #fdecea;
          --ring: rgba(91, 42, 134, .28); --shadow: 0 1px 2px rgba(31, 29, 36, .06),
          0 12px 32px -12px rgba(31, 29, 36, .18); }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #131118; --card: #1d1a23; --text: #ece9f1; --muted: #a39fae;
            --line: #322d3b; --field: #17151c; --brand: #b48ee0; --brand-hi: #c7a6ea;
            --brand-soft: #2a2236; --on-brand: #1d1a23; --bad: #f2b8b5; --bad-soft: #3b1f1f;
            --ring: rgba(180, 142, 224, .35); --shadow: 0 12px 32px -12px rgba(0, 0, 0, .6); }
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; }
  body { min-height: 100vh; display: flex; flex-direction: column; align-items: center;
         justify-content: center; gap: 18px; padding: 32px 16px; background: var(--bg);
         color: var(--text);
         font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  main { width: 100%; max-width: 440px; background: var(--card); border: 1px solid var(--line);
         border-radius: 14px; padding: 30px 30px 26px; box-shadow: var(--shadow); }
  .brand { display: flex; align-items: center; gap: 10px; margin-bottom: 22px;
           font-weight: 600; font-size: 17px; letter-spacing: .2px; }
  .brand svg rect { fill: var(--brand); }
  .brand svg path, .brand svg circle { stroke: var(--on-brand); }
  .brand svg circle { fill: var(--on-brand); }
  h1 { margin: 0 0 14px; font-size: 22px; line-height: 1.25; font-weight: 650; }
  p { margin: 0 0 14px; }
  .muted { color: var(--muted); font-size: 13px; }
  .link { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin: 0 0 16px; }
  .chip { display: inline-flex; align-items: center; gap: 6px; max-width: 100%;
          padding: 5px 11px; border-radius: 999px; background: var(--brand-soft);
          color: var(--brand); font-size: 13px; font-weight: 600; overflow-wrap: anywhere; }
  .chip svg, .perms svg, .err svg { flex: none; }
  .arrow { color: var(--muted); }
  .perms { list-style: none; margin: 0 0 18px; padding: 14px 16px; border: 1px solid var(--line);
           border-radius: 10px; display: grid; gap: 9px; font-size: 14px; }
  .perms li { display: flex; gap: 10px; align-items: flex-start; }
  .perms svg { margin-top: 2px; color: var(--brand); }
  .err { display: flex; gap: 9px; align-items: flex-start; background: var(--bad-soft);
         color: var(--bad); padding: 10px 12px; border-radius: 8px; font-size: 14px; }
  .err svg { margin-top: 2px; }
  label { display: block; font-size: 13px; font-weight: 600; margin: 12px 0 5px; }
  input[type=text], input[type=password] { width: 100%; font: inherit; color: var(--text);
         padding: 10px 12px; background: var(--field); border: 1px solid var(--line);
         border-radius: 8px; }
  input:focus { outline: none; border-color: var(--brand); box-shadow: 0 0 0 3px var(--ring); }
  button { width: 100%; display: flex; align-items: center; justify-content: center; gap: 10px;
           font: inherit; font-weight: 600; padding: 11px 16px; border-radius: 9px;
           cursor: pointer; border: 1px solid var(--brand); background: var(--brand);
           color: var(--on-brand); margin-top: 16px; }
  button:hover { background: var(--brand-hi); border-color: var(--brand-hi); }
  button:focus-visible, summary:focus-visible { outline: 3px solid var(--ring);
         outline-offset: 2px; }
  button.plain { background: transparent; color: var(--text); border-color: var(--line);
                 margin-top: 10px; font-weight: 500; }
  button.plain:hover { background: var(--brand-soft); }
  .avatar { width: 26px; height: 26px; border-radius: 50%; display: inline-grid;
            place-items: center; background: var(--on-brand); color: var(--brand);
            font-size: 13px; font-weight: 700; text-transform: uppercase; }
  details { margin-top: 16px; border-top: 1px solid var(--line); padding-top: 12px; }
  summary { cursor: pointer; color: var(--brand); font-size: 14px; font-weight: 600; }
  .fine { margin: 18px 0 0; padding-top: 14px; border-top: 1px solid var(--line); }
  code { font: 12.5px ui-monospace, SFMono-Regular, Menlo, monospace; background: var(--bg);
         padding: 1px 6px; border-radius: 5px; }
  footer { color: var(--muted); font-size: 12px; }
</style></head><body><main>
<div class="brand"><svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true">
<rect width="32" height="32" rx="9"/><path d="M21.6 11.4a6.6 6.6 0 1 0 0 9.2" fill="none"
stroke-width="2.6" stroke-linecap="round"/><circle cx="22.6" cy="16" r="1.5"/></svg>Chiron</div>
<h1>Sign in to Chiron</h1>
<!--BODY-->
</main><footer>Chiron &middot; sign-in for MCP clients</footer></body></html>"""

# Small inline icons (currentColor), so they follow the text colour in both themes.
_ICONS = {
    "app": '<path d="M4 5h16v11H4z M8 20h8 M12 16v4" />',
    "query": '<circle cx="11" cy="11" r="6" /><path d="M20 20l-4.3-4.3" />',
    "shield": '<path d="M12 3l7 3v5c0 4.4-3 8.3-7 9.5C8 19.3 5 15.4 5 11V6z" />',
    "save": '<path d="M5 4h11l3 3v13H5z M8 4v5h7V4 M8 20v-6h8v6" />',
    "alert": '<circle cx="12" cy="12" r="9" /><path d="M12 7.5v5.5 M12 16.5v.01" />',
}


def _icon(name: str, size: int = 16) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.9" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">{_ICONS[name]}</svg>'
    )


def _html(body: str, status: int = 200) -> HTMLResponse:
    return HTMLResponse(
        _PAGE.replace("<!--BODY-->", body),
        status_code=status,
        headers={
            "Cache-Control": "no-store",
            # same-origin, not no-referrer: it equally keeps this page's URL out of the
            # Referer sent to the client's callback, but under no-referrer a browser
            # posts the form with "Origin: null", which _local() rightly refuses.
            "Referrer-Policy": "same-origin",
            # Never inside a frame, so the buttons cannot be click-jacked.
            "X-Frame-Options": "DENY",
            "Content-Security-Policy": (
                "default-src 'none'; style-src 'unsafe-inline'; "
                "frame-ancestors 'none'; base-uri 'none'"
            ),
        },
    )


def _error(message: str) -> str:
    return f'<p class="err" role="alert">{_icon("alert")}<span>{html.escape(message)}</span></p>'


def _problem(message: str, status: int = 400) -> HTMLResponse:
    return _html(
        _error(message)
        + '<p class="muted">Close this tab and start the sign-in again from your MCP client.</p>',
        status,
    )


def _login_form(txn: str, entry: dict, session_user: str | None, error: str | None) -> HTMLResponse:
    e = html.escape
    params: AuthorizationParams = entry["params"]
    target = urlsplit(str(params.redirect_uri))
    client = e(entry["client_name"])
    perms = [
        ("query", "Run Chiron queries and read the results as you"),
        ("shield", "See only what your Chiron account can see, within your access level"),
    ]
    if CONFIG.allow_save:
        perms.append(("save", "Save reports and replace your open query"))
    parts = [
        f'<p class="link"><span class="chip">{_icon("app", 14)}{client}</span>'
        '<span class="arrow" aria-hidden="true">&rarr;</span>'
        '<span class="chip">Chiron</span></p>',
        f"<p><strong>{client}</strong> wants to query Chiron as you. It will be able to:</p>",
        '<ul class="perms">'
        + "".join(f"<li>{_icon(icon)}<span>{text}</span></li>" for icon, text in perms)
        + "</ul>",
    ]
    if error:
        parts.append(_error(error))
    hidden = f'<input type="hidden" name="txn" value="{e(txn)}">'
    password_form = (
        f'<form method="post" action="{_login_action()}" autocomplete="off">{hidden}'
        '<input type="hidden" name="action" value="password">'
        '<label for="u">Chiron username</label>'
        '<input id="u" type="text" name="username" autocapitalize="none" '
        'autocomplete="username" required>'
        '<label for="p">Password</label>'
        '<input id="p" type="password" name="password" autocomplete="current-password" required>'
        '<button type="submit">Sign in</button></form>'
    )
    if session_user:
        name = e(session_user)
        parts.append(
            f'<form method="post" action="{_login_action()}">{hidden}'
            '<input type="hidden" name="action" value="session">'
            '<button type="submit"><span class="avatar" aria-hidden="true">'
            f"{e(session_user[:1])}</span>"
            f"<span>Continue as {name}</span></button></form>"
            '<p class="muted" style="margin:8px 0 0;text-align:center">You are logged in to '
            "Chiron in this browser.</p>"
            f"<details><summary>Use a different Chiron account</summary>{password_form}</details>"
        )
    else:
        parts.append(password_form)
    parts.append(
        f'<form method="post" action="{_login_action()}">{hidden}'
        '<input type="hidden" name="action" value="deny">'
        '<button type="submit" class="plain">Cancel</button></form>'
        f'<p class="muted fine">The sign-in goes back to <code>{e(target.netloc)}</code> on '
        "this machine. Only continue if you started it from your MCP client.</p>"
    )
    return _html("".join(parts), 401 if error else 200)


def _local(request: Request) -> bool:
    """Is this request addressed to us by a loopback name, and not sent by another site?

    The Host check stops a hostile site that resolves its own name to 127.0.0.1 from
    being treated as this page; the Origin check stops any other site posting the form.
    "Origin: null" (a sandboxed frame, a data: page) counts as another site.
    """
    raw_host = request.headers.get("host", "")
    origin = request.headers.get("origin")
    if CONFIG.hosted:
        # Behind a proxy the Host is whatever the proxy sends, and DNS rebinding onto a
        # loopback port is not the threat for a server on another machine. What still
        # matters is that only the page itself posts the form: Origin, when a browser
        # sends one, must be the public address's origin ("null" never is).
        public = urlsplit(CONFIG.public_url)
        ok = origin is None or origin == f"{public.scheme}://{public.netloc}"
        if not ok:
            print(
                f"chiron-mcp: sign-in page refused {request.method} with Origin={origin!r}; "
                f"expected {public.scheme}://{public.netloc}",
                file=sys.stderr,
            )
        return ok
    ok = False
    try:
        host = urlsplit(f"//{raw_host}")
        ok = (host.hostname or "") in _LOOPBACK and (host.port or 80) == CONFIG.http_port
        if ok and origin is not None:
            o = urlsplit(origin)
            ok = (
                o.scheme == "http"
                and (o.hostname or "") in _LOOPBACK
                and o.port == CONFIG.http_port
            )
    except ValueError:
        ok = False
    if not ok:
        # Say why in the server log: from the browser this is otherwise a dead end.
        print(
            f"chiron-mcp: sign-in page refused {request.method} with Host={raw_host!r} "
            f"Origin={origin!r}; expected a loopback name on port {CONFIG.http_port}",
            file=sys.stderr,
        )
    return ok


async def login(request: Request) -> Response:
    """GET shows the page for a parked /authorize request; POST finishes or cancels it."""
    if not _local(request):
        return _problem("This page only answers on this machine's own address.", 421)

    if request.method == "GET":
        form = {}
        txn = request.query_params.get("txn", "")
    else:
        form = await request.form()
        txn = str(form.get("txn", ""))

    entry = PROVIDER.pending(txn)
    if entry is None:
        return _problem("This sign-in has expired or was already used.")
    params: AuthorizationParams = entry["params"]

    session_user = await anyio.to_thread.run_sync(
        identity.session_username, request.headers.get("cookie")
    )
    if request.method == "GET":
        return _login_form(txn, entry, session_user, None)

    action = str(form.get("action", ""))
    if action == "deny":
        PROVIDER.abandon(txn)
        return RedirectResponse(
            construct_redirect_uri(
                str(params.redirect_uri), error="access_denied", state=params.state
            ),
            status_code=302,
            headers={"Cache-Control": "no-store"},
        )

    if action == "session":
        # Re-read from the cookie on this request; the page's own claim is not trusted.
        username = session_user
        if not username:
            return _login_form(txn, entry, None, "Your Chiron login has ended. Sign in below.")
    elif action == "password":
        username = await anyio.to_thread.run_sync(
            _check_password, str(form.get("username", "")).strip(), str(form.get("password", ""))
        )
        if not username:
            entry["attempts"] += 1
            if entry["attempts"] >= MAX_ATTEMPTS:
                PROVIDER.abandon(txn)
                return _problem("Too many failed attempts.", 403)
            return _login_form(txn, entry, session_user, "That username and password did not match.")
    else:
        return _problem("Unrecognised request.")

    refusal = await anyio.to_thread.run_sync(_acceptable, username)
    if refusal:
        return _login_form(txn, entry, session_user, refusal)

    code = PROVIDER.issue_code(txn, username)
    return RedirectResponse(
        construct_redirect_uri(str(params.redirect_uri), code=code, state=params.state),
        status_code=302,
        headers={"Cache-Control": "no-store"},
    )


def register_routes(mcp) -> None:
    """Add the login page to an MCPServer built with `server_kwargs()`."""
    mcp.custom_route(LOGIN_PATH, methods=["GET", "POST"], include_in_schema=False)(login)

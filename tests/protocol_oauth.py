"""Drive the HTTP endpoint's OAuth login end to end, as two different Chiron users.

Starts `chiron-mcp` with CHIRON_MCP_TRANSPORT=http and CHIRON_MCP_HTTP_AUTH=oauth on a free
loopback port, with no CHIRON_MCP_USERNAME at all, then plays an MCP client: registers,
runs the authorization-code flow with PKCE through the login page, and calls tools with
the token. The point it proves is the last one: two people signed in through the same
endpoint get their own Chiron permissions, not a shared service account's.

It needs one account with subject-level access and one with aggregate-only access. The
defaults are the bundled demo's:

    .venv/bin/python -m tests.protocol_oauth
    CHIRON_MCP_TEST_USER=alice:secret CHIRON_MCP_TEST_AGG_USER=bob:secret \\
        .venv/bin/python -m tests.protocol_oauth

Nothing is changed in Chiron except one login session, created for the cookie check and
deleted again.
"""

import asyncio
import base64
import hashlib
import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

from mcp import ClientSession
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONSOLE = os.path.join(HERE, ".venv", "bin", "chiron-mcp")
REDIRECT = "http://localhost:53999/callback"  # never listened on; we read the Location

FULL = tuple(os.environ.get("CHIRON_MCP_TEST_USER", "demouser:demo1234").split(":", 1))
AGG = tuple(os.environ.get("CHIRON_MCP_TEST_AGG_USER", "agguser:demo1234").split(":", 1))

RESULTS: list[bool] = []


def check(ok: bool, what: str, detail: str = "") -> bool:
    RESULTS.append(bool(ok))
    print(f"{'PASS' if ok else 'FAIL'}  {what}" + (f"  [{detail}]" if detail and not ok else ""))
    return bool(ok)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def http(method: str, url: str, *, form: dict | None = None, body: dict | None = None,
         headers: dict | None = None) -> tuple[int, dict, str]:
    data, hdrs = None, dict(headers or {})
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        hdrs["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        data = json.dumps(body).encode()
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
    try:
        with _OPENER.open(req, timeout=20) as resp:
            return resp.status, dict(resp.headers), resp.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read().decode()


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_listening(port: int, proc: subprocess.Popen, seconds: float = 60) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if proc.poll() is not None:
            return False
        with socket.socket() as s:
            s.settimeout(0.5)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.3)
    return False


# --- the client side of the flow ---------------------------------------------


def register(base: str, redirect: str = REDIRECT, name: str = "oauth test client"):
    return http("POST", f"{base}/register", body={
        "redirect_uris": [redirect], "client_name": name,
        "token_endpoint_auth_method": "none",
        "grant_types": ["authorization_code", "refresh_token"], "response_types": ["code"],
    })


def begin(base: str, client_id: str) -> tuple[str, str, str]:
    """Hit /authorize; return (txn, pkce verifier, state)."""
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    state = secrets.token_urlsafe(8)
    query = urllib.parse.urlencode({
        "response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT,
        "code_challenge": challenge, "code_challenge_method": "S256", "state": state,
        "scope": "chiron", "resource": f"{base}/mcp",
    })
    status, headers, _ = http("GET", f"{base}/authorize?{query}")
    loc = headers.get("Location") or headers.get("location") or ""
    txn = urllib.parse.parse_qs(urllib.parse.urlsplit(loc).query).get("txn", [""])[0]
    if status != 302 or "/oauth/login" not in loc or not txn:
        raise RuntimeError(f"/authorize did not lead to the login page: {status} {loc}")
    return txn, verifier, state


def submit(base: str, txn: str, action: str, *, cookie: str | None = None, **fields):
    headers = {"Origin": base}
    if cookie:
        headers["Cookie"] = cookie
    return http("POST", f"{base}/oauth/login", form={"txn": txn, "action": action, **fields},
                headers=headers)


def code_from(headers: dict, state: str) -> str | None:
    loc = headers.get("Location") or headers.get("location") or ""
    if not loc.startswith(REDIRECT):
        return None
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(loc).query)
    if q.get("state", [""])[0] != state:
        return None
    return q.get("code", [None])[0]


def exchange(base: str, client_id: str, code: str, verifier: str) -> tuple[int, dict]:
    status, _, text = http("POST", f"{base}/token", form={
        "grant_type": "authorization_code", "client_id": client_id, "code": code,
        "code_verifier": verifier, "redirect_uri": REDIRECT,
    })
    return status, json.loads(text or "{}")


def sign_in(base: str, client_id: str, user: tuple[str, str]) -> dict:
    """The whole flow with a password; returns the token response."""
    txn, verifier, state = begin(base, client_id)
    _, headers, _ = submit(base, txn, "password", username=user[0], password=user[1])
    code = code_from(headers, state)
    if not code:
        raise RuntimeError(f"no authorization code for {user[0]}")
    status, tokens = exchange(base, client_id, code, verifier)
    if status != 200:
        raise RuntimeError(f"token exchange failed for {user[0]}: {tokens}")
    return tokens


def initialize_status(base: str, token: str | None) -> tuple[int, dict]:
    headers = {"Accept": "application/json, text/event-stream"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    status, hdrs, _ = http("POST", f"{base}/mcp", headers=headers, body={
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                   "clientInfo": {"name": "probe", "version": "0"}},
    })
    return status, hdrs


async def as_user(base: str, token: str) -> dict:
    """Connect with a token; report who the server says we are and what we may do."""
    async with create_mcp_http_client(headers={"Authorization": f"Bearer {token}"}) as hc:
        async with streamable_http_client(f"{base}/mcp", http_client=hc) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                res = await session.call_tool("chiron_datasets", {})
                info = json.loads(res.content[0].text)
                usable = [d for d in info.get("datasets", []) if d.get("accessible")]
                out = {"identity": info.get("identity"), "tools": len(tools.tools),
                       "levels": sorted({d["access_level"] for d in usable}), "count": None}
                if usable:
                    res = await session.call_tool(
                        "chiron_count_cohort",
                        {"dataset_id": usable[0]["dataset_id"], "cohort_def": []},
                    )
                    out["count"] = json.loads(res.content[0].text)
                return out


async def interleaved(base: str, token_a: str, token_b: str, rounds: int = 4) -> list[tuple[str, str]]:
    """Two people connected at once, calling in turn and together; who does each call act as?"""
    async def whoami(session) -> str:
        res = await session.call_tool("chiron_datasets", {})
        return json.loads(res.content[0].text).get("identity")

    async with create_mcp_http_client(headers={"Authorization": f"Bearer {token_a}"}) as ha, \
            create_mcp_http_client(headers={"Authorization": f"Bearer {token_b}"}) as hb:
        async with streamable_http_client(f"{base}/mcp", http_client=ha) as (ra, wa), \
                streamable_http_client(f"{base}/mcp", http_client=hb) as (rb, wb):
            async with ClientSession(ra, wa) as a, ClientSession(rb, wb) as b:
                await asyncio.gather(a.initialize(), b.initialize())
                seen = []
                for _ in range(rounds):
                    seen.append(tuple(await asyncio.gather(whoami(a), whoami(b))))
                    seen.append((await whoami(a), await whoami(b)))
                return seen


def session_of(base: str, token: str) -> str:
    """Open an MCP session with this token and return its id."""
    _, headers = initialize_status(base, token)
    return headers.get("mcp-session-id") or headers.get("Mcp-Session-Id") or ""


# --- the checks ---------------------------------------------------------------


def run(base: str, state_dir: str) -> None:
    # Discovery, and the refusal that starts every client's flow.
    status, headers = initialize_status(base, None)
    www = headers.get("www-authenticate") or headers.get("WWW-Authenticate") or ""
    check(status == 401 and "resource_metadata=" in www, "no token: 401 pointing at the metadata",
          f"{status} {www}")
    _, _, text = http("GET", f"{base}/.well-known/oauth-protected-resource/mcp")
    prm = json.loads(text)
    check(prm.get("resource") == f"{base}/mcp" and prm.get("authorization_servers") == [base],
          "protected-resource metadata names this server", text)
    _, _, text = http("GET", f"{base}/.well-known/oauth-authorization-server")
    asm = json.loads(text)
    check(asm.get("registration_endpoint") == f"{base}/register"
          and "S256" in asm.get("code_challenge_methods_supported", []),
          "authorization-server metadata offers registration and PKCE", text)

    # Registration.
    status, _, text = register(base, redirect="https://attacker.example/cb")
    check(status == 400 and "invalid_redirect_uri" in text,
          "a non-loopback redirect URI is refused", f"{status} {text}")
    status, _, text = register(base)
    client_id = json.loads(text).get("client_id", "")
    check(status == 201 and client_id, "a loopback client registers", f"{status} {text}")

    # The login page.
    _, _, text = register(base, name="<script>alert(1)</script>")
    hostile = json.loads(text)["client_id"]
    txn, _, _ = begin(base, hostile)
    status, headers, page = http("GET", f"{base}/oauth/login?txn={txn}")
    check(status == 200 and "<script>alert" not in page and "&lt;script&gt;" in page,
          "the login page escapes the client's name")
    check(headers.get("x-frame-options", headers.get("X-Frame-Options", "")).upper() == "DENY",
          "the login page cannot be framed")
    # Under "no-referrer" a real browser posts the form with "Origin: null" and every
    # sign-in dies on the guard below, which a scripted client never notices.
    policy = headers.get("referrer-policy", headers.get("Referrer-Policy", ""))
    check(policy == "same-origin", "the page's referrer policy lets a browser send its origin",
          policy)
    status, _, _ = http("POST", f"{base}/oauth/login",
                        form={"txn": txn, "action": "password", "username": FULL[0],
                              "password": FULL[1]},
                        headers={"Origin": "null"})
    check(status == 421, "a form posted with an opaque origin is refused", str(status))
    status, _, _ = http("POST", f"{base}/oauth/login",
                        form={"txn": txn, "action": "password", "username": FULL[0],
                              "password": FULL[1]},
                        headers={"Origin": "https://attacker.example"})
    check(status == 421, "a form posted from another site is refused", str(status))
    status, _, _ = http("GET", f"{base}/oauth/login?txn={txn}", headers={"Host": "evil.example"})
    check(status == 421, "the page refuses a foreign Host header", str(status))

    txn, verifier, state = begin(base, client_id)
    status, headers, page = submit(base, txn, "password", username=FULL[0], password="wrong")
    check(status == 401 and code_from(headers, state) is None and "did not match" in page,
          "a wrong password gets no code", str(status))
    status, headers, _ = submit(base, txn, "session")
    check(status == 401 and code_from(headers, state) is None,
          "'continue as' without a Chiron session gets no code", str(status))
    status, headers, _ = submit(base, txn, "password", username=FULL[0], password=FULL[1])
    code = code_from(headers, state)
    check(status == 302 and bool(code), "the right password returns a code and the state",
          str(status))

    # The token endpoint.
    status, body = exchange(base, client_id, code or "", "not-the-verifier")
    check(status == 400 and body.get("error") == "invalid_grant", "a wrong PKCE verifier is refused",
          json.dumps(body))
    status, body = exchange(base, client_id, code or "", verifier)
    check(status == 400, "the code cannot be tried a second time", json.dumps(body))

    full = sign_in(base, client_id, FULL)
    agg = sign_in(base, client_id, AGG)
    check(bool(full.get("access_token")) and bool(full.get("refresh_token")),
          "a completed sign-in yields access and refresh tokens")

    # What the feature is for: each person is themselves.
    me = asyncio.run(as_user(base, full["access_token"]))
    check(me["identity"] == FULL[0], f"signed in as {FULL[0]}: the server acts as {FULL[0]}",
          json.dumps(me))
    check(isinstance(me["count"], dict) and "subject_count" in me["count"],
          f"{FULL[0]} may count subjects", json.dumps(me["count"]))
    other = asyncio.run(as_user(base, agg["access_token"]))
    check(other["identity"] == AGG[0], f"signed in as {AGG[0]}: the server acts as {AGG[0]}",
          json.dumps(other))
    check(other["levels"] == ["agg"] and isinstance(other["count"], dict)
          and "subject-level" in str(other["count"].get("error", "")),
          f"{AGG[0]} is refused subject-level data through the same endpoint",
          json.dumps(other))

    # Two people at once never see each other's identity.
    seen = asyncio.run(interleaved(base, full["access_token"], agg["access_token"]))
    check(bool(seen) and all(pair == (FULL[0], AGG[0]) for pair in seen),
          "two users connected at once each stay themselves", json.dumps(seen))

    # One person's token cannot ride on another person's MCP session.
    sid = session_of(base, full["access_token"])
    status, _, text = http("POST", f"{base}/mcp", headers={
        "Accept": "application/json, text/event-stream", "Mcp-Session-Id": sid,
        "Authorization": f"Bearer {agg['access_token']}",
    }, body={"jsonrpc": "2.0", "id": 7, "method": "tools/call",
             "params": {"name": "chiron_datasets", "arguments": {}}})
    check(bool(sid) and status in (403, 404) and FULL[0] not in text,
          f"{AGG[0]}'s token is refused on {FULL[0]}'s session", f"{status} {text[:200]}")

    # Tokens that must not work.
    good = full["access_token"]
    forged = good[:-3] + ("AAA" if not good.endswith("AAA") else "BBB")
    check(initialize_status(base, forged)[0] == 401, "a tampered token is refused")
    check(initialize_status(base, full["refresh_token"])[0] == 401,
          "a refresh token is not accepted as an access token")

    os.environ["CHIRON_MCP_STATE_DIR"] = state_dir  # sign with the server's own key
    from chiron_mcp.bootstrap import ensure_django

    ensure_django()
    from chiron_mcp import oauth

    stale = oauth._sign("access", {"u": FULL[0], "c": "x", "h": "0" * 16})
    check(initialize_status(base, stale)[0] == 401,
          "a correctly signed token is refused once the user's password fingerprint differs")
    ghost = oauth._sign("access", {"u": "no-such-user-xyz", "c": "x", "h": "0" * 16})
    check(initialize_status(base, ghost)[0] == 401, "a token for a user who does not exist is refused")

    # Refresh.
    status, _, text = http("POST", f"{base}/token", form={
        "grant_type": "refresh_token", "client_id": client_id,
        "refresh_token": full["refresh_token"],
    })
    renewed = json.loads(text or "{}")
    check(status == 200 and initialize_status(base, renewed.get("access_token"))[0] == 200,
          "a refresh token yields a working access token", text)
    status, _, text = register(base)
    stranger = json.loads(text)["client_id"]
    status, _, text = http("POST", f"{base}/token", form={
        "grant_type": "refresh_token", "client_id": stranger,
        "refresh_token": full["refresh_token"],
    })
    check(status == 400, "another client cannot use that refresh token", text)

    # The browser's existing Chiron login.
    from django.contrib.auth import get_user_model
    from django.contrib.sessions.backends.db import SessionStore

    user = get_user_model().objects.get(username=FULL[0])
    store = SessionStore()
    store["_auth_user_id"] = str(user.pk)
    store["_auth_user_backend"] = "django.contrib.auth.backends.ModelBackend"
    store["_auth_user_hash"] = user.get_session_auth_hash()
    store.set_expiry(600)
    store.create()
    try:
        cookie = f"sessionid={store.session_key}"
        txn, verifier, state = begin(base, client_id)
        _, _, page = http("GET", f"{base}/oauth/login?txn={txn}", headers={"Cookie": cookie})
        check(f"Continue as {FULL[0]}" in page, "the page offers the browser's Chiron login")
        status, headers, _ = submit(base, txn, "session", cookie=cookie)
        code = code_from(headers, state)
        status, tokens = exchange(base, client_id, code or "", verifier)
        who = asyncio.run(as_user(base, tokens["access_token"]))["identity"] if status == 200 else None
        check(who == FULL[0], "continuing with that login signs in as the same user", str(who))
    finally:
        store.delete()

    # Cancel.
    txn, _, state = begin(base, client_id)
    status, headers, _ = submit(base, txn, "deny")
    loc = headers.get("Location") or headers.get("location") or ""
    check(status == 302 and "error=access_denied" in loc, "cancel returns access_denied", loc)


def main() -> int:
    port = _free_port()
    base = f"http://localhost:{port}"
    with tempfile.TemporaryDirectory(prefix="chiron-oauth-test-") as state_dir:
        env = dict(os.environ, CHIRON_MCP_TRANSPORT="http", CHIRON_MCP_HTTP_AUTH="oauth",
                   CHIRON_MCP_HTTP_PORT=str(port), CHIRON_MCP_STATE_DIR=state_dir)
        env.pop("CHIRON_MCP_USERNAME", None)  # identity must come from the login alone
        env.pop("CHIRON_MCP_OAUTH_SECRET", None)
        cmd = [CONSOLE] if os.path.exists(CONSOLE) else [sys.executable, "-m", "chiron_mcp.server"]
        proc = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE, text=True)
        try:
            if not _wait_listening(port, proc):
                print("FAIL  server did not start listening")
                print((proc.stderr.read() if proc.poll() is not None else "")[-1200:])
                return 1
            print(f"endpoint: {base}/mcp (no CHIRON_MCP_USERNAME configured)")
            run(base, state_dir)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
    failed = RESULTS.count(False)
    print(f"\n{len(RESULTS) - failed} passed, {failed} failed")
    return 1 if failed or not RESULTS else 0


if __name__ == "__main__":
    raise SystemExit(main())

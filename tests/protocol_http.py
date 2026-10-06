"""Drive the server over the streamable-HTTP transport: initialize, list tools, call one.

The HTTP twin of tests/protocol.py. It starts `chiron-mcp` with CHIRON_MCP_TRANSPORT=http
on a free loopback port, talks to it with a real MCP client, and then checks the two
properties that make an unauthenticated endpoint acceptable: it answers only on the
loopback interface, and it refuses a request whose Host header is not local (the
DNS-rebinding guard).

    CHIRON_MCP_USERNAME=<user> .venv/bin/python -m tests.protocol_http
"""

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONSOLE = os.path.join(HERE, ".venv", "bin", "chiron-mcp")


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


def _lan_address() -> str | None:
    """This machine's non-loopback IPv4 address, if it has one."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 9))  # no packet is sent; this only picks a route
            addr = s.getsockname()[0]
        return None if addr.startswith("127.") else addr
    except OSError:
        return None


def _post_status(url: str, host_header: str) -> int:
    body = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                   "clientInfo": {"name": "probe", "version": "0"}},
    }).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Host": host_header,
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code


async def _exercise(url: str) -> bool:
    async with streamable_http_client(url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
            print(f"{len(names)} tools registered over HTTP")

            res = await session.call_tool("chiron_datasets", {})
            payload = json.loads(res.content[0].text)
            usable = [d for d in payload.get("datasets", []) if d.get("accessible")]
            print(f"identity: {payload.get('identity')} "
                  f"| ceiling: {payload.get('access_ceiling')}")
            if not usable:
                print("No dataset reachable by this identity; "
                      "grant one with scripts/grant_access.py")
                return False

            ds = usable[0]["dataset_id"]
            res = await session.call_tool(
                "chiron_count_cohort", {"dataset_id": ds, "cohort_def": []}
            )
            print(f"chiron_count_cohort({ds}) -> {res.content[0].text[:200]}")
            return bool(names)


def main() -> int:
    if not os.environ.get("CHIRON_MCP_USERNAME"):
        print("Set CHIRON_MCP_USERNAME first.", file=sys.stderr)
        return 1

    port = _free_port()
    env = dict(os.environ, CHIRON_MCP_TRANSPORT="http", CHIRON_MCP_HTTP_PORT=str(port),
               CHIRON_MCP_HTTP_AUTH="none")  # the OAuth mode has its own test
    cmd = [CONSOLE] if os.path.exists(CONSOLE) else [sys.executable, "-m", "chiron_mcp.server"]
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                            text=True)
    ok = True
    try:
        if not _wait_listening(port, proc):
            print("FAIL  server did not start listening")
            print((proc.stderr.read() if proc.poll() is not None else "")[-800:])
            return 1
        url = f"http://127.0.0.1:{port}/mcp"
        print(f"endpoint: {url}")

        ok &= asyncio.run(_exercise(url))

        status = _post_status(url, "evil.example.com")
        good = status in (400, 403, 421)
        print(f"{'PASS' if good else 'FAIL'}  foreign Host header refused (HTTP {status})")
        ok &= good

        status = _post_status(url, f"localhost:{port}")
        good = status == 200
        print(f"{'PASS' if good else 'FAIL'}  localhost Host header accepted (HTTP {status})")
        ok &= good

        lan = _lan_address()
        if lan:
            with socket.socket() as s:
                s.settimeout(1.5)
                refused = s.connect_ex((lan, port)) != 0
            print(f"{'PASS' if refused else 'FAIL'}  not reachable on {lan} (loopback only)")
            ok &= refused
        else:
            print("SKIP  no non-loopback address on this machine to probe")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

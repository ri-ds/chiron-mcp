"""Check the running stack end to end, through the same front door a browser uses.

    python3 check.py              # from the deploy/ directory, after setup.sh
    python3 check.py --here       # https mode: reach the site on this machine directly

Standard library only (macOS's system python3 is enough). Makes a real Chiron login
session inside the chiron container, so no password is ever typed or sent. Exit code 0
means every check passed.

--here sends requests for the public name to this machine instead of the internet. Many
home routers cannot reach their own public address from inside ("NAT loopback"), so in
https mode the site can work for everyone else and still time out from here.
"""

import base64
import json
import re
import socket
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
results = []


def env():
    out = {}
    for line in (HERE / ".env").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def gate_header():
    p = HERE / ".gate-password"
    if not p.exists():
        return {}
    text = p.read_text()
    user = re.search(r"^user: (.*)$", text, re.M).group(1)
    pw = re.search(r"^password: (.*)$", text, re.M).group(1)
    return {"Authorization": "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode()}


def get(url, headers=None, timeout=30):
    """(status, body, headers); status 0 with the reason as body when nothing answered."""
    headers = dict(headers or {})
    # Cloudflare's browser check blocks Python's default User-Agent in tunnel mode.
    headers.setdefault("User-Agent", "Mozilla/5.0 (compatible; chiron-check)")
    req = urllib.request.Request(url, headers=headers)
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, r.read().decode("utf-8", "replace"), dict(r.headers)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        if e.code == 403 and "error code: 10" in body:
            body = "blocked by Cloudflare before reaching this machine: " + body[:80]
        return e.code, body, dict(e.headers)
    except (urllib.error.URLError, OSError) as e:
        return 0, f"no answer: {getattr(e, 'reason', e)}", {}


def send_to_this_machine(host):
    """Resolve `host` to 127.0.0.1 for this process, keeping TLS checks on the real name."""
    real = socket.getaddrinfo

    def patched(name, *args, **kwargs):
        return real("127.0.0.1" if name == host else name, *args, **kwargs)

    socket.getaddrinfo = patched


def check(name, ok, detail=""):
    results.append(ok)
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""))


def main():
    e = env()
    base = e["PUBLIC_URL"].rstrip("/")
    auth = gate_header()
    host = urllib.parse.urlparse(base).hostname
    if "--here" in sys.argv and host not in ("localhost", "127.0.0.1"):
        send_to_this_machine(host)
        print(f"checking {base} (sent to this machine)\n")
    else:
        print(f"checking {base}\n")
        status, body, _ = get(base + "/", timeout=10)
        if status == 0:
            print(f"FAIL the site answers  ({body})")
            if e.get("SITE_ADDRESS", ":80") != ":80":
                print("     In https mode this can be the router: try  python3 check.py --here,")
                print("     and open the address on a phone using mobile data.")
            else:
                print("     Is the tunnel up (docker compose ps), and does the name resolve?")
                print(f"     dig +short {host} @1.1.1.1")
            return 1

    if auth:
        status, _, _ = get(base + "/")
        check("the password gate blocks strangers", status == 401, f"HTTP {status}")

    status, body, _ = get(base + "/", auth)
    check("the Chiron UI loads", status == 200 and 'id="root"' in body,
          f"HTTP {status}" if status else body)

    status, body, _ = get(base + "/synthea-small/ask", auth)
    check("UI routes fall back to the app", status == 200 and 'id="root"' in body, f"HTTP {status}")

    status, body, _ = get(base + "/accounts/login/", auth)
    check("Chiron's login page", status == 200 and "login" in body.lower(), f"HTTP {status}")

    status, _, _ = get(base + "/static/admin/css/base.css", auth)
    check("Django static files", status == 200, f"HTTP {status}")

    session = subprocess.run(
        ["docker", "compose", "exec", "-T", "chiron", "python", "/app/deploy/mint_session.py",
         "demouser"], cwd=HERE, capture_output=True, text=True,
    ).stdout.strip().splitlines()[-1:]
    check("a demouser session", bool(session), "made inside the chiron container")
    cookie = dict(auth, Cookie=f"sessionid={session[0]}" if session else "")

    status, body, _ = get(base + "/api/v2/dataset/", cookie)
    names = []
    try:
        names = [d.get("unique_id") for d in json.loads(body).get("datasets", [])]
    except (ValueError, AttributeError):
        pass
    check("Chiron's API as demouser", status == 200 and bool(names), ", ".join(filter(None, names)))

    dataset = "synthea-10k" if "synthea-10k" in names else "synthea-small"
    status, body, _ = get(f"{base}/api/v2/{dataset}/query_tools/count/", cookie)
    check("Chiron's query builder count", status == 200 and '"count"' in body, f"HTTP {status}")

    # The whole dataset, from Chiron's engine; the API above counts the open query.
    out = subprocess.run(
        ["docker", "compose", "exec", "-T", "chiron", "python", "/app/deploy/count_subjects.py",
         dataset], cwd=HERE, capture_output=True, text=True,
    ).stdout.strip().splitlines()[-1:]
    chiron_count = int(out[0]) if out and out[0].isdigit() else None
    check(f"Chiron counts {dataset}", bool(chiron_count), f"{chiron_count} subjects")

    status, body, _ = get(base + "/ask/", auth)
    check("the Ask page", status == 200 and "Ask Chiron" in body, f"HTTP {status}")

    status, body, _ = get(f"{base}/ask/datasets?dataset={dataset}", cookie)
    try:
        who = json.loads(body).get("identity")
    except ValueError:
        who = None
    check("Ask knows who is logged in", who == "demouser", f"identity {who}")

    q = urllib.parse.quote("How many patients are in this dataset?")
    status, body, _ = get(f"{base}/ask/ask?q={q}&dataset={dataset}", cookie, timeout=240)
    events = dict(re.findall(r"event: (\w+)\ndata: (.*)", body))
    answer = json.loads(events["answer"]) if "answer" in events else ""
    error = json.loads(events["error"]) if "error" in events else ""
    if error and re.search(r"claude account|/login", error, re.I):
        check("Ask answers a question", False, "Claude is not logged in yet: "
              "docker compose exec -it ask claude, then /login")
    else:
        figures = {int(n.replace(",", "")) for n in re.findall(r"\d[\d,]*", answer)}
        check("Ask answers a question", chiron_count in figures,
              (answer or error)[:120].replace("\n", " "))

    print(f"\n{sum(results)}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())

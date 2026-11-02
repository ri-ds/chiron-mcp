"""Check the Ask add-on end to end, through the same front door a browser uses.

    python3 check.py                      # from the askpatch/ directory, after compose up
    python3 check.py --user alice --dataset synthea-10k

Standard library only. Reads askpatch/.env for PUBLIC_URL and ASK_BIND, makes a real
Chiron login session inside the ask container (no password is typed or sent), and then
asks a question as that person. The account comes from --user, else ASK_CHECK_USER in
.env, else demouser; it needs access to a dataset (--dataset, ASK_CHECK_DATASET, or the
first it can see). Exit code 0 means every check passed.
"""

import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
results = []


def env():
    out = {}
    p = HERE / ".env"
    if not p.exists():
        sys.exit("askpatch/.env is missing: copy env.example to .env and fill it in")
    for line in p.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def arg(name, default=None):
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def get(url, headers=None, timeout=30):
    """(status, body, seconds between the first and the last byte); status 0 with the
    reason as the body when nothing answered."""
    req = urllib.request.Request(url, headers=dict(headers or {}))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            chunks, first = [], None
            while True:
                chunk = r.read(4096)
                if not chunk:
                    break
                if first is None:
                    first = time.monotonic()
                chunks.append(chunk)
            spread = (time.monotonic() - first) if first else 0.0
            return r.status, b"".join(chunks).decode("utf-8", "replace"), spread
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), 0.0
    except (urllib.error.URLError, OSError) as e:
        return 0, f"no answer: {getattr(e, 'reason', e)}", 0.0


def in_container(*cmd, extra_env=None):
    """Run a command inside the ask container; the last line of its output, or ''."""
    full = ["docker", "compose", "exec", "-T"]
    for k, v in (extra_env or {}).items():
        full += ["-e", f"{k}={v}"]
    full += ["ask", *cmd]
    r = subprocess.run(full, cwd=HERE, capture_output=True, text=True)
    lines = r.stdout.strip().splitlines()
    return (lines[-1] if lines else ""), r.stderr.strip()


def check(name, ok, detail=""):
    results.append(ok)
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""))


def main():
    e = env()
    base = e.get("PUBLIC_URL", "").rstrip("/")
    if not base:
        sys.exit("PUBLIC_URL is not set in askpatch/.env")
    bind = e.get("ASK_BIND", "127.0.0.1:8900")
    local = "http://" + (bind if ":" in bind else f"127.0.0.1:{bind}")
    user = arg("--user", e.get("ASK_CHECK_USER") or "demouser")
    dataset = arg("--dataset", e.get("ASK_CHECK_DATASET") or "")
    print(f"checking {base} (Ask container at {local}) as {user}\n")

    status, body, _ = get(local + "/health", timeout=10)
    try:
        health = json.loads(body)
    except ValueError:
        health = {}
    check("the Ask container answers", status == 200 and health.get("ok") is True,
          f"HTTP {status}" if status else body)
    check("Ask answers only people logged into Chiron", health.get("require_session") is True)

    status, body, _ = get(base + "/accounts/login/")
    check("Chiron's login page", status == 200 and "login" in body.lower(), f"HTTP {status}" if status else body)

    status, body, _ = get(base + "/ask/")
    check("the Ask page through the site (the /ask route)", status == 200 and "Ask Chiron" in body,
          f"HTTP {status}" if status else body)
    if status != 200:
        print("     The web server does not forward /ask to the Ask container yet; see proxy/.")

    session, err = in_container("python", "/app/deploy/mint_session.py", user)
    check(f"a Chiron session for {user}", bool(re.fullmatch(r"[0-9a-z]{20,}", session or "")),
          "made inside the ask container" if session else err[-160:])
    cookie = {"Cookie": f"sessionid={session}"} if session else {}

    status, body, _ = get(f"{base}/ask/datasets?dataset={urllib.parse.quote(dataset)}", cookie)
    try:
        info = json.loads(body)
    except ValueError:
        info = {}
    who = info.get("identity")
    check("Ask knows who is logged in", who == user, f"identity {who!r}, HTTP {status}")
    if not dataset:
        usable = [d.get("dataset_id") or d.get("id") for d in info.get("datasets", [])
                  if d.get("accessible", True)]
        dataset = next((d for d in usable if d), "")
    check(f"{user} can see a dataset", bool(dataset), dataset)
    if not dataset:
        print(f"\n{sum(results)}/{len(results)} passed")
        return 1

    out, err = in_container("python", "/app/deploy/count_subjects.py", dataset,
                            extra_env={"CHIRON_MCP_USERNAME": user})
    count = int(out) if out.isdigit() else None
    check(f"Chiron counts {dataset}", count is not None, f"{count} subjects" if count else err[-160:])

    q = urllib.parse.quote("How many patients are in this dataset?")
    status, body, spread = get(f"{base}/ask/ask?q={q}&dataset={urllib.parse.quote(dataset)}",
                               cookie, timeout=300)
    events = dict(re.findall(r"event: (\w+)\ndata: (.*)", body))
    answer = json.loads(events["answer"]) if "answer" in events else ""
    error = json.loads(events["error"]) if "error" in events else ""
    if error and re.search(r"claude account|/login|not logged in|authentication", error, re.I):
        check("Ask answers a question", False, "the container is not logged in to a model yet: "
              "docker compose exec -it ask claude, then /login (or set the Bedrock lines in .env)")
    else:
        figures = {int(n.replace(",", "")) for n in re.findall(r"\d[\d,]*", answer)}
        check("Ask answers a question with Chiron's count", bool(answer) and count in figures,
              (answer or error or f"HTTP {status}")[:140].replace("\n", " "))
        # The events of an answer arrive over its whole run; a proxy that buffers hands
        # them over all at once at the end, and the page then shows nothing until then.
        if answer:
            check("answers stream through the web server", spread > 1.0,
                  f"{spread:.1f} s between the first and the last event")

    print(f"\n{sum(results)}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())

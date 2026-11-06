"""Conversations that stay, a price that moves, traces that are there.

Offline, in-process: the retention setting (unset, 0 or "never" keeps conversations for
good; a number is idle hours) and what the conversation registry does under each.

Live, against ASK_URL as the demo accounts (needs the server's CHIRON_MCP_* database
settings, like tests/ask_e2e.py):

    ask a question, then /threads lists the conversation with its title and one answer;
    a follow-up continues the same conversation and makes it two;
    /threads?thread= rebuilds both turns, each with its answer and a done trace;
    /usage.json shows one more answer after each, with a cost that is a number;
    every JSON answer says Cache-Control: no-store;
    another account sees neither the conversation nor its turns;
    /forget removes it, from /threads and from /trace.

    PERSIST_RESTART_CMD, when set, runs between the question and the follow-up (for
    example a command that restarts the Ask server); the follow-up must still continue
    the same conversation, since the registry and the transcript live on disk.

    ASK_URL=http://localhost:8900 .venv/bin/python tests/persistence.py   # --live-only, --offline-only
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("CHIRON_MCP_USAGE_DB", "off")   # the in-process part writes no ledger

import ask_e2e as E  # noqa: E402

fails: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    print(f"{'PASS' if cond else 'FAIL'}  {label}  {str(detail)[:220]}", flush=True)
    if not cond:
        fails.append(label)


# --- offline: the retention setting and the registry ------------------------------------

def offline() -> None:
    from chiron_mcp import webapp as W
    from chiron_mcp import trace as tracing

    ttl = W._ttl_hours
    check("[ttl] unset keeps conversations for good", ttl(None) is None)
    check("[ttl] 0, never and off keep them for good", all(ttl(x) is None for x in ("0", "never", "off", "  ", "NEVER")))
    check("[ttl] a number is hours", ttl("12") == 12.0 and ttl("0.5") == 0.5)
    check("[ttl] nonsense and negatives keep them for good rather than failing", ttl("abc") is None and ttl("-3") is None)

    with tempfile.TemporaryDirectory() as tmp:
        old_state, old_ttl = W._state_dir, W.THREAD_TTL_HOURS
        W._state_dir = lambda: Path(tmp)
        try:
            W.THREAD_TTL_HOURS = None
            T = W._Threads()
            T.touch("t1", "alice", "ds", {"cohort_def": []}, question="How many patients have asthma?")
            T.touch("t1", "alice", "ds", None, question="How many of them are women?")
            T.touch("t2", "bob", "ds", None, question="Count them")
            T._data["t1"]["last"] -= 30 * 86400   # a month idle
            T._save()
            check("[registry] a month-old conversation is still valid with no retention limit", T.valid("t1", "alice", "ds"))
            mine = T.mine("alice")
            check("[registry] mine lists only alice's, with the first question as title and two answers",
                  [m["thread"] for m in mine] == ["t1"] and mine[0]["title"] == "How many patients have asthma?"
                  and mine[0]["turns"] == 2 and mine[0]["expired"] is False, mine)
            check("[registry] mine filters by dataset", T.mine("alice", "other") == [] and len(T.mine("alice", "ds")) == 1)
            T.prune()
            check("[registry] prune keeps everything with no retention limit", set(T._data) == {"t1", "t2"})
            check("[registry] turns of someone else's conversation are refused", T.turns("t1", "bob") is None)
            W.THREAD_TTL_HOURS = 24.0
            check("[registry] with a 24-hour limit the month-old one is no longer valid, and listed as expired",
                  not T.valid("t1", "alice", "ds") and T.mine("alice")[0]["expired"] is True and T.valid("t2", "bob", "ds"))
            T.prune()
            check("[registry] prune then drops it and keeps the fresh one", set(T._data) == {"t2"}, sorted(T._data))
            # The registry is read back from disk by a new server process.
            W.THREAD_TTL_HOURS = None
            T2 = W._Threads()
            check("[registry] a new server reads the registry back from disk", set(T2._data) == {"t2"} and T2._data["t2"]["title"] == "Count them")
            # Traces rebuilt into turns, oldest first, with the answer and a summary.
            root = Path(tmp) / "traces"
            tr = tracing.Trace(question="Q1", dataset="ds", user="carol", thread="t3", followup=False, prior=[])
            tr.data["answer"] = "A1"
            tr.finish(0, "")
            tr.save(root)
            time.sleep(0.01)
            tr2 = tracing.Trace(question="Q2", dataset="ds", user="carol", thread="t3", followup=True, prior=[])
            tr2.data["answer"] = "A2"
            tr2.finish(0, "")
            tr2.save(root)
            turns = tracing.turns(root, "t3", "carol")
            check("[traces] a conversation's turns come back oldest first with answers and trace ids",
                  [t["q"] for t in turns] == ["Q1", "Q2"] and [t["answer"] for t in turns] == ["A1", "A2"]
                  and all(t["trace"]["id"] and t["done"] for t in turns), turns)
            check("[traces] nobody else's", tracing.turns(root, "t3", "dave") == [])
            # A conversation registered before titles were kept gets one from its first trace.
            T3 = W._Threads()
            T3._data["t3"] = {"user": "carol", "dataset": "ds", "last": time.time(), "cohort": None}
            T3._save()
            mine = T3.mine("carol")
            check("[registry] an untitled conversation takes its first traced question as title, and keeps it",
                  mine and mine[0]["title"] == "Q1" and json.loads(T3._path.read_text())["t3"].get("title") == "Q1", mine)
        finally:
            W._state_dir, W.THREAD_TTL_HOURS = old_state, old_ttl


# --- live: through the server --------------------------------------------------------------

def headers_of(path: str, cookie: str) -> dict:
    req = urllib.request.Request(E.ASK + path, headers={"Cookie": f"sessionid={cookie}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return {k.lower(): v for k, v in r.headers.items()}


def totals(cookie: str, user: str) -> dict:
    d = E.get_json(f"{E.ASK}/usage.json?period=all&recent=5&user={urllib.parse.quote(user)}", cookie)
    return d.get("totals") or {}, d.get("recent") or []


def live() -> None:
    me, other = E.mint_session("demouser"), E.mint_session("agguser")
    tag = "[live]"
    for path in ("/datasets?dataset=" + E.DS, "/threads?dataset=" + E.DS, "/usage.json?period=today", "/whoami"):
        h = headers_of(path, me)
        check(f"{tag} {path.split('?')[0]} is sent with Cache-Control: no-store", "no-store" in h.get("cache-control", ""), h.get("cache-control"))

    before, _ = totals(me, "demouser")
    ev = E.ask("How many patients have asthma?", me, E.DS)
    tid = ev.get("thread")
    trace_id = (ev.get("trace_start") or {}).get("id")
    check(f"{tag} the question was answered with a figure", bool(E.numbers(ev.get("answer") or "")) and tid, (ev.get("error") or ev.get("answer") or "")[:100])
    listed = E.get_json(f"{E.ASK}/threads?dataset={E.DS}", me)
    mine = [t for t in listed.get("threads") or [] if t["thread"] == tid]
    check(f"{tag} /threads lists the conversation with its title and one answer",
          len(mine) == 1 and mine[0]["title"] == "How many patients have asthma?" and mine[0]["turns"] == 1 and not mine[0]["expired"], mine)
    check(f"{tag} /threads says there is no retention limit", listed.get("ttl_hours") is None, listed.get("ttl_hours"))
    after, recent = totals(me, "demouser")
    check(f"{tag} the usage total grew by one answer with a cost that is a number",
          (after.get("answers") or 0) == (before.get("answers") or 0) + 1 and isinstance(recent[0].get("cost_usd"), (int, float)),
          (before.get("answers"), after.get("answers"), recent[0].get("cost_usd") if recent else None))

    cmd = os.environ.get("PERSIST_RESTART_CMD")
    if cmd:
        print(f"  running PERSIST_RESTART_CMD: {cmd}", flush=True)
        subprocess.run(cmd, shell=True, check=False, timeout=120)
        for _ in range(30):
            try:
                E.get_json(f"{E.ASK}/health", me)
                break
            except Exception:  # noqa: BLE001
                time.sleep(1)

    ev2 = E.ask("How many of them are women?", me, E.DS, tid)
    tr2 = E.get_json(f"{E.ASK}/trace?id={(ev2.get('trace_start') or {}).get('id')}", me)
    check(f"{tag} the follow-up continued the same conversation" + (" across the restart" if cmd else ""),
          ev2.get("thread") == tid and tr2.get("followup") is True and not tr2.get("followup_lost"),
          (ev2.get("thread") == tid, tr2.get("followup"), tr2.get("followup_lost"), (ev2.get("answer") or ev2.get("error") or "")[:80]))
    turns = E.get_json(f"{E.ASK}/threads?thread={tid}", me).get("turns") or []
    check(f"{tag} /threads?thread= rebuilds both turns with their answers and done traces",
          [t["q"] for t in turns] == ["How many patients have asthma?", "How many of them are women?"]
          and all(t.get("answer") and t["trace"]["id"] and t["done"] for t in turns), [(t.get("q"), bool(t.get("answer")), t.get("done")) for t in turns])
    listed = E.get_json(f"{E.ASK}/threads?dataset={E.DS}", me)
    mine = [t for t in listed.get("threads") or [] if t["thread"] == tid]
    check(f"{tag} /threads now counts two answers", mine and mine[0]["turns"] == 2, mine)
    full = E.get_json(f"{E.ASK}/trace?id={trace_id}", me)
    check(f"{tag} the first answer's trace is complete", full.get("done") is True and bool(full.get("steps")), full.get("error"))
    after2, recent2 = totals(me, "demouser")
    check(f"{tag} the usage total grew again and the follow-up's cost is a number",
          (after2.get("answers") or 0) == (after.get("answers") or 0) + 1 and isinstance(recent2[0].get("cost_usd"), (int, float)),
          (after.get("answers"), after2.get("answers"), recent2[0].get("cost_usd") if recent2 else None))

    others = E.get_json(f"{E.ASK}/threads?dataset={E.DS}", other)
    check(f"{tag} another account does not see the conversation", tid not in {t["thread"] for t in others.get("threads") or []})
    r = E.get_json(f"{E.ASK}/threads?thread={tid}", other)
    check(f"{tag} nor its turns", "error" in r and not r.get("turns"), r.get("error"))
    r = E.get_json(f"{E.ASK}/trace?id={trace_id}", other)
    check(f"{tag} nor its traces", "error" in r and not r.get("steps"), r.get("error"))

    r = E.post_json(f"{E.ASK}/forget", {"thread": tid}, me)
    listed = E.get_json(f"{E.ASK}/threads?dataset={E.DS}", me)
    gone = tid not in {t["thread"] for t in listed.get("threads") or []}
    tr = E.get_json(f"{E.ASK}/trace?id={trace_id}", me)
    check(f"{tag} /forget removes the conversation from /threads and its traces", r.get("forgotten") is True and gone and "error" in tr, (r, gone, tr.get("error")))
    E.STARTED.discard((tid, me))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline-only", action="store_true")
    ap.add_argument("--live-only", action="store_true")
    args = ap.parse_args()
    if not args.live_only:
        offline()
    if not args.offline_only:
        live()
        E.cleanup([])
    print("ALL PASS" if not fails else f"{len(fails)} FAILED:\n  " + "\n  ".join(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())

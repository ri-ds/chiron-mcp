"""The usage ledger: one row per answer, kept for good, behind the usage page.

The trace under an answer is deleted with its conversation (it holds patient-level
data), and the call log lives wherever the container's log goes. This is the durable,
privacy-safe copy of what each answer cost: who asked (the username), on which dataset
and at what access level, which model answered, how many model and Chiron calls, the
tokens, the cost, the time, and how it ended. No question text, no tool argument, no
filter value, no result, so it may be kept indefinitely and shown to an administrator.

Written by the trace when an answer finishes (the same moment the call log's `answer`
line goes out), and by scripts/usage_backfill.py from call-log lines for the answers
given before the ledger existed.

    CHIRON_MCP_USAGE_DB               the SQLite file; unset: <state dir>/usage.sqlite,
                                      the state dir being CHIRON_MCP_STATE_DIR or
                                      ~/.cache/chiron-ask, where conversations live;
                                      off: no ledger
    CHIRON_MCP_USAGE_RETENTION_DAYS   rows older than this are pruned; unset: kept

Every function here swallows its own errors: an answer must never fail because the
ledger could not be written.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

COLUMNS = (
    "id", "thread", "user", "dataset", "access_level", "started", "ended", "turn",
    "followup", "status", "model", "model_calls", "chiron_calls", "chiron_errors",
    "retries", "tokens_in", "cache_read", "cache_write", "tokens_out", "thinking",
    "cost_usd", "cost_total", "ms", "model_ms", "chiron_ms", "rc", "source", "limited",
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS access_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT, actor TEXT, username TEXT, dataset TEXT, change TEXT
);
CREATE TABLE IF NOT EXISTS answers (
    id TEXT PRIMARY KEY,
    thread TEXT, user TEXT, dataset TEXT, access_level TEXT,
    started TEXT, ended TEXT, turn INTEGER, followup INTEGER,
    status TEXT, model TEXT,
    model_calls INTEGER, chiron_calls INTEGER, chiron_errors INTEGER, retries INTEGER,
    tokens_in INTEGER, cache_read INTEGER, cache_write INTEGER, tokens_out INTEGER,
    thinking INTEGER,
    cost_usd REAL, cost_total REAL,
    ms INTEGER, model_ms INTEGER, chiron_ms INTEGER, rc INTEGER,
    source TEXT,
    limited INTEGER
);
CREATE INDEX IF NOT EXISTS answers_ended ON answers (ended);
CREATE INDEX IF NOT EXISTS answers_user ON answers (user, ended);
CREATE TABLE IF NOT EXISTS flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT, user TEXT, dataset TEXT, thread TEXT, trace TEXT,
    kind TEXT, note TEXT, question TEXT, answer TEXT, model TEXT, access_level TEXT,
    status TEXT DEFAULT 'open', handled_at TEXT, handled_by TEXT
);
"""
# Columns added after a ledger was first made: CREATE TABLE IF NOT EXISTS leaves an old
# table as it was, so each is added when missing.
_ADDED = {"answers": {"limited": "INTEGER"}}

# The call log's names for an answer's fields, where they differ from the columns.
_FROM_LOG = {"answer": "id", "level": "access_level", "in": "tokens_in", "out": "tokens_out"}

_lock = threading.Lock()
_ready: set[str] = set()


def setting() -> str:
    return os.environ.get("CHIRON_MCP_USAGE_DB", "").strip()


def path() -> Path | None:
    """Where the ledger is, or None when it is switched off."""
    value = setting()
    if value.lower() in ("0", "off", "no", "none", "false"):
        return None
    if value:
        return Path(value).expanduser()
    state = Path(os.environ.get("CHIRON_MCP_STATE_DIR", Path.home() / ".cache" / "chiron-ask"))
    return state / "usage.sqlite"


def retention_days() -> float | None:
    try:
        v = float(os.environ.get("CHIRON_MCP_USAGE_RETENTION_DAYS", "") or 0)
    except ValueError:
        return None
    return v if v > 0 else None


def reset() -> None:
    """Forget which files were prepared (tests switch files)."""
    with _lock:
        _ready.clear()


def _connect(p: Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(p), timeout=10, isolation_level=None)
    con.row_factory = sqlite3.Row
    key = str(p)
    if key not in _ready:
        with _lock:
            if key not in _ready:
                p.parent.mkdir(parents=True, exist_ok=True)
                try:
                    p.parent.chmod(0o700)
                except OSError:
                    pass
                con.executescript(_SCHEMA)
                for table, cols in _ADDED.items():
                    have = {r[1] for r in con.execute(f"PRAGMA table_info({table})").fetchall()}
                    for col, typ in cols.items():
                        if col not in have:
                            con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
                try:
                    p.chmod(0o600)
                except OSError:
                    pass
                _ready.add(key)
    return con


def iso(epoch: float | None) -> str | None:
    if epoch is None:
        return None
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _int(v):
    if v is None or isinstance(v, bool):
        return int(v) if isinstance(v, bool) else None
    try:
        return int(round(float(v)))
    except (TypeError, ValueError):
        return None


def _float(v):
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def row_from(fields: dict, *, started: str | None = None, ended: str | None = None,
             source: str = "live") -> dict:
    """A ledger row from an answer's fields as the call log names them (see trace.py)."""
    row: dict = {c: None for c in COLUMNS}
    for k, v in fields.items():
        row[_FROM_LOG.get(k, k)] = v
    for c in ("turn", "followup", "model_calls", "chiron_calls", "chiron_errors", "retries",
              "tokens_in", "cache_read", "cache_write", "tokens_out", "thinking", "ms",
              "model_ms", "chiron_ms", "rc", "limited"):
        row[c] = _int(row.get(c))
    row["cost_usd"] = _float(row.get("cost_usd"))
    row["cost_total"] = _float(row.get("cost_total"))
    row["started"] = started or row.get("started")
    row["ended"] = ended or row.get("ended")
    row["source"] = source
    return {c: row.get(c) for c in COLUMNS}


def record(fields: dict, *, started: float | None = None, ended: float | None = None,
           source: str = "live", replace: bool = True) -> bool:
    """Write one answer. `fields` as the call log's answer line has them; `started`
    and `ended` as epoch seconds. Returns whether a row was written."""
    p = path()
    if p is None or not fields.get("answer"):
        return False
    try:
        row = row_from(fields, started=iso(started), ended=iso(ended), source=source)
        verb = "INSERT OR REPLACE" if replace else "INSERT OR IGNORE"
        cols = ", ".join(COLUMNS)
        marks = ", ".join("?" for _ in COLUMNS)
        con = _connect(p)
        try:
            cur = con.execute(f"{verb} INTO answers ({cols}) VALUES ({marks})",
                              [row[c] for c in COLUMNS])
            return cur.rowcount > 0
        finally:
            con.close()
    except Exception as exc:  # noqa: BLE001
        print(f"usage ledger: {exc}", file=sys.stderr)
        return False


def prune() -> int:
    """Delete rows past the retention window; the number removed."""
    p, days = path(), retention_days()
    if p is None or days is None or not p.exists():
        return 0
    cutoff = iso(time.time() - days * 86400)
    try:
        con = _connect(p)
        try:
            return con.execute("DELETE FROM answers WHERE ended < ?", (cutoff,)).rowcount
        finally:
            con.close()
    except Exception as exc:  # noqa: BLE001
        print(f"usage ledger: {exc}", file=sys.stderr)
        return 0


def audit(actor: str, username: str, dataset: str | None, change: str) -> None:
    """One line in the access log: who changed whose access to what, when."""
    p = path()
    if p is None:
        return
    try:
        con = _connect(p)
        try:
            con.execute("INSERT INTO access_log (at, actor, username, dataset, change) VALUES (?, ?, ?, ?, ?)",
                        (iso(time.time()), actor, username, dataset, change))
        finally:
            con.close()
    except Exception as exc:  # noqa: BLE001
        print(f"usage ledger: {exc}", file=sys.stderr)


def changes(limit: int = 50, username: str | None = None) -> list[dict]:
    """The latest access changes, newest first."""
    p = path()
    if p is None or not p.exists():
        return []
    try:
        con = _connect(p)
        try:
            where, args = ("WHERE username = ?", [username]) if username else ("", [])
            return [dict(r) for r in con.execute(
                f"SELECT at, actor, username, dataset, change FROM access_log {where} "
                "ORDER BY id DESC LIMIT ?", args + [int(limit)]).fetchall()]
        finally:
            con.close()
    except Exception as exc:  # noqa: BLE001
        print(f"usage ledger: {exc}", file=sys.stderr)
        return []


def delete_users(users: list[str]) -> int:
    """Remove every row of these usernames (a test suite's throwaway accounts)."""
    p = path()
    if p is None or not p.exists() or not users:
        return 0
    try:
        con = _connect(p)
        try:
            marks = ", ".join("?" for _ in users)
            return con.execute(f"DELETE FROM answers WHERE user IN ({marks})", list(users)).rowcount
        finally:
            con.close()
    except Exception as exc:  # noqa: BLE001
        print(f"usage ledger: {exc}", file=sys.stderr)
        return 0


def _where(since: str | None, until: str | None, user: str | None,
           dataset: str | None = None) -> tuple[str, list]:
    parts, args = [], []
    if since:
        parts.append("ended >= ?")
        args.append(since)
    if until:
        parts.append("ended < ?")
        args.append(until)
    if user:
        parts.append("user = ?")
        args.append(user)
    if dataset:
        parts.append("dataset = ?")
        args.append(dataset)
    return (" WHERE " + " AND ".join(parts)) if parts else "", args


_AGG = ("COUNT(*) AS answers, "
        "COALESCE(SUM(cost_usd), 0) AS cost_usd, "
        "AVG(cost_usd) AS avg_cost, "
        "AVG(ms) AS avg_ms, "
        "SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) AS errors, "
        "SUM(CASE WHEN status = 'incomplete' THEN 1 ELSE 0 END) AS incomplete, "
        "COALESCE(SUM(tokens_in), 0) + COALESCE(SUM(cache_read), 0) + COALESCE(SUM(cache_write), 0) AS tokens_in, "
        "COALESCE(SUM(tokens_out), 0) AS tokens_out, "
        "SUM(model_calls) AS model_calls, SUM(chiron_calls) AS chiron_calls, "
        "COALESCE(SUM(limited), 0) AS limited, "
        "MAX(ended) AS last")


# --- flags: an answer a person reported as wrong, incomplete or refused ----------------------
FLAG_KINDS = {"wrong": "Wrong figure or answer", "incomplete": "Incomplete",
              "could_not": "Could not do what was asked", "other": "Something else"}


def flag(*, user: str, dataset: str | None, thread: str | None, trace: str | None, kind: str,
         note: str | None, question: str | None, answer: str | None, model: str | None,
         access_level: str | None) -> int | None:
    """One reported answer, with the question and the answer the person chose to send.
    Returns the flag's id, or None when the ledger is off or the write failed."""
    p = path()
    if p is None:
        return None
    try:
        con = _connect(p)
        try:
            kind = kind if kind in FLAG_KINDS else "other"
            note = (note or "")[:1000] or None
            # The same person reporting the same answer again changes their report, rather
            # than adding another; a handled one is reopened.
            prev = con.execute("SELECT id FROM flags WHERE trace = ? AND user = ? ORDER BY id DESC LIMIT 1",
                               (trace, user)).fetchone() if trace else None
            if prev:
                con.execute("UPDATE flags SET at = ?, kind = ?, note = ?, status = 'open', handled_at = NULL, "
                            "handled_by = NULL WHERE id = ?", (iso(time.time()), kind, note, prev["id"]))
                return int(prev["id"])
            cur = con.execute(
                "INSERT INTO flags (at, user, dataset, thread, trace, kind, note, question, answer, "
                "model, access_level, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')",
                (iso(time.time()), user, dataset, thread, trace, kind, note,
                 (question or "")[:2000] or None, (answer or "")[:6000] or None, model, access_level))
            return int(cur.lastrowid)
        finally:
            con.close()
    except Exception as exc:  # noqa: BLE001
        print(f"usage ledger: {exc}", file=sys.stderr)
        return None


def flags(limit: int = 200, status: str | None = None, user: str | None = None) -> list[dict]:
    """Reported answers, newest first; `status` open or handled, `user` one person's."""
    p = path()
    if p is None or not p.exists():
        return []
    where, args = [], []
    if status:
        where.append("status = ?")
        args.append(status)
    if user:
        where.append("user = ?")
        args.append(user)
    sql = "SELECT * FROM flags" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY id DESC LIMIT ?"
    try:
        con = _connect(p)
        try:
            return [dict(r) for r in con.execute(sql, args + [int(limit)]).fetchall()]
        finally:
            con.close()
    except Exception as exc:  # noqa: BLE001
        print(f"usage ledger: {exc}", file=sys.stderr)
        return []


def set_flag(flag_id: int, status: str, actor: str) -> bool:
    """Mark a reported answer handled (or open again)."""
    p = path()
    if p is None or status not in ("open", "handled"):
        return False
    try:
        con = _connect(p)
        try:
            cur = con.execute("UPDATE flags SET status = ?, handled_at = ?, handled_by = ? WHERE id = ?",
                              (status, iso(time.time()) if status == "handled" else None,
                               actor if status == "handled" else None, int(flag_id)))
            return cur.rowcount > 0
        finally:
            con.close()
    except Exception as exc:  # noqa: BLE001
        print(f"usage ledger: {exc}", file=sys.stderr)
        return False


def last_total(thread: str, user: str) -> float | None:
    """The conversation's running cost after its latest recorded answer, for a follow-up
    whose earlier traces are gone (the ledger outlives them). None when unknown."""
    p = path()
    if not thread or not user or p is None or not p.exists():
        return None
    try:
        con = _connect(p)
        try:
            row = con.execute(
                "SELECT cost_total FROM answers WHERE thread = ? AND user = ? AND cost_total IS NOT NULL "
                "ORDER BY ended DESC, id DESC LIMIT 1", (thread, user)).fetchone()
        finally:
            con.close()
    except sqlite3.Error:
        return None
    return float(row[0]) if row and row[0] is not None else None


def summary(*, since: str | None = None, until: str | None = None, user: str | None = None,
            dataset: str | None = None, recent: int = 100) -> dict:
    """What the usage page shows for a period: totals, per person, per model, per
    dataset, per day, and the most recent answers. Rows carry no question text."""
    p = path()
    out: dict = {"ledger": str(p) if p else None, "since": since, "until": until,
                 "totals": {}, "per_user": [], "per_model": [], "per_dataset": [],
                 "per_day": [], "recent": []}
    if p is None or not p.exists():
        return out
    where, args = _where(since, until, user, dataset)
    try:
        con = _connect(p)
        try:
            def rows(sql, a=args):
                return [dict(r) for r in con.execute(sql, a).fetchall()]

            t = rows(f"SELECT {_AGG}, COUNT(DISTINCT user) AS people, "
                     f"COUNT(DISTINCT dataset) AS datasets FROM answers{where}")[0]
            out["totals"] = t
            out["per_user"] = rows(
                f"SELECT user, {_AGG}, GROUP_CONCAT(DISTINCT dataset) AS datasets, "
                f"GROUP_CONCAT(DISTINCT access_level) AS levels FROM answers{where} "
                "GROUP BY user ORDER BY cost_usd DESC, answers DESC")
            out["per_model"] = rows(
                f"SELECT model, {_AGG} FROM answers{where} GROUP BY model ORDER BY cost_usd DESC")
            out["per_dataset"] = rows(
                f"SELECT dataset, {_AGG} FROM answers{where} GROUP BY dataset ORDER BY answers DESC")
            out["per_day"] = rows(
                f"SELECT substr(ended, 1, 10) AS day, {_AGG} FROM answers{where} "
                "GROUP BY day ORDER BY day")
            out["recent"] = rows(
                f"SELECT {', '.join(COLUMNS)} FROM answers{where} ORDER BY ended DESC LIMIT ?",
                args + [int(recent)])
        finally:
            con.close()
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)
    return out


def rows(*, since: str | None = None, until: str | None = None, user: str | None = None,
         dataset: str | None = None) -> list[dict]:
    """Every row of a period, oldest first (the CSV download)."""
    p = path()
    if p is None or not p.exists():
        return []
    where, args = _where(since, until, user, dataset)
    con = _connect(p)
    try:
        return [dict(r) for r in con.execute(
            f"SELECT {', '.join(COLUMNS)} FROM answers{where} ORDER BY ended", args).fetchall()]
    finally:
        con.close()


def csv_text(**scope) -> str:
    import csv
    import io

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(COLUMNS)
    for r in rows(**scope):
        w.writerow([r.get(c) for c in COLUMNS])
    return buf.getvalue()


# --- from the call log ---------------------------------------------------------------

_LINE = re.compile(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z) ask (request|answer) (.*)$")
_FIELD = re.compile(r'(\w+)=("(?:[^"\\]|\\.)*"|\S+)')


def parse_line(ln: str) -> tuple[float, str, dict] | None:
    """(epoch, kind, fields) of a call-log request or answer line, else None. Anything
    before the timestamp (a docker log prefix) is ignored."""
    m = _LINE.search(ln)
    if not m:
        return None
    ts, kind, rest = m.groups()
    try:
        when = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fZ" if "." in ts else "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None
    fields = {}
    for f in _FIELD.finditer(rest):
        k, v = f.group(1), f.group(2)
        fields[k] = json.loads(v) if v.startswith('"') else v
    return when.replace(tzinfo=timezone.utc).timestamp(), kind, fields


def backfill(lines) -> dict:
    """Write the answers found in call-log lines that the ledger does not have yet.

    A `request` line gives an answer's start, its `answer` line everything else. Rows
    already present are kept (an answer the server itself recorded wins), so this is safe
    to run again. Returns how many answers were seen, written and kept.
    """
    starts: dict[str, float] = {}
    seen = written = 0
    for ln in lines:
        parsed = parse_line(ln)
        if not parsed:
            continue
        when, kind, fields = parsed
        aid = fields.get("answer")
        if not aid:
            continue
        if kind == "request":
            starts[aid] = when
            continue
        seen += 1
        if record(fields, started=starts.get(aid), ended=when, source="backfill", replace=False):
            written += 1
    return {"answers": seen, "written": written, "kept": seen - written}


def period(name: str, now: float | None = None) -> tuple[str | None, str | None]:
    """The [since, until) pair for a period name: today, 7d, 30d, 90d, all, or a
    YYYY-MM-DD..YYYY-MM-DD range (the end day included)."""
    now = now or time.time()
    today = datetime.fromtimestamp(now, timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    if name in ("", "all"):
        return None, None
    if name == "today":
        return today.strftime("%Y-%m-%dT%H:%M:%SZ"), None
    if name.endswith("d") and name[:-1].isdigit():
        start = today - timedelta(days=int(name[:-1]) - 1)
        return start.strftime("%Y-%m-%dT%H:%M:%SZ"), None
    if ".." in name:
        a, b = name.split("..", 1)
        try:
            start = datetime.strptime(a, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            end = datetime.strptime(b, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
        except ValueError:
            return None, None
        return start.strftime("%Y-%m-%dT%H:%M:%SZ"), end.strftime("%Y-%m-%dT%H:%M:%SZ")
    return None, None

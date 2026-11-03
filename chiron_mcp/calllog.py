"""One line in the server log for every call an answer makes: each model call and each
Chiron tool call, plus one line when the question arrives and one when the answer is
done. The trace under an answer holds all of this and more for one answer; this is the
operational copy, for following a whole conversation, a user or a day through the log
with grep.

Every line has the same shape, so a line is one grep away from its neighbours:

    2026-11-03T15:40:12.345Z ask model answer=2f1a... thread=6c3e... user=demouser dataset=synthea-10k call=1 model=us.anthropic.claude-haiku-5-5 in=4210 cache_read=3900 cache_write=0 out=88 stop=tool_use tools=query ms=1830
    2026-11-03T15:40:13.021Z ask chiron answer=2f1a... thread=6c3e... user=demouser dataset=synthea-10k tool=query status=ok count=179 rows=0 ms=410
    2026-11-03T15:40:20.114Z ask answer answer=2f1a... thread=6c3e... user=demouser dataset=synthea-10k turn=1 status=ok model=us.anthropic.claude-haiku-5-5 model_calls=3 chiron_calls=2 chiron_errors=0 in=12600 cache_read=11700 out=240 cost_usd=0.004210 ms=7770

The kinds are `request`, `model`, `chiron`, `retry`, `reroute`, `restart` and `answer`.
No question text, tool arguments, filter values or results are written: a filter value
can be a patient's name, and the server log is read by people the trace is not shown
to. Error lines carry a status, not the message; the trace has the message.

`CHIRON_MCP_CALL_LOG` chooses where the lines go: unset or `stderr` (the default) is the
server's own log, which Docker collects; a path appends to that file; `0` or `off`
writes nothing. The lines come from the trace, so `CHIRON_MCP_TRACE=0` silences them too.

Standard library only.
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import os
import re
import sys
import threading

LOGGER = logging.getLogger("chiron_mcp.calls")
LOGGER.propagate = False

_SETUP = threading.Lock()
_ready = False
_PLAIN = re.compile(r"^[A-Za-z0-9_.:/@+\-]+$")


def setting() -> str:
    return (os.environ.get("CHIRON_MCP_CALL_LOG") or "stderr").strip()


def enabled() -> bool:
    return setting().lower() not in ("0", "off", "no", "none", "false")


def _setup() -> None:
    """Attach the one handler the setting asks for, the first time a line is written."""
    global _ready
    with _SETUP:
        if _ready:
            return
        _ready = True
        LOGGER.setLevel(logging.INFO)
        for h in list(LOGGER.handlers):
            LOGGER.removeHandler(h)
        if not enabled():
            LOGGER.addHandler(logging.NullHandler())
            return
        where = setting()
        if where.lower() == "stderr":
            handler: logging.Handler = logging.StreamHandler(sys.stderr)
        else:
            try:
                handler = logging.FileHandler(where, encoding="utf-8")
            except OSError as exc:
                print(f"chiron_mcp: cannot open the call log {where!r} ({exc}); writing to stderr",
                      file=sys.stderr)
                handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(message)s"))
        LOGGER.addHandler(handler)


def reset() -> None:
    """Forget the handler, so the next line re-reads CHIRON_MCP_CALL_LOG (tests)."""
    global _ready
    with _SETUP:
        for h in list(LOGGER.handlers):
            LOGGER.removeHandler(h)
            try:
                h.close()
            except Exception:  # noqa: BLE001
                pass
        _ready = False


def _value(v) -> str | None:
    """One value as it goes on the line: numbers plain, text quoted only when it must be,
    nothing for None."""
    if v is None:
        return None
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return f"{v:.6f}".rstrip("0").rstrip(".") if v != int(v) else str(int(v))
    if isinstance(v, (list, tuple, set)):
        v = ",".join(str(x) for x in v)
        if not v:
            return None
    s = str(v)
    return s if _PLAIN.match(s) else json.dumps(s)


def line(kind: str, **fields) -> str:
    """The line for one call, without the newline: a UTC timestamp, the word `ask`, the
    kind, then key=value pairs in the order given, None values left out."""
    now = _dt.datetime.now(_dt.timezone.utc)
    parts = [now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z", "ask", kind]
    for k, v in fields.items():
        s = _value(v)
        if s is not None:
            parts.append(f"{k}={s}")
    return " ".join(parts)


def write(kind: str, **fields) -> str | None:
    """Write one line; returns it (or None when the log is off). Never raises: a log line
    must not break an answer."""
    try:
        if not _ready:
            _setup()
        if not enabled():
            return None
        text = line(kind, **fields)
        LOGGER.info(text)
        return text
    except Exception:  # noqa: BLE001
        return None


def ms(t0, t1) -> int | None:
    """A duration in whole milliseconds from two trace clock readings."""
    if t0 is None or t1 is None:
        return None
    return int(round(t1 - t0))

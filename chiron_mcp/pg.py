"""Warehouse queries when Postgres has no shared memory left for parallel workers.

Postgres's parallel workers share their work through dynamic shared memory (/dev/shm in a
container, 64 MB by default). Several big queries at once can use it all up: "could not
resize shared memory segment ... No space left on device". How much they need depends on
work_mem and how many run at once, not on how much data there is. A query that failed that
way is run once more with parallel workers off: slower, but it needs no shared memory.
"""

from __future__ import annotations

import contextlib
import contextvars
import re

from sqlalchemy import event
from sqlalchemy.pool import Pool

_NO_SHARED_MEMORY = re.compile(r"could not (?:resize|create|map|allocate) (?:dynamic )?shared memory segment")
_SERIAL = contextvars.ContextVar("chiron_mcp_serial", default=False)


def out_of_shared_memory(exc_or_text) -> bool:
    """Whether a failure was Postgres running out of shared memory for parallel workers."""
    return bool(_NO_SHARED_MEMORY.search(str(exc_or_text)))


@contextlib.contextmanager
def without_parallel_workers():
    """Every warehouse connection taken inside this block runs with parallel workers off."""
    token = _SERIAL.set(True)
    try:
        yield
    finally:
        _SERIAL.reset(token)


@event.listens_for(Pool, "checkout")
def _parallel_workers(dbapi_conn, record, _proxy) -> None:
    # Every pool (Chiron's engines and ours): set the connection to what the caller wants,
    # only when it differs, so a normal checkout costs nothing.
    want = _SERIAL.get()
    if record.info.get("serial", False) == want or not type(dbapi_conn).__module__.startswith("psycopg"):
        return
    cur = dbapi_conn.cursor()
    try:
        cur.execute("SET max_parallel_workers_per_gather = 0" if want else "RESET max_parallel_workers_per_gather")
    finally:
        cur.close()
    dbapi_conn.commit()  # a later rollback must not undo it
    record.info["serial"] = want

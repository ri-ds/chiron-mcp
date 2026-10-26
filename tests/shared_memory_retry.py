"""A query that fails because Postgres ran out of shared memory is run once more with
parallel workers off (chiron_mcp.pg), and only when that is harmless.

Needs the Chiron warehouse (it reads one Postgres setting) and a user with access to
synthea-100k, from the usual CHIRON_MCP_* settings; no model. With chiron-benchmark's:

    CHIRON_BENCH_USER=bench-toolcheck PYTHONPATH=../chiron-benchmark .venv/bin/python -c \
      "from bench import config; config.setup(); import runpy; runpy.run_path('tests/shared_memory_retry.py', run_name='__main__')"

Exit code 0 means every check held.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("CHIRON_MCP_USERNAME", "tester")

from chiron_mcp import server as S  # noqa: E402
from chiron_mcp import pg, query  # noqa: E402

fails: list[str] = []


def check(name: str, ok: bool, detail="") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:200])
    if not ok:
        fails.append(name)


ERR = ('(psycopg2.errors.DiskFull) could not resize shared memory segment "/PostgreSQL.611217232" '
       'to 8388608 bytes: No space left on device')
check("the error is recognised", pg.out_of_shared_memory(ERR))
check("other errors are not", not pg.out_of_shared_memory("canceling statement due to statement timeout"))


def workers() -> str:
    """max_parallel_workers_per_gather as Chiron's own engine sees it."""
    from chiron.query_engine.postgres import database

    eng = next(iter(database.singleton_engines.values()), None)
    if eng is None:
        S.chiron_query("synthea-100k")  # makes Chiron create its engine
        eng = next(iter(database.singleton_engines.values()))
    with eng.connect() as c:
        return c.exec_driver_sql("SHOW max_parallel_workers_per_gather").scalar()


normal = workers()
with pg.without_parallel_workers():
    inside = workers()
after = workers()
check("parallel workers off inside the block, on Chiron's engine", inside == "0", f"{normal} -> {inside}")
check("and back to normal after it", after == normal and normal != "0", f"after: {after}")

# The retry: the first attempt fails with the error, the second runs without parallel workers.
seen = []
real = query.run


def flaky(*a, **kw):
    seen.append(workers())
    if len(seen) == 1:
        raise RuntimeError(ERR)
    return {"count": 1, "workers": seen[-1]}


query.run = flaky
try:
    out = S.chiron_query("synthea-100k", where=[{"condition": "asthma"}])
    check("a count is run again and answers", out.get("count") == 1, str(out)[:150])
    check("the second attempt had parallel workers off", seen[1:] == ["0"], str(seen))

    seen.clear()
    query.may_repeat = lambda dataset, show: False
    out = S.chiron_query("synthea-100k", show={"report": {"name": "x"}})
    check("not run again when repeating could save a second report", len(seen) == 1 and "error" in out,
          str(seen))
finally:
    query.run = real

import importlib  # noqa: E402

importlib.reload(query)  # the real may_repeat back
check("counts, lists and Results may repeat", query.may_repeat("synthea-100k", {"results": {}})
      and query.may_repeat("synthea-100k", None) and query.may_repeat("synthea-100k", {"report": {"update": True}}))

print()
print("all passed" if not fails else f"{len(fails)} failed: {fails}")
sys.exit(1 if fails else 0)

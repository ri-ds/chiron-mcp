"""Saved reports by name and id: your own report wins over other users' public reports of
the same name (chiron_mcp.query.find_report); a count that started from a report says how
to change that report; chiron_run_saved_report runs a report (it crashed on a Chiron
accessor); the listing says whose each report is.

The first checks are offline (a stub listing). The rest need Chiron and a user who may
save reports on synthea-100k, from the usual CHIRON_MCP_* settings; with chiron-benchmark's:

    CHIRON_BENCH_USER=bench-toolcheck PYTHONPATH=../chiron-benchmark .venv/bin/python -c \
      "from bench import config; config.setup(); import os; os.environ['CHIRON_MCP_ALLOW_SAVE'] = '1'; \
       import runpy; runpy.run_path('tests/report_names.py', run_name='__main__')"

(bench's setup removes CHIRON_MCP_ALLOW_SAVE, so it is set after it.)

Exit code 0 means every check held.
"""

import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("CHIRON_MCP_USERNAME", "tester")

from chiron_mcp.bootstrap import ensure_django  # noqa: E402

ensure_django()
from chiron_mcp import query as Q  # noqa: E402
from chiron_mcp.identity import AccessError  # noqa: E402

fails: list[str] = []


def check(name: str, ok: bool, detail="") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:220])
    if not ok:
        fails.append(name)


# --- by name, offline: a stub of chiron_saved_reports ---------------------------------------
LISTING = [{"report_id": 46, "name": "Asthma cohort", "mine": False, "public": True},
           {"report_id": 45, "name": "Asthma cohort", "mine": True, "public": True},
           {"report_id": 44, "name": "Asthma cohort", "mine": False, "public": True},
           {"report_id": 40, "name": "Other", "mine": True, "public": False}]


def stub_listing(ds, scope="all", report_id=None, search=None):
    if report_id is not None:
        return {"report_id": report_id, "name": next(r["name"] for r in LISTING if r["report_id"] == report_id),
                "cohort_def": [], "mine": next(r["mine"] for r in LISTING if r["report_id"] == report_id)}
    rows = [r for r in LISTING if scope != "mine" or r["mine"]]
    return {"reports": rows, "count": len(rows)}


S = types.SimpleNamespace(chiron_saved_reports=stub_listing)
check("a name shared with other users' public reports resolves to your own",
      Q.find_report(S, "synthea-100k", "report:Asthma cohort")["report_id"] == 45)
check("by id, any viewable report", Q.find_report(S, "synthea-100k", "report:46")["report_id"] == 46)
check("latest is your most recent", Q.find_report(S, "synthea-100k", "report:latest")["report_id"] == 45)
LISTING[0]["mine"] = True  # now two of your own share the name
try:
    Q.find_report(S, "synthea-100k", "report:Asthma cohort")
    check("two of your own with one name: refused, with the ids", False)
except AccessError as exc:
    check("two of your own with one name: refused, with the ids", "(46, yours)" in str(exc) and "(45, yours)" in str(exc)
          and "report:<id>" in str(exc), str(exc)[:160])
LISTING[0]["mine"] = False
try:
    Q.find_report(S, "synthea-100k", "report:Nothing here")
    check("an unknown name is refused", False)
except AccessError as exc:
    check("an unknown name is refused", "No report called" in str(exc))

# --- live: run a saved report; the note after a count from a report; the listing's owners --
from chiron_mcp import server as RS  # noqa: E402

DS = "synthea-100k"
NAME = "Report-names test (delete me)"
for r in (RS.chiron_saved_reports(DS, scope="mine").get("reports") or []):
    if r["name"] == NAME:
        RS.chiron_delete_report(DS, r["report_id"], confirm_name=NAME)
saved = RS.chiron_query("Synthea 100k", where=[{"condition": "asthma"}], show={"report": {"name": NAME, "columns": ["gender"]}})
rid = (saved.get("report") or {}).get("report_id")
check("a report was saved for the live checks", bool(rid), str(saved)[:160])
if rid:
    try:
        ran = RS.chiron_run_saved_report(DS, rid, records_per_page=3)
        check("chiron_run_saved_report runs it (no Chiron accessor crash)", "error" not in ran and ran.get("report_id") == rid,
              str(ran)[:160])
        counted = RS.chiron_query("Synthea 100k", start_from=f"report:{rid}")
        check("a count from the report says how to change the report",
              any("'update': true" in n and f"report:{rid}" in n for n in counted.get("notes") or []), str(counted.get("notes"))[:200])
        changed = RS.chiron_query("Synthea 100k", start_from=f"report:{rid}", where=[{"field": "gender", "is": "female"}],
                                  show={"report": {"name": NAME, "update": True}})
        check("the change itself carries no such note", "error" not in changed and not any("'update': true" in n for n in changed.get("notes") or []),
              str(changed)[:160])
        listing = RS.chiron_saved_reports(DS)
        mine = next((r for r in listing["reports"] if r["report_id"] == rid), {})
        check("the listing says the report is yours", mine.get("owner") == "you" and listing.get("yours", 0) >= 1, str(mine)[:120])
    finally:
        RS.chiron_delete_report(DS, rid, confirm_name=NAME)

print()
print("all passed" if not fails else f"{len(fails)} failed: {fails}")
sys.exit(1 if fails else 0)

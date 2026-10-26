"""An identity that may not view subject details gets no column that identifies a person.

Offline: no database, no model; the rule and the gate are checked on stand-in concepts.

    .venv/bin/python tests/identifying_columns.py
"""

import os
import sys
import tempfile
from types import SimpleNamespace as NS

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
tmp = tempfile.mkdtemp()
os.environ.update(CHIRON_MCP_USERNAME="tester", CHIRON_MCP_STATE_DIR=os.path.join(tmp, "state"), CHIRON_MCP_TRACE="0")

from chiron_mcp import server as S  # noqa: E402
from chiron_mcp.identity import AccessError  # noqa: E402

fails: list[str] = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:200])
    if not ok:
        fails.append(name)


def concept(short, has_phi=False, name=None):
    return NS(permanent_id=f"ds__subject__{short}", has_phi=has_phi, name=name or short)


first, last, ssn, city, birth, pid = (concept(x) for x in ("first", "last", "ssn", "city", "birthdate", "id"))
flagged = concept("mrn", has_phi=True, name="medical record number")

check("names, ssn and a has_phi concept identify a person",
      all(S._identifies_person(c) for c in (first, last, ssn, flagged)))
check("city, birthdate and the patient id do not", not any(S._identifies_person(c) for c in (city, birth, pid)))

deid = NS(can_view_subject_details=False)
full = NS(can_view_subject_details=True)
try:
    S._require_columns_viewable(deid, [pid, first, last, city])
    check("a de-identified identity is refused the name columns", False, "no error")
except AccessError as exc:
    check("a de-identified identity is refused the name columns", "first, last" in str(exc) and "may not view" in str(exc), str(exc)[:120])
try:
    S._require_columns_viewable(deid, [pid, city, birth])
    check("the same identity may list id, city and birthdate", True)
except AccessError as exc:
    check("the same identity may list id, city and birthdate", False, str(exc)[:120])
try:
    S._require_columns_viewable(full, [pid, first, last, ssn])
    check("an identity that may view subject details is not refused", True)
except AccessError as exc:
    check("an identity that may view subject details is not refused", False, str(exc)[:120])

print()
print("all passed" if not fails else f"{len(fails)} failed: {fails}")
sys.exit(1 if fails else 0)

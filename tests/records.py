"""A patient's records, one row each, paired as recorded (chiron_query's show="records").

In-process, no model: the rows the tool hands the model are compared with a direct SQL
read of the warehouse, so a date and a value in one row are the same record's, every
record is there and in order, and the filters, the caps and the gates hold.

Needs the server's CHIRON_MCP_* database settings in the environment (as tests/ask_e2e.py).
Runs as demouser, and makes (then removes) the permission suite's perm_agg account for the
aggregate-only check. TEST_DATASET names the dataset (synthea-10k); TEST_PATIENT_BIRTHDATE
a patient of it with many readings (default 1929-12-14, the patient in the feedback that
led to this).

    .venv/bin/python tests/records.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("CHIRON_MCP_USERNAME", "demouser")

import ask_e2e as E  # noqa: E402  (the warehouse connection and schema names)
import permissions as PM  # noqa: E402  (the perm_* accounts)

DS = E.DS
P = E.P
SCHEMA = E.SCHEMA
BORN = os.environ.get("TEST_PATIENT_BIRTHDATE", "1929-12-14")
fails: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    print(f"{'PASS' if cond else 'FAIL'}  {label}  {str(detail)[:240]}", flush=True)
    if not cond:
        fails.append(label)


def sql_rows(q: str) -> list[tuple]:
    import psycopg2

    with psycopg2.connect(E.WAREHOUSE) as conn, conn.cursor() as cur:
        cur.execute(f"set search_path to {SCHEMA}")
        cur.execute(q)
        return [tuple(str(v) if hasattr(v, "isoformat") else v for v in r) for r in cur.fetchall()]


def lkp(coll: str, short: str, alias: str) -> str:
    return f'left join "lkp_{P}{coll}__{short}" {alias} on {alias}._collection_id = r._id'


def col(alias: str, coll: str, short: str) -> str:
    return f'{alias}."{P}{coll}__{short}"'


def her(coll: str) -> str:
    """FROM ... for one patient's records of a collection (r), by birthdate."""
    return (f'from subject s join "lkp_{P}subject__birthdate" b on b._collection_id = s._id '
            f'join {coll} r on r._subject_id = s._subject_id where {col("b", "subject", "birthdate")} = \'{BORN}\'')


def records(where, spec, user: str = "demouser"):
    from chiron_mcp import query
    from chiron_mcp.config import CONFIG

    before = CONFIG.username
    CONFIG.username = user
    try:
        try:
            r = query.run(DS, where, "all", None, {"records": spec}, None)
        except Exception as exc:  # noqa: BLE001
            return {"error": f"{type(exc).__name__}: {exc}"}
        return r
    finally:
        CONFIG.username = before


def rows_of(r) -> list:
    return (r.get("records") or {}).get("rows") or []


def main() -> int:
    from chiron_mcp.bootstrap import ensure_django

    ensure_django()
    from chiron_mcp import query

    who = [{"field": "birthdate", "is": BORN}]
    tag = "[records]"

    # --- her diastolic readings: every row equals the warehouse, in date order
    truth = sql_rows(f'select {col("d", "observation", "date")}, {col("v", "observation", "value")}, {col("u", "observation", "units")} '
                     f'{her("observation")} and lower({col("n", "observation", "description")}) like \'diastolic%\' order by 1, r._id'
                     .replace("where", f'{lkp("observation", "description", "n")} {lkp("observation", "date", "d")} '
                                       f'{lkp("observation", "value", "v")} {lkp("observation", "units", "u")} where', 1))
    r = records(who, {"of": {"lab": "Diastolic Blood Pressure"}})
    rec = r.get("records") or {}
    got = [(row[1], row[3], row[4]) for row in rows_of(r)]
    check(f"{tag} her diastolic readings: one row per reading, date and value together, same as SQL",
          not r.get("error") and got == truth and len(got) > 20,
          f"error={r.get('error')} sql={len(truth)} got={len(got)} first={got[:1]} vs {truth[:1]}")
    check(f"{tag} the row says the patient, the lab, the value and the units",
          rec.get("columns") == ["patient", "date", "lab", "value", "units"], rec.get("columns"))
    check(f"{tag} totals: total == returned, one patient, not truncated",
          rec.get("total") == len(got) == rec.get("returned") and rec.get("patients") == 1 and rec.get("truncated") is False,
          {k: rec.get(k) for k in ("total", "returned", "patients", "truncated")})
    check(f"{tag} the patient column is the pseudonymous patient ID (a UUID), never a name",
          all(len(str(row[0])) == 36 and str(row[0]).count("-") == 4 for row in rows_of(r)), rows_of(r)[:1])
    check(f"{tag} no row mentions the patient's name fields", not any(k in str(rec.get("columns")) for k in ("first", "last")), rec.get("columns"))

    # --- newest first, a row cap, and the note that says so
    r = records(who, {"of": {"lab": "Diastolic Blood Pressure"}, "order": "newest", "limit": 3})
    rec = r.get("records") or {}
    check(f"{tag} newest first with limit 3: 3 rows, total {len(truth)}, truncated, latest date first",
          rec.get("returned") == 3 and rec.get("total") == len(truth) and rec.get("truncated") is True
          and rows_of(r)[0][1] == truth[-1][0], {k: rec.get(k) for k in ("returned", "total", "truncated")})
    check(f"{tag} the truncation is said in a note for the model", any("Only the first 3 of" in n for n in r.get("notes") or []), r.get("notes"))

    # --- a value filter: the planted impossible systolic reading
    truth_sys = sql_rows(f'select {col("d", "observation", "date")}, {col("v", "observation", "value")} '
                         f'{her("observation")} and lower({col("n", "observation", "description")}) like \'systolic%\' and {col("v", "observation", "value")} > 1000 order by 1'
                         .replace("where", f'{lkp("observation", "description", "n")} {lkp("observation", "date", "d")} {lkp("observation", "value", "v")} where', 1))
    r = records(who, {"of": {"lab": "Systolic Blood Pressure", "op": ">", "value": 1000}})
    check(f"{tag} a value range in 'of' keeps only those readings (systolic > 1000)",
          [(row[1], row[3]) for row in rows_of(r)] == truth_sys and len(truth_sys) >= 1, f"{rows_of(r)[:2]} vs {truth_sys}")

    # --- visits, conditions, prescriptions: dates with each record
    truth_v = sql_rows(f'select {col("a", "encounter", "start")}, {col("c", "encounter", "encounterclass")} {her("encounter")} order by 1, r._id'
                       .replace("where", f'{lkp("encounter", "start", "a")} {lkp("encounter", "encounterclass", "c")} where', 1))
    r = records(who, {"of": "visit"})
    check(f"{tag} her visits: every visit with its date and type, same as SQL",
          [(row[1], row[3]) for row in rows_of(r)] == truth_v and len(truth_v) > 10,
          f"error={r.get('error')} sql={len(truth_v)} got={len(rows_of(r))} columns={(r.get('records') or {}).get('columns')}")
    r = records(who, {"of": {"visit": "emergency"}})
    check(f"{tag} her emergency visits only",
          not r.get("error") and rows_of(r) and all(row[3] == "emergency" for row in rows_of(r))
          and len(rows_of(r)) == sum(1 for v in truth_v if str(v[1]).lower() == "emergency"), rows_of(r)[:2])
    r = records(who, {"of": {"visit": "any", "year": 2000}})
    check(f"{tag} her visits in one year (a date range in 'of')",
          not r.get("error") and rows_of(r) and all(str(row[1]).startswith("2000") for row in rows_of(r))
          and len(rows_of(r)) == sum(1 for v in truth_v if str(v[0]).startswith("2000")), rows_of(r)[:2])
    truth_c = sql_rows(f'select {col("a", "condition", "start")}, {col("z", "condition", "stop")}, {col("n", "condition", "description")} {her("condition")} order by 1, r._id'
                       .replace("where", f'{lkp("condition", "start", "a")} {lkp("condition", "stop", "z")} {lkp("condition", "description", "n")} where', 1))
    r = records(who, {"of": "condition"})
    check(f"{tag} her conditions with start and stop dates", [tuple(row[1:4]) for row in rows_of(r)] == truth_c and truth_c,
          f"{rows_of(r)[:2]} vs {truth_c[:2]}")
    r = records(who, {"of": {"medication": "any"}, "fields": "all"})
    rec = r.get("records") or {}
    check(f"{tag} her prescriptions with every field ('all')",
          not r.get("error") and rows_of(r) and {"start", "stop", "medication", "dispenses"} <= set(rec.get("columns") or []),
          rec.get("columns"))
    r = records(who, {"of": "procedure", "fields": ["date", "procedure", "cost"]})
    check(f"{tag} chosen fields, in the order asked", (r.get("records") or {}).get("columns") == ["patient", "date", "procedure", "cost"]
          and rows_of(r), (r.get("records") or {}).get("columns"))

    # --- a cohort whose own condition is on the same kind of record still gets every record
    r = records([{"lab": "Diastolic Blood Pressure", "op": ">", "value": 80}] + who, {"of": {"lab": "Diastolic Blood Pressure"}})
    check(f"{tag} a cohort defined by 'diastolic > 80' still lists all of her diastolic readings, the low ones too",
          [(row[1], row[3], row[4]) for row in rows_of(r)] == truth and any(float(row[3]) <= 80 for row in rows_of(r)),
          f"error={r.get('error')} got={len(rows_of(r))} sql={len(truth)}")

    # --- latest / earliest per patient over a small group
    small = [{"condition": "asthma"}, {"field": "birthdate", "before": "1932-01-01"}]
    n = query.run(DS, small, "all", None, None, None)["count"]
    truth_latest = sql_rows(
        f'select x.sid, x.d, x.v from (select s._id sid, {col("d", "observation", "date")} d, {col("v", "observation", "value")} v, '
        f'row_number() over (partition by s._id order by {col("d", "observation", "date")} desc, r._id) rn '
        f'from subject s join observation r on r._subject_id = s._subject_id {lkp("observation", "description", "n")} '
        f'{lkp("observation", "date", "d")} {lkp("observation", "value", "v")} '
        f'where lower({col("n", "observation", "description")}) like \'body mass index%\' and s._id in '
        f'(select s2._id from subject s2 join "lkp_{P}subject__birthdate" b on b._collection_id = s2._id '
        f'join condition c on c._subject_id = s2._subject_id {lkp("condition", "description", "cd").replace("r._id", "c._id")} '
        f'where {col("b", "subject", "birthdate")} < \'1932-01-01\' and lower({col("cd", "condition", "description")}) in (\'asthma\', \'asthm\'))) x '
        f'where x.rn = 1 order by x.sid')
    r = records(small, {"of": {"lab": "Body Mass Index"}, "latest": 1})
    rec = r.get("records") or {}
    got = sorted((row[1], row[3]) for row in rows_of(r))
    check(f"{tag} latest 1 BMI per patient over {n} patients: one row each, the newest, same as SQL",
          not r.get("error") and n > 1 and len(rows_of(r)) == len(truth_latest) == rec.get("patients")
          and got == sorted((t[1], t[2]) for t in truth_latest), f"error={r.get('error')} got={got[:3]} sql={len(truth_latest)}")
    r = records(small, {"of": {"lab": "Body Mass Index"}, "earliest": 2})
    check(f"{tag} earliest 2 per patient: two rows each, the first dated first",
          not r.get("error") and len(rows_of(r)) == 2 * n and all(
              rows_of(r)[i][1] <= rows_of(r)[i + 1][1] for i in range(0, len(rows_of(r)) - 1, 2) if rows_of(r)[i][0] == rows_of(r)[i + 1][0]),
          f"error={r.get('error')} rows={len(rows_of(r))}")
    r = records(small, {"of": {"lab": "hemoglobin a1c"}, "latest": 1})
    rec = r.get("records") or {}
    check(f"{tag} patients without such a record have no rows, and the note says how many",
          not r.get("error") and rec.get("patients", 0) < n and any("have no such record" in x for x in r.get("notes") or []),
          f"patients={rec.get('patients')} of {n} notes={r.get('notes')}")

    # --- caps and refusals
    many = [{"condition": "asthma"}]
    r = records(many, {"of": "lab"})
    check(f"{tag} records over a large group are refused with the alternatives, never a sample",
          "error" in r and "Records are for one patient or a small group" in r["error"] and "rows" not in str(r.get("records")), r.get("error", "")[:120])
    r = records(many, {"of": {"lab": "Body Mass Index"}, "latest": 1})
    check(f"{tag} latest per patient over too many patients is refused too", "error" in r and "up to 500" in r["error"], r.get("error", "")[:120])
    r = records(who, {"of": {"lab": "Diastolic Blood Pressure"}, "limit": 5000})
    check(f"{tag} limit is capped at 500", not r.get("error") and (r.get("records") or {}).get("returned") == len(truth), (r.get("records") or {}).get("returned"))
    for spec, why in (({"of": "subject"}, "the patient is not a kind of record"),
                      ({"of": {"visit": "emergency", "at_least": 2}}, "a count rule belongs in where"),
                      ({"of": {"lab": "HbA1c"}, "fields": ["first name"]}, "a patient field is not a record field"),
                      ({"of": {"lab": "HbA1c"}, "latest": 1, "earliest": 1}, "latest and earliest together"),
                      ({"of": "lab", "bogus": 1}, "an unknown key"),
                      ({"kind": "lab"}, "no 'of'")):
        r = records(who, spec)
        check(f"{tag} refused: {why}", "error" in r and not rows_of(r), r.get("error", "")[:100])
    PM.ensure_accounts()
    try:
        r = records(who, {"of": {"lab": "Diastolic Blood Pressure"}}, user="perm_agg")
        check(f"{tag} an aggregate-only account gets no records", "error" in r and not rows_of(r), r.get("error", "")[:100])
        r = records(who, {"of": {"lab": "Diastolic Blood Pressure"}}, user="perm_deid")
        check(f"{tag} a de-identified account without identifying columns gets the readings (no name in them)",
              not r.get("error") and len(rows_of(r)) == len(truth), f"error={r.get('error')} rows={len(rows_of(r))}")
        r = records(who, {"of": "visit", "fields": ["provider", "visit type"]}, user="perm_deid")
        check(f"{tag} and may ask for other record fields", not r.get("error") and rows_of(r), r.get("error", "")[:100])
    finally:
        PM.remove_accounts()
    r = records([], {"of": {"lab": "Diastolic Blood Pressure"}, "latest": 1})
    check(f"{tag} the whole dataset is refused (too many patients)", "error" in r and not rows_of(r), r.get("error", "")[:100])

    # --- the date 'is' form the model writes for one patient
    r = query.run(DS, [{"field": "birthdate", "is": BORN}], "all", None, None, None)
    check(f"{tag} birthdate 'is' one day finds the patient", r.get("count") == 1, r.get("count"))
    r = query.run(DS, [{"field": "birthdate", "is": BORN[:4]}], "all", None, None, None)
    year_n = E.sql(f'select count(distinct _collection_id) from "lkp_{P}subject__birthdate" where extract(year from "{P}subject__birthdate") = {BORN[:4]}')
    check(f"{tag} birthdate 'is' a year means that whole year", r.get("count") == year_n, (r.get("count"), year_n))

    print("ALL PASS" if not fails else f"{len(fails)} FAILED:\n  " + "\n  ".join(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())

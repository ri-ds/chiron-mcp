"""The 'within' condition against a live Chiron: each of Chiron's counts is compared with
the same cohort in raw SQL on the warehouse, and the refusals are checked in words.

Needs a dataset whose tables have event dates (Collection.event_date_field, and an end
date on the interval ones) and whose records are the Synthea ones: the usual CHIRON_MCP_*
settings name the metadata and the warehouse, CHIRON_MCP_TEST_DATASET the dataset
(default synthea-10k) and CHIRON_MCP_TEST_NO_EVENTS one without event dates (default
synthea-small), for the refusal.

    CHIRON_MCP_METADATA_DB=... CHIRON_MCP_WAREHOUSE_URL=postgresql://... \
      CHIRON_MCP_USERNAME=demouser .venv/bin/python tests/within_live.py

Exit code 0 means every check held.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("CHIRON_MCP_USERNAME", "tester")

from chiron_mcp.bootstrap import ensure_django  # noqa: E402

ensure_django()
import psycopg2  # noqa: E402

from chiron_mcp import query as Q  # noqa: E402
from chiron_mcp.identity import AccessError  # noqa: E402

DS = os.environ.get("CHIRON_MCP_TEST_DATASET", "synthea-10k")
NO_EVENTS = os.environ.get("CHIRON_MCP_TEST_NO_EVENTS", "synthea-small")
SCHEMA = DS.replace("-", "_")

conn = psycopg2.connect(os.environ["CHIRON_MCP_WAREHOUSE_URL"].split("?")[0])
conn.set_session(readonly=True, autocommit=True)
cur = conn.cursor()
cur.execute(f"set search_path to {SCHEMA}")
cur.execute("select table_name from information_schema.tables where table_schema = %s and table_name like "
            "'lkp\\_%%\\_\\_subject\\_\\_%%' limit 1", (SCHEMA,))
row = cur.fetchone()
P = row[0][len("lkp_"):].split("subject__")[0] if row else DS + "__"

fails: list[str] = []


def check(name: str, ok: bool, detail="") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:220])
    if not ok:
        fails.append(name)


def recs(table, name_col, name_cond, date_col):
    """One table's records (patient, date) whose name matches: the raw SQL side."""
    col = 'n."' + P + table + "__" + name_col + '"'
    return (f'select t._subject_id sid, l."{P}{table}__{date_col}" d from {table} t '
            f'join "lkp_{P}{table}__{name_col}" n on n._collection_id = t._id '
            f'join "lkp_{P}{table}__{date_col}" l on l._collection_id = t._id '
            f'where {name_cond.replace("VAL", col)}')


def sql_within(src, tgt, lo, hi):
    cur.execute(f"select count(distinct s.sid) from ({src}) s join ({tgt}) g on g.sid = s.sid "
                f"and (s.d::date - g.d::date) between {lo} and {hi}")
    return cur.fetchone()[0]


def run(where, dataset=DS, **kw):
    try:
        return Q.run(dataset, where, **kw)
    except AccessError as exc:
        return {"error": str(exc)}


t2dm = recs("condition", "description", "lower(VAL) like 'type 2 diabetes%'", "start")
metf = recs("medication", "description", "lower(VAL) like 'metformin%'", "start")
er = recs("encounter", "encounterclass", "lower(VAL) = 'emergency'", "start")
urgent = recs("encounter", "encounterclass", "lower(VAL) = 'urgentcare'", "start")
urgent_end = recs("encounter", "encounterclass", "lower(VAL) = 'urgentcare'", "stop")
asthma = recs("condition", "description", "lower(VAL) in ('asthma', 'asthm')", "start")
asthma_end = recs("condition", "description", "lower(VAL) in ('asthma', 'asthm')", "stop")
albuterol = recs("medication", "description", "lower(VAL) like 'albuterol%'", "start")

r = run([{"medication": "metformin", "within": {"days_after": 90, "of": {"condition": "type 2 diabetes"}}}])
want = sql_within(metf, t2dm, 0, 90)
check("metformin within 90 days after a type 2 diabetes record = SQL", r.get("count") == want, (r.get("count"), want, r.get("error")))
check("Chiron's own words carry the timing", "90 days after" in r.get("what_was_counted", ""), r.get("what_was_counted"))
check("and so do the plain words", any("within 90 days after" in t for t in r.get("timing", [])), r.get("timing"))
rules = [e.get("event_rule", {}).get("type") for e in r.get("cohort_def", [])]
check("the other record gets 'any date', the timed one the relative rule",
      rules == ["no_restriction", "relative_to_other_event"], rules)
g1 = r.get("group")

r = run([{"visit": "emergency", "within": {"days_before": 30, "of": {"condition": "asthma"}}}])
want = sql_within(er, asthma, -30, 0)
check("an ER visit within 30 days before an asthma record = SQL", r.get("count") == want, (r.get("count"), want, r.get("error")))

r = run([{"visit": "urgent care", "within": {"days_after": 30, "of": {"visit": "emergency"}}}])
want = sql_within(urgent, er, 0, 30)
check("two records of one table (urgent care after an ER visit) = SQL", r.get("count") == want, (r.get("count"), want, r.get("error")))

r = run([{"visit": "emergency", "within": {"days": 7, "of": {"condition": "asthma"}}}])
want = sql_within(er, asthma, -7, 7)
check("'days': either side = SQL", r.get("count") == want, (r.get("count"), want, r.get("error")))

r = run([{"visit": "emergency", "within": {"days_after": 30, "of": {"visit": "urgent care"}, "from": "end"}}])
want = sql_within(er, urgent_end, 0, 30)
check("from 'end': counted from the other record's end date = SQL", r.get("count") == want, (r.get("count"), want, r.get("error")))

r = run([{"medication": "albuterol", "within": {"days_before": 60, "of": {"condition": "asthma"}, "from": "end"}}])
want = sql_within(albuterol, asthma_end, -60, 0)
check("before, from 'end' = SQL", r.get("count") == want, (r.get("count"), want, r.get("error")))

r = run([{"field": "gender", "is": "female"}], start_from=g1)
cur.execute(f"select count(distinct s.sid) from ({metf}) s join ({t2dm}) g on g.sid = s.sid and (s.d::date - g.d::date) "
            f'between 0 and 90 join "lkp_{P}subject__gender" x on x._collection_id = s.sid '
            f'where upper(x."{P}subject__gender") = \'F\'')
want = cur.fetchone()[0]
check("a follow-up narrows the timed group = SQL", r.get("count") == want, (r.get("count"), want, r.get("error")))

r = run([{"medication": "metformin", "within": {"days_after": 90, "of": {"condition": "type 2 diabetes"}}},
         {"condition": "asthma"}], match="any")
cur.execute(f"select count(distinct sid) from ((select s.sid from ({metf}) s join ({t2dm}) g on g.sid = s.sid and "
            f"(s.d::date - g.d::date) between 0 and 90) union (select sid from ({asthma}) a)) x")
want = cur.fetchone()[0]
check("'any' with a timed condition (inclusion-exclusion) = SQL", r.get("count") == want, (r.get("count"), want, r.get("error")))

r = run([{"visit": "emergency", "within": {"days_after": 7, "of": {"procedure": "throat culture"}, "from": "end"}}])
check("from 'end' on a table with one date is refused", "no end date" in r.get("error", ""), r.get("error", r.get("count")))

r = run([{"medication": "metformin", "within": {"days_after": 90, "of": {"condition": "type 2 diabetes"}}}], dataset=NO_EVENTS)
check("a dataset without event dates is refused in words", "gives them none" in r.get("error", ""), r.get("error", r.get("count")))

print("\nALL PASS" if not fails else f"\nFAILED: {', '.join(fails)}")
sys.exit(1 if fails else 0)

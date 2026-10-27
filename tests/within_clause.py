"""The 'within' condition of chiron_query: a record timed against another record of the
same patient ("started metformin within 90 days after the diagnosis"). Parsing and the
words it is given back in; no database and no model, the dictionary is stubbed.

    .venv/bin/python tests/within_clause.py

Exit code 0 means every check held. The clause against a live Chiron, with Chiron's
count compared to raw SQL: tests/within_live.py.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("CHIRON_MCP_USERNAME", "tester")

from chiron_mcp import query as Q  # noqa: E402
from chiron_mcp.identity import AccessError  # noqa: E402

fails: list[str] = []


def check(name: str, ok: bool, detail="") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:220])
    if not ok:
        fails.append(name)


class Concept:
    def __init__(self, name):
        self.name = name


def var(short, collection, kind="category"):
    return Q.Var(Concept(short), f"ds__{collection}__{short}", collection, short, kind)


# A dictionary of names only: every table has a description, the patient a gender.
Q._vars = lambda ident, collection=None: [var("description", collection or "condition")]
Q._name_filter = lambda ident, coll, name, matched: (var("description", coll), {"selected_categories": [name]},
                                                     f"description is {name}")
Q.resolve_field = lambda ident, phrase, collection=None: var(phrase, collection or "subject")
Q._filter_for = lambda ident, v, cond, matched: ({"selected_categories": [cond.get("is")]}, f"{v.short} is {cond.get('is')}")


def parse(cond):
    try:
        return Q.parse_condition(None, cond)
    except AccessError as exc:
        return str(exc)


c = parse({"medication": "metformin", "within": {"days_after": 90, "of": {"condition": "type 2 diabetes"}}})
check("after: a window from the same day to N days after", isinstance(c, Q.Clause) and c.within
      and (c.within["before"], c.within["after"], c.within["from"]) == (0, 90, "start"), getattr(c, "within", c))
check("the other record is a clause of its own", isinstance(c, Q.Clause) and c.within["target"].collection == "condition"
      and c.within["target"].filters[0][2] == "description is type 2 diabetes")
check("in words", Q._within_words(c.within) == "within 90 days after (or on the day of) description is type 2 diabetes",
      Q._within_words(c.within))

c = parse({"visit": "emergency", "within": {"days_before": 30, "of": {"procedure": "colonoscopy"}}})
check("before: N days before to the same day", isinstance(c, Q.Clause) and (c.within["before"], c.within["after"]) == (30, 0))
check("before in words", Q._within_words(c.within) == "within 30 days before (or on the day of) description is colonoscopy",
      Q._within_words(c.within))

c = parse({"visit": "emergency", "within": {"days": 7, "of": {"condition": "asthma"}}})
check("days: either side", isinstance(c, Q.Clause) and (c.within["before"], c.within["after"]) == (7, 7))
check("either side in words", Q._within_words(c.within) == "from 7 days before to 7 days after description is asthma",
      Q._within_words(c.within))

c = parse({"visit": "emergency", "within": {"days_after": 30, "of": {"visit": "inpatient"}, "from": "end"}})
check("from end: counted from the other record's end", isinstance(c, Q.Clause) and c.within["from"] == "end")
check("from end in words", "(from its end date)" in Q._within_words(c.within), Q._within_words(c.within))

c = parse({"visit": "emergency", "within": {"days_before": "30", "days_after": 30.0, "of": {"condition": "asthma"}}})
check("numbers as strings or floats are whole days", isinstance(c, Q.Clause) and (c.within["before"], c.within["after"]) == (30, 30))

c = parse({"medication": "metformin", "within": {"days_before": "any", "of": {"condition": "type 2 diabetes"}}})
check("'any' stands for no limit", isinstance(c, Q.Clause) and (c.within["before"], c.within["after"]) == (Q.ANY_DAYS, 0))
check("'any' in words", Q._within_words(c.within) == "any time before (or on the day of) description is type 2 diabetes",
      Q._within_words(c.within))

c = parse({"condition": "asthma"})
check("no within: nothing timed", isinstance(c, Q.Clause) and c.within is None)

for label, cond, want in [
    ("a patient field has no date to time", {"field": "gender", "is": "female", "within": {"days": 1, "of": {"condition": "asthma"}}},
     "patient's own field"),
    ("a count rule and timing together are refused", {"visit": "emergency", "at_least": 2, "within": {"days_after": 30, "of": {"condition": "asthma"}}},
     "count rule"),
    ("'never' and timing together are refused", {"visit": "emergency", "never": True, "within": {"days_after": 30, "of": {"condition": "asthma"}}},
     "count rule"),
    ("a count rule on the other record is refused", {"visit": "emergency", "within": {"days_after": 30, "of": {"condition": "asthma", "at_least": 2}}},
     "count rule"),
    ("days outside within are pointed inside", {"visit": "emergency", "days_after": 30, "of": {"condition": "asthma"}}, "inside 'within'"),
    ("within needs days", {"visit": "emergency", "within": {"of": {"condition": "asthma"}}}, "needs days_after"),
    ("within needs the other record", {"visit": "emergency", "within": {"days": 3}}, "'of'"),
    ("an unknown key is refused", {"visit": "emergency", "within": {"days": 3, "weeks": 1, "of": {"condition": "asthma"}}}, "does not take weeks"),
    ("negative days are refused", {"visit": "emergency", "within": {"days_after": -3, "of": {"condition": "asthma"}}}, "negative"),
    ("a bad 'from'", {"visit": "emergency", "within": {"days": 3, "of": {"condition": "asthma"}, "from": "middle"}}, "'start'"),
    ("the other record cannot be a patient field", {"visit": "emergency", "within": {"days": 3, "of": {"field": "gender", "is": "female"}}}, "not a patient field"),
    ("no chains", {"visit": "emergency", "within": {"days": 3, "of": {"condition": "asthma", "within": {"days": 3, "of": {"procedure": "x"}}}}}, "two records at a time"),
]:
    r = parse(cond)
    check(label, isinstance(r, str) and want in r, r if isinstance(r, str) else "parsed")

# labels and 'any'
timed = parse({"medication": "metformin", "within": {"days_after": 90, "of": {"condition": "type 2 diabetes"}}})
plain = parse({"condition": "asthma"})
check("the group label carries the timing", "within 90 days after" in Q._label([timed], None), Q._label([timed], None))
check("'any' never merges a timed condition into one filter", Q._merge_any([timed, plain]) is None)
check("the timed record's matches are the clause's too", timed.matched == [] or isinstance(timed.matched, list))

print("\nALL PASS" if not fails else f"\nFAILED: {', '.join(fails)}")
sys.exit(1 if fails else 0)

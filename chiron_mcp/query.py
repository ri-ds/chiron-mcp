"""chiron_query: a question described in plain terms in; Chiron's own answer out (plan P2).

The model says WHAT it wants ("lab HbA1c >= 6.5", "condition COPD, never", "at least 3
emergency visits") and this module does the mechanics a model gets wrong:

- finds the table, variable and every recorded spelling of each value (dictionary.py,
  plus the values Chiron itself holds);
- gives every condition its own group (criteria set), so "asthma and COPD" means two
  records of a patient, never one record that is both, while a lab's name and its value
  stay on the same record;
- turns strict limits into Chiron's inclusive ones exactly ("over 4,500" is just above
  4,500, not 4,501), and dates likewise;
- writes count rules Chiron can read ("at least 3", "exactly 0" for "never");
- does "either" across tables by exact inclusion-exclusion of Chiron's own counts;
- then counts, breaks down, lists or gives a value range with Chiron's engine, and says
  in Chiron's own words what was counted.

Nothing here invents a figure: every number comes from Chiron. When a question can't be
expressed, it says so instead of dropping a condition.
"""

from __future__ import annotations

import copy
import difflib
import html
import itertools
import json
import os
import re
import time
from datetime import date, datetime, timedelta
from typing import Any

from chiron_mcp import dictionary as D
from chiron_mcp import identity
from chiron_mcp.identity import AccessError

KINDS = {
    "CohortDefCategory": "category", "CohortDefBoolean": "category",
    "CohortDefText": "text", "CohortDefTextCustomSort": "text", "CohortDefOntology": "ontology",
    "CohortDefNumber": "number", "CohortDefNumberWithCategories": "number",
    "CohortDefDate": "date", "CohortDefDateDeid": "year", "CohortDefDetailedAge": "age",
}
SPEC_HELP = (
    "Each item of `where` is one condition, for example: {'condition': 'asthma'}; "
    "{'condition': 'COPD', 'never': true}; {'lab': 'HbA1c', 'op': '>=', 'value': 6.5}; "
    "{'medication': 'metformin'}; {'visit': 'emergency', 'at_least': 3}; "
    "{'condition': 'hypothyroidism', 'year_between': [2010, 2015]}; "
    "{'field': 'income', 'op': '>', 'value': 150000}; {'field': 'gender', 'is': 'female'}; "
    "{'field': 'death date', 'has_value': true}; {'field': 'birthdate', 'before': '1945-01-01'}; "
    "{'visit': 'self-pay', 'with': [{'field': 'cost', 'op': '>', 'value': 1000}]}."
)
TABLE_KEYS = {w: coll for coll, words in D.TABLES.items() if coll != "subject" for w in words}
TABLE_KEYS.update({"lab": "observation", "vital": "observation", "test": "observation"})
_COUNT_KEYS = {"at_least": "at least", "at_most": "at most", "exactly": "exactly",
               "more_than": "more than", "fewer_than": "fewer than", "less_than": "fewer than"}
_OPS = {">": ">", ">=": ">=", "≥": ">=", "<": "<", "<=": "<=", "≤": "<=", "=": "=", "==": "=",
        "over": ">", "above": ">", "more than": ">", "greater than": ">", "at least": ">=",
        "under": "<", "below": "<", "less than": "<", "fewer than": "<", "at most": "<=",
        "equals": "=", "is": "="}

_CACHE: dict[str, Any] = {}


class Var:
    """One Chiron variable (concept) as this identity may use it."""

    def __init__(self, concept, cid: str, collection: str, short: str, kind: str | None):
        self.concept, self.cid, self.collection, self.short, self.kind = concept, cid, collection, short, kind
        self.name = concept.name or short

    def label(self) -> str:
        return f"{self.collection} {self.name}"


class Clause:
    """One condition: filters on ONE record of one table (or on the patient), plus how
    many such records the patient must have."""

    def __init__(self, collection: str, text: str):
        self.collection, self.text = collection, text
        self.filters: list[tuple[Var, dict, str]] = []  # (variable, Chiron filter fields, what it means)
        self.count_rule: tuple[str, int] | None = None
        self.matched: list[dict] = []


# --- what the identity can see -------------------------------------------------------------
def catalogue(ident) -> list[Var]:
    key = f"cat:{ident.dataset_id}"
    if key in _CACHE:
        return _CACHE[key]
    from chiron import models

    cu = identity.checked_chironuser(ident)
    out = []
    for c in (models.Concept.objects.filter(collection__dataset=ident.dataset, published=True)
              .select_related("collection")):
        try:
            if not c.user_can_use_concept_in_cohort_def(cu)[0]:
                continue
            proc = c.get_cohort_def_processor(cu)
        except Exception:  # noqa: BLE001
            continue
        parts = c.permanent_id.split("__")
        if len(parts) < 3:
            continue
        out.append(Var(c, c.permanent_id, parts[1], "__".join(parts[2:]),
                       KINDS.get(type(proc).__name__) if proc else None))
    _CACHE[key] = out
    return out


def _vars(ident, collection: str | None = None) -> list[Var]:
    return [v for v in catalogue(ident) if collection is None or v.collection == collection]


def _var(ident, collection: str, short: str) -> Var | None:
    return next((v for v in _vars(ident, collection) if v.short == short), None)


# --- datasets --------------------------------------------------------------------------------
def resolve_dataset(name: str) -> str:
    """A dataset id from its id, display name or a usual name for it ("Synthea 300")."""
    from chiron_mcp import server as S

    rows = (S.chiron_datasets() or {}).get("datasets") or []
    n = D.norm(name)
    flat = n.replace(" ", "")

    def words(r):
        return [D.norm(r["dataset_id"]), D.norm(r.get("name")), *map(D.norm, D.DATASET_WORDS.get(r["dataset_id"], ()))]

    hits = [r for r in rows if flat in {w.replace(" ", "") for w in words(r) if w}]
    if not hits:
        toks = set(n.split())
        scored = []
        for r in rows:
            best = max((len(w.split()) for w in words(r) if w and set(w.split()) <= toks), default=0)
            if best:
                scored.append((best, r))
        if scored:
            top = max(s for s, _ in scored)
            hits = [r for s, r in scored if s == top]
    usable = [r for r in rows if r.get("accessible")]
    names = ", ".join(f"{r.get('name') or r['dataset_id']} ({r['dataset_id']})" for r in usable) or "none"
    if len(hits) != 1:
        raise AccessError(
            f"There is no dataset called {name!r} here, so this cannot be answered from it. "
            f"Datasets you can use: {names}. Say plainly that {name!r} is not available; do not "
            "answer from another dataset unless the user asks for that one."
            if not hits else
            f"{name!r} could be {', '.join(r['dataset_id'] for r in hits)}. Say which one.")
    r = hits[0]
    if not r.get("accessible"):
        raise AccessError(f"You have no access to {r.get('name') or r['dataset_id']}: {r.get('reason')}. "
                          f"Datasets you can use: {names}.")
    return r["dataset_id"]


# --- variables -------------------------------------------------------------------------------
def resolve_field(ident, phrase: str, collection: str | None = None) -> Var:
    n = D.norm(phrase)
    pool = _vars(ident, collection)
    if not pool:
        raise AccessError(f"This dataset has no {collection} records." if collection else "No variables.")
    # 1) its own id or short name
    hits = [v for v in pool if n in (D.norm(v.cid), D.norm(v.short), D.norm(f"{v.collection} {v.short}"))]
    # 2) the dictionary's words for it
    if not hits:
        hits = [v for v in pool if n in {D.norm(w) for w in D.FIELDS.get(v.collection, {}).get(v.short, ())}]
    # 3) its display name
    if not hits:
        hits = [v for v in pool if n == D.norm(v.name)]
    # 4) close spelling
    if not hits:
        names = {D.norm(v.name): v for v in pool} | {D.norm(v.short): v for v in pool}
        close = difflib.get_close_matches(n, list(names), n=2, cutoff=0.86)
        hits = [names[c] for c in close][:1]
    hits = list({v.cid: v for v in hits}.values())
    if len(hits) > 1:
        # a patient-level variable wins over a record field of the same name ("date")
        subj = [v for v in hits if v.collection == "subject"]
        if len(subj) == 1:
            hits = subj
    if len(hits) != 1:
        opts = ", ".join(v.label() for v in (hits or pool)[:30])
        raise AccessError(
            (f"{phrase!r} could mean {opts}. Say which (or give the table)." if hits else
             f"No variable called {phrase!r}" + (f" on {collection} records" if collection else "")
             + f". Variables: {opts}."))
    return hits[0]


# --- values ----------------------------------------------------------------------------------
def _groups(ident, var: Var) -> tuple[list[dict], dict]:
    """A variable's recorded values, spelling variants merged. Listing them reads every
    record (seconds to a minute on large tables) and every question runs a fresh Chiron MCP
    process, so the list is also kept on disk until the dataset is next loaded (or a week).
    It holds the variable's values only, never patient data."""
    key = f"vals:{ident.dataset_id}:{var.cid}"
    if key in _CACHE:
        return _CACHE[key]
    path = _value_cache_file(ident.dataset_id, var.cid)
    stamp = _etl_stamp(ident.dataset_id)
    try:
        cached = json.loads(path.read_text())
        if cached.get("stamp") == stamp and time.time() - cached.get("made", 0) < 7 * 86400:
            _CACHE[key] = (cached["groups"], cached["counts"])
            return _CACHE[key]
    except (OSError, ValueError, KeyError):
        pass
    from chiron_mcp import server as S

    counts = S._value_counts(ident, [], var.concept)
    groups, _ = S._groups(counts, 10 ** 6)
    _CACHE[key] = (groups, counts)
    if _identifying(var):
        return _CACHE[key]  # names, ids, addresses: kept in memory for this question only
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"stamp": stamp, "made": time.time(), "groups": groups,
                                   "counts": {str(k): v for k, v in counts.items()}}))
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except OSError:
        pass
    return _CACHE[key]


SMALL_TABLES = 200_000  # records; listing values of a table this size takes a second or two


def cached_groups(ident, var: Var):
    """A variable's merged values if they are cached, or cheap to list (a small table);
    None otherwise, so a caller in a hurry never triggers a full scan."""
    key = f"vals:{ident.dataset_id}:{var.cid}"
    if key in _CACHE:
        return _CACHE[key][0]
    try:
        cached = json.loads(_value_cache_file(ident.dataset_id, var.cid).read_text())
        if cached.get("stamp") == _etl_stamp(ident.dataset_id):
            return cached["groups"]
    except (OSError, ValueError, KeyError):
        pass
    if _identifying(var):
        return None
    if _table_rows(ident, var.collection) <= SMALL_TABLES:
        return _groups(ident, var)[0]
    return None


def _table_rows(ident, collection: str) -> int:
    key = f"rows:{ident.dataset_id}:{collection}"
    if key not in _CACHE:
        try:
            import sqlalchemy as sa
            from django.conf import settings

            if "engine" not in _CACHE:
                _CACHE["engine"] = sa.create_engine(settings.CHIRON_SQL_ALCHEMY_CONNECTION_STRING, pool_size=1)
            schema = ident.dataset.unique_id.replace("-", "_")
            with _CACHE["engine"].connect() as conn:
                row = conn.execute(sa.text(
                    "select reltuples::bigint from pg_class c join pg_namespace n on n.oid = c.relnamespace "
                    "where n.nspname = :s and c.relname = :t"), {"s": schema, "t": collection}).fetchone()
            _CACHE[key] = int(row[0]) if row and row[0] and row[0] > 0 else 10 ** 9
        except Exception:  # noqa: BLE001
            _CACHE[key] = 10 ** 9
    return _CACHE[key]


def units_by_name(ident, collection: str, refresh: bool = False) -> dict | None:
    """{lab name: [units it is recorded in]} for a collection that has a name and a units
    variable (labs and vitals), from the warehouse: one distinct scan, no patient counts,
    kept on disk like value lists. None when the collection has no units variable."""
    name_var = _var(ident, collection, D.NAME_FIELD.get(collection) or "")
    unit_var = _var(ident, collection, "units")
    if not name_var or not unit_var:
        return None
    path = _value_cache_file(ident.dataset_id, f"{collection}__units_by_name")
    stamp = _etl_stamp(ident.dataset_id)
    if not refresh:
        try:
            cached = json.loads(path.read_text())
            if cached.get("stamp") == stamp:
                return cached["units"]
        except (OSError, ValueError, KeyError):
            pass
    import sqlalchemy as sa
    from django.conf import settings

    if "engine" not in _CACHE:
        _CACHE["engine"] = sa.create_engine(settings.CHIRON_SQL_ALCHEMY_CONNECTION_STRING, pool_size=1)
    schema = ident.dataset.unique_id.replace("-", "_")
    n_tab, u_tab = f"lkp_{name_var.cid}", f"lkp_{unit_var.cid}"
    sql = (f'select distinct n."{name_var.cid}", u."{unit_var.cid}" from "{schema}"."{n_tab}" n '
           f'join "{schema}"."{u_tab}" u on u._collection_id = n._collection_id')
    with _CACHE["engine"].connect() as conn:
        rows = conn.execute(sa.text(sql)).fetchall()
    groups, _ = _groups(ident, name_var)
    label_of = {v: g["label"] for g in groups for v in g["values"]}
    out: dict[str, list] = {}
    for name, unit in rows:
        if name is None or unit is None:
            continue
        units = out.setdefault(label_of.get(name, name), [])
        if str(unit) not in units:
            units.append(str(unit))
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"stamp": stamp, "units": out}))
        os.chmod(path, 0o600)
    except OSError:
        pass
    return out


def cached_units(ident, collection: str) -> dict | None:
    try:
        cached = json.loads(_value_cache_file(ident.dataset_id, f"{collection}__units_by_name").read_text())
        if cached.get("stamp") == _etl_stamp(ident.dataset_id):
            return cached["units"]
    except (OSError, ValueError, KeyError):
        pass
    return None


def warm(dataset_id: str) -> list[str]:
    """List every category variable's values once, so later questions find them cached."""
    ident = identity.resolve(dataset_id)
    done = []
    for v in catalogue(ident):
        if v.kind in ("category", "text") and not _identifying(v):
            try:
                n = len(_groups(ident, v)[0])
                done.append(f"{v.cid}: {n} values")
            except Exception as exc:  # noqa: BLE001
                done.append(f"{v.cid}: {type(exc).__name__}: {exc}"[:200])
    for coll in sorted({v.collection for v in catalogue(ident)}):
        try:
            u = units_by_name(ident, coll, refresh=True)
            if u is not None:
                done.append(f"{coll} units: {len(u)} names")
        except Exception as exc:  # noqa: BLE001
            done.append(f"{coll} units: {type(exc).__name__}: {exc}"[:200])
    return done


def _identifying(var: Var) -> bool:
    """A variable whose values identify people (names, ids, addresses): never written to
    disk and never listed in the summary."""
    return bool(getattr(var.concept, "has_phi", False)) or var.short in ("id", "first", "last", "ssn", "zip", "postcode",
                                                                          "drivers", "passport", "address")


def _value_cache_file(dataset_id: str, cid: str):
    from pathlib import Path

    base = Path(os.environ.get("CHIRON_MCP_CACHE_DIR") or Path.home() / ".cache" / "chiron-mcp")
    return base / "values" / re.sub(r"[^A-Za-z0-9_.-]", "_", dataset_id) / (re.sub(r"[^A-Za-z0-9_.-]", "_", cid) + ".json")


def _etl_stamp(dataset_id: str):
    """The dataset's latest load in Chiron's ETL log: a new load refreshes cached values."""
    try:
        from chiron import models

        last = models.EtlLog.objects.filter(dataset=dataset_id).order_by("-id").first()
        return last.id if last else 0
    except Exception:  # noqa: BLE001
        return None


def _contains(label: str, cand: str) -> bool:
    lw, cw = label.split(), cand.split()
    return bool(cw) and all(any(x == w or (len(w) >= 4 and x.startswith(w)) for x in lw) for w in cw)


def resolve_values(ident, var: Var, phrases) -> tuple[list[str], list[dict]]:
    """Every recorded spelling of each phrase's value, and what each matched."""
    if isinstance(phrases, str):
        phrases = [phrases]
    groups, counts = _groups(ident, var)
    values, matched = [], []
    for phrase in phrases:
        g = _match_group(var, groups, counts, str(phrase))
        values += [v for v in g["values"] if v not in values]
        matched.append({"you asked": str(phrase), "variable": var.label(), "matched": g["label"],
                        "spellings": g["values"]})
    return values, matched


def _match_group(var: Var, groups: list[dict], counts: dict, phrase: str) -> dict:
    codes = D.CODES.get(var.short)
    if codes:
        n = D.norm(phrase)
        for code, words in codes.items():
            if n in {D.norm(w) for w in words}:
                vals = [v for v in counts if D.norm(v) == code]
                if vals:
                    return {"label": max(vals, key=lambda v: counts[v]), "values": vals}
    for cand in D.value_words(phrase):
        exact = [g for g in groups if cand == D.norm(g["label"]) or any(cand == D.norm(v) for v in g["values"])]
        if len(exact) == 1:
            return exact[0]
        within = [g for g in groups if _contains(D.norm(g["label"]), cand)]
        if len(within) == 1:
            return within[0]
        if len(within) > 1:
            opts = "; ".join(f"{g['label']!r}" for g in sorted(within, key=lambda g: -g["approx"])[:12])
            raise AccessError(f"{phrase!r} matches several {var.label()} values: {opts}. "
                              "Say which one (or pass several in a list).")
    labels = [D.norm(g["label"]) for g in groups]
    close = difflib.get_close_matches(D.norm(phrase), labels, n=1, cutoff=0.86)
    if close:
        return groups[labels.index(close[0])]
    top = "; ".join(f"{g['label']!r}" for g in sorted(groups, key=lambda g: -g["approx"])[:25])
    raise AccessError(f"No {var.label()} value matches {phrase!r}. Its values include: {top}.")


# --- numbers and dates -----------------------------------------------------------------------
def _num(x) -> float:
    try:
        return float(str(x).replace(",", "").replace("$", "").replace("%", "").strip())
    except ValueError:
        raise AccessError(f"{x!r} is not a number.") from None


def _eps(v: float) -> float:
    # Chiron's limits are inclusive; strict ones move by far less than any recorded step
    return 1e-9 * max(1.0, abs(v))


def number_fields(op: str, value=None, between=None) -> tuple[dict, str]:
    if between is not None:
        a, b = (_num(x) for x in between)
        return {"cd_numeric_min": min(a, b), "cd_numeric_max": max(a, b)}, f"between {min(a, b):g} and {max(a, b):g} (inclusive)"
    v = _num(value)
    op = _OPS.get(str(op).strip().lower(), str(op).strip())
    table = {">=": ({"cd_numeric_min": v}, f">= {v:g}"), ">": ({"cd_numeric_min": v + _eps(v)}, f"> {v:g}"),
             "<=": ({"cd_numeric_max": v}, f"<= {v:g}"), "<": ({"cd_numeric_max": v - _eps(v)}, f"< {v:g}"),
             "=": ({"cd_numeric_min": v, "cd_numeric_max": v}, f"= {v:g}")}
    if op not in table:
        raise AccessError(f"Unknown comparison {op!r}: use >, >=, <, <=, = or between.")
    return table[op]


def _day(x, end: bool = False) -> date:
    """A date from '2015-03-01', '03/01/2015', 2015 or '2015' (a bare year is its first
    day, or its last with end=True)."""
    s = str(x).strip()
    if re.fullmatch(r"\d{4}", s):
        return date(int(s), 12, 31) if end else date(int(s), 1, 1)
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%Y-%m", "%B %d, %Y", "%b %d, %Y"):
        try:
            d = datetime.strptime(s, fmt).date()
            if fmt == "%Y-%m" and end:
                nxt = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
                return nxt - timedelta(days=1)
            return d
        except ValueError:
            pass
    raise AccessError(f"{x!r} is not a date (use YYYY-MM-DD or a year).")


def date_fields(var: Var, cond: dict) -> tuple[dict, str]:
    """Chiron date-range fields for has_value / year / before / after / between / op."""
    lo = hi = None
    what = ""
    if cond.get("has_value"):
        lo, what = date(1800, 1, 1), "has a value"
    elif cond.get("year") is not None:
        lo, hi, what = _day(cond["year"]), _day(cond["year"], end=True), f"in {cond['year']}"
    elif cond.get("year_between") or cond.get("between") or cond.get("date_between"):
        a, b = cond.get("year_between") or cond.get("between") or cond.get("date_between")
        lo, hi, what = _day(a), _day(b, end=True), f"from {a} to {b} (inclusive)"
    else:
        before, after = cond.get("before"), cond.get("after")
        op, value = cond.get("op"), cond.get("value")
        if op is not None:
            op = _OPS.get(str(op).strip().lower(), str(op).strip())
            if op in ("<", "<="):
                before = value if op == "<" else None
                hi = _day(value, end=True) if op == "<=" else hi
            elif op in (">", ">="):
                after = value if op == ">" else None
                lo = _day(value) if op == ">=" else lo
            elif op == "=":
                lo, hi = _day(value), _day(value, end=True)
        if before is not None:
            hi = _day(before) - timedelta(days=1)
        if after is not None:
            lo = _day(after, end=True) + timedelta(days=1)
        what = " and ".join(x for x in (f"from {lo}" if lo else "", f"to {hi}" if hi else "") if x)
    if lo is None and hi is None:
        raise AccessError(f"Say which dates for {var.name}: has_value, year, before, after, or between.")
    if var.kind == "year":
        f = {"query_type": "date_range"}
        if lo:
            f["cd_numeric_min"] = str(lo.year)
        if hi:
            f["cd_numeric_max"] = str(hi.year)
        return f, what + " (this date is stored as a year)"
    f = {"query_type": "date_range"}
    if lo:
        f["cd_numeric_min"] = lo.strftime("%m/%d/%Y")
    if hi:
        f["cd_numeric_max"] = hi.strftime("%m/%d/%Y")
    return f, what


# --- one condition -----------------------------------------------------------------------------
def _filter_for(ident, var: Var, cond: dict, matched: list) -> tuple[dict, str]:
    """Chiron filter fields for one variable from a condition's is/op/value/... keys."""
    if var.kind in ("category", "text"):
        want = cond.get("is", cond.get("is_any", cond.get("is_not")))
        if want is None:
            raise AccessError(f"Say which {var.name} with 'is' (one value or a list).")
        values, m = resolve_values(ident, var, want)
        matched += m
        field = "selected_categories" if var.kind == "category" else "chiron_text_field_selection"
        f = {field: values if field == "selected_categories" else "\n".join(values)}
        if var.kind == "text":
            f["ignore_warnings"] = True
        if cond.get("is_not") is not None:
            f["exclude_selected"] = True
        return f, f"{var.name} {'is not' if cond.get('is_not') is not None else 'is'} " + " or ".join(
            x["matched"] for x in m)
    if var.kind == "number":
        if cond.get("has_value"):
            return {"cd_numeric_min": -1e15}, f"{var.name} has a value"
        f, what = number_fields(cond.get("op", "="), cond.get("value"), cond.get("between"))
        return f, f"{var.name} {what}"
    if var.kind in ("date", "year"):
        f, what = date_fields(var, cond)
        return f, f"{var.name} {what}"
    raise AccessError(f"{var.label()} is a {var.kind or 'special'} variable that chiron_query cannot "
                      "filter yet; use chiron_edit_cohort with chiron_describe_concept's filter_input.")


def _record_value_keys(cond: dict) -> bool:
    return any(k in cond for k in ("op", "value", "between", "has_value"))


def parse_condition(ident, cond: dict) -> Clause:
    if not isinstance(cond, dict) or not cond:
        raise AccessError("Each condition is an object. " + SPEC_HELP)
    table_key = next((k for k in cond if D.norm(k) in TABLE_KEYS), None)
    if table_key is not None:
        coll = TABLE_KEYS[D.norm(table_key)]
        if not _vars(ident, coll):
            raise AccessError(f"This dataset has no {coll} records.")
        clause = Clause(coll, json.dumps(cond))
        name = cond[table_key]
        if name not in (None, "", "any"):
            clause.filters.append(_name_filter(ident, coll, name, clause.matched))
        # a lab's number is on the same result as its name
        if _record_value_keys(cond) and "field" not in cond:
            vf = D.VALUE_FIELD.get(coll)
            var = _var(ident, coll, vf) if vf else None
            if not var:
                raise AccessError(f"{coll} records have no value to compare; give a 'field'.")
            clause.filters.append((var, *_filter_for(ident, var, cond, clause.matched)))
        # the record's own date
        if any(k in cond for k in ("year", "year_between", "date_between", "before", "after")):
            df = D.DATE_FIELD.get(coll)
            var = _var(ident, coll, df) if df else None
            if not var:
                raise AccessError(f"{coll} records have no date here.")
            clause.filters.append((var, *_filter_for(ident, var, cond, clause.matched)))
        for extra in cond.get("with") or []:
            var = resolve_field(ident, extra.get("field", ""), coll)
            clause.filters.append((var, *_filter_for(ident, var, extra, clause.matched)))
        if "field" in cond:
            var = resolve_field(ident, cond["field"], coll)
            clause.filters.append((var, *_filter_for(ident, var, cond, clause.matched)))
    elif "field" in cond:
        var = resolve_field(ident, cond["field"])
        clause = Clause(var.collection, json.dumps(cond))
        clause.filters.append((var, *_filter_for(ident, var, cond, clause.matched)))
        for extra in cond.get("with") or []:
            v2 = resolve_field(ident, extra.get("field", ""), var.collection)
            clause.filters.append((v2, *_filter_for(ident, v2, extra, clause.matched)))
    else:
        raise AccessError(f"Not a condition: {json.dumps(cond)[:200]}. " + SPEC_HELP)
    if not clause.filters:
        raise AccessError(f"{json.dumps(cond)[:200]} has nothing to filter on. " + SPEC_HELP)

    # how many such records
    rules = [(k, cond[k]) for k in _COUNT_KEYS if k in cond]
    if cond.get("never"):
        rules.append(("exactly", 0))
    if isinstance(cond.get("count"), dict):
        c = cond["count"]
        rules.append((_OPS.get(str(c.get("op", ">=")).lower(), c.get("op")), c.get("value")))
    if len(rules) > 1:
        raise AccessError("Give one count rule per condition.")
    if rules:
        if clause.collection == "subject":
            raise AccessError("A count rule applies to records (visits, labs, prescriptions), not to the patient.")
        k, n = rules[0]
        n = int(_num(n))
        canon = {"at least": ("at least", n), ">=": ("at least", n), "at most": ("at most", n),
                 "<=": ("at most", n), "exactly": ("exactly", n), "=": ("exactly", n),
                 "more than": ("at least", n + 1), ">": ("at least", n + 1),
                 "fewer than": ("at most", n - 1), "<": ("at most", n - 1)}.get(_COUNT_KEYS.get(k, k))
        if canon is None or canon[1] < 0:
            raise AccessError(f"Count rule {k!r} {n} is not one Chiron can run.")
        clause.count_rule = canon
    return clause


def _name_filter(ident, coll: str, name, matched: list) -> tuple[Var, dict, str]:
    """A table's naming value ("asthma", "emergency", "self-pay"): the table's name variable
    first, then its other category variables, the first that has the value."""
    order = [D.NAME_FIELD.get(coll)] + [v.short for v in _vars(ident, coll)
                                        if v.kind in ("category", "text") and v.short != D.NAME_FIELD.get(coll)]
    errors = []
    for short in [s for s in order if s]:
        var = _var(ident, coll, short)
        if not var or var.kind not in ("category", "text"):
            continue
        try:
            f, what = _filter_for(ident, var, {"is": name}, matched)
            return var, f, what
        except AccessError as exc:
            if "matches several" in str(exc):
                raise
            errors.append(str(exc))
    raise AccessError(errors[0] if errors else f"No {coll} value matches {name!r}.")


# --- building the cohort with Chiron's own transformations -------------------------------------
def _apply(cu, cd: list, t: dict) -> tuple[list, str | None]:
    from chiron.api.utils import cohort_def as cd_utils

    from chiron_mcp import server as S

    t, _ = S.check_transformation(t)
    r = cd_utils.transformation_function_lookup[t["type"]](cu, copy.deepcopy(cd), t)
    if not r.get("transformation_successful"):
        raise AccessError(f"Chiron refused {t.get('type')} on {t.get('concept_id', '')}: "
                          f"{r.get('transformation_errors')}")
    return copy.deepcopy(r["cohort_def"]), r.get("entry_id")


def _sets(cd: list, coll: str) -> list[dict]:
    return [e for e in cd if e.get("entry_type") == "criteria_set" and e.get("collection_id") == coll]


def _ids(cd: list) -> set:
    out = set()
    for e in cd:
        out.add(e.get("entry_id"))
        for x in e.get("list") or []:
            out.add(x.get("entry_id"))
            for y in x.get("list") or []:
                out.add(y.get("entry_id"))
    return out


def build(ident, clauses: list[Clause], base: list | None = None) -> list:
    """The cohort_def for all clauses ANDed (on top of `base`), each record clause in a
    group of its own."""
    cu = identity.checked_chironuser(ident)
    cd = copy.deepcopy(base or [])
    for clause in clauses:
        coll = clause.collection
        own_group = coll != "subject" and bool(_sets(cd, coll))
        target = None
        if own_group:
            before = _ids(cd)
            cd, _ = _apply(cu, cd, {"type": "add_criteria_set", "collection_id": coll})
            target = next(s["entry_id"] for s in _sets(cd, coll) if s["entry_id"] not in before)
        for var, fields, _ in clause.filters:
            before = _ids(cd)
            cd, new_id = _apply(cu, cd, {"type": "add_entry", "concept_id": var.cid, **fields})
            new_id = new_id or next(iter(_ids(cd) - before), None)
            if target is None and coll != "subject":
                target = next((s["entry_id"] for s in _sets(cd, coll)
                               if any(x.get("entry_id") == new_id for x in s.get("list") or [])), None)
            elif own_group:
                group = next(s for s in _sets(cd, coll) if s["entry_id"] == target)
                if not any(x.get("entry_id") == new_id for x in group.get("list") or []):
                    cd, _ = _apply(cu, cd, {"type": "sort_cd_entries", "entry_id": target,
                                            "child_ids": [x["entry_id"] for x in group.get("list") or []] + [new_id]})
                    group = next(s for s in _sets(cd, coll) if s["entry_id"] == target)
                    if not any(x.get("entry_id") == new_id for x in group.get("list") or []):
                        raise AccessError("Could not put a filter in its own group; use chiron_edit_cohort.")
        if clause.count_rule:
            op, n = clause.count_rule
            cd, _ = _apply(cu, cd, {"type": "add_criteria_set_count_rule", "entry_id": target,
                                    "rule_operator": op, "rule_count": n})
    return cd


def describe(ident, cd: list) -> str:
    """Chiron's own plain-words description of a cohort, as its query builder shows it."""
    if not cd:
        return "every patient in the dataset (no filters)"
    from chiron.query_definition import cohort_def_functions as cdfuncs

    cu = identity.checked_chironuser(ident)
    info = cdfuncs.clean_cohort_def(copy.deepcopy(cd), cu, include_metadata=True)
    raw = cdfuncs.describe_cohort_def(info["extended_cohort_def"])
    return html.unescape(re.sub(r"<[^>]+>", "", str(raw).replace("<br>", "\n"))).strip()


# --- conversation groups (plan P5 builds on these) -----------------------------------------------
def _groups_path() -> str | None:
    return os.environ.get("CHIRON_MCP_GROUPS_FILE") or None


def _load_groups() -> dict:
    path = _groups_path()
    if path and os.path.exists(path):
        try:
            with open(path) as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return {}
    return _CACHE.setdefault("groups", {})


def _save_group(entry: dict) -> str:
    groups = _load_groups()
    name = f"g{len(groups) + 1}"
    groups[name] = entry
    path = _groups_path()
    if path:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(groups, fh)
        os.replace(tmp, path)
        os.chmod(path, 0o600)
    return name


def get_group(name: str) -> dict:
    g = _load_groups().get(str(name).strip())
    if not g:
        known = ", ".join(f"{k} ({v.get('label', '')})" for k, v in _load_groups().items()) or "none yet"
        raise AccessError(f"No group called {name!r}. Groups in this conversation: {known}.")
    return g


# --- the tool ------------------------------------------------------------------------------------
def run(dataset: str, where: list | None = None, match: str = "all", start_from: str | None = None,
        show: dict | None = None, label: str | None = None) -> dict:
    from chiron_mcp import server as S

    dataset_id = resolve_dataset(dataset)
    ident = identity.resolve(dataset_id)
    identity.require_workspace(ident)
    identity.require_subject_level(ident)
    base, base_text = [], None
    if start_from and _is_report_ref(start_from):
        rep = find_report(S, dataset_id, start_from)
        base = rep.get("cohort_def") or []
        base_text = f"report {rep['name']!r} (id {rep['report_id']})"
    elif start_from:
        g = get_group(start_from)
        if g.get("dataset_id") != dataset_id:
            raise AccessError(f"Group {start_from} is on {g.get('dataset_id')}, not {dataset_id}.")
        base, base_text = g["cohort_def"], f"{start_from}: {g.get('label') or g.get('what')}"
    if where is not None and not isinstance(where, list):
        where = [where]
    clauses = [parse_condition(ident, c) for c in (where or [])]
    matched = [m for c in clauses for m in c.matched]
    notes: list[str] = []
    out: dict[str, Any] = {"dataset_id": dataset_id}
    if base_text:
        out["started_from"] = base_text

    match = str(match or "all").strip().lower()
    if match not in ("all", "any"):
        raise AccessError("match is 'all' (every condition) or 'any' (at least one).")
    if match == "any" and len(clauses) > 1:
        merged = _merge_any(clauses)
        if merged is not None:
            clauses = [merged]
        else:
            return _either(ident, S, clauses, base, out, matched, show)

    cd = build(ident, clauses, base)
    S._validated_cohort(ident, cd)  # refuses anything Chiron reports as an error
    out["what_was_counted"] = describe(ident, cd)
    out["count"] = S._count(ident, cd)
    out["matched"] = matched
    out = _show(ident, S, cd, show or {}, out, notes)
    out["group"] = _save_group({"dataset_id": dataset_id, "cohort_def": cd, "count": out["count"],
                                "what": out["what_was_counted"], "label": label or _label(clauses, base_text)})
    out["cohort_def"] = cd
    if notes:
        out["notes"] = notes
    out["how_to_answer"] = (
        "Lead with `count` (distinct patients). Say what was counted from what_was_counted, in plain "
        "words, and which spellings were included (matched). For a follow-up about these patients, "
        f"pass start_from='{out['group']}'.")
    return out


def _label(clauses, base_text) -> str:
    parts = [f.split(" (")[0] for c in clauses for _, _, f in c.filters]
    return "; ".join(parts)[:160] or (base_text or "everyone")


def _merge_any(clauses: list[Clause]) -> Clause | None:
    """'asthma or COPD': one filter on one variable takes several values at once."""
    first = clauses[0]
    if all(len(c.filters) == 1 and not c.count_rule and c.collection == first.collection
           and c.filters[0][0].cid == first.filters[0][0].cid
           and "selected_categories" in c.filters[0][1] and not c.filters[0][1].get("exclude_selected")
           for c in clauses):
        values = list(dict.fromkeys(v for c in clauses for v in c.filters[0][1]["selected_categories"]))
        merged = Clause(first.collection, " or ".join(c.text for c in clauses))
        merged.filters = [(first.filters[0][0], {"selected_categories": values},
                           " or ".join(c.filters[0][2] for c in clauses))]
        merged.matched = [m for c in clauses for m in c.matched]
        return merged
    return None


def _either(ident, S, clauses, base, out, matched, show) -> dict:
    """At least one of conditions on different variables: Chiron has no OR between groups,
    so the count is exact inclusion-exclusion over Chiron's own counts of every overlap."""
    if len(clauses) > 4:
        raise AccessError("'any' across different variables works for up to 4 conditions.")
    if show and set(show) - {"count"}:
        raise AccessError("A breakdown or list of 'either' patients across different variables "
                          "is not one Chiron cohort; count each condition instead.")
    total, parts = 0, []
    for k in range(1, len(clauses) + 1):
        for combo in itertools.combinations(range(len(clauses)), k):
            n = S._count(ident, build(ident, [clauses[i] for i in combo], base))
            total += n if k % 2 else -n
            parts.append({"conditions": [i + 1 for i in combo], "patients": n})
    out.update(count=total, matched=matched,
               what_was_counted="patients meeting at least one of: " + "; ".join(
                   f"({i + 1}) " + describe(ident, build(ident, [c], [])) for i, c in enumerate(clauses)),
               overlaps=parts,
               notes=["Exact, from Chiron's counts of each condition and every overlap (inclusion-"
                      "exclusion): Chiron cannot hold 'either' across different variables as one "
                      "cohort, so there is no single query to hand over."])
    out["how_to_answer"] = "Lead with `count`; say it combines the conditions with OR."
    return out


def _show(ident, S, cd, show: dict, out: dict, notes: list) -> dict:
    ds = ident.dataset_id
    if not show or show.get("count") and len(show) == 1:
        return out
    if show.get("breakdown"):
        by = show["breakdown"] if isinstance(show["breakdown"], list) else [show["breakdown"]]
        ids = [_by_var(ident, b).cid for b in by]
        out["breakdown"] = S.chiron_breakdown(ds, cd, ids, int(show.get("top") or 0))
    elif show.get("top"):
        of = show.get("of") or "condition"
        var = _by_var(ident, of)
        out["top"] = S.chiron_breakdown(ds, cd, [var.cid], int(show["top"]))
    elif show.get("list") is not None:
        cols = show["list"] if isinstance(show["list"], list) else [show["list"]]
        columns = []
        pid = _var(ident, "subject", "id")
        if pid:
            columns.append({"concept_id": pid.cid})
        for c in cols:
            v = resolve_field(ident, c)
            if v.cid not in [x["concept_id"] for x in columns]:
                columns.append({"concept_id": v.cid})
        out["rows"] = S.chiron_run_table(ds, cd, columns, 1, int(show.get("limit") or 10))
    elif show.get("values") is not None:
        # a variable's recorded values (spellings merged) and roughly how many patients
        # have each, in the whole dataset: "which labs are recorded", "what units"
        var = _column_var(ident, show["values"])
        if var.kind not in ("category", "text"):
            raise AccessError(f"{var.label()} is a {var.kind} variable; ask for its range instead.")
        groups, _ = _groups(ident, var)
        top = sorted(groups, key=lambda g: -g["approx"])[: int(show.get("limit") or 50)]
        units = cached_units(ident, var.collection) if var.short == D.NAME_FIELD.get(var.collection) else None
        out["values"] = {"variable": var.label(), "count_of_values": len(groups),
                         "values": [{"value": g["label"], "patients_about": g["approx"],
                                     "spellings": len(g["values"]),
                                     **({"units": units.get(g["label"], [])} if units else {})} for g in top]}
        notes.append("patients_about adds the spellings' counts, so a patient recorded under two "
                     "spellings counts twice; for an exact count of one value, ask chiron_query.")
    elif show.get("stats") is not None or show.get("range") is not None:
        out["range"] = _stats(ident, S, cd, show)
    elif show.get("results") is not None:
        spec = show["results"] if isinstance(show["results"], dict) else {"columns": show["results"]}
        cd2, cols, sort = plain_columns(ident, cd, spec.get("columns") or [], spec.get("sort"))
        r = S.chiron_update_results(ds, cd2, cols, sort=sort or None)
        if r.get("error"):
            raise AccessError(f"Results not changed: {r['error']} To answer in the chat instead (no change "
                              "to Results): show={'list': [fields], 'limit': N} lists patients, "
                              "show={'range': {'lab': 'HbA1c'}} gives the lowest and highest value.")
        out["results"] = _written(S, ds, r)
        notes.append("The Results tab now holds these patients and columns; check `results` for what "
                     "Chiron shows, and report its row count.")
    elif show.get("report") is not None and isinstance(show["report"], dict) and show["report"].get("update"):
        spec = show["report"]
        rep = find_report(S, ds, spec.get("name") or "latest", mine=True)
        kw: dict = {"cohort_def": cd}
        if spec.get("columns"):
            cd2, cols, sort = plain_columns(ident, cd, spec["columns"], spec.get("sort"))
            kw.update(cohort_def=cd2, columns=cols, sort=sort or None)
        if spec.get("new_name"):
            kw["name"] = spec["new_name"]
        if spec.get("public") is not None:
            kw["public"] = bool(spec["public"])
        r = S.chiron_update_report(ds, rep["report_id"], **kw)
        if r.get("error"):
            raise AccessError(f"Report not changed: {r['error']}")
        after = find_report(S, ds, str(rep["report_id"]))
        out["report"] = {"report_id": rep["report_id"], "name": after.get("name"),
                         "public": after.get("public"), "patients_now": out["count"],
                         "filters_now": describe(ident, after.get("cohort_def") or [])}
    elif show.get("report") is not None:
        spec = show["report"] if isinstance(show["report"], dict) else {"name": show["report"]}
        if not spec.get("name"):
            raise AccessError("A report needs a name: {'report': {'name': ..., 'columns': [...]}}.")
        cd2, cols, sort = plain_columns(ident, cd, spec.get("columns") or [], spec.get("sort"))
        r = S.chiron_open_in_ui(ds, cd2, cols or None, spec["name"], "report",
                                spec.get("description"), sort or None)
        if r.get("error"):
            raise AccessError(f"Report not saved: {r['error']}")
        if spec.get("public") and r.get("report_id"):
            u = S.chiron_update_report(ds, r["report_id"], public=True)
            if u.get("error"):
                notes.append(f"Saved, but not made public: {u['error']}")
        out["report"] = _written(S, ds, r)
    elif show.get("query_builder") or show.get("load_query"):
        r = S.chiron_open_in_ui(ds, cd, None, show.get("name") or "Query from Ask", "workspace")
        if r.get("error"):
            raise AccessError(f"Query builder not loaded: {r['error']}")
        out["query_builder"] = _written(S, ds, r)
    else:
        raise AccessError("show is {'count': true}, {'breakdown': [...]}, {'top': N, 'of': 'condition'}, "
                          "{'list': [fields], 'limit': N}, {'range': {'lab': 'HbA1c'}}, {'values': 'lab'}, "
                          "{'results': {'columns': [...], 'sort': [...]}}, "
                          "{'report': {'name': ..., 'columns': [...], 'public': false}} or {'query_builder': true}.")
    return out


def _is_report_ref(ref) -> bool:
    return str(ref).strip().lower().startswith(("report:", "report "))


def find_report(S, ds: str, ref, mine: bool = False) -> dict:
    """A saved report, with its definition, by "report:<name>", "report:<id>", a plain
    name or id, or "latest" (the most recent you created)."""
    text = re.sub(r"^report[: ]\s*", "", str(ref).strip(), flags=re.I).strip()
    listing = S.chiron_saved_reports(ds, scope="mine" if mine else "all")
    if listing.get("error"):
        raise AccessError(listing["error"])
    reports = listing.get("reports") or []
    if text.lower() in ("latest", "most recent", "newest", "last"):
        own = [r for r in reports if r.get("mine")]
        if not own:
            raise AccessError("You have no saved reports.")
        hit = own[0]
    elif text.isdigit():
        hit = {"report_id": int(text)}
    else:
        hits = [r for r in reports if D.norm(r.get("name")) == D.norm(text)]
        if len(hits) != 1:
            names = ", ".join(f"{r['name']!r} ({r['report_id']})" for r in reports[:20]) or "none"
            raise AccessError((f"Several reports are called {text!r}" if hits else f"No report called {text!r}")
                              + f". Reports: {names}.")
        hit = hits[0]
    full = S.chiron_saved_reports(ds, report_id=hit["report_id"])
    if full.get("error"):
        raise AccessError(full["error"])
    return full


def _written(S, ds: str, r: dict) -> dict:
    """What Chiron holds after a write, read back from Chiron (plan P4): never what was meant."""
    keep = {k: r[k] for k in ("url", "report_id", "name", "mode", "public", "columns", "sort", "rows",
                              "record_count", "patients", "subject_count") if k in r}
    return keep or r


# --- columns in plain terms (plan P4) --------------------------------------------------------------
_SUMMARIES = {"max": "max", "highest": "max", "min": "min", "lowest": "min", "average": "average",
              "mean": "average", "median": "median", "sum": "sum", "total": "sum", "latest": "latest",
              "earliest": "earliest", "first": "earliest", "last": "latest"}


def plain_columns(ident, cd: list, columns: list, sort=None) -> tuple[list, list, list]:
    """Plain columns -> Chiron columns, plus the cohort they need.

      "birthdate", "gender", "city"          one value per patient (rows stay one per patient)
      {"has": {"medication": "metformin"}}   yes/no: has a matching record
      {"max": {"lab": "HbA1c"}}              highest value of that lab (also min, average,
                                             median, sum, latest, earliest)
      {"count_distinct": "medication"}       how many different medications
      {"count": {"visit": "emergency"}}      how many matching records
      {"list": "condition"}                  the different values

    A lab-limited summary needs a group in the cohort that holds that lab's results; it is
    added with the count rule "at least 0", which Chiron reads as no condition on patients,
    so the patients stay exactly the cohort's. The patient id comes first when the dataset
    has one, so every row is one patient.
    """
    cd2 = copy.deepcopy(cd)
    cols: list[dict] = []
    labels: list[tuple[str, int]] = []
    pid = _var(ident, "subject", "id")
    if pid:
        cols.append({"concept_id": pid.cid})
    cu = identity.checked_chironuser(ident)
    for c in columns or []:
        if isinstance(c, str):
            var = _column_var(ident, c)
            if var.cid not in [x["concept_id"] for x in cols]:
                cols.append({"concept_id": var.cid})
            labels.append((D.norm(c), len(cols) - 1))
            continue
        if not isinstance(c, dict) or len(c) != 1:
            raise AccessError(f"Not a column: {c!r}. " + plain_columns.__doc__.split("\n\n")[0])
        kind, target = next(iter(c.items()))
        k = D.norm(kind).replace(" ", "_")
        if k == "has":
            clause = parse_condition(ident, target)
            var, fields, _ = clause.filters[0]
            values = fields.get("selected_categories") or fields.get("chiron_text_field_selection", "").split("\n")
            cols.append({"concept_id": var.cid, "aggregation": "has_value",
                         "settings": {"values": values, "return_value": "boolean"}})
        elif k in _SUMMARIES or k in ("count", "count_all"):
            clause = parse_condition(ident, target if isinstance(target, dict) else {"lab": target})
            if k in _SUMMARIES:
                vf = D.VALUE_FIELD.get(clause.collection)
                var = _var(ident, clause.collection, vf) if vf else None
                if not var:
                    raise AccessError(f"{clause.collection} records have no value to summarise.")
                agg = _SUMMARIES[k]
            else:
                var, agg = clause.filters[0][0], "count_all"
            cd2, group = _column_group(ident, cu, cd2, clause)
            cols.append({"concept_id": var.cid, "aggregation": agg, "aggregation_criteria_set": group})
        elif k in ("count_distinct", "list", "list_distinct"):
            var = _by_var(ident, target)
            cols.append({"concept_id": var.cid,
                         "aggregation": "count_distinct" if k == "count_distinct" else "list_distinct"})
        else:
            raise AccessError(f"Unknown column kind {kind!r}: use has, max, min, average, median, sum, "
                              "latest, earliest, count, count_distinct or list.")
        labels.append((D.norm(json.dumps(c)), len(cols) - 1))
    out_sort = []
    for srt in ([sort] if isinstance(sort, dict) else sort or []):
        col = srt.get("column")
        if isinstance(col, dict):
            want = D.norm(json.dumps(col))
        else:
            want = D.norm(col)
        idx = next((i for lab, i in labels if lab == want), None)
        if idx is None and isinstance(col, str):
            idx = next((i for lab, i in labels if want in lab), None)
        if idx is None:
            raise AccessError(f"Sort column {col!r} is not one of the columns asked for.")
        out_sort.append({"column": cols[idx]["concept_id"], "direction": srt.get("direction", "asc")})
    return cd2, cols, out_sort


def _column_var(ident, phrase: str) -> Var:
    coll = TABLE_KEYS.get(D.norm(phrase))
    if coll and D.NAME_FIELD.get(coll):
        return _var(ident, coll, D.NAME_FIELD[coll])
    return resolve_field(ident, phrase)


def _column_group(ident, cu, cd: list, clause: Clause) -> tuple[list, str]:
    """A group holding one kind of record for a column to summarise, which does not
    change the patients (count rule "at least 0")."""
    before = {s["entry_id"] for s in _sets(cd, clause.collection)}
    cd = build(ident, [clause], cd)
    group = next((s["entry_id"] for s in _sets(cd, clause.collection) if s["entry_id"] not in before), None)
    if group is None:  # the first group of that table: build put the filters there
        group = _sets(cd, clause.collection)[0]["entry_id"]
    cd, _ = _apply(cu, cd, {"type": "add_criteria_set_count_rule", "entry_id": group,
                            "rule_operator": "at least", "rule_count": 0})
    return cd, group


def _by_var(ident, phrase) -> Var:
    """A variable to group by: a table word means its name variable ('condition')."""
    coll = TABLE_KEYS.get(D.norm(phrase))
    if coll and D.NAME_FIELD.get(coll):
        v = _var(ident, coll, D.NAME_FIELD[coll])
        if v:
            return v
    return resolve_field(ident, phrase)


def _stats(ident, S, cd, show: dict) -> dict:
    """Smallest and largest recorded value: of a lab or vital (only its own results), or of a
    patient-level number, within the cohort."""
    of = show.get("range") if show.get("range") is not None else show.get("of")
    cu = identity.checked_chironuser(ident)
    if isinstance(of, dict):
        clause = parse_condition(ident, of)
        vf = D.VALUE_FIELD.get(clause.collection)
        var = _var(ident, clause.collection, vf) if vf else None
        if not var:
            raise AccessError("A range needs a lab or vital (or a numeric field).")
        scope = build(ident, [clause], cd)
    else:
        var = resolve_field(ident, of)
        scope = cd
    proc = var.concept.get_cohort_def_processor(cu)
    raw = proc.get_statistics(copy.deepcopy(scope)) or {}
    st = raw.get("stats") or {}
    return {"variable": var.label(), "within": describe(ident, scope),
            "min": st.get("min"), "max": st.get("max"), "average": st.get("avg"),
            "results": st.get("count_non_null"), "patients": st.get("unique_patients"),
            "results_without_a_value": raw.get("count_missing_values")}


if __name__ == "__main__":
    import sys

    from chiron_mcp.bootstrap import ensure_django

    ensure_django()
    if len(sys.argv) == 3 and sys.argv[1] == "--warm":
        for line in warm(sys.argv[2]):
            print(line)
    else:
        print("python -m chiron_mcp.query --warm <dataset_id>")

"""A small web server that puts a chat box in front of the Chiron MCP tools.

Each question is answered by running Claude Code headless (`claude -p`) with this
project's MCP server loaded, so it uses the operator's existing Claude subscription
rather than an API key. Progress and the final answer stream back over SSE.

    .venv/bin/python -m chiron_mcp.webapp

Then open http://localhost:8900, or embed that URL in the Chiron UI (see
docs/chiron-ui-integration.md).

Standard library only, so it adds no dependencies to the MCP server itself.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from chiron_mcp import trace as tracing
from chiron_mcp.config import CONFIG

HERE = Path(__file__).resolve().parent
WEBUI = HERE / "webui"
PORT = int(os.environ.get("CHIRON_MCP_WEB_PORT", "8900"))

# Every answer keeps a step-by-step trace the page shows on request, for working out
# why an answer is wrong (see trace.py). CHIRON_MCP_TRACE=0 switches it off.
TRACE = os.environ.get("CHIRON_MCP_TRACE", "1") != "0"
# Ask Claude Code for summaries of the model's reasoning, so the trace can show why it
# chose each step. The Ask server turns this on in main(); code that imports ask_stream
# (the benchmark) keeps Claude Code's default unless it sets the variable. Set it to ""
# to leave the flag off.
THINKING_DISPLAY = os.environ.get("CHIRON_MCP_THINKING_DISPLAY")

# Only the read-only analysis tools are offered by default. The hand-off tool is
# included so "open this in Chiron" works, but it is itself gated on
# CHIRON_MCP_ALLOW_SAVE inside the server.
# The short list (the default): chiron_query does the cohort mechanics, so a small model
# never writes Chiron's internal definitions. CHIRON_MCP_ASK_TOOLS=full also offers the
# low-level tools (and the instructions for them).
TOOLS_SHORT = [
    "chiron_query",
    "chiron_datasets",
    "chiron_results",
    "chiron_update_results",
    "chiron_saved_reports",
    "chiron_run_saved_report",
    "chiron_update_report",
    "chiron_delete_report",
]
ASK_TOOLS = (os.environ.get("CHIRON_MCP_ASK_TOOLS") or "short").strip().lower()


# The models the page may choose from, when the deployment offers a choice:
#   CHIRON_MCP_ASK_MODELS="us.anthropic.claude-opus-5-5=Opus 5.5,us.anthropic.claude-haiku-5-5=Haiku 5.5"
# Each entry is a model id Claude Code accepts (its --model flag), with a label after "="
# for the page. Haiku is the default when it is listed, else Opus, else the first. Unset,
# Claude Code's own model answers, as before, and the page shows no switcher.
def _parse_models(spec: str | None) -> list[dict]:
    out: list[dict] = []
    for part in (spec or "").split(","):
        mid, _, label = part.strip().partition("=")
        mid = mid.strip()
        if mid and all(m["id"] != mid for m in out):
            out.append({"id": mid, "label": label.strip() or mid})
    return out


ASK_MODELS = _parse_models(os.environ.get("CHIRON_MCP_ASK_MODELS"))


# Models Bedrock refused since this server started (the deployment's role may not call
# them, or the region lacks them): no longer offered, and a question that asked for one
# is answered by the next (see fallback_model).
DENIED: set[str] = set()


def offered_models() -> list[dict]:
    return [m for m in ASK_MODELS if m["id"] not in DENIED]


def _first(models: list[dict], family: str) -> str | None:
    return next((m["id"] for m in models if family in m["id"].lower()), None)


def default_model() -> str | None:
    """The model a question uses when the page names none: Haiku when it is offered,
    else Opus, else the first offered; None when there is no list."""
    offered = offered_models()
    if not offered:
        return None
    return _first(offered, "haiku") or _first(offered, "opus") or offered[0]["id"]


def fallback_model(model: str) -> str | None:
    """The model that answers instead when `model` is refused: Opus when offered, else
    the first other offered model; None when there is none."""
    others = [m for m in offered_models() if m["id"] != model]
    return (_first(others, "opus") or others[0]["id"]) if others else None


def pick_model(requested: str | None) -> str | None:
    """The model to answer with: the page's choice when it is offered, else the default.
    A name not on the list is ignored, so the page cannot run any model."""
    requested = (requested or "").strip()
    if requested and any(m["id"] == requested for m in offered_models()):
        return requested
    return default_model()


# Claude Code's model slots. With a model chosen, every slot is pinned to it, so a
# question calls no other model (a deployment's Bedrock policy may allow only the listed
# ones).
_MODEL_SLOTS = ("ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL", "ANTHROPIC_DEFAULT_SONNET_MODEL",
                "ANTHROPIC_DEFAULT_HAIKU_MODEL", "ANTHROPIC_SMALL_FAST_MODEL")


def model_env(model: str | None) -> dict | None:
    """The environment for Claude Code with `model` in every slot; None keeps the server's."""
    if not model:
        return None
    env = dict(os.environ)
    for slot in _MODEL_SLOTS:
        env[slot] = model
    return env
TOOLS_FULL = [
    "chiron_query",
    "chiron_datasets",
    "chiron_find_concepts",
    "chiron_describe_concept",
    "chiron_concept_values",
    "chiron_edit_cohort",
    "chiron_event_rule_options",
    "chiron_count_cohort",
    "chiron_run_table",
    "chiron_crosstab",
    "chiron_breakdown",
    "chiron_saved_reports",
    "chiron_run_saved_report",
    "chiron_open_in_ui",
    "chiron_update_report",
    "chiron_delete_report",
    "chiron_results",
    "chiron_update_results",
    "chiron_column_options",
]
TOOLS = TOOLS_FULL if ASK_TOOLS == "full" else TOOLS_SHORT

SYSTEM_PROMPT_FULL = """You are a research data analyst answering questions about one Chiron dataset.

Use the chiron tools. Never invent a number: every figure must come from a tool result.

Start with chiron_query for counts, breakdowns, top lists, patient lists and value
ranges: describe the question in plain terms, as in its examples, and it finds every
spelling of each value, builds the query, checks it and counts. Lead your answer with its
count and say what was counted (its what_was_counted). For a follow-up about the same
patients ("how many of them..."), pass start_from with the group name from the earlier
answer. If it refuses because a dataset does not exist, say so and do not answer from
another dataset. Use the lower-level tools below only when chiron_query says it cannot
express the question, and for the Results tab and saved reports.

The dataset's variables, their exact concept ids and their filter types are listed after
the question. Use them directly: do not call chiron_find_concepts or
chiron_describe_concept to discover variables. Call chiron_describe_concept only if a
filter you built is rejected and you need its exact input fields.

Condition, medication, procedure and encounter names ("Asthma", "Albuterol") are VALUES
of a description variable, not variables. Find them with chiron_concept_values on that
variable. Values are often recorded with case and spelling variants ("Asthma", "ASTHMA",
"asthma", "Asthm"), and coded values too ("F" and "f"). Include every variant of the
value you mean in selected_categories, and say in one clause that you did.

Building a cohort: start from [] and add one filter per chiron_edit_cohort call, always
passing the cohort_def the previous call returned. Filters on different collections
combine with AND and work fine together. Then call chiron_count_cohort on the final
cohort_def. Never write a cohort_def by hand. Any patient count you state for a cohort
must come from chiron_count_cohort on exactly that cohort, even when you could read it
off value counts or a breakdown: that count is what gives the user a working Query
button for those patients.

Patients WITHOUT something ("no hypertension", "never had asthma"): add the filter for
the thing, then call chiron_edit_cohort with type "add_criteria_set_count_rule",
entry_id = that criteria set's entry_id (the top-level entry, not the filter inside it),
rule_operator "exactly", rule_count 0. Never use exclude_selected for this: on a
multi-value field it means "has at least one record that is something else", which
counts almost everyone and is wrong.

Comparing several cohorts in one answer: build and count each one separately from [].

Breakdowns ("by gender", "split by race", "per ethnicity"): call chiron_breakdown with
the cohort_def and one or two Category variables. It returns exact distinct-patient
counts with spelling variants already merged. Show them as a markdown table; add a chart
when there are several groups. Take every total from the tool's row_totals and
col_totals; never add cells up yourself, because a patient missing one variable is in
a total but in no cell.

Rankings ("top 5 conditions", "most common medications", "which encounter types are
most frequent"): one chiron_breakdown call on that variable with top=N, passing the
cohort_def if the question is about a group of patients. Do not count each item
separately. Label coded values plainly (F as Female, M as Male). If
no_value shows patients with no recorded value, add one short line saying how many, so
the table visibly adds up. Do not use chiron_crosstab unless chiron_breakdown fails.

Reports: chiron_saved_reports(scope="mine") lists the ones this user made. To rename one,
reword it, change its filters or columns, or make it public or private, use
chiron_update_report (to change filters, fetch its cohort_def first and edit it with
chiron_edit_cohort). Only call chiron_delete_report when the user explicitly asks to
delete a specific report, passing its exact current name as confirm_name, and say
plainly afterwards that it is gone. Never delete to "tidy up".

Results tab: Chiron's Results tab shows the user's open query (the filters in their query
builder) as a table. chiron_results shows what is there now; chiron_update_results
changes it. Use them when the user asks to see something in Results, add or remove
columns, change how a column is shown, reorder or sort. To put a cohort from this
conversation into Results, pass its cohort_def; that replaces the filters open in their
query builder, so only do it when they ask for it in Results or their query. Rows are
grouped by the stacked columns: with only gender stacked there is one row per gender and
every other column is combined within it; to list patients one per row, stack
patient-level columns such as birthdate and city. A column's aggregation is "stack" or a
method from chiron_column_options: list_distinct, count_all, count_distinct,
most_frequent, has_value (with the values to look for, returning true/false or a count),
and for numbers sum, average, median, min, max, for dates min_date, max_date. Name
columns by concept_id, or by the label chiron_results gives ("medication description").
Reports take exactly the same column changes through chiron_update_report. To save
what is in Results as a report, pass chiron_open_in_ui the cohort_def, columns (with
their aggregation and settings) and sort that chiron_results gives. After a
change, say in one sentence what the table now shows and how many rows and patients it
has; the page adds a Results button.

Follow-up questions: this may be a continuing conversation. The cohorts you built and
counted earlier are in your context. When the user says "them", "those patients", "that
cohort", "now only women", start from the cohort_def behind your previous answer and
extend it with chiron_edit_cohort, then call chiron_count_cohort on the result. For
"show their medications" or "what else do they have", pass that cohort_def to the tool
so the figures are about those patients, not the whole dataset.

Answering. The reader wants the figure, not an essay.
- One short sentence with the answer, the figure in digits (20, not "twenty"). Add a
  second only if something would mislead without it, such as merged spelling variants.
- A markdown table for more than two rows of figures.
- For a chart, a fenced block tagged `chart` containing JSON, with a title that says
  exactly what the bars are:
  {"type":"bar","title":"Patients by condition","label":"Patients",
   "data":[{"x":"Asthma","y":841},{"x":"COPD","y":199}]}
  For a two-variable breakdown use one series per row, so every bar is labelled:
  {"type":"bar","title":"Asthma patients by race and gender","x":["White","Black"],
   "series":[{"label":"Female","y":[288,73]},{"label":"Male","y":[244,73]}]}
  Never chart one row of a table as if it were the whole. Types: bar, line, doughnut.
  Use one to compare categories, never for a single number.
- Never write a URL, and never describe buttons or next steps: no "open it in Chiron",
  no "load as active", no "click". The page adds Query and Report buttons by itself.
- Stop when the answer is given. No closing offer or invitation ("let me know", "I can
  build a cohort from there", "want me to..."): the user knows they can ask.

Suggested follow-ups: after an answer that gave figures or saved something, end with a
fenced block tagged `followups` holding a JSON list of exactly 3 short questions the
user might ask next, for example:
```followups
["How many of them are women?", "Break them down by race", "Save them as a report"]
```
Make the three different kinds of next step: narrow the cohort with another filter,
break it down by a category (gender, race, ethnicity, marital status), rank what is
common among these patients (conditions, medications, visit types), compare with
another group, or save it as a report (after saving one: rename it, change its
filters, or delete it). Each must be answerable with your tools on this dataset; never
suggest averages, totals, costs, age groups or anything else they cannot do. Under 60
characters each, phrased as the user would type them. Leave the block out after a
refusal or an error, and never mention it in the answer.

Saving: call chiron_open_in_ui only when the user asks to save a report
(mode="report") or to load the cohort into their query (mode="workspace"). Pass as
columns the variables you filtered on.

Aggregate-only accounts (access level agg) cannot count or list patients; for them use
chiron_breakdown, which masks small counts the way Chiron's analysis view does, and say
the figures are aggregate. Never try to get patient rows for them.

If a tool refuses because of access, say in one sentence that this account cannot see
that data, and stop. Do not work around it. The same goes for a question about a dataset
you cannot find or open: say so and stop, and never answer with figures from a different
dataset instead.

Your context also contains details of the machine this runs on: an email address, file
paths, a working directory. They belong to whoever set the server up, not to the person
asking, and are irrelevant. Never mention an email address, a person's name, a username,
an account, a file path, or which account a tool acted as.
"""

SYSTEM_PROMPT_SHORT = """You are a research data analyst answering questions about one Chiron dataset.

Every figure you write must come from a tool result. Never estimate, add up or subtract
figures yourself: chiron_query does any arithmetic exactly.

Asking Chiron. Call chiron_query for each question, describing it in plain terms as in its
examples. It finds every spelling of each value, builds the query with Chiron's own
rules, checks it and counts. Translate the question faithfully:
- "over", "above", "more than", "greater than" -> op ">"; "or more", "at least", "or
  higher" -> ">="; "under", "below", "less than" -> "<"; "or less", "at most" -> "<=";
  "between X and Y" -> "between" (both ends included).
- How many times: "3 or more ER visits" -> {"visit": "emergency", "at_least": 3}; also
  exactly, at_most, more_than, fewer_than. "Never", "no", "without" -> "never": true.
- Two conditions on the same kind of record are separate conditions: list both.
- A lab or vital with a number is one result: {"lab": "HbA1c", "op": ">=", "value": 6.5}.
- Dates on a record: year, year_between, before, after ("diagnosed in 2018",
  "started before 2010"). "Died" is {"field": "death date", "has_value": true}.
- Timing between two records ("started metformin within 90 days after the diagnosis",
  "an ER visit in the 30 days before the procedure"): "within" on the record that is
  timed, with the other record in "of": {"medication": "metformin", "within":
  {"days_after": 90, "of": {"condition": "type 2 diabetes"}}}; days_before for the
  other direction, both for a window either side, "from": "end" to count from the
  other record's end (a discharge). Never approximate timing with years or plain AND.
- Follow-ups ("how many of them", "of those", "break them down"): pass start_from with
  the group of the answer they refer to; the groups so far are listed with the question.
  When the user names a group ("the widowed patients"), use the group that is exactly
  those patients, not simply the latest one; if no group is exactly them (only a
  narrower one, such as "widowed and died"), describe them afresh in where. Say in a few
  words which patients you used.
- Another dataset: pass its name as dataset. If chiron_query says it does not exist, say
  so in one sentence and stop; never answer from another dataset instead.
- If chiron_query says a word matches several values, pick the one the question means
  (or pass several in a list) and say which; if it says something cannot be expressed
  here (such as timing between records on a dataset without event dates), say that in
  one sentence, then give the closest figure it can count and say exactly what that
  figure counts.
Lead with chiron_query's count (distinct patients) and say what was counted, in plain
words from its what_was_counted, including the spellings it merged when there were
several. For breakdowns and top lists take every figure from its output (rows,
row_totals, no_value); never add cells up yourself.

What to show. These answer in the chat and change nothing in Chiron:
- how many: the count (the default, no show needed)
- split by, broken down by: show={"breakdown": ["gender", "ethnicity"]} (one or two)
- most common: show={"top": 5, "of": "condition"} (or "medication", "procedure", "visit")
- a list of patients: show={"list": ["birthdate", "death date", "city"], "limit": 10}
- lowest, highest or average of a lab or number: show={"range": {"lab": "HbA1c"}} or
  show={"range": "income"}
- which values exist (labs, units, visit types, payers): show={"values": "lab"}
Write to Results or a report only when the user asks for their Results tab or a report.

Results tab and reports, all with chiron_query unless said otherwise:
- "Put ... in my Results ...": show={"results": {"columns": [...], "sort": [...]}} with
  plain columns: "birthdate", "gender", "city"; {"has": {"medication": "metformin"}};
  {"max": {"lab": "HbA1c"}} (also min, average, latest, earliest);
  {"count_distinct": "medication"}. Sort: [{"column": <one of the columns>, "direction":
  "desc"}].
- To change what Results shows now (sort it, add or remove a column), use
  chiron_update_results; chiron_results lists its columns and rows.
- "Save ... as a report called X": show={"report": {"name": "X", "columns": [...]}}.
- Rename a report, make it public, or change its filters: start_from="report:<name>" (or
  "report:latest"), any new conditions in where, and show={"report": {"name": <its
  name>, "update": true, "new_name": ..., "public": true}}.
- "What reports do I have": chiron_saved_reports(scope="mine"). A report's patient count:
  chiron_query(start_from="report:<name>" or "report:latest").
- Delete a report only when the user asks, with chiron_delete_report and its exact name.
- "Load ... into my query": show={"query_builder": true}.
After a change say in one sentence what Chiron now holds (patients, rows, columns).

Answering. The reader wants the figure, not an essay.
- One short sentence with the answer, the figure in digits (20, not "twenty"). Add a
  second only if something would mislead without it, such as merged spelling variants.
- A markdown table for more than two rows of figures.
- For a chart, a fenced block tagged `chart` containing JSON, with a title that says
  exactly what the bars are:
  {"type":"bar","title":"Patients by condition","label":"Patients",
   "data":[{"x":"Asthma","y":841},{"x":"COPD","y":199}]}
  For a two-variable breakdown use one series per row, so every bar is labelled:
  {"type":"bar","title":"Asthma patients by race and gender","x":["White","Black"],
   "series":[{"label":"Female","y":[288,73]},{"label":"Male","y":[244,73]}]}
  Never chart one row of a table as if it were the whole. Types: bar, line, doughnut.
  Use one to compare categories, never for a single number.
- Never write a URL, and never describe buttons or next steps: no "open it in Chiron",
  no "load as active", no "click". The page adds Query and Report buttons by itself.
- Stop when the answer is given. No closing offer or invitation ("let me know", "I can
  build a cohort from there", "want me to..."): the user knows they can ask.

Suggested follow-ups: after an answer that gave figures or saved something, end with a
fenced block tagged `followups` holding a JSON list of exactly 3 short questions the
user might ask next, for example:
```followups
["How many of them are women?", "Break them down by race", "Save them as a report"]
```
Make the three different kinds of next step: narrow the cohort with another filter,
break it down by a category (gender, race, ethnicity, marital status), rank what is
common among these patients (conditions, medications, visit types), compare with
another group, or save it as a report (after saving one: rename it, change its
filters, or delete it). Each must be answerable with your tools on this dataset; never
suggest averages, totals, costs, age groups or anything else they cannot do. Under 60
characters each, phrased as the user would type them. Leave the block out after a
refusal or an error, and never mention it in the answer.

Aggregate-only accounts (access level agg) cannot count or list patients; for them use
chiron_breakdown, which masks small counts the way Chiron's analysis view does, and say
the figures are aggregate. Never try to get patient rows for them.

If a tool refuses because of access, say in one sentence that this account cannot see
that data, and stop. Do not work around it. The same goes for a question about a dataset
you cannot find or open: say so and stop, and never answer with figures from a different
dataset instead.

Your context also contains details of the machine this runs on: an email address, file
paths, a working directory. They belong to whoever set the server up, not to the person
asking, and are irrelevant. Never mention an email address, a person's name, a username,
an account, a file path, or which account a tool acted as.
"""

SYSTEM_PROMPT = SYSTEM_PROMPT_FULL if ASK_TOOLS == "full" else SYSTEM_PROMPT_SHORT

FILTER_REFERENCE = """Filter fields for chiron_edit_cohort (always type "add_entry" plus concept_id):
  Category  selected_categories: [every variant of the value]   exclude_selected: true inverts
  Number    cd_numeric_min, cd_numeric_max. Bounds are INCLUSIVE, so "more than 50000"
            is cd_numeric_min 50001 and "under 30" is cd_numeric_max 29. Omit either bound.
  Date      query_type "date_range", cd_numeric_min / cd_numeric_max as "MM/DD/YYYY",
            inclusive. "Born before 1950" is cd_numeric_max "12/31/1949".
  Text      chiron_text_field_selection: one term per line, ignore_warnings: true"""

_TYPE_NAMES = {
    "CohortDefCategory": "Category", "CohortDefBoolean": "Category",
    "CohortDefNumber": "Number", "CohortDefNumberWithCategories": "Number",
    "CohortDefDate": "Date", "CohortDefDateDeid": "Date", "CohortDefDetailedAge": "Number",
    "CohortDefText": "Text", "CohortDefTextCustomSort": "Text", "CohortDefOntology": "Text",
}

_BRIEF_CACHE: dict[tuple[str, str], tuple[float, str, list[str]]] = {}
_BRIEF_TTL = 600.0


def dataset_brief(dataset_id: str, username: str, allow_superuser: bool) -> tuple[str, list[str]]:
    """The variables this identity may filter on, grouped by collection, plus their ids.

    Handed to the model up front so it does not spend five tool calls rediscovering the
    schema on every question; that search was most of the wait and most of the chips.
    Built as the requesting user, so it only lists what they are allowed to use.
    """
    import time

    key = (dataset_id, username)
    hit = _BRIEF_CACHE.get(key)
    if hit and time.time() - hit[0] < _BRIEF_TTL:
        return hit[1], hit[2]
    if ASK_TOOLS != "full":
        brief = plain_brief(dataset_id, username, allow_superuser)
        _BRIEF_CACHE[key] = (time.time(), brief, [])
        return brief, []

    from chiron import models
    from chiron_mcp import identity

    ident = identity.resolve(dataset_id, username=username, allow_superuser=allow_superuser)
    cu = identity.checked_chironuser(ident)
    root = getattr(ident.dataset.root_collection, "permanent_id", None)
    by_coll: dict[str, list[str]] = {}
    ids: list[str] = []
    qs = models.Concept.objects.filter(
        collection__dataset=ident.dataset, published=True
    ).select_related("collection").order_by("collection__permanent_id", "permanent_id")
    for oConcept in qs:
        can_use, _ = oConcept.user_can_use_concept_in_cohort_def(cu)
        if not can_use:
            continue
        try:
            proc = oConcept.get_cohort_def_processor(cu)
            kind = _TYPE_NAMES.get(type(proc).__name__, "Other") if proc else "Other"
        except Exception:  # noqa: BLE001
            kind = "Other"
        coll = oConcept.collection.permanent_id
        by_coll.setdefault(coll, []).append(f"{oConcept.permanent_id} ({kind})")
        ids.append(oConcept.permanent_id)

    lines = [f"Dataset {dataset_id}. Variables you may use, by collection:"]
    for coll, items in by_coll.items():
        tag = "  [one row per patient]" if coll == root else ""
        lines.append(f"  {coll}{tag}: " + ", ".join(items))
    brief = "\n".join(lines) + "\n\n" + FILTER_REFERENCE
    _BRIEF_CACHE[key] = (time.time(), brief, ids)
    return brief, ids


def plain_brief(dataset_id: str, username: str, allow_superuser: bool) -> str:
    """What the dataset records, in the words chiron_query takes, built as the requesting
    user from Chiron itself: each kind of record with its variables, and the actual values
    where a variable has few (lab names, visit types, payers, conditions...). Values are
    listed only when already cached (or the table is small), so building this never makes
    a person wait; `python -m chiron_mcp.query --warm <dataset>` fills the cache after a load."""
    from chiron_mcp import dictionary as D
    from chiron_mcp import identity
    from chiron_mcp import query as Q

    ident = identity.resolve(dataset_id, username=username, allow_superuser=allow_superuser)
    words = {"subject": "patients", "condition": "conditions", "medication": "medications",
             "procedure": "procedures", "encounter": "visits", "observation": "labs and vitals"}
    colls = sorted({v.collection for v in Q.catalogue(ident)}, key=lambda c: (c != "subject", c))
    lines = [f"Dataset {ident.dataset.display_name or dataset_id} ({dataset_id}). What it records, in the "
             "words to use with chiron_query:"]
    for coll in colls:
        vs = Q._vars(ident, coll)
        names = []
        for v in vs:
            alias = (D.FIELDS.get(coll, {}).get(v.short) or (v.short.replace("_", " "),))[0]
            names.append(f"{alias} ({v.kind or 'other'})")
        lines.append(f"- {words.get(coll, coll)}: " + ", ".join(names))
        for v in vs:
            if v.kind != "category":
                continue
            groups = Q.cached_groups(ident, v)
            if groups is None or not 1 <= len(groups) <= 30:
                continue
            alias = (D.FIELDS.get(coll, {}).get(v.short) or (v.short.replace("_", " "),))[0]
            units = Q.cached_units(ident, coll) if v.short == D.NAME_FIELD.get(coll) else None
            codes = D.CODES.get(v.short) or {}

            def shown(g):
                meaning = codes.get(D.norm(g["label"]))
                text = g["label"] + (f" = {meaning[0]}" if meaning and D.norm(meaning[0]) != D.norm(g["label"]) else "")
                return text + (f" ({', '.join(units[g['label']])})" if units and units.get(g["label"]) else "")
            vals = "; ".join(shown(g) for g in groups)
            lines.append(f"    {alias} values{' (units)' if units else ''}: {vals}")
    return "\n".join(lines)


def usable_concept_ids(dataset_id: str, username: str, allow_superuser: bool) -> list[str]:
    """Every variable this identity may filter on, as Chiron concept ids: what the full
    brief lists, taken from the query catalogue when the short tool list is in use."""
    from chiron_mcp import identity
    from chiron_mcp import query as Q

    ident = identity.resolve(dataset_id, username=username, allow_superuser=allow_superuser)
    return [v.cid for v in Q.catalogue(ident)]


def starter_pool(dataset_id: str, username: str, allow_superuser: bool) -> list[dict]:
    """The starter questions for a dataset, whichever tool list is in use.

    The pool is built from the dataset's variables. The full brief lists them with their
    ids; the short tool list's brief (the default) names them in plain words and carries
    no ids, which left the page with the two generic starters only."""
    _, ids = dataset_brief(dataset_id, username, allow_superuser)
    if not ids:
        ids = usable_concept_ids(dataset_id, username, allow_superuser)
    return suggestion_pool(dataset_id, username, allow_superuser, ids)


# --- starter questions ---------------------------------------------------------------
#
# A pool of questions built from this dataset's real values, each tagged with the Ask
# feature it shows off. The page picks six from six different features for every new
# chat and avoids ones the user has just seen, so the starters keep changing and, over a
# few chats, walk through everything Ask can do. tests/ask_e2e.py --suggestions runs the
# whole pool, so a starter cannot ship broken.

FEATURES = {
    "count": "Count", "combine": "Combine filters", "number": "Number range",
    "date": "Dates", "negation": "Without", "compare": "Compare", "breakdown": "Breakdown",
    "breakdown2": "Two-way breakdown", "ranking": "Top list and chart", "visits": "Visits",
    "medications": "Medications", "rows": "Patient list", "report": "Save a report",
    "query": "Open in Chiron", "results": "Results table", "columns": "Report columns",
    "filters": "What is here",
}

# Long or clinical names that read badly in a question, and a plainer form the model
# still finds (it looks the value up, variants included).
_ALIASES = {
    "chronic obstructive pulmonary disease": "COPD",
    "body mass index 30+ - obesity": "obesity",
    "type 2 diabetes mellitus": "type 2 diabetes",
    "type 1 diabetes mellitus": "type 1 diabetes",
}
_ENCOUNTER_WORDS = {"urgentcare": "urgent care", "ambulatory": "ambulatory",
                    "emergency": "emergency", "wellness": "wellness",
                    "outpatient": "outpatient", "inpatient": "inpatient"}
# Medications that go with a condition, so "How many asthma patients take albuterol?"
# asks something a researcher would.
_PAIRS = {"asthma": "albuterol", "type 2 diabetes": "metformin",
          "hypothyroidism": "levothyroxine", "essential hypertension": "lisinopril",
          "major depressive disorder": "sertraline", "coronary arteriosclerosis": "atorvastatin"}

_POOL_CACHE: dict = {}
_POOL_TTL = 3600


def _plain(value: str) -> str | None:
    """A value as it reads in a sentence, or None when it would read badly."""
    v = " ".join(str(value).split())
    alias = _ALIASES.get(v.lower())
    if alias:
        return alias
    if len(v) > 32 or any(ch in v for ch in "()[]/+:;"):
        return None
    return v if v.isupper() else v[0].lower() + v[1:]


def _medication(value: str) -> str:
    words = str(value).split()
    n = 2 if words and words[0].lower() == "insulin" and len(words) > 1 else 1
    return " ".join(words[:n]).lower()


def _top(ident, concept_id: str, n: int) -> list[str]:
    """The n most common values of a variable, spelling variants merged."""
    from chiron_mcp import server as S

    try:
        oConcept = S._concept(ident, concept_id)
        groups, _ = S._groups(S._value_counts(ident, [], oConcept), n)
    except Exception:  # noqa: BLE001  a starter is never worth an error
        return []
    return [g["label"] for g in groups]


def suggestion_pool(dataset: str, username: str, allow_superuser: bool,
                    concept_ids: list[str]) -> list[dict]:
    """Starter questions for this dataset as [{"q", "feature"}], cached for an hour."""
    import time

    key = (dataset, username)
    hit = _POOL_CACHE.get(key)
    if hit and time.time() - hit[0] < _POOL_TTL:
        return hit[1]

    from chiron_mcp import identity

    have = {c.split("__", 1)[-1]: c for c in concept_ids}
    pool: list[dict] = []

    def add(feature, q):
        if q and not any(p["q"] == q for p in pool):
            pool.append({"q": q, "feature": feature})

    try:
        ident = identity.resolve(dataset, username=username, allow_superuser=allow_superuser)
    except identity.AccessError:
        return []

    cond_id = have.get("condition__description")
    if cond_id and "subject__gender" in have:
        conds = [c for c in (_plain(v) for v in _top(ident, cond_id, 14)) if c][:9]
        meds = [_medication(v) for v in _top(ident, have.get("medication__description", ""), 8)] \
            if "medication__description" in have else []
        visits = [_ENCOUNTER_WORDS.get(v.lower(), v.lower())
                  for v in _top(ident, have.get("encounter__encounterclass", ""), 6)] \
            if "encounter__encounterclass" in have else []
        pairs = list(zip(conds, conds[1:] + conds[:1]))

        for c in conds:
            add("count", f"How many patients have {c}?")
            add("combine", f"How many women have {c}?")
            add("breakdown", f"Break down patients with {c} by race")
            add("breakdown2", f"Break down patients with {c} by gender and race")
            add("report", f"Save patients with {c} as a report")
            add("query", f"Load patients with {c} into my query")
            add("rows", f"Show 10 patients with {c}, with their city and birthdate")
            add("results", f"Show patients with {c} in my results, with their birthdate and city")
            m = _PAIRS.get(c.lower())
            if m and "medication__description" in have:
                add("columns", f"Save patients with {c} as a report with their birthdate, "
                               f"city and whether they take {m}")
        for c in conds[:5]:
            add("combine", f"How many men have {c}?")
        for a, b in pairs[:6]:
            add("negation", f"How many patients have {a} but not {b}?")
            add("compare", f"How many patients have {a}, and how many have {b}?")
        add("negation", "How many patients do not have essential hypertension?"
            if "essential hypertension" in conds else None)

        if "subject__income" in have:
            for n in ("30,000", "50,000", "75,000", "100,000"):
                add("number", f"How many patients earn more than ${n} a year?")
            for c in conds[:4]:
                add("number", f"How many patients with {c} earn over $50,000?")
            add("number", "How many patients earn between $30,000 and $60,000?")
        if "subject__birthdate" in have:
            for y in (1940, 1950, 1960, 1970):
                add("date", f"How many patients were born before {y}?")
            for c in conds[:3]:
                add("date", f"How many patients born after 1980 have {c}?")
        if "subject__deathdate" in have:
            add("date", "How many patients have died?")
        if "subject__ethnicity" in have:
            add("breakdown", "How many patients are there of each ethnicity?")
            for c in conds[:3]:
                add("combine", f"How many Hispanic patients have {c}?")
        if "subject__married" in have:
            add("breakdown", "How many patients are there of each marital status?")

        add("ranking", "Which 5 conditions affect the most patients? Chart it")
        add("ranking", "What are the 10 most common conditions?")
        for c in conds[:4]:
            add("ranking", f"Top 5 medications among patients with {c}")
        if meds:
            add("ranking", "Top 10 medications by number of patients")
            for m in meds[:6]:
                add("medications", f"How many patients take {m}?")
            for c in conds:
                m = _PAIRS.get(c)
                if m and m in meds:
                    add("medications", f"How many patients with {c} take {m}?")
        if "procedure__description" in have:
            add("ranking", "What are the 5 most common procedures? Chart them")
        if visits:
            add("ranking", "Which visit types are most common? Chart them")
            for v in visits:
                add("visits", f"How many patients have had an {v} visit?"
                    if v[0] in "aeiou" else f"How many patients have had a {v} visit?")
            if "emergency" in visits:
                for c in conds[:3]:
                    add("visits", f"How many patients with {c} have had an emergency visit?")
        add("filters", "What can I filter on?")
    else:
        # Any other dataset: questions that work on every Chiron schema.
        add("count", "How many subjects are in this dataset?")
        add("filters", "What can I filter on?")
        cats = [c for c in concept_ids if c.split("__")[-2:-1] and "subject" in c][:3]
        for c in cats:
            name = c.split("__")[-1].replace("_", " ")
            add("breakdown", f"Break down subjects by {name}")
            add("ranking", f"What are the most common values of {name}? Chart them")

    _POOL_CACHE[key] = (time.time(), pool)
    return pool


def request_identity(cookie_header: str | None) -> tuple[str, bool]:
    """Who this request acts as, and whether a superuser is acceptable.

    The person logged into Chiron, when their session cookie is valid: the chat must see
    exactly what they could see in Chiron, no more, and must save reports they can open.
    With no session (the page opened on its own, outside Chiron) it falls back to
    CHIRON_MCP_USERNAME, and that configured service identity may not be a superuser.
    """
    who = session_username(cookie_header)
    if who:
        return who, True
    if REQUIRE_SESSION:
        return None, False
    return CONFIG.username, False


# On a public deployment nobody should get the fallback identity: every question must
# come from someone logged into Chiron. The Docker stack turns this on.
REQUIRE_SESSION = os.environ.get("CHIRON_MCP_REQUIRE_SESSION") == "1"
NOT_LOGGED_IN = "Log in to Chiron first; Ask answers as the person logged in."


def _mcp_config(username: str, allow_superuser: bool, thread: str | None = None) -> Path:
    """A per-request MCP config, so two people asking at once never swap identities.

    `thread` gives chiron_query a file for the conversation's groups (g1, g2, ...), so a
    follow-up can start from an earlier answer's patients; each question runs a fresh
    Chiron MCP process, so the groups cannot live in memory."""
    import tempfile

    env = {
        "CHIRON_MCP_CHIRON_SRC": CONFIG.chiron_src,
        "CHIRON_MCP_USERNAME": username,
        "CHIRON_MCP_MAX_ACCESS_LEVEL": CONFIG.max_access_level,
        "CHIRON_MCP_UI_URL": CONFIG.ui_url,
    }
    if CONFIG.metadata_db:
        env["CHIRON_MCP_METADATA_DB"] = CONFIG.metadata_db
    if CONFIG.warehouse_url:
        env["CHIRON_MCP_WAREHOUSE_URL"] = CONFIG.warehouse_url
    if CONFIG.allow_save:
        env["CHIRON_MCP_ALLOW_SAVE"] = "1"
    if allow_superuser:
        env["CHIRON_MCP_ALLOW_SUPERUSER"] = "1"
    if thread:
        env["CHIRON_MCP_GROUPS_FILE"] = str(_groups_file(thread))
    if ASK_TOOLS != "full":
        env["CHIRON_MCP_TOOLS"] = ",".join(TOOLS)  # the short list is all the model sees

    console = Path(sys.executable).parent / "chiron-mcp"
    cfg = {"mcpServers": {"chiron": {"command": str(console), "env": env}}}
    fd, path = tempfile.mkstemp(prefix="chiron-mcp-", suffix=".json")
    with os.fdopen(fd, "w") as fh:
        json.dump(cfg, fh)
    return Path(path)


class _CohortTracker:
    """Work out which cohort, if any, the answer is about.

    Only results that actually succeeded count. The earlier version recorded whatever
    cohort_def the model *passed* to a tool, including ones the tool rejected, so the
    Query button sometimes carried a malformed or hand-written cohort and failed.
    """

    _COUNTED = {"chiron_count_cohort", "chiron_run_table", "chiron_export_table",
                "chiron_crosstab", "chiron_breakdown", "chiron_open_in_ui",
                "chiron_update_report"}

    def __init__(self):
        self._calls: dict[str, tuple[str, dict]] = {}
        self.cohort: dict | None = None
        self.last_edit: dict | None = None
        # The tool calls those two came from, for the trace.
        self.cohort_call: tuple[str, str] | None = None
        self.edit_call: tuple[str, str] | None = None
        self.breakdown: dict | None = None  # the last breakdown's groups, for subgroup buttons
        self.link: dict | None = None
        self.deleted: list[int] = []  # report ids deleted in this answer
        self.counted = False  # a tool counted patients in this answer
        self.count_value: int | None = None  # the last count chiron_query returned

    def tool_use(self, block: dict) -> None:
        self._calls[block.get("id", "")] = (
            block.get("name", "").replace("mcp__chiron__", ""),
            block.get("input") or {},
        )

    def tool_result(self, block: dict) -> None:
        name, args = self._calls.get(block.get("tool_use_id", ""), ("", {}))
        if not name or block.get("is_error"):
            return
        if name in ("chiron_query", "chiron_count_cohort", "chiron_breakdown", "chiron_crosstab",
                    "chiron_run_table", "chiron_run_saved_report"):
            self.counted = True
        content = block.get("content")
        if isinstance(content, list):
            content = "".join(c.get("text", "") for c in content if isinstance(c, dict))
        try:
            data = json.loads(content or "")
        except (TypeError, ValueError):
            return
        if not isinstance(data, dict) or data.get("error"):
            return
        if name == "chiron_query" and isinstance(data.get("count"), int):
            self.count_value = data["count"]

        ds = args.get("dataset_id")
        if name == "chiron_query" and data.get("cohort_def") is not None:
            # chiron_query built and counted this cohort itself (args name the dataset in
            # words; the result carries its id).
            ds = data.get("dataset_id")
            bd = data.get("breakdown") or data.get("top")
            if isinstance(bd, dict) and bd.get("by"):
                self.breakdown = {
                    "dataset_id": ds, "cohort_def": data["cohort_def"],
                    "concept_id": bd["by"][0].get("concept_id"), "rows": bd.get("rows") or [],
                    "totals": bd.get("row_totals") or [], "variants": bd.get("merged_variants") or {},
                }
            if data["cohort_def"]:
                self.cohort = {"dataset_id": ds, "cohort_def": data["cohort_def"], "columns": []}
                self.cohort_call = (name, block.get("tool_use_id", ""))
            for key, label, mode in (("results", "Results", "results"), ("report", "Report", "report"),
                                     ("query_builder", "Query", "workspace")):
                written = data.get(key)
                if isinstance(written, dict) and written.get("url"):
                    self.link = {"label": label, "url": written["url"], "mode": mode}
            return
        if name == "chiron_edit_cohort":
            if data.get("successful") and data.get("cohort_def"):
                self.last_edit = {"dataset_id": ds, "cohort_def": data["cohort_def"],
                                  "columns": []}
                self.edit_call = (name, block.get("tool_use_id", ""))
            return

        # A saved or updated report gets its button whether or not this call carried a
        # cohort (a rename does not), so take the link before looking for one.
        if name == "chiron_update_results" and data.get("url"):
            self.link = {"label": "Results", "url": data["url"], "mode": "results"}
        if name in ("chiron_open_in_ui", "chiron_update_report") and data.get("url"):
            self.link = {
                "label": "Report" if data.get("mode") == "report" else "Query",
                "url": data["url"],
                "mode": data.get("mode"),
            }
        if name == "chiron_delete_report" and data.get("deleted"):
            self.link = None  # never point at a report that no longer exists
            self.deleted.append(data.get("report_id"))

        if name == "chiron_breakdown":
            by = [b.get("concept_id") for b in data.get("by") or [] if isinstance(b, dict)]
            if by:
                self.breakdown = {
                    "dataset_id": ds, "cohort_def": args.get("cohort_def") or [],
                    "concept_id": by[0], "rows": data.get("rows") or [],
                    "totals": data.get("row_totals") or [],
                    "variants": data.get("merged_variants") or {},
                }

        if name not in self._COUNTED or not args.get("cohort_def"):
            return
        self.cohort = {
            "dataset_id": ds,
            "cohort_def": args["cohort_def"],
            "columns": [c for c in (args.get("columns") or []) if isinstance(c, dict)],
        }
        self.cohort_call = (name, block.get("tool_use_id", ""))

    def final(self) -> dict | None:
        return self.cohort or self.last_edit

    def final_call(self) -> tuple[str, str] | None:
        """(tool, tool_use id) behind final()."""
        return self.cohort_call if self.cohort else self.edit_call if self.last_edit else None


_FOLLOWUPS = re.compile(r"```followups\s*([\s\S]*?)```", re.I)
# What the tools cannot do; a suggestion that invites it would fail when clicked.
_UNANSWERABLE = re.compile(
    r"\b(average|mean|median|sum|totals?|costs?|spend|price|age groups?|by age)\b", re.I)


def followup_audit(text: str) -> list[dict]:
    """Every suggestion the model wrote, whether the page shows it, and if not, why."""
    out: list[dict] = []
    shown: list[str] = []
    for block in _FOLLOWUPS.findall(text or ""):
        try:
            items = json.loads(block)
        except ValueError:
            out.append({"q": block.strip()[:200], "shown": False, "why": "the block is not valid JSON"})
            continue
        for q in items if isinstance(items, list) else []:
            q = " ".join(str(q).split())
            why = ("empty" if not q
                   else "longer than 90 characters" if len(q) > 90
                   else "asks for something the tools cannot do" if _UNANSWERABLE.search(q)
                   else "repeats another suggestion" if q.lower() in (f.lower() for f in shown)
                   else "only 3 are shown" if len(shown) >= 3
                   else None)
            if not why:
                shown.append(q)
            out.append({"q": q, "shown": not why, "why": why})
    return out


def split_followups(text: str) -> tuple[str, list[str]]:
    """The answer without its ```followups block, and up to 3 usable suggestions."""
    found = [f["q"] for f in followup_audit(text) if f["shown"]]
    return _FOLLOWUPS.sub("", text or "").rstrip(), found


_NUMBER = re.compile(r"(?<![\w.,])\d{1,3}(?:,\d{3})+(?![\d])|(?<![\w.,])\d+(?![\d,])")


def _numbers_in(content) -> set[int]:
    """Every whole number in a tool result's text ("12,755" and 12755 alike)."""
    if isinstance(content, list):
        content = "".join(c.get("text", "") for c in content if isinstance(c, dict))
    out = set()
    for m in re.finditer(r"\d{1,3}(?:,\d{3})+(?!\d)|\d+", str(content or "")):
        try:
            out.add(int(m.group().replace(",", "")))
        except ValueError:
            pass
    return out


def headline_figure(answer: str) -> int | None:
    """The figure an answer leads with: its first bold number, else its first number.

    "**445** of the 841 asthma patients are women" leads with 445, not 841. A Query
    button must be about the patients the answer is about, not a larger cohort it
    merely mentions.
    """
    # Only the prose counts: tables bold their totals and charts are all numbers.
    prose = re.sub(r"```[\s\S]*?```", " ", answer or "")
    prose = "\n".join(line for line in prose.splitlines() if not line.lstrip().startswith("|"))
    for bold in re.findall(r"\*\*([^*]+)\*\*", prose):
        m = _NUMBER.search(bold)
        if m:
            return int(m.group().replace(",", ""))
    m = _NUMBER.search(prose)
    return int(m.group().replace(",", "")) if m else None


def subgroup_cohort(bd: dict, figure: int, username: str, allow_superuser: bool) -> dict | None:
    """The cohort behind one group of the last breakdown, when the answer leads with it.

    "How many of them are women?" is sometimes answered by breaking the cohort down by
    gender and reading off one row. The cohort counted was all of them, so its button
    would be for the wrong patients; the group's own cohort is the base AND that group.
    """
    from chiron_mcp import identity, server as S

    for label, total in zip(bd["rows"], bd["totals"]):
        if total != figure:
            continue
        try:
            ident = identity.resolve(bd["dataset_id"], username=username,
                                     allow_superuser=allow_superuser)
            oConcept = S._concept(ident, bd["concept_id"])
            proc = oConcept.get_cohort_def_processor(identity.checked_chironuser(ident))
            field = S._GROUPABLE.get(type(proc).__name__)
            if not field:
                return None
            values = bd["variants"].get(label) or [label]
            cohort_def = S._add_filter(ident, bd["cohort_def"], oConcept, values, field)
        except Exception:  # noqa: BLE001  no button is better than a wrong one
            return None
        return {"dataset_id": bd["dataset_id"], "cohort_def": cohort_def, "columns": []}
    return None


def states_count(answer: str, n: int) -> bool:
    """Whether the answer states `n` as a figure ("7,861" or "7861", not "17861")."""
    for m in re.finditer(r"(?<![\w.,])\d{1,3}(?:,\d{3})+(?![\d])|(?<![\w.,])\d+(?![\d,])",
                         answer or ""):
        if int(m.group().replace(",", "")) == n:
            return True
    return False


def verify_cohort(state: dict, username: str, allow_superuser: bool,
                  why: list | None = None) -> dict | None:
    """Re-check a cohort as the requesting user before offering a button for it.

    Runs the same validation /load will run and counts it, so every Query button that
    appears is one that works, and it can say how many subjects it will load. Returns
    None for whole-dataset cohorts (nothing to load) and anything that fails, and says
    which in `why` when given one.
    """
    from chiron.query_engine import get_querytool
    from chiron_mcp import identity, server as S

    try:
        ident = identity.resolve(
            state["dataset_id"], username=username, allow_superuser=allow_superuser
        )
        identity.require_workspace(ident)
        identity.require_subject_level(ident)
        cohort = S._validated_cohort(ident, state.get("cohort_def") or [])
        if not cohort.cohort_def:
            if why is not None:
                why.append("The cohort has no filters (the whole dataset), so there is nothing to load.")
            return None
        n = get_querytool(identity.checked_chironuser(ident), cohort.cohort_def).get_cohort_count()
        return {**state, "cohort_def": cohort.cohort_def, "subject_count": int(n)}
    except Exception as exc:  # noqa: BLE001
        if why is not None:
            why.append(f"{type(exc).__name__}: {exc}"[:500])
        return None


def _state_dir() -> Path:
    """Where the Ask server keeps its working directory and thread registry.

    Stable across restarts, so a conversation can be resumed after the server is
    restarted. Claude runs with this as its cwd, so no project memory or CLAUDE.md is
    picked up, and its transcripts land in one predictable place we can prune.
    """
    d = Path(os.environ.get("CHIRON_MCP_STATE_DIR", Path.home() / ".cache" / "chiron-ask"))
    d.mkdir(parents=True, exist_ok=True)
    try:
        d.chmod(0o700)
    except OSError:
        pass
    return d


def _group_counts(tid: str) -> set[int]:
    try:
        return {g.get("count") for g in json.loads(_groups_file(tid).read_text()).values()
                if isinstance(g.get("count"), int)}
    except (OSError, ValueError, AttributeError):
        return set()


def _groups_note(tid: str) -> str:
    try:
        groups = json.loads(_groups_file(tid).read_text())
    except (OSError, ValueError):
        return ""
    if not groups:
        return ""
    items = list(groups.items())[-8:]
    lines = [f"- {name}: {g.get('label') or g.get('what')} ({g.get('count'):,} patients)"
             if isinstance(g.get("count"), int) else f"- {name}: {g.get('label') or g.get('what')}"
             for name, g in items]
    return ("\n\nGroups so far in this conversation (start_from takes the name; the latest is "
            f"{items[-1][0]}):\n" + "\n".join(lines))


def _groups_dict(tid: str) -> dict:
    """A conversation's groups as the trace names them: name -> what was counted, how many."""
    try:
        groups = json.loads(_groups_file(tid).read_text())
    except (OSError, ValueError):
        return {}
    return {str(name): {"count": g.get("count"), "what": g.get("label") or g.get("what")}
            for name, g in groups.items() if isinstance(g, dict)}


def _groups_file(tid: str) -> Path:
    """Where chiron_query keeps a conversation's groups (cohort definitions, no patients)."""
    return _state_dir() / "groups" / f"{tid}.json"


def _neutral_dir() -> str:
    wd = _state_dir() / "workdir"
    wd.mkdir(exist_ok=True)
    return str(wd)


def _trace_root() -> Path:
    """Where answers' traces are kept, one folder per conversation (see trace.py)."""
    return _state_dir() / "traces"


THREAD_TTL_HOURS = float(os.environ.get("CHIRON_MCP_THREAD_TTL_HOURS", "12"))


class _Threads:
    """Conversations that can be continued, and who they belong to.

    A follow-up is answered by resuming the same headless Claude session, so the model
    still has the cohorts it built. Each thread is bound to the Chiron user and dataset
    that started it; a thread id presented by anyone else is ignored and a new
    conversation starts, so one person can never resume another's.

    Claude Code saves each session's transcript to disk, tool results included, which
    means patient-level data. So a thread's transcript is deleted when it is cleared or
    once it has been idle for THREAD_TTL_HOURS, and its answers' traces with it.
    """

    def __init__(self):
        self._path = _state_dir() / "threads.json"
        self._guard = threading.Lock()
        self._locks: dict[str, threading.Lock] = {}
        self._running: dict[str, tuple] = {}  # tid -> (claude process, its outcome)
        try:
            self._data = json.loads(self._path.read_text())
        except (OSError, ValueError):
            self._data = {}

    def _save(self) -> None:
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data))
        tmp.chmod(0o600)
        tmp.replace(self._path)

    def valid(self, tid: str | None, user: str, dataset: str | None) -> bool:
        import time

        if not tid:
            return False
        with self._guard:
            t = self._data.get(tid)
            return bool(
                t and t["user"] == user and t.get("dataset") == dataset
                and time.time() - t["last"] < THREAD_TTL_HOURS * 3600
            )

    def touch(self, tid: str, user: str, dataset: str | None,
              cohort: dict | None = None) -> None:
        """Record activity, and the cohort behind the latest Query button if there was one.

        The cohort is a filter definition (concept ids and values), not patient data.
        """
        import time

        with self._guard:
            prev = self._data.get(tid) or {}
            self._data[tid] = {"user": user, "dataset": dataset, "last": time.time(),
                               "cohort": cohort or prev.get("cohort")}
            self._save()

    def cohort(self, tid: str) -> dict | None:
        with self._guard:
            return (self._data.get(tid) or {}).get("cohort")

    def lock(self, tid: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(tid, threading.Lock())

    def started(self, tid: str, proc, outcome: dict) -> None:
        with self._guard:
            self._running[tid] = (proc, outcome)

    def finished(self, tid: str, proc) -> None:
        with self._guard:
            if self._running.get(tid, (None,))[0] is proc:
                self._running.pop(tid, None)

    def stop(self, tid: str) -> bool:
        """Stop the answer running in a conversation, for a newer question in it."""
        with self._guard:
            entry = self._running.get(tid)
        if not entry:
            return False
        proc, outcome = entry
        outcome["cancelled"] = True
        if proc.poll() is None:
            proc.kill()
        return True

    @staticmethod
    def _delete_transcript(tid: str) -> None:
        import shutil as _sh

        root = Path.home() / ".claude" / "projects"
        for f in root.glob(f"*/{tid}.jsonl"):
            f.unlink(missing_ok=True)
        for d in root.glob(f"*/{tid}"):
            if d.is_dir():
                _sh.rmtree(d, ignore_errors=True)
        tracing.delete_thread(_trace_root(), tid)
        _groups_file(tid).unlink(missing_ok=True)

    def forget(self, tid: str, user: str) -> bool:
        with self._guard:
            t = self._data.get(tid)
            if not t or t["user"] != user:
                return False
            self._data.pop(tid, None)
            self._save()
        self._delete_transcript(tid)
        return True

    def prune(self) -> None:
        import time

        cutoff = time.time() - THREAD_TTL_HOURS * 3600
        with self._guard:
            stale = [tid for tid, t in self._data.items() if t["last"] < cutoff]
            for tid in stale:
                self._data.pop(tid, None)
            if stale:
                self._save()
        for tid in stale:
            self._delete_transcript(tid)
        # Also any trace left by a conversation that was never registered (the browser
        # went away before its first answer finished).
        tracing.prune(_trace_root(), THREAD_TTL_HOURS)


THREADS = _Threads()


_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PATH = re.compile(r"(?<![\w])(?:/Users|/home|/private|/tmp|/var/folders)/[^\s`'\")\]]*")


_URL = re.compile(r"\[([^\]]*)\]\((https?://[^)\s]+)\)|<?(https?://[^\s>)]+)>?")


def tidy(answer: str) -> str:
    """Remove links into Chiron from the prose; the page shows them as buttons.

    The model is told not to write URLs, but it sometimes does, and a pasted URL used to
    become a second Report button next to the real one.
    """
    base = CONFIG.ui_url.rstrip("/")

    def repl(m: re.Match) -> str:
        url = m.group(2) or m.group(3) or ""
        if base and url.startswith(base):
            return m.group(1) or ""
        return m.group(0)

    out = _URL.sub(repl, answer)
    # Answers about cohorts never need an email address or a local path, and the
    # headless session can see the operator's (see ask_stream), so neither leaves here.
    out = _EMAIL.sub("[redacted]", out)
    out = _PATH.sub("", out)
    out = re.sub(r"[ \t]*[:—-]?[ \t]*\n(?=\s*\n)", "\n", out)
    return re.sub(r"\n{3,}", "\n\n", out).strip()


def _tidy_audit(before: str, after: str) -> dict:
    """What tidy() took out of an answer, for its trace."""
    base = CONFIG.ui_url.rstrip("/")
    links = [m for m in _URL.finditer(before or "")
             if base and (m.group(2) or m.group(3) or "").startswith(base)]
    return {"changed": (before or "").strip() != after, "links_removed": len(links),
            "emails_redacted": len(_EMAIL.findall(before or "")),
            "paths_removed": len(_PATH.findall(before or "")), "before": before}


def _redact(text: str) -> str:
    """The operator's email and paths never reach a trace (the page shows it to whoever
    asked, who may not be the operator)."""
    return _PATH.sub("[path]", _EMAIL.sub("[email]", text))


_NOT_LOGGED_IN = re.compile(
    r"invalid api key|please run /login|not logged in|log ?in to|authenticat|oauth|"
    r"credit balance|x-api-key", re.I)
# Bedrock refusing a model the deployment's AWS role may not call.
_MODEL_DENIED = re.compile(
    r"AccessDenied|not authorized to perform|don.t have access to the model|"
    r"could not resolve the foundation model|model identifier is invalid", re.I)


def explain_claude_error(text: str) -> str:
    """Turn the CLI's own wording for a missing or expired login into what to do."""
    if _MODEL_DENIED.search(text or ""):
        return ("This server's AWS role may not call that model on Bedrock. Pick another "
                "model, or have the role's Bedrock policy extended to this one.")
    if _NOT_LOGGED_IN.search(text or ""):
        return ("Ask is not connected to a Claude account on this server yet, or its "
                "login has expired. Whoever runs the server can fix it: docker compose "
                "exec -it ask claude, then /login.")
    return text


# How long one answer may take, and how often to show the browser the stream is alive.
TURN_SECONDS = int(os.environ.get("CHIRON_MCP_TURN_SECONDS", "240"))
PING_SECONDS = 10


def _pump(stream, lines: "queue.Queue") -> None:
    """Copy the CLI's output into a queue, so waiting for it can time out."""
    try:
        for line in stream:
            lines.put(line)
    finally:
        lines.put(None)


def _drain(trace):
    """The trace's changed steps as page events."""
    for step in trace.drain():
        yield "trace", step


def _claude_turn(cmd: list[str], username: str, allow_superuser: bool, outcome: dict,
                 inherited: dict | None = None, tid: str = "", trace=tracing.OFF,
                 known: set | None = None, env: dict | None = None):
    """One headless Claude run, translated into page events.

    `inherited` is the cohort behind the conversation's previous Query button. A
    follow-up the model answers from what it already has ("chart that", "as a table")
    makes no tool calls, so without it such an answer would lose its button.

    Sets outcome["answered"], outcome["rc"], outcome["stderr"] and outcome["cohort"]
    (the state behind any Query button offered) for the caller.

    While Claude is quiet (thinking, or retrying a busy API) this yields "ping" every
    PING_SECONDS. The write fails once the browser has gone (reloaded, closed, or
    stopped), and that ends the run, so an abandoned answer never keeps its
    conversation locked. A run is stopped after TURN_SECONDS.

    Every event is also fed to `trace`, which records the run step by step, and the
    steps it changes go to the page as "trace" events (see trace.py).
    """
    import queue
    import time

    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL, text=True, bufsize=1, cwd=_neutral_dir(), env=env,
    )
    tracker = _CohortTracker()
    tool_numbers: set[int] = set()
    outcome.update(answered=False, rc=None, stderr="")
    THREADS.started(tid, proc, outcome)
    lines: queue.Queue = queue.Queue()
    threading.Thread(target=_pump, args=(proc.stdout, lines), daemon=True).start()
    deadline = time.monotonic() + TURN_SECONDS
    try:
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                proc.kill()
                outcome["answered"] = True
                took = (f"{TURN_SECONDS // 60} minutes" if TURN_SECONDS >= 120
                        else f"{TURN_SECONDS} seconds")
                message = f"No answer after {took}, so it was stopped. Claude may be busy; ask again."
                trace.error(message)
                yield from _drain(trace)
                yield "error", message
                break
            try:
                line = lines.get(timeout=min(PING_SECONDS, left))
            except queue.Empty:
                yield "ping", None
                continue
            if line is None:
                break
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            trace.feed(ev)
            trace.raw(line, ev)
            yield from _drain(trace)

            kind = ev.get("type")
            if kind == "system" and ev.get("subtype") == "api_retry":
                # The CLI retries a busy or unresponsive API by itself, sometimes for
                # minutes; say so rather than look frozen.
                yield "step", "retrying"
            elif kind == "assistant":
                for block in ev.get("message", {}).get("content", []):
                    if block.get("type") == "tool_use":
                        raw = block.get("name", "")
                        # Only surface Chiron work; Claude's own housekeeping is noise.
                        if not raw.startswith("mcp__chiron__"):
                            continue
                        tracker.tool_use(block)
                        yield "step", raw.replace("mcp__chiron__chiron_", "")
            elif kind == "user":
                for block in ev.get("message", {}).get("content", []) or []:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        tracker.tool_result(block)
                        if not block.get("is_error"):
                            tool_numbers.update(_numbers_in(block.get("content")))
            elif kind == "result":
                if ev.get("is_error"):
                    message = explain_claude_error(ev.get("result") or "Claude returned an error.")
                    trace.error(message)
                    yield from _drain(trace)
                    yield "error", message
                    outcome["answered"] = True
                    continue
                # The suggested follow-ups travel separately; everything below judges
                # the answer itself, never numbers that only appear in a suggestion.
                text, followups = split_followups(ev.get("result", ""))
                # The answer's lead figure must be one a tool returned (plan P7). When it is
                # not, the answer is held back and the caller asks once for a checked one.
                lead = headline_figure(text)
                if (known is not None and tracker.counted and lead is not None
                        and lead not in tool_numbers and lead not in known):
                    outcome.update(answered=True, unbacked=lead)
                    trace.note("Lead figure not from a tool",
                               f"The answer led with {lead:,}, which no tool returned; it was not "
                               "shown, and the model was asked to check it.", status="warn")
                    yield from _drain(trace)
                    continue
                # A count came back but the answer states no figure in digits ("Twenty
                # patients have asthma"): held back the same way, for the figure in digits.
                # A count of 0 is left alone ("No patients have ...").
                if (known is not None and lead is None and tracker.count_value
                        and not re.search(r"\d", text)):
                    outcome.update(answered=True, nodigits=tracker.count_value)
                    trace.note("No figure in digits",
                               f"A tool returned the count {tracker.count_value:,}, but the answer states no "
                               "figure in digits; it was not shown, and the model was asked for the figure.",
                               status="warn")
                    yield from _drain(trace)
                    continue
                trace.post("followups", followup_audit(ev.get("result", "")))
                trace.post("charts", tracing.chart_audit(text))
                # Earlier answers may carry Report buttons for what was just deleted;
                # the page retires them.
                for rid in tracker.deleted:
                    yield "deleted", rid
                if tracker.link:
                    yield "link", tracker.link
                trace.post("link", tracker.link)
                trace.post("deleted", tracker.deleted)
                # Why the answer did or did not get a Query button, for the trace.
                decision: dict = {"offered": None}
                # A workspace hand-off has already loaded the query, and its link says
                # so; a second Query button for the same cohort would just repeat it.
                if not (tracker.link and tracker.link.get("mode") in ("workspace", "results")):
                    state = tracker.final() or inherited
                    call = tracker.final_call() if tracker.final() else None
                    why: list[str] = []
                    verified = state and verify_cohort(state, username, allow_superuser, why)
                    # The button is labelled with its count; offer it only when that is
                    # the figure the answer leads with, so it is never about other
                    # patients than the ones the answer describes. If the answer leads
                    # with one group of a breakdown, offer that group's cohort instead.
                    figure = headline_figure(text)
                    decision.update(
                        source=(f"the cohort passed to {call[0]}" if call else
                                "the previous answer's cohort" if state else None),
                        step=trace.step_for_call(call[1]) if call else None,
                        cohort=tracing.cohort_lines(state.get("cohort_def")) if state else None,
                        figure=figure, verified=verified["subject_count"] if verified else None,
                        verify_error=why[0] if why else None)
                    if verified and verified["subject_count"] != figure:
                        verified = None
                        sub = tracker.breakdown and figure is not None and subgroup_cohort(
                            tracker.breakdown, figure, username, allow_superuser)
                        checked = sub and verify_cohort(sub, username, allow_superuser)
                        if tracker.breakdown and figure is not None:
                            decision["subgroup"] = {
                                "found": bool(sub),
                                "count": checked["subject_count"] if checked else None}
                        if checked and checked["subject_count"] == figure:
                            state, verified = sub, checked
                            decision["source"] = "one group of the breakdown"
                    if verified:
                        outcome["cohort"] = state
                        decision["offered"] = verified["subject_count"]
                        yield "cohort", verified
                    else:
                        decision["reason"] = (
                            "No cohort was built or counted, and none carried over." if not state
                            else "The cohort could not be re-checked." if decision["verified"] is None
                            else f"The answer leads with {figure if figure is not None else 'no figure'}, "
                                 f"not the cohort's {decision['verified']:,} patients.")
                else:
                    decision["reason"] = "The answer already put this in Chiron; its own button opens it."
                trace.post("cohort", decision)
                if followups:
                    yield "followups", followups
                answer = tidy(text)
                trace.post("tidy", _tidy_audit(text, answer))
                trace.answer(answer)
                yield from _drain(trace)
                yield "answer", answer
                outcome["answered"] = True
        proc.wait(timeout=10)
        outcome["rc"] = proc.returncode
        outcome["stderr"] = (proc.stderr.read() or "").strip()
    finally:
        THREADS.finished(tid, proc)
        if proc.poll() is None:
            proc.kill()


def ask_stream(
    question: str,
    dataset: str | None,
    username: str,
    allow_superuser: bool,
    thread: str | None = None,
    model: str | None = None,
):
    """Answer one question as `username`, continuing `thread` when it is theirs.

    `model` is the page's pick among CHIRON_MCP_ASK_MODELS (pick_model decides what it
    means); a follow-up may switch, since the transcript is resumed by id.

    Events: thread (the conversation id to send back with a follow-up), step, link,
    cohort (verified, with its subject count), answer, error. With tracing on, also
    trace_start (the trace's id and what it is about), trace (one step, new or changed)
    and trace_end (totals and checks); the whole trace is then at /trace?id=.
    """
    import uuid

    global THINKING_DISPLAY

    claude = shutil.which("claude") or os.path.expanduser("~/.local/bin/claude")
    if not Path(claude).exists():
        yield "error", "Claude Code CLI not found. Install it, or put `claude` on PATH."
        return
    model = pick_model(model)
    env = model_env(model)

    THREADS.prune()
    resume = THREADS.valid(thread, username, dataset)
    tid = thread if resume else str(uuid.uuid4())
    lock = THREADS.lock(tid)
    if not lock.acquire(blocking=False):
        # The page asks one question at a time, so another one in the same conversation
        # (only its owner can resume it) means the earlier answer was abandoned: the
        # page was reloaded or stopped while it was stuck. Stop it and go on.
        THREADS.stop(tid)
        if not lock.acquire(timeout=20):
            yield "error", "Still answering your previous question in this conversation."
            return

    cfg = _mcp_config(username, allow_superuser, thread=tid)
    trace = tracing.OFF
    outcome: dict = {}
    try:
        yield "thread", tid
        if TRACE:
            trace = tracing.Trace(
                question=question, dataset=dataset, user=username, thread=tid, followup=resume,
                prior=tracing.prior(_trace_root(), tid, username) if resume else [],
                inherited=THREADS.cohort(tid) if resume else None, redact=_redact,
                groups=_groups_dict(tid) if resume else None)
            yield "trace_start", trace.head()
        for _attempt in range(2):
            if resume:
                # The dataset brief is already in the conversation. The groups chiron_query
                # made so far are listed, so "them" and "the widowed patients" find theirs.
                prompt = f"Follow-up question: {question}" + _groups_note(tid)
                session = ["--resume", tid]
            else:
                prompt = question
                if dataset:
                    try:
                        brief, _ = dataset_brief(dataset, username, allow_superuser)
                        prompt = f"Question: {question}\n\n{brief}"
                    except Exception as exc:  # noqa: BLE001
                        # No access: let the model meet the same refusal and say so.
                        prompt = f"[dataset: {dataset}]\n\n{question}\n\n(Access check: {exc})"
                session = ["--session-id", tid]

            inherited = THREADS.cohort(tid) if resume else None
            for _flag in range(2):
                cmd = _claude_command(claude, prompt, session, cfg, model)
                outcome = {}
                trace.launched(cmd, prompt, SYSTEM_PROMPT, resume)
                yield from _claude_turn(cmd, username, allow_superuser, outcome, inherited, tid, trace,
                                        known=_numbers_in(question) | _group_counts(tid), env=env)
                if outcome.get("answered") or not _thinking_flag_refused(outcome):
                    break
                # A Claude Code too old for --thinking-display: ask again without it, and
                # stop passing it for as long as this server runs.
                THINKING_DISPLAY = None
                trace.note("Reasoning summaries unavailable",
                           "This Claude Code does not know --thinking-display, so the question was "
                           "asked again without it; the trace shows no reasoning.", status="info")
                yield from _drain(trace)

            if outcome.get("cancelled"):
                message = "Stopped, because a newer question in this conversation replaced it."
                trace.error(message)
                yield "error", message
                break
            if outcome.get("answered"):
                break
            if model and _MODEL_DENIED.search(outcome.get("stderr") or "") and fallback_model(model):
                # Bedrock refused the model (the deployment's role may not call it, or the
                # region lacks it): stop offering it, and answer with the next one as a new
                # conversation, since the refused start may have claimed the session id.
                DENIED.add(model)
                nxt = fallback_model(model)
                resume = False
                tid = str(uuid.uuid4())
                trace.rerouted(tid, model, nxt)
                yield from _drain(trace)
                yield "thread", tid
                model, env = nxt, model_env(nxt)
                continue
            if resume:
                # The transcript is gone (expired, or cleared elsewhere): start this
                # question as a fresh conversation rather than failing it.
                resume = False
                tid = str(uuid.uuid4())
                trace.restarted(tid)
                yield from _drain(trace)
                yield "thread", tid
                continue
            if outcome.get("stderr"):
                message = explain_claude_error(outcome["stderr"][:500])
                trace.error(message)
                yield "error", message
            break
        if (outcome.get("unbacked") is not None or outcome.get("nodigits")) and not outcome.get("cancelled"):
            # Held back: its lead figure came from no tool, or it states no figure in digits.
            # Ask once for a checked answer, and show that one whatever it says.
            if outcome.get("unbacked") is not None:
                fig = outcome["unbacked"]
                note = (f"Check before answering: your answer led with {fig:,}, but no tool returned "
                        "that figure. Every figure must come from a tool result: get it with a tool "
                        "(chiron_query does any arithmetic exactly), then give the whole answer again.")
            else:
                note = (f"Check before answering: a tool returned the count {outcome['nodigits']:,}, but your "
                        "answer states no figure in digits. Give the whole answer again with the figure "
                        "in digits (20, not \"twenty\").")
            cmd = _claude_command(claude, note, ["--resume", tid], cfg, model)
            outcome = {}
            trace.launched(cmd, note, SYSTEM_PROMPT, True)
            yield from _claude_turn(cmd, username, allow_superuser, outcome,
                                    THREADS.cohort(tid), tid, trace, env=env)
        THREADS.touch(tid, username, dataset, outcome.get("cohort"))
        if TRACE:
            trace.finish(outcome.get("rc"), outcome.get("stderr", ""))
            trace.save(_trace_root())
            yield from _drain(trace)
            yield "trace_end", trace.tail()
    finally:
        if TRACE and trace is not tracing.OFF and not trace.data.get("done"):
            # The page went away (or a newer question stopped this one) mid-answer:
            # keep what was recorded, so a stuck answer can still be looked into.
            trace.note("Stopped before the end",
                       "The page closed, or a newer question replaced this one, before the answer "
                       "finished.", status="warn")
            trace.finish(outcome.get("rc"), outcome.get("stderr", ""))
            trace.save(_trace_root())
        lock.release()
        try:
            cfg.unlink()
        except OSError:
            pass


def _claude_command(claude: str, prompt: str, session: list[str], cfg: Path,
                    model: str | None = None) -> list[str]:
    # Isolate the headless session from the operator's own Claude Code setup.
    # Without this it inherits their git identity, project files, memory and
    # every other MCP server they have configured, and repeats them in answers.
    # The account email is injected by Claude Code itself and cannot be switched
    # off without an API key (--bare), which is why tidy() also redacts.
    return [
        claude, "-p", prompt, *session,
        *(["--model", model] if model else []),
        "--mcp-config", str(cfg),
        "--strict-mcp-config",
        "--setting-sources", "",
        # No built-in tools at all (Bash, Read, Write, WebFetch...): the only thing
        # a question can make Claude do is call Chiron. Without this, a visitor
        # could ask it to read files on the server, the Claude login among them.
        "--tools", "",
        "--allowed-tools", ",".join(f"mcp__chiron__{t}" for t in TOOLS),
        "--system-prompt", SYSTEM_PROMPT,
        *(["--thinking-display", THINKING_DISPLAY] if THINKING_DISPLAY else []),
        "--output-format", "stream-json",
        "--verbose",
    ]


def _thinking_flag_refused(outcome: dict) -> bool:
    return bool(THINKING_DISPLAY) and "thinking-display" in (outcome.get("stderr") or "")


# The session-cookie lookup lives in identity, shared with the OAuth login page.
from chiron_mcp.identity import session_username  # noqa: E402,F401


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # keep the console quiet
        pass

    def _allowed_origins(self) -> set[str]:
        # A browser's Origin is scheme and host only, while the UI's address may carry
        # a path (a deployment under /chiron), so compare against its origin.
        ui = urlparse(CONFIG.ui_url)
        allowed = {
            f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}",
            f"{ui.scheme}://{ui.netloc}" if ui.netloc else CONFIG.ui_url,
        }
        extra = os.environ.get("CHIRON_MCP_ALLOWED_ORIGINS", "")
        return allowed | {o.strip() for o in extra.split(",") if o.strip()}

    def _cors(self):
        # Only the page itself calls this server, from its own origin, so no other site
        # is ever told it may read the answers. (It used to say "*".)
        origin = self.headers.get("Origin")
        if origin and origin in self._allowed_origins():
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _same_site(self) -> bool:
        """Refuse requests another site's page makes a visitor's browser send.

        Browsers label every request with Sec-Fetch-Site; the Ask page's own requests
        are "same-origin". Without this, a page elsewhere could start question runs on
        the operator's Claude account just by being visited. Tools such as curl send no
        such header and are judged by Origin alone.
        """
        site = self.headers.get("Sec-Fetch-Site")
        if site and site not in ("same-origin", "none"):
            return False
        return self._origin_ok()

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        url = urlparse(self.path)

        if url.path in ("/", "/index.html"):
            return self._file(WEBUI / "index.html", "text/html; charset=utf-8")
        if url.path == "/health":
            return self._json({"ok": True, "identity": CONFIG.username})
        if url.path == "/datasets":
            if not self._same_site():
                return self.send_error(403, "cross-site request refused")
            return self._datasets()
        if url.path == "/ask":
            if not self._same_site():
                return self.send_error(403, "cross-site request refused")
            return self._ask(parse_qs(url.query))
        if url.path == "/trace":
            if not self._same_site():
                return self.send_error(403, "cross-site request refused")
            return self._trace(parse_qs(url.query))

        self.send_error(404)

    def do_POST(self):
        url = urlparse(self.path)
        if url.path == "/load":
            return self._load()
        if url.path == "/forget":
            return self._forget()
        self.send_error(404)

    def _file(self, path: Path, ctype: str):
        if not path.exists():
            return self.send_error(404)
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        # The page is read from disk on every request, so never let a browser hold on
        # to an old copy: an edit here should show up on reload, not after a hard
        # refresh someone has to know to do.
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _datasets(self):
        """Who is asking, what they may use, and starter questions for ?dataset=."""
        who, allow_su = request_identity(self.headers.get("Cookie"))
        dataset = (parse_qs(urlparse(self.path).query).get("dataset") or [None])[0]
        out: dict = {"identity": who, "datasets": [], "suggestions": [],
                     "models": offered_models(), "model": default_model()}
        if not who:
            out["error"] = NOT_LOGGED_IN
            return self._json(out)
        try:
            from chiron import models
            from chiron_mcp import identity

            for oDataset in models.Dataset.objects.all().order_by("unique_id"):
                try:
                    ident = identity.resolve(
                        oDataset.unique_id, username=who, allow_superuser=allow_su
                    )
                except identity.AccessError:
                    continue
                out["datasets"].append({
                    "id": oDataset.unique_id,
                    "name": oDataset.display_name or oDataset.unique_id,
                    "access_level": ident.access_level,
                })
            if dataset:
                match = next((d for d in out["datasets"] if d["id"] == dataset), None)
                out["access_level"] = match["access_level"] if match else None
                if match and match["access_level"] in ("phi", "deid"):
                    out["pool"] = starter_pool(dataset, who, allow_su)
                    out["features"] = FEATURES
        except Exception as exc:  # noqa: BLE001
            out["error"] = str(exc)
        return self._json(out)

    def _origin_ok(self) -> bool:
        """Reject cross-site POSTs to /load.

        /load writes to the workspace of whoever the request's session cookie belongs
        to, so without this a page on another origin could make a visitor's browser
        clobber their Chiron query. Same-origin requests from the page itself send an
        Origin of this server; the UI embeds us in an iframe, which does not change it.
        """
        origin = self.headers.get("Origin")
        if not origin:
            return True  # curl, scripts, and same-origin form posts from this page
        return origin in self._allowed_origins()

    def _load(self):
        """Replace the browser user's live Chiron query with a cohort from an answer.

        Body: {"dataset_id", "cohort_def", "columns"?}.  Writes to the workspace of the
        Chiron user behind the request's session cookie, falling back to
        CHIRON_MCP_USERNAME when there is none.  Same guards as chiron_open_in_ui:
        CHIRON_MCP_ALLOW_SAVE must be on, and an errored definition is refused.
        """
        if not self._same_site():
            return self._json({"error": "Refused: request came from an untrusted origin."})
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, TypeError):
            return self._json({"error": "Body must be JSON."})
        dataset_id = body.get("dataset_id")
        cohort_def = body.get("cohort_def")
        if not dataset_id or not isinstance(cohort_def, list) or not cohort_def:
            return self._json({"error": "dataset_id and a non-empty cohort_def are required."})

        from chiron_mcp import server as S

        who, allow_su = request_identity(self.headers.get("Cookie"))
        if not who:
            return self._json({"error": NOT_LOGGED_IN})
        result = S.open_in_ui(
            dataset_id, cohort_def, body.get("columns") or [], mode="workspace",
            username=who, allow_superuser=allow_su,
        )
        result["browser_user"] = who
        return self._json(result)

    def _forget(self):
        """A conversation deleted in the page: drop it and delete its transcript now."""
        if not self._same_site():
            return self._json({"error": "Refused: request came from an untrusted origin."})
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, TypeError):
            return self._json({"error": "Body must be JSON."})
        who, _ = request_identity(self.headers.get("Cookie"))
        tid = body.get("thread") or ""
        return self._json({"forgotten": bool(tid) and THREADS.forget(tid, who)})

    def _trace(self, params):
        """One answer's full trace, for the person who asked it (see trace.py)."""
        who, _ = request_identity(self.headers.get("Cookie"))
        data = tracing.find(_trace_root(), (params.get("id") or [""])[0], who)
        if data is None:
            return self._json({"error": (
                "No trace for this answer. Traces are kept only as long as their conversation "
                f"({THREAD_TTL_HOURS:g} hours after its last question), and only for the person "
                "who asked.")})
        return self._json(data)

    def _ask(self, params):
        question = (params.get("q") or [""])[0].strip()
        dataset = (params.get("dataset") or [None])[0]
        if not question:
            return self.send_error(400, "missing q")

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self._cors()
        self.end_headers()

        def send(event, data):
            # A ping is an SSE comment: the page ignores it, but writing it shows
            # whether the browser is still there.
            chunk = ": ping\n\n" if event == "ping" else \
                f"event: {event}\ndata: {json.dumps(data)}\n\n"
            self.wfile.write(chunk.encode())
            self.wfile.flush()

        who, allow_su = request_identity(self.headers.get("Cookie"))
        if not who:
            send("error", NOT_LOGGED_IN)
            send("done", "")
            return
        thread = (params.get("thread") or [None])[0]
        model = (params.get("model") or [None])[0]
        stream = ask_stream(question, dataset, who, allow_su, thread, model)
        try:
            for event, payload in stream:
                send(event, payload)
            send("done", "")
        except (BrokenPipeError, ConnectionResetError):
            pass  # the browser navigated away
        finally:
            stream.close()  # stops Claude and frees the conversation if it is still running


def main() -> int:
    if not CONFIG.username:
        print("CHIRON_MCP_USERNAME is required.", file=sys.stderr)
        return 1
    WEBUI.mkdir(exist_ok=True)
    # Boot Django once, up front: several handlers use the ORM directly, and a request
    # with no session cookie would otherwise reach it before anything had set it up.
    from chiron_mcp.bootstrap import ensure_django

    ensure_django()
    # The Ask page shows the model's reasoning in its traces, so ask for it.
    global THINKING_DISPLAY
    if THINKING_DISPLAY is None:
        THINKING_DISPLAY = "summarized"
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Chiron Ask running at http://localhost:{PORT}")
    print("  identity : the user logged into Chiron; with no session, "
          f"{CONFIG.username} (ceiling {CONFIG.max_access_level})")
    print(f"  chiron ui: {CONFIG.ui_url}")
    print(f"  traces   : {'on' if TRACE else 'off'}"
          + (f", reasoning {THINKING_DISPLAY}" if TRACE and THINKING_DISPLAY else ""))
    print("  Ctrl-C to stop")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

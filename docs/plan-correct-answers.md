# Plan: correct Chiron answers from any model, Haiku included

**Goal.** Every model gives the right answer, however the question is phrased, including
cheap ones like Haiku 5.5. The way there is to move the hard parts out of the model and
into Chiron MCP. Then we run the benchmark again to show the gain.

Status: draft for approval, 2026-10-26. Nothing here has been built yet.

---

## 1. Where we are

### Score on the 49 benchmark questions (synthea-100k)

| Model | Correct | Notes |
|---|---|---|
| Opus 5.5 (Chiron Ask page) | 44 | |
| Opus 4.6 (Bedrock) | 40 | |
| Sonnet 4.6 (Bedrock) | 37 | |
| Qwen3-Next 80B (Bedrock) | 23 | |
| gpt-oss-20b (this Mac) | 22 | 20 timeouts |
| Opus 5.5 (Bedrock) | 15 of 17 | stopped run, not a full score |
| Haiku 5.5 (Bedrock) | not measured yet | step 0.1 measures it |

### Why answers go wrong

There were 81 wrong or missing answers across all runs, and each was read by hand. None
were caused by Chiron counting wrong. Every one came from turning the question into a
Chiron query, or from Chiron being too slow.

| # | Cause | Wrong answers | Example | Fixed in |
|---|---|---|---|---|
| A | **Two conditions on the same table.** For example "both asthma and COPD", or "HbA1c ≥ 6.5 and, at another time, < 5.7". Chiron always adds a new filter to the first group of that table, so both conditions must hold on the same record and the count drops to 0. The models guess fields like `parent_id` and `set_id` to fix this, and Chiron silently ignores them. | 14 | q02, q03, q11, q12 | P2 |
| B | **Count rule written as `at_least`.** Chiron only knows `at least`, `at most` and `exactly`. It accepts `at_least` without error and treats it as `exactly`. The follow-ups then build on the wrong group. | 12 | q07 → q08, q09 (all 4 benchmark models) | P1, P2 |
| C | **Results and reports built wrong or too slowly.** For example, an extra cohort filter added just to get a "highest HbA1c" column (5,933 rows instead of 6,914), or a report's filters changed without saving the report. | 12 | q37–q44 | P4 |
| D | **"Over" or "above" turned into "at least".** For example, "over $4,500" became ≥ 4,501, which skips $4,500.01–$4,500.99, and "above 4.5" became ≥ 4.5. | 11 | q29 → q30, q31; q34 | P2 |
| E | **A Chiron step too slow for the 5-minute limit.** Value lists and breakdowns over the 21.5M lab rows take minutes. | 9 | q32, q33, q01 | P6 |
| F | **Malformed tool calls**, mostly from small models: hand-written `cohort_def`, missing `collection_id`, made-up transformation types, wrong tool names. | 7 | gpt-oss q16 (6 broken calls), Qwen q18 | P1, P2, P8 |
| G | **Answered for a dataset that doesn't exist** ("MIMIC-IV") using synthea-100k numbers. | 4 | q48 | P3, P7 |
| H | **Wrong field**, for example "base encounter cost" instead of "total claim cost". | 3 | Qwen q29 → q30, q31 | P3 |
| I | **Wrong dataset name or list**, for example a Synthea 300 question answered from Synthea 100k. | 3 | q35, q36 | P3 |
| J | **Value not found** (what label does "depression screening" have?). | 2 | q46 | P3 |
| K | **A follow-up built on an earlier wrong answer.** | 2 | Qwen q23, q47 | P5 |
| L | **Model too slow, or too many steps** (gpt-oss on this Mac). | 2 | gpt-oss q20, q47 | P2, P8 |

**The pattern.** Small models fail on mechanics: Chiron's internal query format, its rule
names, which group a filter goes into, inclusive limits, dataset ids and field ids. Big
models fail where the tools give them no correct way to say something (A, D) or accept a
mistake silently (B). The English in the questions is not the problem.

---

## 2. Targets for the re-run

These are what we're aiming for. The re-run will measure whether we hit them.

| Measure | Target |
|---|---|
| Opus 5.5, Sonnet 5.5, Haiku 5.5 (all on Bedrock), all 236 questions | every answer right |
| Answers stating a figure that didn't come from Chiron | 0 |
| Timeouts caused by a Chiron step | 0; every Chiron step under 30 s on 100k |
| Every answer | says exactly what it counted, in Chiron's own words |

"Never wrong" can't be promised for questions that really are ambiguous. "Never silently
wrong" can. Every answer will either be right, show exactly what it counted so a
mismatch is obvious, or say which reading it chose.

---

## 3. The plan

### P0. Baseline and test sets, before changing anything

**0.1 Haiku 5.5 baseline.** Run the current system on the 49 questions with Haiku 5.5, so
the improvement can be measured. Rough cost: under $1.

**0.2 Robustness sets.** These are written now and kept away from development, so we
can't tune the system to them.
- **Re-phrased set:** 3 versions of each of the 49 questions (147 in all), with the same
  checks as the originals:
  - casual: "how many ppl had 3+ ER visits"
  - clinical: "patients with ≥ 3 emergency department encounters"
  - indirect, or with typos and units: "diabetic-range A1c", "a1c over 6.5 %"
- **New set:** about 40 new questions on the same data, with answers worked out by
  SQL in `bench/truth.py`. They use other labs, conditions and numbers, plus "under",
  "between", "never", "at most", "exactly", date ranges, lists, top-N and report
  actions. They run only at the end.
- **Fair readings:** a question with two fair readings accepts both, and the answer must
  say which one it used.

**0.3 Offline tests.** A test harness that needs no model: a query description goes in,
and the resulting Chiron count is compared with the SQL answer. Every change in P1–P6
gets tests here. It follows the same approach as `tests/ask_trace.py`.

### P1. Strict tools that explain mistakes (small change, big effect)

- Give every tool argument an exact schema: enums for transformation types and count
  rules, and no unknown fields allowed.
- **An unknown parameter returns an error that names the right way.** Example: "`set_id`
  is not a field; to put a filter in its own group use …". Today these are silently
  ignored (cause A).
- **Accept the usual spellings of count rules and correct them:** `at_least`, `>=`, `min`
  become `at least`, and the reply says so (cause B).
- Check every `cohort_def` with Chiron's own cleaner before counting. Never count a
  malformed or empty definition; an empty one would match all 100,000 patients.
- Rewrite unhelpful Chiron messages. "Please enter a minimum or maximum value" becomes
  "to ask whether a date or number is present, use `has_value`".

### P2. One simple query tool: `chiron_query` (the core of the plan)

The model describes the question in plain terms. Chiron MCP turns that into Chiron's
query format, checks it and counts. One call replaces the 5–15 low-level steps needed
today. Draft of what the model sends:

```json
{
  "dataset": "Synthea 100k",
  "start_from": "g3",
  "where": [
    {"lab": "HbA1c", "op": ">=", "value": 6.5},
    {"lab": "HbA1c", "op": "<", "value": 5.7, "separately": true},
    {"condition": "asthma"},
    {"condition": "COPD", "never": true},
    {"count_of": {"encounter": "emergency room admission"}, "op": ">=", "value": 3},
    {"field": "death date", "op": "has_value"},
    {"condition": "hypothyroidism", "date_between": ["2010-01-01", "2015-12-31"]}
  ],
  "match": "all",
  "show": {"count": true}
}
```

`start_from` names a group kept from an earlier answer (P5).

What Chiron MCP does with it:
- **Resolves** every word to a field and its value variants, using the dictionary (P3).
- **Gives each condition its own group** (criteria set). Patient-level AND/OR/NOT then
  work, and "both asthma and COPD" no longer turns into "one record that is both"
  (cause A). It uses Chiron's own functions, including the entry move the UI uses for
  drag and drop, so the result is exactly what the Chiron UI would build.
- **Keeps a lab's name and value on the same record** ("HbA1c ≥ 6.5" means one HbA1c
  result of at least 6.5).
- **Handles real comparisons:** >, ≥, <, ≤, =, between, has value, is empty. Strict
  limits are turned into Chiron's inclusive ones correctly for decimal values (cause
  D). Each number type gets a test against SQL.
- **"At least N times"** becomes a valid count rule (cause B).
- **Does set arithmetic itself** ("both", "either", "only A"), so the model never
  estimates.
- **Returns** the count, Chiron's own plain-English description of the cohort, the
  exact values it matched (for example "Asthma, ASTHMA, asthma, Asthm"), any
  assumptions, and a name for the group (P5).
- **Says plainly when something can't be expressed**, for example timing between two
  events on a dataset without event rules (q15). It never quietly drops a condition.

The same tool also gives the other answer shapes, so one call covers most questions:
- `"show": {"breakdown": ["gender", "ethnicity"]}`
- `"show": {"top": 5, "of": "condition"}`
- `"show": {"list": ["birthdate", "death date", "city"], "limit": 10}`
- `"show": {"stats": ["min", "max"], "of": {"lab": "HbA1c"}}`

### P3. A dictionary for each dataset, and resolvers

- **Dataset resolver.** "Synthea 300", "synthea small", "the 100k" and similar map to
  the right dataset id. An unknown name ("MIMIC-IV") returns "there is no dataset called
  MIMIC-IV; you can use: …", and the model must not answer from another dataset (causes
  G, I).
- **Field dictionary.** Built automatically from Chiron's own metadata (names,
  collections, types, units, descriptions), plus a short curated list per dataset in
  `chiron-mcp/dictionaries/<dataset>.yaml`. Examples:
  - "ER visit" → encounter "Emergency room admission"
  - "visit cost" → total claim cost (with a note that base cost also exists)
  - "died" → death date has value
  - "HbA1c" or "A1c" → its exact lab name, in %
  - "TSH" → Thyrotropin
  - "COPD" → chronic obstructive pulmonary disease

  It describes the data, never the benchmark answers (causes H, J).
- **Value resolver.** Matching ignores case, spacing and punctuation. It also handles
  values cut off by the data load ("Major depressive disorde") and close misspellings.
  It returns every variant it matched, with counts. If two different things match, it
  asks instead of guessing.
- Ask's dataset summary gets a short version of the dictionary.

### P4. Results and reports at the same level

- **`chiron_results_table`** takes a group or a query plus plain columns, for example:
  `["birthdate", "gender", {"has": {"medication": "metformin"}}, {"max": {"lab": "HbA1c"}}]`.
  - Lab and medication columns use Chiron's column-level filter (`prefilter_value`),
    not an extra cohort filter, so q37 keeps all 6,914 patients.
  - It sorts and paginates the same way.
- **`chiron_report`** covers save, rename, make public, change filters, run and delete,
  by name.
  - "Change filters" updates the saved report itself (q43).
  - Delete needs the exact name.
- **After every write, Chiron is read back** and the tool returns what is actually
  there: rows, columns and the filter description. The model reports what is there,
  not what it intended.

### P5. Keep conversation groups on the server

- Every query result gets a short name ("g1", "g2", …) stored with the conversation. Ask
  already keeps the previous cohort, and this extends that.
- Follow-ups use `start_from` instead of rebuilding the definition. The prompt tells the
  model which group "them" most likely means, and the answer says which one it used
  (cause K).

### P6. Speed, so nothing times out

- **chiron-ask database:** raise Postgres shared memory from 64 MB to 1 GB. Add indexes
  on the observation lookup tables (description, value, units), then ANALYZE. This is
  only the local benchmark copy; for deployments it becomes a documented setting.
- **Cache** value lists and breakdowns for each conversation.
- **Time limit per Chiron call** (for example 60 s). When an answer is stopped, its
  database queries are cancelled too. This moves the benchmark's leftover-query
  watchdog into Chiron MCP itself.
- **Target:** every Chiron step under 30 s on 100k (cause E). gpt-oss on this Mac stays
  slow, and fewer steps help it most (cause L).

### P7. Check the answer before it is shown

- **Number check.** Every figure in the answer must appear in a tool result, or come
  from the server's own arithmetic. If not, the model gets one automatic retry with the
  problem named; after that the answer shows a warning. This builds on the Oct 13
  answer-trace checks (`trace.py`).
- **Every answer** includes Chiron's description of what was counted.
- **A question about a dataset that doesn't exist** gets a clear "not available" answer
  (cause G).

### P8. Short instructions and a small tool set for small models

- Rewrite the Ask instructions. They're 8,600 characters now. The new version has a
  short core plus one worked example per question type: count, both/either/never,
  over/under, at least N times, date range, breakdown/top-N, list, Results, report
  actions, other dataset, and can't-do.
- **Ask shows small models a short tool list by default:** datasets, dictionary lookup,
  `chiron_query`, Results, reports, open in Chiron. The 18 low-level tools stay
  available to MCP clients and strong models. A setting lets us benchmark both ways.

---

## 4. Order of work, with a check after each step

| Step | Work | Check before moving on |
|---|---|---|
| 0 | Baseline (Haiku on the 49) and the robustness sets | Baseline numbers recorded; sets saved and not looked at again |
| 1 | P1 strict tools | Offline tests; Haiku on the 49 |
| 2 | P2 `chiron_query` + P3 dictionary and resolvers | Offline tests against SQL for every operator; Haiku and Qwen on the 49 |
| 3 | P4 Results/reports + P5 groups | Offline tests; Haiku on sets 15–19 |
| 4 | P6 speed | Every Chiron step timed on 100k; no step over 30 s |
| 5 | P7 answer checks + P8 instructions and tool list | Haiku, Qwen and gpt-oss on the 49 |
| 6 | **Final benchmark** | All models × (49 + re-phrased + new); AWS CloudTrail check; LangSmith export; PDF |

Every in-between check uses Haiku. It's cheap, it's the target, and if Haiku gets it
right the bigger models should too. Opus is spot-checked for regressions.

**Final benchmark cost, roughly:** 236 questions per model.
- Haiku 5.5: about $1
- Qwen3-Next: about $2
- Opus 5.5 (Bedrock): about $20
- Opus 4.6: about $20
- Sonnet 4.6: about $20
- Opus 5.5 (Claude account): $0
- gpt-oss-20b: $0, but many hours on this Mac

Running the larger models on only the 49 plus the new questions about halves their cost.

---

## 5. Where the code goes, and the risks

- **chiron-mcp:** a new branch off `mcp-hosted`.
  - New code: `chiron_mcp/query.py` (the P2 compiler), `chiron_mcp/dictionary.py` and
    `dictionaries/`.
  - Changes: `server.py` (P1, and new tools P2/P4), `webapp.py` (P5, P7, P8).
  - New tests: `tests/query_*.py`.
  - The hosted deployment (genoquery) stays untouched until you approve a merge.
- **chiron-benchmark:**
  - `questions/` gets the re-phrased and new sets.
  - `bench/truth.py` gets the new facts.
  - A setting to run with the new or old tool set.
- **Risks, and how they are handled:**
  - **Tuning to the 49 questions.** The new set is written first and only run at the
    end, and the dictionary describes data, not questions.
  - **Strict limits on decimals.** Tested against SQL for each number type.
  - **A question `chiron_query` can't express.** It says so, and strong models can
    still use the low-level tools.
  - **The local database changes in P6** affect only the chiron-ask benchmark copy, not
    the data itself.

## 6. Decisions

1. **Done (2026-10-26):** the Oct 13 answer-trace work was committed on `mcp-hosted`
   (157c49b). This work happens on the `ask-reliable-queries` branch.
2. **Yes:** small models in Ask see only the short tool list by default. The full list
   stays for MCP clients and strong models.
3. **Decided (2026-10-26):** the final benchmark has three models, all on Bedrock: Opus 5.5,
   Sonnet 5.5 and Haiku 5.5. Qwen3-Next, gpt-oss and the 4.6 models are dropped. The run
   covers all 236 questions (the 49, the three re-phrased sets and the 40 new ones).
4. **Decided:** no gpt-oss.
5. **The benchmark's purpose (the user's words):** every model answers every question
   correctly, however it is phrased and however big the dataset is. The benchmark then compares
   **cost and time**. A wrong answer is a bug to fix in Chiron MCP for every model, never a
   tuning for one model and never a hard-coded answer.

## 7. Progress

- **Step 0, started 2026-10-26.**
  - 0.1: Haiku 5.5 baseline, run `20261026-062329` (chiron-benchmark).
  - 0.2: re-phrased sets `questions/synthea-100k.rephrased-{a,b,c}.json`, written by
    `scripts/make_rephrased.py` (147 questions). New set `questions/synthea-100k.new.json`
    (40 questions, n01–n40), with answer keys from `bench/truth.py` `build_new`.
  - The benchmark runs any set: `./bench.sh run --questions rephrased-a`, or
    `question_set` in `/api/bench/start`.

- **Step 0 done.** The Haiku 5.5 baseline (`20261026-062329`) got **37/49**, cost $0.10 and had a
  typical answer time of 14 s. Its misses: `at_least` (q07–09), "over" (q29–31, q34), one spelling
  variant (q25), the highest-HbA1c column (q37, q38), a timeout (q33) and the wrong follow-up
  group (q19).
- **Steps 1 and 2 merged** (P1 strict tools, P2 `chiron_query`, P3 dictionary). Haiku
  (`20261026-070501`) got **45/49**, cost $0.07 and had a typical time of 10.6 s.
  `tool_check.py` matches every SQL answer key: 27 counts, plus the follow-up group, the refusal
  of an unknown dataset, a value range and a top-5 list.
- **Steps 3–6 and 8 merged.**
  - P4: Results, reports and the query builder from plain columns, with a column's
    `aggregation_criteria_set` and an "at least 0" group. `tool_check_writes.py` passes q37–q46.
  - P5: the conversation's groups are listed with every follow-up.
  - P6: a value cache refreshed by the ETL log; `client_connection_check_interval` and
    `statement_timeout` on warehouse connections; `python -m chiron_mcp.query --warm`.
  - P8: the short tool list and plain instructions by default; a dataset summary in plain words
    with real values and lab units; identifying values are never cached.
- **P7** (number check with one retry) is decided after the next Haiku run.
- **P7 merged** (an answer whose lead figure no tool returned is held back and checked once).
  Haiku `20261026-074734`: 47/49. After the list/range fix, Haiku `20261026-080125`:
  **49/49**, no timeouts, typical answer 7.7 s, $0.039 for all 49.
- **Next:** the three Bedrock models on the 40 new questions (first pass, untuned), then the
  re-phrased sets; fix every wrong answer in Chiron MCP for all models; then the final run of
  all 236 questions, one model at a time, to compare cost and time.
- **Held-out set, first pass, untuned** (run `20261026-081837`, the three Bedrock models side by side).
  After three grader fixes (below): **Opus 5.5 39/40, Sonnet 5.5 39/40, Haiku 5.5 37/40**.
  - n28, all three: Postgres ran out of shared memory for parallel workers ("could not resize
    shared memory segment"), with three big lab queries at once on Docker's 64 MB /dev/shm.
    All three said they could not get the figure; none made one up. Fixed twice: `shm_size: 1g`
    in both compose files (applied to `chiron-ask-db-1`), and `chiron_mcp/pg.py` runs a query
    that failed this way once more with parallel workers off (`tests/shared_memory_retry.py`).
  - n38, n39, Haiku: put only the COPD patients with an FEV1/FVC result in Results. The column
    came back as "observation value", so nothing said it held only FEV1/FVC. chiron_query now
    returns `columns_in_words` and says a summary column never removes patients.
  - Grader fixes, all in chiron-benchmark `bench/score.py`. They change 3 of 722 stored answers,
    each from wrong to right, and nothing else:
    - "(payer = medicaid)" was read as a worked sum;
    - "Synthea 300" was taken as the lead figure;
    - "30-day" was taken as a count;
    - "there's no UK Biobank dataset" was not seen as a refusal.
- **n28 traced to its causes and fixed** (the Desktop session hit its limit on this; continued in a
  terminal session the same morning).
  - Chiron's own warehouse engines never had the 240 s statement timeout: Chiron passes its own
    libpq options (search_path + CHIRON_PG_CONN_OPTIONS_SITE, default 30 min), which replace the
    URL's. A stopped question's query ran on for 5 minutes. Now `CHIRON_PG_CONN_OPTIONS_SITE`
    carries the timeout and the client check; `tests/pg_options.py` checks it on Chiron's engine.
  - A lab's range went through Chiron's `get_statistics`: eight statements, and min, max and
    average each gather every value into one JSON array (min and max twice, for the histogram).
    Systolic blood pressure, 3.6 million readings: 13.5 minutes alone (max alone 205 s). The range
    now comes from one aggregate over the FROM and WHERE of Chiron's own query builder, with the
    lab kept by Chiron's prefilter predicate instead of a cohort group: 14.6 s cold, and the
    numbers (min, max, average to 3 significant digits, result and patient counts, missing
    counts) equal `get_statistics` on every lab where it can finish. Ranges are kept on disk by
    the cohort's meaning (entry ids ignored) and the user's subject permissions, refreshed by the
    ETL log, with a lock so three models asking at once run the query once; `warm_ranges` fills
    the common labs and vitals at warm-up (73 s for Synthea 100k). A cohort group that only
    repeats the range's lab (`where` the lab and the range of it, as Haiku writes it) is left out
    of the query: with the prefilter it changes nothing, and Chiron checked it with another pass
    (196 s). `tests/range_cache.py`.
  - Three models at once on the old form took 136–250 s each (51 s alone): the benchmark's
    grader also read "6,208.4" as 208.4; fixed (`bench/score.py` decimals), changing 1 of 737
    stored grades, Opus's n28 from wrong to right.
  - **n28 re-tested on all three at once** (run `20261026-102615`): right on every model, 10–15 s
    wall, Chiron step 0.5–3.4 s. With n38–n40 (run `20261026-084021`) that makes every held-out
    question right for every model.
- **Re-phrased sets** (a, b, c; 49 questions each, all three models at once): started with set a,
  run `20261026-102704`.
  - **Set a** (run `20261026-102704`): Opus 49/49, Sonnet 49/49, Haiku 48/49, after two faults
    outside the models were put right:
    - The grader read "3 or more ER visits" as the lead figure 3 (one Sonnet answer: "Of the
      19,713 patients with 3 or more ER visits, 1,224 have a recorded death date"). `bench/score.py`
      now skips "N or more / N+" thresholds like "at least N"; 1 of 890 stored grades changed.
    - The harness deleted a user's reports before every conversation that saves reports (added
      2026-10-26 for the held-out set), so "what reports do I have? ... change the latest" always
      started from none, for all three models. `bench/runner.py` keeps the reports for a
      conversation that reads them. s16+s17 were re-run (`20261026-104616`) and swapped in.
    - Haiku's one miss: asked to change the report's filters to women, it counted the women and
      said it could not change a report. On the way it had found three same-named public reports
      (the three models' own, side by side) and `chiron_run_saved_report` had crashed on a Chiron
      accessor. Fixed in Chiron MCP for every model: `chiron_run_saved_report` runs again
      (`get_definition`); a report name shared with other users' public reports resolves to
      your own (`find_report`); the listing says whose each report is ("owner": "you" / "another
      user (public)", with "yours" and "others_public" counts and a note); and a count that
      started from a report comes with the exact call that changes that report, so the model
      has the recipe in hand when the follow-up asks for it. `tests/report_names.py`.
  - With the report fixes live, Haiku's set-a report follow-up (`20261026-110506`) and Sonnet's
    set-b one (`20261026-110607`) both change the report and give 4,320; swapped in. **Set a:
    49/49 for all three. Set b** (run `20261026-104801`): **49/49 for all three** (Sonnet's one
    miss was the same report follow-up, before the fix).
  - Three models at once triple the heavy Chiron steps: breakdown by gender and ethnicity
    within a group 110 s, top-5 conditions within a group 147 s, sorting Results by a summary
    column 63 s, a count rule over visits 35–44 s. All under the limit; the final run is one
    model at a time. Typical answer 7.8–8.2 s per model.
  - **Set c** (run `20261026-110737`): first grades Haiku 47/49, Sonnet 47/49, Opus 48/49; none
    of the misses was a wrong figure from Chiron:
    - q15 (the 90-day rule, "say it cannot be done"): Sonnet said it cannot be done and gave the
      figure Chiron can count, labelled as such; the grader took "within 90 days" as the lead
      figure. `bench/score.py` now ignores a figure with a unit (days, months, mg/dL, %...) as
      the lead; 1 of 1,204 stored grades changed.
    - q35: the re-wording had turned "which datasets can I query" into "what data can I query
      here", so no model named Synthea 300. Restored "datasets" in
      `questions/synthea-100k.rephrased-c.json` (backup in state/); re-run below.
    - q36, Haiku: "Twenty patients in Synthea 300 have ... asthma", right, in words. The
      instructions now say "the figure in digits (20, not 'twenty')", and the answer check
      holds back an answer that states no figure in digits although a tool returned a count.
  - With the digits check live and "datasets" restored, set c's s14 re-run (`20261026-112633`)
    is right for all three, swapped in: **set c 49/49 for all three.** So every re-phrased
    question (147) and every held-out question (40) has been answered right by Opus 5.5,
    Sonnet 5.5 and Haiku 5.5.
- **Final run** `20261026-112756` (all 236 questions, one model at a time, 11:27–14:07 UTC,
  Chiron MCP at 5dcf4b5, caches warmed first): after four grader fixes (years in a date span
  and numbers in names such as "type 2" are not the lead figure; "isn't one of the datasets" and
  "can't build that table" are refusals; a count of 0 may be said in words), which flip exactly
  the five grades they were written for out of 1,918 stored answers: **Opus 5.5 236/236,
  Sonnet 5.5 235/236, Haiku 5.5 235/236.** The two misses are the models' own: Sonnet counted
  from a report instead of restricting its filters (b43); Haiku ran a MIMIC-IV question on
  Synthea 100k without saying MIMIC-IV is absent (a48). Nothing re-asked, nothing swapped.
  Cost $5.55 / $2.57 / $0.18, median 8.4 / 6.9 / 7.7 s. CloudTrail: 1,431 calls, all matched.
  `results/runs/20261026-112756/AUDIT.md`.
- **A fresh held-out set, written after every fix** (`questions/synthea-100k.fresh.json`, f01–f40,
  keys from `bench/truth.py build_fresh`): the held-out n01–n40 had been run four times and n28
  drove the range fix, and a/b/c re-word the 49 the fixes were tuned on, so a set no model has
  seen is the real test. It asks for things no earlier set asked (lay and class names such as
  blood sugar, statin, ACE inhibitor and insurer; a month-level window; the date a lab was
  taken; payer and cost on one visit; organisation and provider rankings; study group B;
  medication cost; averaged labs; a one-to-two count rule; names and SSNs that are not there).
  Rule: run once, no re-runs, no swaps; a fix made after it needs another fresh set.
  - Building its keys found a Chiron MCP bug: the spelling-variant rule folded "prov-14" into
    "prov-147" (a short value with exactly one *larger* group starting with it), doubling four
    providers' counts in rankings. A cut-off spelling must now be the start of exactly one
    longer name and at most a tenth as common (real cut-offs are below 0.3%). Commit 0c3ed50,
    `tests/value_groups.py`; value caches rebuilt. Also f3e123c: the note with a count started
    from a report now says to make the update call when a change was asked for.
  - Comparison decided by the user: the three PHI-safe Bedrock lanes plus **Opus 5.5 on the
    local Claude account** (lane `opus-5-5`), which also runs the 236 known questions
    afterwards, to be merged with the final run. Fresh run: `20261026-142345`, four lanes one at
    a time, Bedrock first.

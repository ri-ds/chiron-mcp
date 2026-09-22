# chiron-mcp

An [MCP](https://modelcontextprotocol.io) server that exposes **Chiron**, a cohort-discovery
platform for human-subject research data, to an LLM client such as Claude.

Ask *"how many asthma patients are there, and what were their diagnosis dates?"* and the model
finds the right variable, builds the cohort, counts it, and pulls the rows, without anyone
writing SQL, and without bypassing Chiron's own access rules.

```
"How many patients in this dataset?"          -> 300
"What conditions are most common?"            -> obesity 64 · hypertension 57
"Build a cohort of asthma patients"           -> cohort_def
"How many is that?"                           -> 20
"Show me their diagnoses and dates"           -> 20 records with diagnosis dates
```

---

## Quickstart

Everything is bundled: Chiron itself, 300 synthetic patients, the MCP server, a chat
page, and the Chiron UI with an **Ask** tab. Nothing external is required beyond Docker,
Python 3.12+, Node 20+, and the [Claude Code CLI](https://claude.com/claude-code) logged in.

```bash
git clone https://github.com/rohzzn/chiron-mcp.git
cd chiron-mcp
./install.sh                                  # python venv + dependencies
docker compose up -d                          # Postgres warehouse
.venv/bin/python scripts/bootstrap_demo.py    # data dictionary + real ETL + demo users
./scripts/run_all.sh                          # starts all three servers
```

Then open **<http://localhost:5173>** and log in as **`demo` / `demo`**.

The first `run_all.sh` installs the UI's npm dependencies, which takes a few minutes.
After that it starts in seconds.

### What you get

| URL | What |
|---|---|
| **http://localhost:5173** | **Chiron UI with the Ask tab** — start here |
| http://localhost:8001 | Chiron itself (server-rendered pages, admin) |
| http://localhost:8900 | The Ask chat page on its own |

In the UI, **Ask** sits in the header beside Aggregate. Type a question and you get an
answer with real figures, markdown tables, charts, and a button through to Chiron's
filter builder:

> What are the most common conditions?
> How many patients have asthma?
> Show the top 10 medications as a chart
> Build an asthma cohort and open it in Chiron

Questions take roughly 25 to 60 seconds, because the model makes several Chiron tool
calls. Each one shows as a chip while it works.

### The demo data

Four datasets, the useful one being **300 synthetic patients** (Synthea) with conditions,
encounters, observations, medications and procedures:

| Dataset | Subjects | Content |
|---|---|---|
| `synthea-small` | 300 | Synthetic clinical records. The one to demo with |
| `dataset2_stored` | 6 | Chiron's own test fixture |
| `dataset1_stored` | 2 | Test fixture, the only one with event-date rules configured |
| `dataset3_stored` | 0 | Dictionary only, no rows |

Real figures out of the box: obesity 64, hypertension 57, depression 35, asthma 20.

Three demo accounts, all with password `demo`: **`demo`** (de-identified),
**`demo_agg`** (aggregate only, refused row-level data), **`demo_admin`** (PHI, staff).

### Pointing at a real deployment

Skip `bootstrap_demo.py` and set `CHIRON_MCP_METADATA_DB` and `CHIRON_MCP_WAREHOUSE_URL`
at your own Chiron. See [Configuration](#configuration).

## Table of contents

- [Quickstart](#quickstart)
- [What Chiron is](#what-chiron-is)
- [What this server does](#what-this-server-does)
- [Why it runs in-process](#why-it-runs-in-process-and-not-over-chirons-rest-api)
- [Install](#install)
- [Setup guide for an AI agent](#setup-guide-for-an-ai-agent)
- [Configuration](#configuration)
- [The tools](#the-tools)
- [How a query actually gets built](#how-a-query-actually-gets-built)
- [Access model and safety](#access-model-and-safety)
- [Known limits](#known-limits)
- [Troubleshooting](#troubleshooting)
- [Project layout](#project-layout)

---

## What Chiron is

Chiron (`is4r-chiron`) is a reusable Django application for exploring research and clinical
data, with a focus on human-subject and longitudinal datasets. Researchers use it to build
patient cohorts and pull reports without writing queries.

Its defining idea is that **the data dictionary is database rows, not a config file**:

| Layer | Holds | Reached via |
|---|---|---|
| **Metadata database** | The data dictionary (`Dataset` → `Collection` → `Concept`), plus users, access grants, saved reports and ETL logs | Django ORM |
| **Warehouse** | The actual subject data, one Postgres **schema per dataset** | SQLAlchemy only |

The warehouse's tables and columns are **generated at runtime from the dictionary rows**, not
migrated. The two databases cannot be joined, because there is no Django database router, so the ORM
describes the *shape* of the data while SQLAlchemy queries the data itself.

A researcher's work is expressed as two JSON documents:

- **`cohort_def`**: which subjects qualify
- **`table_def`**: which columns to show

Chiron compiles those into a single SELECT against the warehouse, injecting the user's
subject-visibility filter into the WHERE clause. A saved "report" is just a stored
`cohort_def` + `table_def` pair.

## What this server does

It exposes that machinery as **16 MCP tools**, so cohort building can happen in conversation.

It is **stateless by design**: every tool takes a `cohort_def` and returns one, so the model
holds the working query and Chiron holds none of it. No tool writes a snapshot, so using this
server never disturbs a researcher's saved workspace in the Chiron UI.

It is **read-only**. Nothing here runs an ETL, alters a schema, or saves a report.

## Why it runs in-process, and not over Chiron's REST API

Three findings from reading the Chiron source, in order of how much they constrain the design:

**1. The query API cannot accept a cohort you give it.**
`QueryToolsViewSet._get_cohort_def` (`chiron/api/viewsets/query_tools.py:204-214`) discards any
supplied definition and returns the caller's *active server-side snapshot*, despite a docstring
promising otherwise. An HTTP wrapper would therefore have to overwrite a researcher's live
workspace on every turn, and `CohortDefSnapshot.save` deletes their redo stack
(`chiron/models/user_models.py:189-193`).

**2. Chiron has no token authentication.** No `rest_framework.authtoken`, no JWT, no OAuth, no
API key, no service-account concept, and no login *endpoint*. `rest_framework.urls` is commented
out. `REST_FRAMEWORK` is unset, so DRF's stock defaults (Session + Basic) apply by accident.

The result is an API split down the middle. HTTP Basic works on the metadata endpoints and is
rejected on **every endpoint that queries data**, because those viewsets set
`authentication_classes = [CsrfExemptSessionAuthentication]`, which *replaces* DRF's default list
rather than extending it:

| Basic auth works | Session cookie only |
|---|---|
| `/api/v2/auth/`, `/api/v2/dataset/` | `query_tools/` (count, preview, export) |
| `{ds}/concepts/`, `{ds}/collections/` | `cohort_def/`, `table_def/`, `analysis_def/` |
| `{ds}/concept_categories/` | `reports/`, `report_tools/`, `analysis_tools/` |

**3. The operator surface has no HTTP API at all.** ETL logs, dictionary validation and the
schema visualiser exist only as staff HTML pages and management commands.

So the server calls Chiron's own Python in the same interpreter, binding to one Django user and
resolving that user's real `ChironUser` per dataset. Chiron's permission logic does the filtering.

## Install

Requires Python 3.12+, a Chiron checkout, and network access to a Chiron metadata database and
warehouse.

```bash
git clone https://github.com/rohzzn/chiron-mcp.git
cd chiron-mcp
./install.sh
```

`install.sh` creates `.venv` and installs `mcp` plus Chiron's own base requirements. It finds
Chiron automatically when `is4r-chiron` sits beside this project or is pip-installed; otherwise
set `CHIRON_MCP_CHIRON_SRC`.

Then confirm the deployment resolves, before touching any MCP client:

```bash
CHIRON_MCP_USERNAME=<user> .venv/bin/python scripts/harness.py
```

It prints the Chiron source, both database locations, and every dataset that user can reach,
including the ones it refuses and why. **If this doesn't work, nothing else will.**

### Register with Claude

Copy the block from `claude_mcp_config.example.json` into your Claude config, filling in
absolute paths. On macOS that file is
`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "chiron": {
      "command": "/abs/path/to/chiron-mcp/.venv/bin/chiron-mcp",
      "env": {
        "CHIRON_MCP_METADATA_DB": "/abs/path/to/chiron_metadata.sqlite3",
        "CHIRON_MCP_WAREHOUSE_URL": "postgresql://user:pass@localhost:5432/chiron",
        "CHIRON_MCP_USERNAME": "your-service-user",
        "CHIRON_MCP_MAX_ACCESS_LEVEL": "deid"
      }
    }
  }
}
```

Restart the client. Sixteen `chiron_*` tools appear.

### Grant the service user access

The server **never** creates access records. A Django user needs a `ChironUser` row per dataset:

```bash
.venv/bin/python scripts/grant_access.py --user <user> --datasets <dataset> --level deid
.venv/bin/python scripts/grant_access.py --list
.venv/bin/python scripts/grant_access.py --user <user> --datasets <dataset> --revoke
```

## Setup guide for an AI agent

Written for an AI assistant setting this up on someone's machine. Every step has a check.
Do not skip a check, and do not continue past a failed one.

> **Chiron and its UI are already vendored** at `vendor/is4r-chiron` and
> `vendor/is4r-chiron-ui`. Do not clone or `pip install` them. The `chiron` package on
> PyPI is an unrelated DNA basecaller, and the real repository is behind organisation SSO.

**First decide which path you are on. Ask the user if it is not obvious.**

| | Use when |
|---|---|
| **Path A — bundled demo** | They want it working. Ships 300 synthetic patients. Needs nothing external |
| **Path B — their own Chiron** | They already run Chiron and want to query their real data |

Path A is the default. Take Path B only if the user says they have a deployment.

---

### Path A: the bundled demo

```bash
./install.sh
docker compose up -d
.venv/bin/python scripts/bootstrap_demo.py
./scripts/run_all.sh
```

**Check:** `bootstrap_demo.py` ends with `Demo ready. 4 dataset(s) queryable.` and lists
`synthea-small: 300 subjects`. Then `run_all.sh` prints three URLs and stays running.

**Check:** `curl -s -o /dev/null -w '%{http_code}' http://localhost:5173/` returns 200.

Tell the user to open <http://localhost:5173>, log in as **`demo` / `demo`**, and click
**Ask**. You are done. Everything below is Path B.

Requirements, which you should confirm first: Python 3.12+, Node 20+, Docker running, and
the Claude Code CLI installed and logged in (`claude --version`). The first `run_all.sh`
spends a few minutes on `npm install`.

---

### Path B: point at an existing Chiron deployment

Same repo, but skip `bootstrap_demo.py` and aim the two database variables at their
deployment. Do **not** run `bootstrap_demo.py` on Path B: it builds a separate demo
database and never touches theirs, but running it wastes several minutes.

#### B1. Gather four things from the user

1. The **metadata database** — usually a SQLite file holding datasets, users and access
   grants. In a Docker deployment it is often a bind mount; look in the compose file for a
   path mapped to `db.sqlite3`.
2. The **warehouse connection string** — `postgresql://user:pass@host:port/dbname`. Also in
   the compose file, as `CHIRON_SQL_ALCHEMY_CONNECTION_STRING`. If Chiron runs in Docker it
   may say `host.docker.internal`; from outside the container that is `localhost`.
3. The **Django username** the server should act as.
4. The **URL of their Chiron UI**, for hand-off links.

If you cannot get 1 and 2, stop and ask. Do not guess a path or a password.

#### B2. Verify before configuring anything

```bash
CHIRON_MCP_USERNAME=<user> \
CHIRON_MCP_METADATA_DB=/path/to/their_metadata.sqlite3 \
CHIRON_MCP_WAREHOUSE_URL=postgresql://user:pass@localhost:5432/chiron \
.venv/bin/python scripts/harness.py
```

**Check:** it ends with `N dataset(s) reachable by this identity`, N at least 1.

Lines marked `[refused]` are not failures; they mean that user has no access record for
that dataset, which is correct behaviour. If **every** dataset is refused, see B3.

If this fails, nothing else will work. Fix it here.

#### B3. Grant access only if asked

```bash
.venv/bin/python scripts/grant_access.py --list
.venv/bin/python scripts/grant_access.py --user <user> --datasets <dataset> --level deid
```

This writes to **their** metadata database. Tell the user which account and which dataset
before doing it, and get their agreement. Never pick a superuser: the server refuses to
start as one in analyst mode, and that refusal is deliberate.

#### B4. Run against their deployment

```bash
export CHIRON_MCP_METADATA_DB=/path/to/their_metadata.sqlite3
export CHIRON_MCP_WAREHOUSE_URL=postgresql://user:pass@localhost:5432/chiron
export CHIRON_MCP_USERNAME=<user>
export CHIRON_MCP_UI_URL=http://their-chiron-ui        # for hand-off links
export CHIRON_MCP_ALLOW_SAVE=1                         # enables "open this in Chiron"

.venv/bin/python -m chiron_mcp.webapp                   # Ask chat at :8900
```

`run_all.sh` honours the same variables, but on Path B do not start `serve_chiron.py`:
they already have a Chiron running, and a second one on `:8001` would confuse everyone.
Either run only the Ask server as above, or add the **Ask** tab to their own UI following
[docs/chiron-ui-integration.md](docs/chiron-ui-integration.md).

**Check:** ask the chat "how many patients are in <their dataset>?" and confirm with the
user that the number matches what Chiron shows.

#### B5. Also register with Claude Desktop, if they want it there too

See [Register with Claude](#register-with-claude). Use the same variables.

---

### If something goes wrong

| Symptom | What it means | Fix |
|---|---|---|
| `Could not find the Chiron source tree` | Discovery failed | Set `CHIRON_MCP_CHIRON_SRC` to the directory containing `chiron/` |
| `No Django project settings at ...` | Wrong host project | Set `CHIRON_MCP_PROJECT_DIR` to the directory with `manage.py`, and `CHIRON_MCP_BASE_SETTINGS` if its settings module is not `project.settings` |
| `has no ChironUser on dataset` | Working as designed | Grant it with `scripts/grant_access.py`, with the user's agreement |
| `is a superuser. Refusing to start` | Working as designed | Use a dedicated service account |
| `cannot see subject-level data` | The account is `agg` | Correct behaviour. Use `chiron_crosstab` or `chiron_concept_values` |
| `npm install` fails on peer deps | The UI pins eslint 9, a plugin wants 8 | `run_all.sh` already passes `--legacy-peer-deps`; use that flag if installing by hand |
| `You must set settings.ALLOWED_HOSTS` | Running Django with `DEBUG=False` | Already handled in `chiron_mcp/django_settings.py`; make sure you launch through `scripts/serve_chiron.py` |
| Tools missing after restart | Config not loaded | Check the JSON parses, paths are absolute, and you edited the right file |
| `Server disconnected` in the client | The client did not honour `cwd` | Set `command` to `.venv/bin/chiron-mcp` and drop `args` and `cwd` entirely |
| `pip install chiron` "worked" but nothing imports | Wrong package | Chiron is vendored here and is not on PyPI |

### What to tell the user when you are done

Which path you took, which Django user the server is bound to, its access ceiling, and
exactly which datasets are reachable. If you granted any access during setup, say so
explicitly including the level: that is a change to their deployment, not just to this tool.

## Configuration

Every setting is an environment variable. Defaults are the conservative end of each choice.

| Variable | Default | Meaning |
|---|---|---|
| `CHIRON_MCP_USERNAME` | **required** | Django user the server acts as |
| `CHIRON_MCP_MAX_ACCESS_LEVEL` | `deid` | Ceiling. Clamps whatever the `ChironUser` actually has, so PHI is opt-in |
| `CHIRON_MCP_DATASETS` | *(all with a grant)* | Comma-separated allowlist |
| `CHIRON_MCP_OPERATOR` | off | Enables the operations tools (also requires `is_staff`) |
| `CHIRON_MCP_ALLOW_SAVE` | off | Reserved; the write tool is not implemented |
| `CHIRON_MCP_MAX_EXPORT_ROWS` | `50000` | Cap on `chiron_export_table` |
| `CHIRON_MCP_CHIRON_SRC` | auto-discovered | The `is4r-chiron` checkout |
| `CHIRON_MCP_PROJECT_DIR` | `<src>/test_project` | The Django host project |
| `CHIRON_MCP_BASE_SETTINGS` | `project.settings` | Host project's settings module |
| `CHIRON_MCP_METADATA_DB` | *(host project's)* | Metadata SQLite |
| `CHIRON_MCP_WAREHOUSE_URL` | *(host project's)* | SQLAlchemy warehouse URL |

See `.env.example`. A superuser is refused in analyst mode; point it at a dedicated service user.

## The tools

### Orient

| Tool | Purpose |
|---|---|
| `chiron_datasets` | Datasets this identity can reach, its access level on each, and why anything is refused |
| `chiron_find_concepts` | Search a dataset's variables by name or description |
| `chiron_describe_concept` | One variable in full, **including the exact field names required to filter on it** |
| `chiron_concept_values` | Distinct values with subject counts |

### Build a cohort

| Tool | Purpose |
|---|---|
| `chiron_edit_cohort` | Apply one transformation; returns the new `cohort_def` plus a plain-English description |
| `chiron_event_rule_options` | Which date/age restrictions apply to a criteria set |
| `chiron_count_cohort` | How many subjects match |

### Hand off to the Chiron UI

| Tool | Purpose |
|---|---|
| `chiron_open_in_ui` | Turn a cohort built in conversation into real Chiron filters and return a link. Requires `CHIRON_MCP_ALLOW_SAVE=1` |

### Get results

| Tool | Purpose |
|---|---|
| `chiron_run_table` | One page of rows; columns are a plain list, no `table_def` authoring |
| `chiron_export_table` | Complete result set, capped, with an acknowledged-count interlock |
| `chiron_crosstab` | Break a cohort down by one or two variables |
| `chiron_saved_reports` | Browse saved reports, or open one's stored definitions |
| `chiron_run_saved_report` | Run a saved report by id |

### Operations

Gated behind `CHIRON_MCP_OPERATOR` **and** a staff account.

| Tool | Purpose |
|---|---|
| `chiron_validate_dictionary` | Run Chiron's own validator. Non-empty means the next ETL will refuse to run |
| `chiron_schema_diagram` | The dataset's shape as a Mermaid ER diagram |
| `chiron_etl_history` | The ETL audit trail, which has no HTTP API |
| `chiron_explain_access` | Why this identity can or cannot use a variable, Chiron's verdicts verbatim |

## How a query actually gets built

The non-obvious part, and the reason `chiron_describe_concept` exists:

**Chiron publishes no machine-readable schema for cohort filter inputs.** A filter is submitted
as HTML *form field names*, and which names apply depends on the variable's processor. The only
source of truth is each processor's `validate_form()` body in `chiron/processors/cohort_def/`.
Those were read directly and transcribed into `chiron_mcp/filters.py`:

| Processor | Required input | Also accepts |
|---|---|---|
| `CohortDefCategory` | `selected_categories` (list) | `exclude_selected` |
| `CohortDefBoolean` | `selected_categories` (list) | |
| `CohortDefNumber` | `cd_numeric_min` / `cd_numeric_max` | `exclude_selected`, `include_null_and_missing` |
| `CohortDefNumberWithCategories` | `cd_numeric_min` / `cd_numeric_max` | `selected_categories`, and the above |
| `CohortDefDate` / `CohortDefDateDeid` | `query_type` | `cd_numeric_min`, `cd_numeric_max`, `days_ago` |
| `CohortDefDetailedAge` | `cd_age_min_year` / `cd_age_min_day` / `cd_age_max_year` / `cd_age_max_day` | |
| `CohortDefText` | `chiron_text_field_selection` (newline-separated) | `ignore_warnings` |
| `CohortDefOntology` | `chiron_ontology_field_selection` | `include_ontology_unknown`, `ignore_warnings` |

So the working sequence is always: **describe the concept, then filter it.**

```python
chiron_describe_concept(ds, "condition__description")   # -> CohortDefCategory
chiron_edit_cohort(ds, [], {
    "type": "add_entry",
    "concept_id": "condition__description",
    "selected_categories": ["Asthma"],
})                                                       # -> cohort_def
chiron_count_cohort(ds, cohort_def)                      # -> 838
```

Date and age restrictions ("diagnosed between 2015 and 2020") are a **second** step on a
criteria set, and take two transformations:

```python
chiron_event_rule_options(ds, cohort_def, entry_id)      # -> which options apply
chiron_edit_cohort(ds, cohort_def, {"type": "create_event_rule", "entry_id": eid})
chiron_edit_cohort(ds, cohort_def, {
    "type": "modify_event_rule", "entry_id": eid,
    "option_type": "date_range", "date_min": "2015", "date_max": "2020",
})
```

Note the key is `option_type`, not `option_id`. `chiron_event_rule_options` asks Chiron directly
rather than relying on a transcription, so it cannot drift from the code.

## Handing a cohort to the Chiron UI

The point of building a cohort in conversation is usually to keep working on it somewhere else.
`chiron_open_in_ui` writes the cohort into Chiron proper and returns a link.

It has two modes, because there are two genuinely different things a user means by "open it in
Chiron".

**`mode="report"` (default, non-destructive).** Saves the cohort and columns as a private Chiron
report and returns `/<dataset>/reports/<id>`. Nothing the researcher currently has open is
touched. They can then use Chiron's own "load as active" to pull it into the builder when ready.

**`mode="workspace"` (destructive).** Writes the cohort and table straight into the user's live
query workspace and returns `/<dataset>/query`, so the link opens the filter builder with the
filters already applied. This is the mode that makes a conversation become a UI page.

Be deliberate about the second one. It mirrors what Chiron's own `load_as_active` does
(`chiron/api_v2/viewsets/report_tools.py:108-133`): it calls `clear_history` on both snapshot
models, so the researcher's current cohort, current table **and their entire undo history on
that dataset** are replaced. Ask before using it.

### Why a link is enough

The React UI's query route fetches `GET /api/v2/<dataset>/cohort_def/`
(`src/store/cohortSlice.ts:319`), and that endpoint returns
`CohortDefSnapshot.get_active_cohort_def(request.chironuser)`. So writing an active snapshot for
that ChironUser *is* the hand-off; no URL parameters or deep-link encoding are involved, and the
UI needs no changes.

One consequence worth understanding: the hand-off lands in the workspace of the Django user the
server is bound to (`CHIRON_MCP_USERNAME`). If several people share one service account, they
share one workspace and will overwrite each other. Give each person their own account, or use
`mode="report"`, which has no such problem.

Set `CHIRON_MCP_UI_URL` to point the links at your deployment (default `http://localhost:3000`).

## Access model and safety

Access in Chiron is not a login check. It is a `ChironUser` record per (Django user, dataset),
carrying one of three levels plus `PermissionGroup` memberships.

| Level | Subject rows | Counts / crosstabs |
|---|---|---|
| `phi` | yes, identifiable | yes |
| `deid` | yes, with PHI variables automatically swapped for de-identified forms | yes |
| `agg` | **refused** | yes |

### Gates re-implemented here

Calling Chiron's Python directly skips three permission classes that exist **only** in the HTTP
layer. They are re-implemented in `chiron_mcp/identity.py`, and every tool calls them first:

| Gate | Mirrors |
|---|---|
| `require_subject_level` | `SubjectLevelAccess` (`chiron/api/permissions.py:64-79`) |
| `require_workspace` | `CanViewWorkspacePermission` (`chiron/api_v2/permissions.py:37-45`) |
| `require_analysis_view` | `AnalysisViewOn` (`chiron/api/permissions.py:55-62`) |

`Concept.user_can_view_concept_stats` is **not** a substitute for the first: it explicitly
*allows* agg users for non-PHI concepts (`data_definition_models.py:1114-1120`). The agg block is
the DRF class, and only the DRF class.

### Four hazards handled explicitly

1. **No silent provisioning.** `get_request_chironuser` (`chiron/authorization.py:61-72`) writes a
   `ChironUser` as a side effect of a *read*, granting at `Dataset.auto_access_level`, which is
   `phi` on some datasets. This server refuses instead and says what to create deliberately.
2. **Never a `None` chironuser.** `CohortDefProcessor.__init__:42` substitutes `SystemChironUser`
   (hardcoded PHI, every permission group, all datasets) when passed `None`.
   `identity.checked_chironuser()` makes that a hard error rather than a silent escalation.
3. **An errored cohort is never executed.** `clean_cohort_def` reduces an errored definition to an
   empty list, and an empty `cohort_def` matches **every subject**. Running one would silently
   return the whole dataset, so the server refuses.
4. **A failed filter returns no reusable cohort.** On failure `chiron_edit_cohort` omits the
   `cohort_def` key entirely and returns `unchanged_cohort_def` instead, so a failed transformation
   cannot be chained into an accidental whole-dataset query.

### Verifying

```bash
CHIRON_MCP_USERNAME=<deid-user> .venv/bin/python tests/safety.py   # invariants
CHIRON_MCP_USERNAME=<agg-user>  .venv/bin/python tests/safety.py   # agg refusals
.venv/bin/python -m tests.protocol                                 # real MCP stdio handshake
```

## Known limits

- **`chiron_save_cohort_as_report` is not implemented.** `CHIRON_MCP_ALLOW_SAVE` is reserved but
  currently does nothing; there is no path from the model back into the Chiron UI.
- **Crosstab needs a configured root collection.** `run_analysis` reads
  `dataset.root_collection.event_id_field` and dereferences it without a null check. Datasets that
  leave it unset get a clear refusal instead of an `AttributeError`.
- **Most collections are not event collections.** Where `event_date_field` is unset, event rules do
  not apply at all.
- **Regex text filters are broken upstream.** Chiron's own tests document `/slash-wrapped/` terms
  as returning wrong answers.
- **Terms absent from the data are rejected** with `Entry X not found`. Pass `ignore_warnings` to
  accept the filter anyway.
- **Most variables are multi-value**, living in their own lookup table joined one-to-many, so a
  filter matches a subject if *any* of their values match. "No white race value" and "a non-white
  race value" are different questions.
- **`chiron_crosstab` returns preformatted text**, not structured rows. That is what Chiron's
  analysis engine hands back.
- **Remote deployment is not supported.** The transport is stdio and execution is in-process, so
  the server must run where it can reach both databases. Serving it remotely would need HTTP
  transport plus an authentication story Chiron does not currently have.

## Troubleshooting

| Symptom | Cause |
|---|---|
| `Could not find the Chiron source tree` | Set `CHIRON_MCP_CHIRON_SRC` to the checkout containing `chiron/` |
| `No Django project settings at ...` | Set `CHIRON_MCP_PROJECT_DIR` (the directory with `manage.py`) and `CHIRON_MCP_BASE_SETTINGS` |
| `has no ChironUser on dataset` | Expected. Grant it with `scripts/grant_access.py` |
| `is a superuser. Refusing to start` | Use a dedicated service user, or set `CHIRON_MCP_OPERATOR=1` deliberately |
| `cannot see subject-level data` | The identity is `agg`. Use `chiron_crosstab` or `chiron_concept_values` |
| `Please select at least one value` | Wrong field name; call `chiron_describe_concept` and use its `filter_input` |
| Tools missing in the client | Restart it; check the paths in the config are absolute |
| `Server disconnected` / `No module named 'chiron_mcp'` | The client ignored `cwd`. Use the `.venv/bin/chiron-mcp` console script as `command`, with no `args` and no `cwd` |

## Project layout

```
chiron_mcp/
  config.py           environment configuration and path discovery
  bootstrap.py        starts Django in-process, keeping stdout clean for the protocol
  django_settings.py  inherits the host project's settings, overrides only the databases
  identity.py         identity resolution and the re-implemented permission gates
  filters.py          cohort filter input schemas, transcribed from validate_form()
  server.py           the 16 tools
scripts/
  harness.py          deployment check with no MCP involved
  grant_access.py     grant, update, revoke or list ChironUser rows
tests/
  safety.py           permission and whole-dataset invariants
  smoke.py            end-to-end tool exercise
  protocol.py         real MCP stdio handshake
```

Built against Chiron 6.5.4.

## License

MIT

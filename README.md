# chiron-mcp

An [MCP](https://modelcontextprotocol.io) server that exposes **Chiron**, a cohort-discovery
platform for human-subject research data, to an LLM client such as Claude.

Ask *"how many asthma patients are there, and what were their diagnosis dates?"* and the model
finds the right variable, builds the cohort, counts it, and pulls the rows, without anyone
writing SQL, and without bypassing Chiron's own access rules.

```
"How many patients in this dataset?"          -> 10,000
"What conditions are most common?"            -> obesity 2,421 · hypertension 2,134
"Build a cohort of asthma patients"           -> cohort_def
"How many is that?"                           -> 838
"Show me their diagnoses and dates"           -> 829 records across 838 subjects
```

---

## Quickstart (self-contained, no Chiron deployment needed)

Chiron is vendored at `vendor/is4r-chiron`, so this repo stands up a working demo on its own:

```bash
git clone https://github.com/rohzzn/chiron-mcp.git
cd chiron-mcp
./install.sh
docker compose up -d
.venv/bin/python scripts/bootstrap_demo.py
```

That builds a metadata database, runs a real Chiron ETL over the bundled CSVs into Postgres,
creates demo accounts (`demo` at deid, `demo_agg` at agg, `demo_admin` at phi), verifies each
dataset answers, and prints the exact Claude config block to paste. Restart Claude and sixteen
`chiron_*` tools appear.

The demo dictionary is Chiron's own test fixture, so the datasets are small (a handful of
subjects). It exercises the full pipeline end to end. To work against a real deployment instead,
set `CHIRON_MCP_METADATA_DB` and `CHIRON_MCP_WAREHOUSE_URL` and skip the bootstrap.

## Table of contents

- [Quickstart](#quickstart-self-contained-no-chiron-deployment-needed)
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

This section is written for an AI assistant setting this up on someone's machine. Follow it in
order. Every step has a check. Do not skip a check, and do not continue past a failed one.

### Before you start, establish these four facts

> **Chiron is already vendored at `vendor/is4r-chiron`.** Do not try to clone or
> `pip install` it. The `chiron` package on PyPI is an unrelated DNA basecaller, and the
> real repository is behind organisation SSO.

**If the user just wants it working, follow [Quickstart](#quickstart-self-contained-no-chiron-deployment-needed):
`./install.sh`, `docker compose up -d`, `scripts/bootstrap_demo.py`. That needs nothing
external and prints the config block. The steps below are for pointing at an existing
deployment instead.**

Confirm each of these before running anything, asking the user where you cannot determine it
yourself:

1. **Python 3.12 or newer** is available.
2. **A Chiron checkout** exists on this machine (a directory containing a `chiron/` package).
   Ask the user for the path if you cannot find one.
3. **A Chiron metadata database** exists (usually a SQLite file). This holds datasets, users and
   access grants.
4. **A Chiron warehouse** is reachable (a Postgres database holding the subject data).

If any of 2 to 4 is missing, stop and tell the user. This server cannot create them. Setting up a
Chiron deployment is a separate task, and installing this repo alone will not produce a working
tool.

### Step 1: install

```bash
git clone https://github.com/rohzzn/chiron-mcp.git
cd chiron-mcp
./install.sh
```

If `install.sh` reports that it cannot find Chiron, rerun it with the path:

```bash
CHIRON_MCP_CHIRON_SRC=/path/to/is4r-chiron ./install.sh
```

**Check:** `.venv/bin/python -c "import mcp, django; print(django.__version__)"` prints a version.

### Step 2: find out which Django user to bind to

The server acts as exactly one Django user and never creates access for itself. List what exists:

```bash
CHIRON_MCP_USERNAME=any .venv/bin/python scripts/grant_access.py --list
```

This prints every existing `ChironUser` row as `user / dataset / level`. Choose a non-superuser
at `deid` level if one exists. If none does, ask the user which account to use and whether to
grant it access. Do not pick a superuser: the server refuses to start as one in analyst mode,
and that refusal is deliberate.

**Check:** you can name one Django user and at least one dataset it already has a row for.

### Step 3: verify the deployment resolves

This is the single most important step. It exercises everything except the MCP protocol itself.

```bash
CHIRON_MCP_USERNAME=<user> .venv/bin/python scripts/harness.py
```

Add the database paths if the host project's own settings do not already point at the deployment
you want:

```bash
CHIRON_MCP_USERNAME=<user> \
CHIRON_MCP_METADATA_DB=/path/to/chiron_metadata.sqlite3 \
CHIRON_MCP_WAREHOUSE_URL=postgresql://user:pass@host:5432/chiron \
.venv/bin/python scripts/harness.py
```

**Check:** the output ends with `N dataset(s) reachable by this identity` where N is at least 1.

Lines marked `[refused]` are not failures. A refusal means that user has no access record for
that dataset, which is correct behaviour. If **every** dataset is refused, grant one:

```bash
.venv/bin/python scripts/grant_access.py --user <user> --datasets <dataset> --level deid
```

Treat granting access as a change that needs the user's agreement, because it alters the
deployment's metadata database. Say which user and which dataset before doing it.

### Step 4: confirm the warehouse actually answers

The harness proves metadata resolves. This proves the warehouse does too:

```bash
CHIRON_MCP_USERNAME=<user> .venv/bin/python -c "
import sys; sys.path.insert(0, '.')
from chiron_mcp import server as S
print(S.chiron_count_cohort('<dataset>', []))"
```

**Check:** a subject count comes back, not an `error` key. An empty `cohort_def` means every
subject, so this is the dataset's total.

### Step 5: register with Claude

Locate the config file:

| Client | Path |
|---|---|
| Claude Desktop, macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Claude Desktop, Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Claude Code | `.mcp.json` in the project, or the user config |

Add the `chiron` entry from `claude_mcp_config.example.json`, merging it into any existing
`mcpServers` object rather than replacing the file. Back the file up first.

Three rules that prevent almost every reported failure:

- **Use absolute paths everywhere.** The `command`, the `cwd`, and every path in `env`. A relative
  path fails silently because the client does not launch from your shell's directory.
- **Point `command` at `.venv/bin/python`**, not a system `python`. The dependencies are in the
  venv.
- **Set the database variables explicitly** if the host project's settings do not already point at
  the right deployment. Otherwise the server will start successfully against the wrong database
  and the mistake will look like missing data rather than a config error.

**Check:** restart the client, then confirm sixteen `chiron_*` tools are listed. If you cannot see
the client's tool list, run the protocol test instead, which uses the real MCP transport:

```bash
.venv/bin/python -m tests.protocol
```

It should print `16 tools registered` followed by a live tool call result.

### Step 6: confirm the safety gates are active

Do not skip this. The server re-implements three permission checks that Chiron normally enforces
only in its web layer, and they are what keeps it from handing out data Chiron itself would
refuse.

```bash
CHIRON_MCP_USERNAME=<deid-user> .venv/bin/python tests/safety.py
```

**Check:** every line reads `PASS`. If an aggregate-level account exists, run it as that user too
and confirm the row-level tools are refused.

### If something goes wrong

| Symptom | What it means | Fix |
|---|---|---|
| `Could not find the Chiron source tree` | Discovery failed | Set `CHIRON_MCP_CHIRON_SRC` to the directory containing `chiron/` |
| `No Django project settings at ...` | Wrong host project | Set `CHIRON_MCP_PROJECT_DIR` to the directory with `manage.py`, and `CHIRON_MCP_BASE_SETTINGS` if its settings module is not `project.settings` |
| `has no ChironUser on dataset` | Working as designed | Grant it with `scripts/grant_access.py`, with the user's agreement |
| `is a superuser. Refusing to start` | Working as designed | Use a dedicated service account |
| `cannot see subject-level data` | The account is `agg` | Correct behaviour. Use `chiron_crosstab` or `chiron_concept_values` |
| Tools missing after restart | Config not loaded | Check the JSON parses, paths are absolute, and you edited the right file |
| `Server disconnected` in the client | The client did not honour `cwd`, so `-m chiron_mcp.server` could not import | Set `command` to `.venv/bin/chiron-mcp` and drop `args` and `cwd` entirely |
| Server starts but datasets look empty | Pointing at the wrong metadata database | Set `CHIRON_MCP_METADATA_DB` explicitly |
| `ModuleNotFoundError: mcp.server.fastmcp` | `mcp` 1.x code against 2.x | This project targets `mcp>=2.0.0`, which renamed `FastMCP` to `MCPServer` |
| `pip install chiron` seemed to work but nothing imports | **Wrong package.** `chiron` on PyPI is an unrelated nanopore DNA basecaller | Chiron is not on PyPI. Install from the `is4r-chiron` source checkout, or set `CHIRON_MCP_CHIRON_SRC` |

### What to tell the user when you are done

Report which Django user the server is bound to, its access ceiling, and exactly which datasets
are reachable. If you granted any access during setup, say so explicitly, including the level.
That grant is a change to their deployment, not just to this tool.

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

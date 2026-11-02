# Plan: Ask as an add-on for any Chiron ("AskPatch")

Written 2 November 2026, from the team call: point the Ask feature at any Chiron
deployment, apply it, and get the Ask window without touching Chiron's core code; the
models it uses are configuration; nothing else about the deployment changes.

## What the add-on has to touch, and what it already does without touching

| Piece | The Docker bundle today | The add-on |
| --- | --- | --- |
| The Ask server | Runs Chiron in-process with the deployment's own settings: `CHIRON_MCP_CHIRON_SRC`, `CHIRON_MCP_PROJECT_DIR`, `CHIRON_MCP_BASE_SETTINGS`, `CHIRON_MCP_METADATA_DB`, `CHIRON_MCP_WAREHOUSE_URL`. Authenticates by the Chiron session cookie it gets on the same origin. | Already deployment-agnostic; the bundle only wires it through compose. The add-on is that wiring, for a Chiron that is not ours. |
| Chiron's code | Never edited at run time: the bundle's `settings_custom.py` rides on Chiron's own `from .settings_custom import *` hook, and that is for the demo's database, login page and path prefix, which an existing deployment already has. | Nothing. Ask needs no Chiron setting. |
| The two engine fixes in the vendored copy | A mutable default in `CohortDefProcessor._generate_cd_entry_template` (chiron-mcp already deep-copies around it) and event dates kept in lookup tables for the relative-date rule (what `within` needs on the Synthea-style loads). | The host Chiron will not have them. Carry both as run-time patches in `chiron_mcp` applied at bootstrap when the host's function lacks them (the signature says), and send both upstream. |
| The route | Caddy: `/ask/*` to the Ask server on the same origin, with server-sent events flushed at once. | One snippet each for Caddy, nginx and Apache. Additive. |
| The React UI | The Ask tab is in the UI's develop branch already, with the Ask address fixed to `http://localhost:8900`; the bundle's copy reads it from `VITE_ASK_URL`. | Upstream: `VITE_ASK_URL`, and no tab when it is unset (one file, about ten lines); until merged, a patch file for `git apply`. |
| The built-in Django UI | Not used. | `CHIRON_EXTRA_NAVBAR_ITEMS` is a template include: one template with the Ask link, one setting line, no code. |
| Models | `ASK_MODELS` (ids and labels, Haiku default), Bedrock through `CLAUDE_CODE_USE_BEDROCK` and the machine's role, or the Claude login kept in the home volume. | The same, as the add-on's env file. |
| Identity and safety | `CHIRON_MCP_REQUIRE_SESSION=1`: every question is someone logged into Chiron; `CHIRON_MCP_MAX_ACCESS_LEVEL` caps what Ask may see. | Defaults of the add-on, not options. |

So "without touching core code" is already true of the server; the work is packaging,
the route, the UI switch, and the two fixes travelling with Ask instead of with Chiron.

## Two shapes

**A. A sidecar container (first).** An image built from the deployment's own Chiron
source, so its Python dependencies and custom processors are the deployment's, with
chiron-mcp and the Claude Code CLI added; one compose file with the `ask` service (and the
optional `mcp` one); the deployment's project directory mounted read-only; an env file.
Nothing is installed on the host, Node and the CLI stay inside, and it is the shape the
bundle already runs in. Cost: a build step per deployment.

**B. Into the deployment's own Python environment.** `pip install` chiron-mcp from GitHub,
`python -m chiron_mcp.webapp` under systemd, Node 22 and the CLI on the host. Natural for a
bare-metal gunicorn deployment; couples versions and installs on the host.

Both read the same env contract. Build A, document B.

## The install story to aim for

1. `git clone` chiron-mcp, `cd askpatch`, copy `env.example` to `.env`: the Chiron source
   and project directory, the settings module, the two database URLs, the public URL, the
   models and which backend answers.
2. `docker compose up -d --build`: builds the Ask image from that Chiron and starts it.
3. Add the proxy snippet for `/ask`.
4. The UI: rebuild with `VITE_ASK_URL=/ask` once upstream has the switch, or
   `git apply askpatch/ui-ask-tab.patch`; for the built-in UI, the navbar include.
5. `python3 askpatch/check.py`: logs in, asks, and confirms the answer's figure is Chiron's
   count through the Query button (a reuse of `deploy/check.py`).

## Work, in order

| Step | What | Size |
| --- | --- | --- |
| W1 | The env contract, `askpatch/compose.yml`, `askpatch/Dockerfile` building from an external Chiron source, `env.example` | 1 day |
| W2 | Proxy snippets for Caddy, nginx and Apache, with the SSE flush notes | half a day |
| W3 | UI: `VITE_ASK_URL` with the tab hidden when unset, as an upstream change and as a patch file; the built-in UI's navbar template | half a day |
| W4 | The two fixes as run-time patches applied at bootstrap when the host lacks them, and the two upstream pull requests | half a day, plus review |
| W5 | Proof on a stock Chiron: this Mac's `is4r-chiron-develop` with its test project (SQLite metadata, Postgres warehouse) and the stock UI on 5173, installed by the story above, then the test suites and `check.py` pointed at it; then the Docker bundle again, for no regression | 1 day |
| W6 | `askpatch/README.md`, the "Setup guide for an AI agent" section, a cross-link from `deploy/README.md` | half a day |
| W7 | The permission suite (to-do item 5) run against the add-on, since that is where other people's Chirons will meet it | with item 5 |

About four to five days of work.

## Risks, and what in the plan meets them

- **The login must reach Ask.** Ask reads the Chiron session cookie, so it has to be on
  Chiron's origin: the proxy route is not optional. A deployment that serves its UI from
  another origin is out of scope, and the docs say so.
- **Importing the deployment's settings.** Ask runs Django with the host project's settings
  module, so the project directory must be importable where Ask runs and its extra
  packages present: building the image from the deployment's Chiron and requirements is
  what makes that true. `check.py` fails loudly when it is not.
- **Chiron version drift.** chiron-mcp uses Chiron's internals (cohort definition functions,
  the query engine). Name the Chiron versions tested; the smoke test is the tripwire.
- **A dataset with every concept multivalue.** `within` needs the event-date fix; the
  run-time patch carries it until upstream does.
- **Models from inside the deployment's network.** Bedrock through the machine's role, or
  the Claude login in the home volume, as in the bundle; nothing new.
- **Nothing else changes.** The tab appears only when `VITE_ASK_URL` is set, the route is
  additive, Chiron's code and settings are untouched.

## Decisions to make

1. Sidecar container first, pip second: agreed?
2. The UI switch: as an upstream change to the Chiron UI (whoever maintains it reviews),
   or only as a patch file we ship?
3. Carry the two Chiron fixes as run-time patches in chiron-mcp until upstream merges them
   (recommended), or require a patched Chiron?
4. Where to prove it after this Mac's stock stack: the PCGC box runs the bundle, so a real
   target would be another group's Chiron, when there is one.

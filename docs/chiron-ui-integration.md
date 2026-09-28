# Putting "Ask" inside the Chiron UI

`chiron_mcp.webapp` serves a chat page that answers questions using the Chiron MCP
tools. It runs Claude Code headless (`claude -p`), so it uses the operator's existing
Claude subscription and needs no API key.

## 1. Run the server

```bash
CHIRON_MCP_USERNAME=<user> \
CHIRON_MCP_METADATA_DB=/path/to/chiron_metadata.sqlite3 \
CHIRON_MCP_WAREHOUSE_URL=postgresql://user:pass@localhost:5432/chiron \
CHIRON_MCP_ALLOW_SAVE=1 \
.venv/bin/python -m chiron_mcp.webapp
```

It listens on 8900 (`CHIRON_MCP_WEB_PORT`). `CHIRON_MCP_ALLOW_SAVE=1` is what lets it
answer "open this in Chiron"; without it the rest still works.

Usable on its own at <http://localhost:8900>, with `?dataset=<id>` to preselect.

## 2a. Without the React UI

The React UI is vendored under `vendor/is4r-chiron-ui` and `scripts/run_all.sh` starts it
with the Ask tab already added. If you would rather not run Node at all:

```bash
.venv/bin/python scripts/serve_chiron.py   # Chiron (Django UI) at :8001, demo / demo
.venv/bin/python -m chiron_mcp.webapp      # Ask Chiron at :8900
```

That gives you Chiron's own server-rendered pages (`/workspace`, `/reports`) plus the
chat page side by side. Set `CHIRON_MCP_UI_URL=http://localhost:8001` so hand-off links
point at it.

The steps below are only needed to embed the chat as a tab inside the React UI.

## 2b. Add the tab to the React Chiron UI

The UI has an extension point for exactly this: `src/overrideConfig.tsx` feeds
`routes.datasetMore` and `header.nav` through `deepMerge`, so no UI source is forked.
Copy `docs/overrideConfig.example.tsx` over `src/overrideConfig.tsx` in your
`is4r-chiron-ui` checkout, then rebuild or run `npm run dev`.

It adds a route at `/<dataset>/ask` and an **Ask** item in the header nav. The page is
embedded as an iframe, so all markdown, table and chart rendering stays in the Ask
server and the override stays a few lines.

Two gotchas worth knowing:

- `deepMerge` replaces arrays wholesale (`isObject` in `lib/utils.ts` excludes arrays),
  so the nav must be **restated in full**, not appended to. Drop an item and it
  disappears from the header.
- The iframe points at `ASK_URL`, hardcoded to `http://localhost:8900` in the example.
  Change it for a deployment, and make sure that host is reachable from the browser,
  not just from the server.

## What it can do

- Answers with real figures, since every number comes from a tool call
- Markdown tables, and charts via a fenced ```chart block the page renders with Chart.js
- **Follow-up questions.** Each conversation remembers its own cohorts: "them", "those
  patients" and "now only women" refer to the cohort behind the previous answer.
- **Conversation history.** A sidebar keeps past conversations (in the browser, per Chiron
  user and dataset), grouped by day and searchable. **New chat** starts another; reopening
  one continues it; the trash icon deletes it, and its transcript on the server.
- **Starter questions that change.** Each new chat shows six, from six different features
  (counts, combined filters, dates, "without", comparisons, breakdowns, rankings, visits,
  medications, patient lists, reports, the Query hand-off), picked from a pool the server
  builds from the dataset's own values. Features shown least recently come first, and
  questions seen lately are skipped.
- **Suggested follow-ups.** Claude ends each answer with three next steps its tools can
  answer; the server takes them out of the text (dropping any that ask for averages, costs
  or age groups) and the page shows them as chips under the latest answer.
- **Breakdowns** by one or two Category variables, with exact distinct-patient counts per
  group and cell, spelling variants merged, and patients with no recorded value called out.
- **Reports**: save, rename, change filters or columns, make public or private, delete.
- **Query · N** under any answer about a cohort: one click replaces the filters in
  Chiron's query builder with the ones behind that answer and opens the builder. N is
  Chiron's own count for them, recounted as the clicking user before the button appears.
- **Report** under an answer that saved or changed a report, opening it in Chiron.
- Live progress: each Chiron tool call appears as a chip while it works

A question takes roughly 10 to 40 seconds, because the model makes several tool calls.

## How a conversation works

The first question in a tab runs `claude -p --session-id <new uuid>`; each follow-up runs
`claude -p --resume <that uuid>`, so the model sees its earlier tool calls and the
`cohort_def` behind each answer. The page keeps the id in `sessionStorage` and sends it
back as `thread=` with the next question.

The server only resumes a conversation for the user who started it, on the dataset it
started on, within `CHIRON_MCP_THREAD_TTL_HOURS` (12 by default) of its last question.
Anyone else presenting the id gets a fresh conversation with no context. One question
runs per conversation at a time; a second one sent meanwhile is told to wait.

Claude Code writes each conversation's transcript to
`~/.claude/projects/<working-dir>/<id>.jsonl`. Transcripts contain tool results, which
means patient data. Deleting a conversation in the sidebar deletes its transcript at once,
and any conversation idle past the TTL is deleted on the next question. The sidebar still
shows an expired conversation; a follow-up in it is answered on its own, and the page
says so under that answer. Transcripts written before this
existed are not tracked; delete them with:

```bash
rm -rf ~/.claude/projects/*chiron-ask*
```

## Limits

- **It acts as the person logged into Chiron.** The Ask server reads the browser's Chiron
  session cookie, validates it against Chiron's own session table, and runs every question
  as that user: it sees exactly what they may see, reports are saved as them, and the
  Query button loads into their own workspace. With no session (the page opened on its
  own) it falls back to `CHIRON_MCP_USERNAME`, which may not be a superuser. A logged-in
  superuser is refused unless `CHIRON_MCP_ALLOW_SUPERUSER=1`.
- **Cookies ignore the port**, which is why this works when Chiron, the UI and the Ask
  server share a host. On separate hosts the Ask server cannot see the Chiron session.
- **Claude can only call Chiron.** Each question runs `claude -p` with `--tools ""` (no
  shell, file or web tools), `--strict-mcp-config` (no other MCP servers), no settings
  files and Ask's own system prompt, in an empty working directory. Asked to read a file
  on the server, it has no tool to do it with.
- **Bind it to localhost** or put it behind your own auth before exposing it.
- **It inherits the operator's Claude usage limits**, and every question is a `claude`
  process on the operator's machine.
- **Run it where Chiron runs.** With a SQLite metadata database, the Ask server and
  Chiron must share file locking: both on the host, or both in containers on one mount.
  A Dockerised Chiron reading a SQLite file the host writes will intermittently fail with
  "database disk image is malformed".

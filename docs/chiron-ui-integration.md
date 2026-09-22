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

## 2a. No React UI to hand? Use the bundled one

The React UI is a separate repository and is **not** vendored here. If you do not have a
checkout of it, you still get a complete working system from this repo:

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
- Markdown tables
- Charts, via a fenced ```chart block the page renders with Chart.js
- Links into Chiron, rendered as buttons, from `chiron_open_in_ui`
- **"Use as my current query"** under any answer that came from a cohort. It replaces
  the filters open in Chiron's query builder with the ones behind that answer, then
  opens the builder. The server watches the tool calls behind each answer and keeps
  the last `cohort_def` that was counted, tabulated or handed off; the button posts it
  to `/load`. It asks for confirmation first, because Chiron's workspace load also
  erases the undo history.
- Live progress: each Chiron tool call appears as a chip while it works

A question takes roughly 25 to 60 seconds, because the model makes several tool calls.

## Limits

- **One identity for answers.** Questions are answered as `CHIRON_MCP_USERNAME` for
  everyone who opens the page. It is fine for a single analyst or a trusted team on a
  private network; it is not multi-user. There is no login of its own.
- **Workspace loads follow the browser.** The "Use as my current query" button and the
  `/load` endpoint act as the Chiron user behind the browser's `sessionid` cookie, so
  the query lands in the workspace of whoever clicked. That works because Chiron, the
  UI and this server share a host and cookies ignore the port. With no session cookie
  the load falls back to `CHIRON_MCP_USERNAME`. A `chiron_open_in_ui` hand-off that
  the model performs itself still lands in `CHIRON_MCP_USERNAME`'s workspace.
- **Bind it to localhost** or put it behind your own auth before exposing it.
- It inherits the operator's Claude usage limits.

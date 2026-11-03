# Ask as an add-on for an existing Chiron

Point Ask at a Chiron that is already running, anywhere, and get the Ask tab, without
changing Chiron: one container, one route in the web server, one switch in the UI. Take
the three away and Chiron is as it was. The models Ask answers with are configuration.

| What | Where it goes | What it touches in Chiron |
| --- | --- | --- |
| The Ask server | A container built from the deployment's own Chiron source, with chiron-mcp and the Claude Code CLI added; reads the deployment's settings module and its two databases | Nothing. It reads Chiron's metadata and warehouse as the person who is logged in |
| The `/ask` route | One snippet in the web server that already serves Chiron ([proxy/](proxy/)) | Nothing. Ask is served on Chiron's address, which is how it knows who is logged in |
| The Ask tab | A build-time switch in the Chiron UI, `VITE_ASK_URL` ([ui-ask-tab.patch](ui-ask-tab.patch)); for the built-in Django UI, a navbar include ([templates/](templates/askpatch/ask_navbar.html)) | Unset, there is no tab and nothing else changes |

[Ask-add-on-guide.pdf](Ask-add-on-guide.pdf) is this, written out for the person who looks
after a Chiron deployment: how it works, the steps, day to day, removal, troubleshooting
(`guide/make_guide.py` rebuilds it).

Two fixes Chiron needs for this (a mutable default in `CohortDefProcessor`, and event
dates kept in lookup tables for the relative-date rule) travel inside chiron-mcp and are
applied in Ask's own process when the host Chiron lacks them
(`chiron_mcp/chiron_patches.py`); Chiron's files are never written to. Chiron's own query
builder gets them only when they are merged upstream, or when a deployment applies
[chiron-fixes.patch](chiron-fixes.patch) to its checkout itself (three files, the content
of the upstream pull request).

## In five steps

1. Get it and describe your Chiron:

   ```bash
   git clone https://github.com/ri-ds/chiron-mcp.git
   cd chiron-mcp/askpatch
   cp env.example .env && chmod 600 .env
   # fill in .env: CHIRON_SRC, CHIRON_PROJECT_DIR, CHIRON_MCP_METADATA_DB, CHIRON_MCP_WAREHOUSE_URL, PUBLIC_URL
   ```

2. Start the Ask container:

   ```bash
   docker compose up -d --build
   docker compose ps          # "healthy"
   ```

3. Route `/ask` in the web server already in front of Chiron: paste the snippet for it from
   [proxy/](proxy/) (`ask.caddy`, `ask-nginx.conf` or `ask-apache.conf`) into Chiron's site
   block, then reload:

   ```bash
   sudo nginx -t && sudo nginx -s reload        # nginx
   sudo apachectl graceful                      # Apache
   caddy reload --config /etc/caddy/Caddyfile   # Caddy
   ```

4. Turn the tab on in the Chiron UI and rebuild it:

   ```bash
   cd /path/to/is4r-chiron-ui
   git apply /path/to/chiron-mcp/askpatch/ui-ask-tab.patch   # once, if src/overrideConfig.tsx has no VITE_ASK_URL yet
   VITE_ASK_URL=/ask npm run build                            # deploy the build as you normally do
   ```

5. Connect a model and check:

   ```bash
   docker compose exec -it ask claude   # choose the subscription login, approve in the browser, /exit
                                        # or Bedrock: CLAUDE_CODE_USE_BEDROCK=1, AWS_REGION, ANTHROPIC_MODEL in .env
   python3 check.py                     # every line PASS
   ```

**Remove it** in three:

```bash
cd chiron-mcp/askpatch && docker compose down -v                              # container, login, conversations
# delete the /ask snippet from the web server and reload it (same reload command as step 3)
cd /path/to/is4r-chiron-ui && git apply -R /path/to/chiron-mcp/askpatch/ui-ask-tab.patch && npm run build
```

Chiron's code, settings and databases are never touched, so there is nothing else to undo.
The rest of this page explains each step.

## What the deployment needs

- **Chiron 6.5.x on Postgres**, its metadata in Postgres too (SQLite file locks do not
  cross the container boundary; a SQLite deployment runs Ask on the host instead, below).
- The Chiron **source checkout** and the **Django project** (settings module, custom
  processors) on the machine that runs Ask, and the two databases reachable from a
  container there.
- A **web server in front of Chiron** that can take one more route (Caddy, nginx or
  Apache). Ask must be on Chiron's origin: a UI served from another host name cannot
  carry the Chiron login to it.
- Sessions in Django's database or cache backends (the default), whatever the cookie is
  named.
- Docker with Compose v2.17 or newer (for `additional_contexts`).
- A way to reach a model: a Claude account (Pro or Max) to log the container in to, or
  Amazon Bedrock through the machine's role or an AWS profile.

## Install

```bash
git clone https://github.com/ri-ds/chiron-mcp.git
cd chiron-mcp/askpatch
cp env.example .env && chmod 600 .env        # then fill it in: paths, databases, address
docker compose up -d --build                 # builds the image from your Chiron, starts Ask
```

`.env` names the Chiron checkout (`CHIRON_SRC`) and project (`CHIRON_PROJECT_DIR`), the
two databases **as the container reaches them** (a Postgres on the same machine is
`host.docker.internal`, not `localhost`), the site's address (`PUBLIC_URL`, with its path
prefix if it has one), and the models. Everything in it reaches the container, so a
settings module that reads environment variables gets them too. Extra Python packages the
project needs go in [requirements-extra.txt](requirements-extra.txt) before the build.

**The route.** Add the snippet for your web server from [proxy/](proxy/) to the site
that serves Chiron, then reload it. It forwards `/ask` to `127.0.0.1:8900` (`ASK_BIND` in
`.env` to change), with the streaming setting each server needs. Under a path prefix,
the route is `<prefix>/ask`.

**The Ask tab.** In the Chiron UI (`is4r-chiron-ui`), the tab is a build-time switch:
with `VITE_ASK_URL=/ask` the build has it, without it the UI is as before. A checkout that
does not have the switch yet gets it with

```bash
cd is4r-chiron-ui && git apply /path/to/chiron-mcp/askpatch/ui-ask-tab.patch   # or: patch -p1 <
VITE_ASK_URL=/ask npm run build
```

(one file, `src/overrideConfig.tsx`; the same change is proposed upstream). For the
built-in Django UI, two settings lines put an Ask link in the navbar, in `settings.py`
after `TEMPLATES` is defined:

```python
TEMPLATES[0]["DIRS"].append("/path/to/chiron-mcp/askpatch/templates")
CHIRON_EXTRA_NAVBAR_ITEMS = "askpatch/ask_navbar.html"
```

In a `settings_custom.py`, which `settings.py` star-imports at its end, `TEMPLATES` is not
in scope; the comment at the top of
[templates/askpatch/ask_navbar.html](templates/askpatch/ask_navbar.html) has the form that
reaches it through the settings module.

**The model.** For a Claude account, log the container in once, yourself, in a real
terminal: `docker compose exec -it ask claude`, choose the subscription login, open the
link it prints, approve, paste the code back, `/exit`. The login lives in the `ask-home`
volume. For Bedrock, set `CLAUDE_CODE_USE_BEDROCK=1`, `AWS_REGION` and `ANTHROPIC_MODEL`
in `.env`; on an EC2 instance the role is used (its metadata hop limit must be 2 for a
container to reach it), elsewhere add [compose.aws.yml](compose.aws.yml) for a profile in
`~/.aws`. `CHIRON_MCP_ASK_MODELS` lists the models the page may switch between
(`id=Label,...`; Haiku is the default when listed).

**Check it**, through the same front door a browser uses:

```bash
python3 check.py              # --user alice --dataset <id> for an account of your own
```

It makes a login session for the account inside the container (no password is typed),
confirms Ask sees that login through the route, asks a question, and compares the figure
in the answer with Chiron's own count; the last line checks that answers stream through
the web server rather than arriving all at once. Every line should say PASS.

## What people get

The **Ask** tab beside Aggregate: a question in plain words, an answer with Chiron's
figures, follow-ups, a **Query · N** button that loads the answer's cohort into Chiron's
query builder, charts, saved reports, the Results tab. What Ask may see is what the person
may see in Chiron, capped by `CHIRON_MCP_MAX_ACCESS_LEVEL` (`deid` by default). Every
question runs Claude with only the Chiron tools: no shell, no files, no web. See the
repository README for the tools and the access model.

## Run it on the host instead (a SQLite deployment, no Docker)

The same server in the deployment's own Python environment: `pip install` chiron-mcp's
dependencies there (`constraints.txt` pins what was tested, SQLAlchemy below 2.1 above
all), Node 22 with `npm install -g @anthropic-ai/claude-code`, and run

```bash
CHIRON_MCP_CHIRON_SRC=/path/to/is4r-chiron CHIRON_MCP_PROJECT_DIR=/path/to/project \
CHIRON_MCP_METADATA_DB=/path/to/db.sqlite3 CHIRON_MCP_WAREHOUSE_URL=postgresql://... \
CHIRON_MCP_UI_URL=https://chiron.example.org CHIRON_MCP_REQUIRE_SESSION=1 \
CHIRON_MCP_ALLOW_SAVE=1 python -m chiron_mcp.webapp        # :8900, under systemd
```

The route and the tab are the same. The Claude login is the user's that runs it
(`claude` then `/login`). Keep the Ask process on the machine that holds the SQLite file.

## Undo

`docker compose down -v` (removes the container, its login and conversations), delete the
proxy snippet and reload the web server, rebuild the UI without `VITE_ASK_URL` (or
`git apply -R ui-ask-tab.patch`), remove the two navbar settings lines if you added them.
Chiron's code, settings and databases were never changed, so nothing there to undo.
Reports people saved through Ask stay, as any saved report would.

## Proven on

- This repository's own stack: the Docker bundle in `deploy/` is the same server wired
  the same way, and `tests/` run against it.
- A stock Chiron 6.5.4 checkout (unpatched) with its own settings, on a Mac: a fresh
  clone installed by the five steps above with Bedrock as the model; `check.py` 10 of 10
  through Caddy, nginx and Apache, each with its shipped snippet; the Ask link in the
  built-in UI's navbar; the model menu; the aggregate-only account refused and masked as
  Chiron does; `tests/ask_e2e.py` (34 cases as three users) through the front door; the
  `within` timing tests, which need the run-time fixes, inside the container; four
  `git pull` and rebuild upgrades; removal and reinstall. Details and what it found in
  [docs/plan-askpatch.md](../docs/plan-askpatch.md).

## Setup guide for an AI agent

Paste this to Claude Code on the machine that runs Chiron. Fill in the first block.

````text
CHIRON_SRC      = /srv/chiron/is4r-chiron          (the checkout holding chiron/)
PROJECT_DIR     = /srv/chiron/is4r-chiron/test_project   (the directory holding manage.py)
PUBLIC_URL      = https://chiron.example.org       (where people open Chiron, with its prefix)
WEB_SERVER      = nginx                            (caddy, nginx or apache; its config file)
METADATA_DB     = postgresql://user:pass@host.docker.internal:5432/chiron_meta
WAREHOUSE_URL   = postgresql://user:pass@host.docker.internal:5432/chiron
MODEL           = claude account | bedrock

Add the Ask tab to this Chiron with chiron-mcp's askpatch, without changing Chiron.
Repo: https://github.com/ri-ds/chiron-mcp, clone to ~/chiron-mcp (git pull if there).
Read askpatch/README.md first.

Limits: touch only ~/chiron-mcp/askpatch, the chiron-askpatch container, the one web
server snippet, and the UI build. Do not edit Chiron's code, settings or databases, and
do not run migrations. Never print or paste askpatch/.env. Ask me before reloading the
web server and before rebuilding the UI.

1. Check Docker (Compose 2.17+) and that the two databases answer from a container:
   docker run --rm postgres:17 pg_isready -d "<each URL>". If one does not, stop and tell me.
2. Write askpatch/.env from env.example with the values above (chmod 600), and
   docker compose up -d --build. Show me the last lines of the build if it fails.
3. Show me the snippet from askpatch/proxy/ for WEB_SERVER, adapted to the prefix in
   PUBLIC_URL if any, and where it goes in the config; apply it when I agree, then reload.
4. The UI: if its src/overrideConfig.tsx has no VITE_ASK_URL, apply askpatch/ui-ask-tab.patch;
   then rebuild it with VITE_ASK_URL=/ask the way this deployment builds it, when I agree.
5. The model: for a Claude account tell me to run `docker compose exec -it ask claude`
   myself and log in; for Bedrock set the three lines in .env and restart the container.
6. python3 askpatch/check.py --user <an account I name> and show me every line.
7. Tell me what was added (container, snippet, UI switch), what was not touched, and how
   to remove it.
````

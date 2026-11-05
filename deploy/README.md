# Run Chiron and Ask on your own machine, with Docker

One command brings up Chiron, its UI with the Ask tab, and demo data, behind one address
such as `https://chiron.example.org` and one password. Everything runs in Docker; the only
thing you do by hand is log the server in to Claude.

| Service | What it is | Reachable from outside |
| --- | --- | --- |
| web | Caddy: the built UI, HTTPS, the password gate, routing | Yes, the only one |
| chiron | Chiron's Django app (gunicorn); builds the demo data on first start | No |
| ask | The Ask server, running the Claude Code CLI with chiron-mcp as its tools | No |
| db | Postgres 17: the warehouse and Chiron's metadata | No |
| tunnel | Optional Cloudflare tunnel, only with `--mode tunnel` | Outbound only |

Chiron's metadata lives in Postgres here, not in a SQLite file, so the containers never
share a file lock (the problem that corrupts reads when they do).

Already running a Chiron of your own? Add Ask to it instead, without changing it:
[../askpatch/README.md](../askpatch/README.md).

## Before you start

- Docker Desktop, running, with at least 6 GB of memory (Settings, Resources).
- About 10 GB of disk.
- A Claude account (Pro or Max) for the Ask tab. Every question uses its usage limits.
- For a real address: the DNS name, plus one of the two ways in below.

## Pick how the address reaches this machine

| Mode | Use it when | What it needs |
| --- | --- | --- |
| `tunnel` | The domain's DNS is on Cloudflare (`dig +short NS example.org` shows `*.ns.cloudflare.com`). The easiest: no router changes, no open ports | A new Cloudflare tunnel, its token in `deploy/.env`, and a public hostname pointed at `http://web:80` |
| `https` | The name points at your public IP and the router forwards ports 80 and 443 to this machine | Nothing else; Caddy gets and renews the certificate |
| `local` | Trying it on this machine only | Nothing; serves `http://localhost:8088` |

**Tunnel mode, step by step (in the Cloudflare dashboard).** Zero Trust, then Networks,
Tunnels, Create a tunnel, Cloudflared. Name it `chiron`. Create a new tunnel for this, and
never reuse one that already runs somewhere else: two connectors on one tunnel share its
traffic. Copy the token, the long string after `--token` in the install command it shows,
and put it in `deploy/.env` as `CLOUDFLARE_TUNNEL_TOKEN=...` yourself. Then add a public
hostname: subdomain `chiron`, your domain, type HTTP, URL `web:80`. Cloudflare creates the
DNS record for you.

**Https mode on a domain whose DNS is on Cloudflare.** Make the record DNS only (grey
cloud), at least until Caddy has its certificate; with the orange proxy on, set SSL/TLS to
Full (strict). Tunnel mode avoids all of this.

## Set it up

```bash
git clone https://github.com/ri-ds/chiron-mcp.git
cd chiron-mcp/deploy
./setup.sh --domain chiron.example.org --mode tunnel      # or --mode https, or --local
```

The first run builds the images and then the demo data (a real Chiron ETL), about 10
minutes in all; if you drive it from Claude Code, run it in the background with a log.
It is safe to re-run: secrets in `deploy/.env` are kept, and an interrupted first start
finishes on the next one.

When it finishes it prints the address and the site password (also saved in
`deploy/.gate-password`). Then log the server in to Claude, yourself, in a separate
Terminal window (it needs a real terminal):

```bash
cd chiron-mcp/deploy && docker compose exec -it ask claude
```

Pick a theme if asked, choose **Claude account with subscription**, open the link it
prints, approve it in your browser, and paste the code back. If it skips straight to a
prompt, type `/login`. Then `/exit`. The login is kept in a Docker volume, so this is
once per machine.

Check everything, through the same front door a browser uses:

```bash
python3 check.py
```

Every line should say PASS; the last one asks Ask a real question. In https mode, if the
site works from a phone on mobile data but not from this machine, the router cannot reach
its own public address: run `python3 check.py --here`.

## Bring the 10,000-patient dataset

The demo has about 300 synthetic patients plus Chiron's small test datasets. To add
synthea-10k (or any other dataset), export it on a machine that has it and import it here.

```bash
# on the machine that has it (from the repo root, with its venv)
CHIRON_MCP_METADATA_DB=... CHIRON_MCP_WAREHOUSE_URL=... CHIRON_MCP_USERNAME=demouser \
  .venv/bin/python scripts/export_dataset.py synthea-10k        # writes a ~400 MB file

# copy the file over (AirDrop, USB), then here
./import-dataset.sh ~/Downloads/synthea-10k.chiron.tar.gz
```

The file holds the data dictionary and the warehouse tables, so no ETL runs here (about a
minute). A bundle is trusted content, like any database dump: import only your own. Only
ever move synthetic data this way.

## Serve it under a path, behind another web server

To put the whole site at a path such as `https://example.org/chiron/`, behind a web
server that forwards that path with its prefix intact (Apache:
`ProxyPass /chiron http://localhost:8088/chiron`), set two lines in `deploy/.env`:

```bash
BASE_PATH=/chiron
PUBLIC_URL=https://example.org/chiron
```

Then rebuild and restart: `docker compose up -d --build`. The UI is built for that prefix,
Django adds it to every URL it makes, the Ask tab moves to `/chiron/ask/`, and
`python3 check.py` tests through `PUBLIC_URL` as before. The bare host redirects to the
prefix; anything else outside it is a 404. Leave `BASE_PATH` empty (the default) to serve
at the root.

## Connect your own Claude (MCP over HTTPS)

People can also use the Chiron tools from their own MCP client (Claude Code, ...): each
signs in once as their own Chiron user and every call acts with that account's
permissions. The `mcp` service is off by default because it needs an HTTPS address;
chiron-mcp refuses to publish its sign-in over plain http. In `deploy/.env`:

```bash
COMPOSE_PROFILES=mcp
MCP_PUBLIC_URL=https://example.org/chiron     # the site's public HTTPS address, BASE_PATH included
```

Then `docker compose up -d`. People add it with

```bash
claude mcp add --transport http chiron https://example.org/chiron/mcp
```

and the first call opens a browser on the Chiron sign-in page. The endpoint is
`<MCP_PUBLIC_URL>/mcp`; its OAuth discovery documents are at the site root, so a web
server in front that only forwards the prefix must forward these two paths as well
(Apache, for `/chiron`):

```apache
ProxyPass /.well-known/oauth-protected-resource/chiron   http://localhost:8088/.well-known/oauth-protected-resource/chiron
ProxyPass /.well-known/oauth-authorization-server/chiron http://localhost:8088/.well-known/oauth-authorization-server/chiron
```

`MCP_OAUTH_SECRET` (made by setup.sh) signs the tokens; changing it signs everyone out.
`MCP_MAX_ACCESS_LEVEL` caps what any caller gets (default `deid`).

## Day to day

| To | Run (in `deploy/`) |
| --- | --- |
| See what is running | `docker compose ps` |
| Read a service's log | `docker compose logs --tail 100 chiron` (or ask, web, db, tunnel) |
| Follow every model call and Chiron call | `docker compose logs -f --no-log-prefix ask \| grep ' ask '` (one line each, with user, dataset, model, tokens, cost, tool, status and time; see "The call log" in the main README) |
| One conversation, end to end | `docker compose logs --no-log-prefix ask \| grep thread=<id>` (the id is in the page's address and in every line of the conversation) |
| See who Ask takes you for, and what a sign-on gateway in front sends | open `<PUBLIC_URL>/ask/whoami` in the browser, signed in: name, email and access level per dataset; a staff account also sees the request headers that arrived, with the values of those that may carry a sign-on identity |
| See what Ask is used for and what it costs, per person, model, dataset and day | open `<PUBLIC_URL>/ask/usage` signed in as `admin` (everyone's; anyone else sees their own, and so do the members of the Django group `ASK_USAGE_GROUP` in `.env` names); "Who has what" lists every account's access per dataset. The ledger behind it lives in the `ask-home` volume, one row per answer, no question text (see "The usage page" in the main README) |
| Add the answers given before the ledger existed | `docker compose logs --no-log-prefix ask \| docker compose exec -T ask python /app/scripts/usage_backfill.py` (safe to repeat) |
| Prove what each kind of account can and cannot get out of Ask | `docker compose exec -T ask env ASK_URL=http://localhost:8900 CHIRON_API=http://chiron:8000 python /app/tests/permissions.py` (six identities, one question set, about ten minutes; makes and removes its own `perm_*` accounts) |
| Stop, keeping everything | `docker compose stop` |
| Start again | `docker compose up -d` |
| Update to the latest code | `git pull && ./setup.sh` with the same options as before |
| Keep the Mac awake while testing | `caffeinate -dims` in a Terminal window (Ctrl-C to end) |

In tunnel mode `setup.sh` sets `COMPOSE_PROFILES=tunnel` in `.env`, so all of these include
the tunnel container.

## Let people pick the model

By default every question goes to the model Claude Code is set to (`ANTHROPIC_MODEL`
in your override). To offer a choice on the page, list the models in `deploy/.env`,
each a model id Claude Code accepts with a label after `=`:

```
ASK_MODELS=us.anthropic.claude-opus-5-5=Opus 5.5,us.anthropic.claude-sonnet-5-5=Sonnet 5.5,us.anthropic.claude-haiku-5-5=Haiku 5.5
```

Then `docker compose up -d ask`. The composer shows a small menu. Haiku is the default
when it is listed, else Opus, else the first. A question runs with every
Claude Code model slot pinned to the chosen model, so nothing else is called, and the
trace under the answer names the model that answered. Only listed models can be chosen.
On Bedrock, the AWS role must be allowed to call each listed model. A model Bedrock
refuses is dropped from the menu for as long as the server runs, and the question is
answered by the next one (Opus when it is listed); the trace under the answer says so.

## Undo it all after testing

1. Log Claude out: `docker compose exec -it ask claude`, then `/logout`, then `/exit`.
2. Remove the containers, images and data: `docker compose down -v --rmi all`
   (this also deletes the Claude login and the conversations).
3. Tunnel mode: delete the tunnel, and its public hostname and DNS record, in the
   Cloudflare dashboard. Https mode: remove the router's port forwards and the DNS record.
4. Optionally delete `deploy/.env`, `deploy/gate.caddy` and `deploy/.gate-password`.

## Who is asking: a sign-on gateway in front

Chiron has its own login page, so on a site that already signs people in (an access
manager, a Shibboleth service provider) everyone meets a second login and ends up as a
demo account, and Ask, the traces, the call log and the usage ledger then say
"demouser" rather than who it was. Such a gateway forwards every request with headers
that name the person (`OBLIX_UID`, `REMOTE_USER`, `eppn`, `X-Remote-User` and the like),
and with those Chiron can log the person in itself (`chiron_mcp/header_login.py`).
In this order:

1. **See what arrives.** Open `<PUBLIC_URL>/ask/whoami` in the browser, signed in as
   `admin`: `headers.names` lists every request header the server received, and
   `headers.identity` the values of those that may carry an identity.
2. **Check that a visitor cannot forge one.** In the browser's console, on any page of
   the site, signed in (the site's own path before `/ask`):
   ```js
   await (await fetch('/app/chiron/ask/whoami', {headers: {'OBLIX_UID': 'forged'}})).json()
   ```
   If `headers.identity` shows `forged` under the header you meant to use, the gateway
   passes a visitor's own value through, and that header is not safe to sign on with.
   Only a header the gateway strips or overwrites may be used. Measured on the PCGC
   gateway on 2026-11-04: it overwrites its own `Oblix-Uid`, `Oblix-Fname`,
   `Oblix-Lname` and `Oblix-Email`, but passes a visitor's `eppn` and `X-Remote-User`
   straight through, so there only `Oblix-Uid` will do.
3. **Check that nothing but the gateway reaches the web server.** `HTTP_PORT` in
   `deploy/.env` must bind the loopback address the proxy in front uses
   (`127.0.0.1:8088`), never every interface: a request that skipped the gateway could
   carry any header.
4. **Lower Chiron's auto-create rule.** In the Django admin each dataset has "autocreate
   chiron user" and "auto access level": Chiron's own pages give anyone new that level
   on their first visit, and the demo datasets ship with full access there. Set it to
   aggregate or switch it off; the usage page's "Who has what" warns while it is above
   aggregate, and `tests/permissions.py` fails on it once sign-on is on.
5. **Turn it on**, in `deploy/.env`:
   ```
   SSO_USER_HEADER=OBLIX_UID           # the header that names the person (step 1)
   SSO_FIRST_NAME_HEADER=OBLIX_FNAME   # optional, with SSO_LAST_NAME_HEADER and SSO_EMAIL_HEADER;
                                       # or SSO_DISPLAY_NAME_HEADER for one "First Last" header
   SSO_STRIP_DOMAIN=1                  # optional: abc1de@example.org signs in as abc1de
   SSO_DEFAULT_ACCESS=agg              # a newcomer's level on every dataset: agg (default), deid, phi, none
   SSO_DEFAULT_DATASETS=synthea-10k    # optional: those datasets only; unset, all of them
   SSO_LOGOUT_URL=https://...          # optional: the gateway's logout, so Logout ends both sessions
   ```
   then `docker compose up -d chiron ask`. From then on a person who reaches the site is
   logged into Chiron as themselves on their first request. The account is made on first
   sight, with names and email from the headers and no rights, and gets the default
   access on each dataset; an administrator raises individuals to de-identified or full
   access in Chiron's admin (Chiron users) or with `scripts/grant_access.py`. The login
   page keeps only the password form, for `admin` and for test accounts. A request that
   carries the header is always that person, so behind the gateway nobody can stay
   signed in as a different account (the password form is of no use there); a request
   without the header is left as it is, since the gateway adds it to everything it lets
   through and only the deploy check and the test suites, from inside, send none. To
   retire `ADMIN_BUTTON`, sign in once through the gateway so your account exists, make
   it a superuser in the Django admin (Users, "superuser status") or with
   `docker compose exec -T chiron python -c "..."`, and remove the line from `.env`.
6. **Prove it**: step 1 again as yourself (your name top right, `/ask/whoami` naming
   you), then the permission suite from "Day to day".

## Security

- **The password gate is on by default**, because the site is on the internet and
  Chiron's demo login page has one-click buttons for accounts with known passwords.
  Without it anyone could log in and ask questions on your Claude account. Use
  `--no-gate` only when something else guards the site, such as Cloudflare Access.
- **No one-click admin.** The deployment's login page keeps buttons only for the two
  limited demo accounts. `admin` (full access) signs in with its own password,
  `ADMIN_PASSWORD` in `deploy/.env`, which setup.sh generates; read it with
  `grep ADMIN_PASSWORD deploy/.env`. When something else already guards the site (an
  SSO in front of it, say), `ADMIN_BUTTON=1` in `deploy/.env` followed by
  `docker compose up -d --build chiron` puts the admin button back; admin then signs in
  with the demo password the button posts, and gets `ADMIN_PASSWORD` again once the
  line is removed and the container restarted. `admin` is a Django superuser: Chiron's
  admin views open for any staff account, but the Django admin at `/admin/`, where the
  data dictionary is edited (a collection's event date, say), needs it.
- **Ask answers only people logged into Chiron** (`CHIRON_MCP_REQUIRE_SESSION=1`), and
  refuses requests another site's page makes a visitor's browser send.
- **A question can only call Chiron.** Each answer runs Claude with every built-in tool
  (shell, files, web) switched off and only the Chiron tools allowed, so nobody can talk
  it into reading files on the server, the Claude login among them.
- **Chiron's published secret key is replaced** with a random one in `deploy/.env`.
  Django signs login sessions with it; the one in Chiron's repository is public.
- **Only the web service publishes a port.** Postgres, Chiron and Ask are reachable only
  inside Docker.
- **Questions go to Anthropic** under the logged-in Claude account, with the figures
  and rows they return. Fine for synthetic data; check your rules before real data.
- `deploy/.env`, `deploy/gate.caddy` and `deploy/.gate-password` hold secrets. They are
  git-ignored; keep them that way, and do not paste them anywhere.

## When something goes wrong

| Symptom | Cause and fix |
| --- | --- |
| 502 from the site right after setup | Chiron is still building the demo; `docker compose logs -f chiron` |
| The new name does not resolve | A lookup made before the record existed can be cached for up to 30 minutes. Check with `dig +short chiron.example.org @1.1.1.1`; if that answers, wait, or flush the DNS cache |
| Certificate errors in `https` mode | Ports 80 and 443 do not reach this machine, the DNS name points elsewhere, or Cloudflare's proxy is on. `docker compose logs web` says which |
| Works from a phone, not from this Mac (https mode) | The router has no NAT loopback; `python3 check.py --here` checks it locally |
| check.py says "blocked by Cloudflare" | Cloudflare's bot protection rejected it before it reached you; the site itself is fine for browsers |
| "Ask is not connected to a Claude account" | Log the server in: `docker compose exec -it ask claude`, then `/login` |
| "Log in to Chiron first" in Ask | Open the site's Chiron login page and click a demo login button |
| `setup.sh` says a port is in use | Something else has 80 or 443; stop it, or use `--mode tunnel` |
| Login page says "CSRF verification failed" | The address in the browser differs from `PUBLIC_URL` in `deploy/.env`; re-run setup with the right `--domain` |

## Let Claude set it up

Paste this to Claude Code on the machine that will run it. Change the two lines at the
top; everything else refers to them.

````text
DOMAIN = chiron.example.org        (the address the site will have)
ZONE   = example.org               (the domain it belongs to)

Set up Chiron with its Ask tab on this Mac with Docker, reachable at https://DOMAIN.

Repo: https://github.com/ri-ds/chiron-mcp. Clone it to ~/chiron-mcp (or git pull if it is
already there) and work in ~/chiron-mcp/deploy. Read deploy/README.md first; it explains
every step below.

Limits: only touch this project (the chiron-ask Docker containers and ~/chiron-mcp). Ask
me before anything that deletes data (docker prune, docker compose down -v, removing
volumes), before using sudo, and before installing anything. Do not edit the repo's code.
Never print or paste the contents of deploy/.env, deploy/gate.caddy or
deploy/.gate-password, except the site password in the final summary.

1. Check that Docker Desktop is installed and running with at least 6 GB of memory, and
   that git, python3, openssl and nc exist. If something is missing, tell me.
2. Work out how DOMAIN will reach this Mac, and tell me what you found before changing
   anything: `dig +short NS ZONE` (Cloudflare nameservers mean tunnel mode is the easy
   choice), `dig +short DOMAIN @1.1.1.1`, this Mac's public IP (`curl -s https://api.ipify.org`),
   whether cloudflared is installed or running, and whether ports 80 or 443 are in use
   (`nc -z -w 1 127.0.0.1 80; nc -z -w 1 127.0.0.1 443`). Recommend a mode and wait for me
   to agree. For tunnel mode, walk me through creating a NEW tunnel (see "Tunnel mode, step
   by step" in the README) and wait while I put the token into deploy/.env myself. Never
   reuse a tunnel that already runs on this Mac.
3. If ~/Downloads/synthea-10k.chiron.tar.gz exists, add --import with that path. If it is
   not there, ask me whether I meant to copy it before going on.
4. Run ./setup.sh --domain DOMAIN --mode <mode> [--import ...] in the background, with
   its output in ~/chiron-mcp/deploy/setup.log, and follow the log until it prints
   "==> done" or fails. The first run takes about 10 minutes. If it fails, read
   `docker compose logs --tail 100 <service>`, fix the cause and re-run; it is safe to
   re-run.
5. Do not log in to Claude for me and do not type any password or token. When setup is
   done, tell me to open a separate Terminal window and run
   `cd ~/chiron-mcp/deploy && docker compose exec -it ask claude`, choose "Claude account
   with subscription" (or type /login), approve it in my browser, paste the code back, and
   type /exit. Wait until I say it is done.
6. Run python3 check.py and show me the output. Every line should PASS. If one fails, use
   the README's "When something goes wrong" table, fix it, and run it again. (A new DNS
   name can take up to 30 minutes to resolve everywhere.)
7. Finish with: the address, the site password (from deploy/.gate-password), which demo
   login button to click, how to keep this Mac awake (caffeinate -dims), and the README's
   "Undo it all after testing" steps for when I am done.
````

# syntax=docker/dockerfile:1
#
# The Ask server as an add-on for an existing Chiron: one image built from THAT
# deployment's Chiron source, so its Python dependencies and custom processors are the
# deployment's own, with chiron-mcp and the Claude Code CLI added. Nothing of Chiron is
# changed; the deployment's Django project is mounted read-only at run time (compose.yml).
#
# Build context is the chiron-mcp repository root; the Chiron checkout comes in as a second
# context named `chiron` (compose.yml passes CHIRON_SRC from askpatch/.env):
#
#   cd askpatch && docker compose build

FROM node:22-bookworm-slim AS node

FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Node, only because the Claude Code CLI is an npm package; copied from the official image
# (both are Debian bookworm, so the binary's libc matches).
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
# Pinned to the version Ask was tested with (it relies on this CLI's flags and its
# stream-json events). Raise it on purpose, then run check.py. Needs Node 22 or newer.
ARG CLAUDE_CODE_VERSION=2.1.283
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
 && npm install -g --no-audit --no-fund "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" \
 && npm cache clean --force

WORKDIR /app

# The deployment's Chiron: its requirements first (layer caching), then the package.
# USE_CONSTRAINTS=1 pins the versions chiron-mcp was tested with (constraints.txt); build
# with --build-arg USE_CONSTRAINTS=0 if pip reports a conflict with the deployment's own
# pins. SQLAlchemy stays below 2.1 either way: 2.1 switched postgresql:// to a driver
# Chiron does not install, and every warehouse query then fails.
ARG USE_CONSTRAINTS=1
COPY --from=chiron requirements/base.txt /srv/chiron/requirements/base.txt
COPY constraints.txt askpatch/requirements-extra.txt /app/
RUN c=""; [ "$USE_CONSTRAINTS" = "1" ] && c="-c /app/constraints.txt"; \
    pip install $c -r /srv/chiron/requirements/base.txt -r /app/requirements-extra.txt \
      "mcp>=2.0.0" "SQLAlchemy<2.1"
COPY --from=chiron chiron /srv/chiron/chiron

COPY pyproject.toml README.md /app/
COPY chiron_mcp /app/chiron_mcp
COPY scripts /app/scripts
COPY tests /app/tests
# used by askpatch/check.py through `docker compose exec ask`
COPY deploy/mint_session.py deploy/count_subjects.py /app/deploy/

# Installs the chiron-mcp console script next to python, which is where the Ask server
# looks for it when it writes each question's MCP config.
RUN pip install --no-deps -e /app

# Run as an ordinary user. HOME is a volume in compose: it keeps the Claude login and the
# Ask server's conversation state across restarts.
RUN useradd --create-home --uid 1000 app
USER app
ENV HOME=/home/app \
    CHIRON_MCP_CHIRON_SRC=/srv/chiron \
    CHIRON_MCP_PROJECT_DIR=/srv/project

EXPOSE 8900

# syntax=docker/dockerfile:1
#
# One image for both Python services in deploy/compose.yml:
#   chiron  Chiron's own Django app (gunicorn), plus the one-time demo bootstrap
#   ask     the Ask server, which runs the Claude Code CLI with chiron-mcp as its tools
#
# Build context is the repository root:  docker compose -f deploy/compose.yml build

FROM node:22-bookworm-slim AS node

FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Node, only because the Claude Code CLI is an npm package. Copied from the official
# image rather than installed from a third-party apt repository; both are Debian
# bookworm, so the binary's libc matches.
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
# Pinned to the version Ask was tested with: it relies on this CLI's flags (--tools "",
# --setting-sources "", --strict-mcp-config) and its stream-json events. Raise it on
# purpose, then run check.py. The CLI needs Node 22 or newer.
ARG CLAUDE_CODE_VERSION=2.1.283
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
 && npm install -g --no-audit --no-fund "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" \
 && npm cache clean --force

WORKDIR /app

# Python dependencies first, for layer caching. Everything here ships as a wheel for
# both amd64 and arm64, so no compiler is needed.
# constraints.txt pins the exact versions everything was tested with.
COPY vendor/is4r-chiron/requirements/base.txt /app/vendor/is4r-chiron/requirements/base.txt
COPY constraints.txt /app/constraints.txt
RUN pip install -c /app/constraints.txt \
      -r /app/vendor/is4r-chiron/requirements/base.txt "mcp>=2.0.0" gunicorn

COPY vendor/is4r-chiron /app/vendor/is4r-chiron
COPY pyproject.toml README.md /app/
COPY chiron_mcp /app/chiron_mcp
COPY scripts /app/scripts
COPY tests /app/tests
COPY deploy/entrypoint-chiron.sh deploy/mint_session.py deploy/import_dataset.py \
     deploy/count_subjects.py /app/deploy/
# Chiron's settings.py ends with `from .settings_custom import *`; this is how the
# deployment's database, secret key and host settings get in without forking Chiron.
COPY deploy/settings_custom.py /app/vendor/is4r-chiron/test_project/project/settings_custom.py

# Installs the chiron-mcp console script next to python, which is where the Ask server
# looks for it when it writes each question's MCP config.
RUN pip install --no-deps -e /app

# Run as an ordinary user. HOME is a volume in compose: it keeps the Claude login and
# the Ask server's conversation state across restarts.
RUN useradd --create-home --uid 1000 app \
 && mkdir -p /app/static \
 && chown -R app:app /app/static /app/vendor/is4r-chiron/test_project \
 && chmod +x /app/deploy/entrypoint-chiron.sh
USER app
ENV HOME=/home/app \
    CHIRON_MCP_CHIRON_SRC=/app/vendor/is4r-chiron

EXPOSE 8000 8900

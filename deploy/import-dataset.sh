#!/usr/bin/env bash
# Load a dataset exported with scripts/export_dataset.py into the running stack.
#
#   ./import-dataset.sh ~/Downloads/synthea-10k.chiron.tar.gz [--replace]
#
# Restores the warehouse schema straight into Postgres (no ETL, no source files), then
# registers the data dictionary and grants the demo accounts. Safe to re-run: the schema
# is replaced, and the dictionary is kept unless --replace is given.
set -euo pipefail
cd "$(dirname "$0")"

bundle="${1:?usage: ./import-dataset.sh <file.chiron.tar.gz> [--replace]}"
replace="${2:-}"
[ -f "$bundle" ] || { echo "No such file: $bundle"; exit 1; }
docker compose ps --status running --services 2>/dev/null | grep -qx chiron \
  || { echo "The stack is not running. Start it first: docker compose up -d"; exit 1; }

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
tar -xzf "$bundle" -C "$tmp"
dataset="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["dataset"])' "$tmp/manifest.json")"
schema="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["schema"])' "$tmp/manifest.json")"
# Both names end up in SQL and in file paths; a bundle is data from elsewhere, so only
# plain names get through.
case "$dataset$schema" in
  ""|*[!A-Za-z0-9_-]*) echo "Refusing: the bundle's dataset or schema name is not a plain name."; exit 1 ;;
esac
echo "Importing $dataset (warehouse schema $schema)"

echo "[1/2] restoring the warehouse schema (the slow step)"
docker compose exec -T db psql -q -U chiron -d chiron -c "DROP SCHEMA IF EXISTS \"$schema\" CASCADE" >/dev/null
docker compose exec -T db pg_restore -U chiron -d chiron --no-owner --no-privileges \
  < "$tmp/warehouse.dump"

echo "[2/2] registering the data dictionary and granting the demo accounts"
docker compose exec -T chiron mkdir -p /tmp/import
docker compose cp "$tmp/$dataset.json" "chiron:/tmp/import/$dataset.json" >/dev/null
docker compose exec -T chiron python /app/deploy/import_dataset.py "/tmp/import/$dataset.json" $replace

echo "Done. $dataset is in the dataset list; log in again if the UI was open."

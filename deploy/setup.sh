#!/usr/bin/env bash
# Set up and start the whole stack. Safe to re-run: existing secrets are kept.
#
#   ./setup.sh --domain chiron.example.org                  Caddy gets the certificate
#   ./setup.sh --domain chiron.example.org --mode tunnel    Cloudflare tunnel in front
#   ./setup.sh --local [--port 8088]                        this machine only
#
# Options:
#   --import FILE   also load a dataset bundle (from scripts/export_dataset.py)
#   --no-gate       no password in front (only if something else guards the site,
#                   e.g. Cloudflare Access)
#   --no-build      skip rebuilding the images
#
# Written for the bash that ships with macOS (3.2), so no newer bash features.
set -euo pipefail
cd "$(dirname "$0")"

domain="" mode="" port="8088" import="" gate=1 build=1
while [ $# -gt 0 ]; do
  case "$1" in
    --domain) domain="$2"; shift 2 ;;
    --mode) mode="$2"; shift 2 ;;
    --local) mode="local"; shift ;;
    --port) port="$2"; shift 2 ;;
    --import) import="$2"; shift 2 ;;
    --no-gate) gate=0; shift ;;
    --no-build) build=0; shift ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1 (see --help)"; exit 2 ;;
  esac
done
if [ -z "$mode" ]; then mode="https"; fi
case "$mode" in
  https|tunnel) [ -n "$domain" ] || { echo "--domain is required for --mode $mode"; exit 2; } ;;
  local) ;;
  *) echo "--mode must be https, tunnel or local"; exit 2 ;;
esac

say() { printf '\n==> %s\n' "$*"; }

command -v docker >/dev/null || { echo "Docker is not installed. Install Docker Desktop first."; exit 1; }
docker info >/dev/null 2>&1 || { echo "Docker is not running. Start Docker Desktop, then re-run."; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "This needs Docker Compose v2 (docker compose)."; exit 1; }

# --- .env: keep what is there, fill in what is missing ------------------------------
touch .env
chmod 600 .env
get_key() { grep -E "^$1=" .env | tail -n 1 | cut -d= -f2- || true; }
set_key() {
  local key="$1" value="$2" tmp
  tmp="$(mktemp)"
  grep -vE "^$key=" .env > "$tmp" || true
  printf '%s=%s\n' "$key" "$value" >> "$tmp"
  mv "$tmp" .env
  chmod 600 .env
}
secret() { openssl rand -hex 32; }

[ -n "$(get_key POSTGRES_PASSWORD)" ] || set_key POSTGRES_PASSWORD "$(secret)"
[ -n "$(get_key DJANGO_SECRET_KEY)" ] || set_key DJANGO_SECRET_KEY "$(secret)"
case "$mode" in
  https)
    set_key SITE_ADDRESS "$domain"
    set_key PUBLIC_URL "https://$domain"
    set_key HTTP_PORT "80"
    set_key HTTPS_PORT "443" ;;
  tunnel)
    set_key SITE_ADDRESS ":80"
    set_key PUBLIC_URL "https://$domain"
    # the tunnel reaches web inside Docker; this is only for checking from this Mac
    set_key HTTP_PORT "127.0.0.1:$port"
    set_key HTTPS_PORT "127.0.0.1:8443" ;;
  local)
    set_key SITE_ADDRESS ":80"
    set_key PUBLIC_URL "http://localhost:$port"
    set_key HTTP_PORT "127.0.0.1:$port"
    set_key HTTPS_PORT "127.0.0.1:8443" ;;
esac
# Compose reads COMPOSE_PROFILES from .env, so in tunnel mode every plain
# `docker compose ...` (ps, stop, down, logs) includes the tunnel container too.
if [ "$mode" = "tunnel" ]; then set_key COMPOSE_PROFILES "tunnel"; else set_key COMPOSE_PROFILES ""; fi
if [ "$mode" = "tunnel" ] && [ -z "$(get_key CLOUDFLARE_TUNNEL_TOKEN)" ]; then
  set_key CLOUDFLARE_TUNNEL_TOKEN ""
  echo "Tunnel mode needs a Cloudflare tunnel token. In the Cloudflare dashboard:"
  echo "  Zero Trust > Networks > Tunnels > Create a tunnel > Cloudflared, name it chiron."
  echo "  Create a NEW tunnel for this; never reuse one that already runs elsewhere."
  echo "  Copy the token (the long string after --token in the command it shows)."
  echo "  Public hostname: subdomain ${domain%%.*}, domain ${domain#*.}, type HTTP, URL web:80."
  echo "Then add this line to $(pwd)/.env yourself, and re-run this script:"
  echo "  CLOUDFLARE_TUNNEL_TOKEN=<the token>"
  exit 1
fi

# --- in https mode Caddy needs ports 80 and 443 on this machine ----------------------
if [ "$mode" = "https" ] && [ -z "$(docker compose ps -q web 2>/dev/null)" ]; then
  for p in 80 443; do
    if nc -z -w 1 127.0.0.1 "$p" >/dev/null 2>&1; then
      echo "Port $p is already in use on this machine, and https mode needs it."
      echo "Stop whatever uses it, or use --mode tunnel (no local ports needed)."
      exit 1
    fi
  done
fi

# --- the password gate -------------------------------------------------------------
if [ "$gate" = 0 ]; then
  echo "# no password gate (setup.sh --no-gate): something else must guard this site" > gate.caddy
elif ! grep -q basic_auth gate.caddy 2>/dev/null; then
  say "creating the password gate"
  pw="$(openssl rand -base64 18 | tr -d '/+=')"
  hash="$(docker run --rm caddy:2-alpine caddy hash-password --plaintext "$pw")"
  printf 'basic_auth {\n\tchiron %s\n}\n' "$hash" > gate.caddy
  printf 'user: chiron\npassword: %s\n' "$pw" > .gate-password
  chmod 600 .gate-password gate.caddy
fi

# --- build and start ---------------------------------------------------------------
if [ "$build" = 1 ]; then
  say "building the images (the first build takes several minutes)"
  docker compose build
fi

# Chiron first, on its own: everything else waits for it to be healthy, and a Chiron that
# keeps crashing would otherwise make `up` wait forever without saying why.
say "starting Chiron (the first start builds the demo data: a few minutes)"
docker compose up -d db chiron
cid="$(docker compose ps -q chiron)"
state=""
for _ in $(seq 1 240); do
  state="$(docker inspect -f '{{.State.Status}} {{.RestartCount}} {{if .State.Health}}{{.State.Health.Status}}{{end}}' "$cid")"
  case "$state" in
    "running "*" healthy") break ;;
    exited*|dead*|restarting*|"running "[1-9]*)
      echo "Chiron failed to start. Its log:"; docker compose logs --tail 60 chiron; exit 1 ;;
  esac
  sleep 5
done
case "$state" in
  "running "*" healthy") echo "Chiron is up." ;;
  *) echo "Chiron did not become healthy in 20 minutes; see: docker compose logs chiron"; exit 1 ;;
esac

say "starting the rest"
docker compose up -d
# Caddy reads the gate file only when it starts, so restart it to be sure it has this one.
docker compose restart web >/dev/null

if [ -n "$import" ]; then
  say "importing $import"
  ./import-dataset.sh "$import"
fi

url="$(get_key PUBLIC_URL)"
say "done"
echo "Open:        $url"
if [ "$gate" = 1 ]; then
  echo "Site login:  $(sed -n 's/^user: //p' .gate-password) / $(sed -n 's/^password: //p' .gate-password)   (saved in deploy/.gate-password)"
fi
echo "Then click a demo login button on Chiron's login page."
echo
echo "One step left for the Ask tab: log the server in to Claude, yourself:"
echo "  cd $(pwd) && docker compose exec -it ask claude"
echo "then type /login, open the link it prints, approve, paste the code back, and /exit."
echo
echo "Check everything:  python3 check.py"

#!/usr/bin/env bash
# Tier A smoke (Linux / CI): compose build/up, DB ready, server log, ctrContracts schema.
# Repository root = two levels above this script.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

SKIP_BUILD=false
SKIP_UP=false
MAX_WAIT="${MAX_WAIT:-180}"

usage() {
  echo "Usage: $0 [--skip-build] [--skip-up]" >&2
  echo "  MAX_WAIT=300 $0   # extend wait window (seconds)" >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-build) SKIP_BUILD=true ;;
    --skip-up)    SKIP_UP=true ;;
    -h|--help)    usage ;;
    *) echo "Unknown option: $1" >&2; usage ;;
  esac
  shift
done

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not found on PATH" >&2
  exit 1
fi

if [[ "$SKIP_BUILD" != true ]]; then
  echo "==> docker compose build server"
  docker compose build server
fi

if [[ "$SKIP_UP" != true ]]; then
  echo "==> docker compose up -d"
  docker compose up -d
fi

db_sql() {
  docker compose exec -T db mariadb -ueva -pevemu evemu "$@"
}

echo "==> Waiting for MariaDB..."
deadline=$(( $(date +%s) + MAX_WAIT ))
until db_sql -e "SELECT 1" >/dev/null 2>&1; do
  if (( $(date +%s) > deadline )); then
    echo "MariaDB not ready within ${MAX_WAIT}s" >&2
    echo "==> docker compose ps -a" >&2
    docker compose ps -a >&2 || true
    echo "==> docker compose logs db (tail)" >&2
    docker compose logs db --tail 200 >&2 || true
    exit 1
  fi
  sleep 2
done
echo "    MariaDB OK."

echo "==> Waiting for game server log (TCP Server started on port)..."
deadline=$(( $(date +%s) + MAX_WAIT ))
while true; do
  if docker logs server --tail 500 2>&1 | grep -Fq "TCP Server started on port"; then
    break
  fi
  if (( $(date +%s) > deadline )); then
    echo "Server log not ready within ${MAX_WAIT}s" >&2
    exit 1
  fi
  sleep 3
done
echo "    Server log OK."

echo "==> Schema: ctrContracts corp-routing columns..."
schema_sql="SELECT IF(
  (SELECT COUNT(*) FROM information_schema.columns
   WHERE table_schema = DATABASE() AND table_name = 'ctrContracts'
     AND column_name IN ('acceptorCorpID', 'issuerWalletKey', 'acceptorWalletKey')) = 3,
  'OK', 'FAIL') AS ctrcontracts_smoke;"
out="$(db_sql -N -e "$schema_sql" | tr -d '\r')"
echo "    ${out}"
if [[ "$out" != *OK* ]]; then
  echo "ctrContracts schema check failed (expected OK)" >&2
  exit 1
fi
echo "    Schema OK."

echo "==> Optional: port 26000 (localhost)..."
if command -v nc >/dev/null 2>&1; then
  if nc -z localhost 26000 2>/dev/null; then
    echo "    Port 26000 open."
  else
    echo "    Port 26000 not reachable (non-fatal)."
  fi
else
  echo "    nc not installed; skip port check."
fi

echo "==> Tier A smoke PASSED."

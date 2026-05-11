#!/usr/bin/env bash
# Smoke setup validator: verify infrastructure files are present.
# Does NOT attempt to run tests or simulate gameplay.
# See: scripts/SMOKE_PIPELINE_FOR_AGENTS.md

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

FAIL=0

echo "==> Smoke Pipeline Setup Validator"
echo ""

# Tier A runners
echo "Tier A (CI-automatable):"
for f in scripts/smoke/docker-smoke.{ps1,sh}; do
  if [[ -f "$f" ]]; then
    echo "  ✓ $f"
  else
    echo "  ✗ MISSING: $f"
    FAIL=1
  fi
done

# Tier B evidence SQL
echo ""
echo "Tier B (evidence collection):"
for f in scripts/smoke/sql/{contracts_courier_assertions,corp_market_assertions,paper_doll_assertions}.sql \
         scripts/live-smoke/run-post-client-evidence.ps1; do
  if [[ -f "$f" ]]; then
    echo "  ✓ $f"
  else
    echo "  ✗ MISSING: $f"
    FAIL=1
  fi
done

# Documentation
echo ""
echo "Documentation:"
for f in scripts/SMOKE_PIPELINE_FOR_AGENTS.md \
         scripts/smoke/README.md \
         scripts/live-smoke/README.md \
         EVEMU_RESTORATION_STATE.md; do
  if [[ -f "$f" ]]; then
    echo "  ✓ $f"
  else
    echo "  ✗ MISSING: $f"
    FAIL=1
  fi
done

echo ""
if [[ $FAIL -eq 0 ]]; then
  echo "==> OK: Smoke infrastructure intact."
  echo "    Tier A is CI-ready. Tier B/C require manual client + eve-test wiring."
  echo "    See: scripts/SMOKE_PIPELINE_FOR_AGENTS.md"
  exit 0
else
  echo "==> FAIL: Missing smoke infrastructure files."
  exit 1
fi

#!/usr/bin/env bash
# Scheduled pipeline run (Linux / macOS / WSL / Git Bash). Safe to run from cron.
# Reads credentials from the environment or from ./.env (not committed). Exit code != 0 means failure.
set -u
cd "$(dirname "$0")/.."
mkdir -p logs
LOG="logs/pipeline_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1

if [ -f .env ]; then set -a; . ./.env; set +a; fi
for v in GEE_PROJECT SUPABASE_URL SUPABASE_SERVICE_ROLE_KEY; do
  if [ -z "${!v:-}" ]; then echo "missing $v"; exit 2; fi
done

PY="${PYTHON:-python3}"
echo "== $(date -Is) tests";            "$PY" -m pytest scripts/tests -q || exit 3
echo "== $(date -Is) update";           "$PY" scripts/realtime_update.py; RC=$?
echo "== $(date -Is) output checks";    "$PY" scripts/check_outputs.py || RC=4
echo "== $(date -Is) done rc=$RC"
exit $RC

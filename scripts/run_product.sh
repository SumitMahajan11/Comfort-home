#!/usr/bin/env bash
# scripts/run_product.sh
# One-command local runner for ClimateAdapt-Comfort v2 decision-support product.
# Validates manifest checksums, audits CPWD cost rates, and starts API & Web Frontend.

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"
export PATH="$HOME/.local/bin:$PATH"

ALLOW_UNFILLED=false
API_PORT=8000
WEB_PORT=3000

for arg in "$@"; do
  case $arg in
    --allow-unfilled-costs)
      ALLOW_UNFILLED=true
      shift
      ;;
    --api-port=*)
      API_PORT="${arg#*=}"
      shift
      ;;
    --web-port=*)
      WEB_PORT="${arg#*=}"
      shift
      ;;
  esac
done

echo "================================================================================"
echo " ClimateAdapt-Comfort v2: One-Command Product Runner"
echo "================================================================================"

PYTHON_EXE="python3"
if [ -f "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON_EXE="$PROJECT_ROOT/.venv/bin/python"
elif [ -f "$PROJECT_ROOT/.venv/Scripts/python.exe" ]; then
    PYTHON_EXE="$PROJECT_ROOT/.venv/Scripts/python.exe"
fi

# 1. Validate data/export Checksums
echo ""
echo "[1/3] Verifying data/export/manifest.json integrity checksums..."
$PYTHON_EXE -c "
import sys
from api.loader import ArtifactStore
store = ArtifactStore()
try:
    store.verify_and_load()
    print(f'Verification PASSED: {len(store.manifest_data.get(\"files\", {}))} artifacts match manifest SHA256.')
except Exception as e:
    print(f'FATAL Checksum Error: {e}', file=sys.stderr)
    sys.exit(1)
"

# 2. Run CPWD Cost Rate Validator
echo ""
echo "[2/3] Auditing CPWD DSR rate schedules..."
set +e
$PYTHON_EXE tools/validate_costs.py
COST_EXIT=$?
set -e

if [ $COST_EXIT -ne 0 ]; then
    if [ "$ALLOW_UNFILLED" = true ]; then
        echo ""
        echo "[WARNING] CPWD DSR cost rates contain 'TO BE FILLED' placeholders."
        echo "Continuing because --allow-unfilled-costs was specified."
        echo "Under Decision D-025, monetary costs will display as 'Rates unpopulated in official DSR schedule'."
    else
        echo ""
        echo "================================================================================"
        echo " PRODUCT STARTUP BLOCKED: UNFILLED COST RATES (Decision D-025)"
        echo "================================================================================"
        echo "CPWD DSR cost rates are still marked 'TO BE FILLED'."
        echo "Under non-negotiable project honesty rules, release is blocked while placeholders remain."
        echo ""
        echo "To resolve:"
        echo "  1. Populate official rates in data/costs/dsr_rates_template.csv and run tools/csv_to_dsr_json.py"
        echo "  2. Or run with --allow-unfilled-costs to start with strict null-gated cost warnings:"
        echo "     ./scripts/run_product.sh --allow-unfilled-costs"
        exit 1
    fi
fi

# 3. Start Backend & Frontend Services
echo ""
echo "[3/3] Launching FastAPI Backend and Next.js Web Frontend..."
echo "  FastAPI Service:   http://127.0.0.1:$API_PORT (Docs: http://127.0.0.1:$API_PORT/docs)"
echo "  Next.js Frontend:  http://localhost:$WEB_PORT"
echo ""

$PYTHON_EXE -m uvicorn api.main:app --host 127.0.0.1 --port $API_PORT &
API_PID=$!

cd "$PROJECT_ROOT/web"
npm run dev -- -p $WEB_PORT &
WEB_PID=$!

trap "kill $API_PID $WEB_PID 2>/dev/null || true" EXIT INT TERM

wait

#!/usr/bin/env bash
# ============================================================
# run_unit_tests.sh — Quick validation for artifact evaluators
# ============================================================
# Installs the package in editable mode with dev dependencies
# and runs the full test suite.
#
# Usage:
#   bash scripts/run_unit_tests.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=============================================="
echo " RAC Artifact — Unit Test Runner"
echo "=============================================="
echo ""

cd "$REPO_ROOT"

# 1. Create a virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "[1/3] Creating virtual environment..."
    python3 -m venv .venv
else
    echo "[1/3] Virtual environment already exists."
fi

# shellcheck disable=SC1091
source .venv/bin/activate

# 2. Install the package
echo "[2/3] Installing react-agent-compensation[dev]..."
pip install -q -e ".[dev]"

# 3. Run tests
echo "[3/3] Running pytest..."
echo ""
pytest -v --tb=short

echo ""
echo "=============================================="
echo " All tests passed."
echo "=============================================="

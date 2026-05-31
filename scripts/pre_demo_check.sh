#!/usr/bin/env bash
# Pre-demo readiness check.
# Exits 0 only if: integration tests pass AND fast-eval hit_target_rate >= 0.6.
# Run from the project root: bash scripts/pre_demo_check.sh

set -euo pipefail

PYTHON=".venv/bin/python"
PYTEST=".venv/bin/pytest"
FAST_DATASET="src/lexara/eval/data/rewrite_fast.json"
EVAL_OUT="/tmp/lexara_predemo_eval_$$.json"
MIN_HIT_RATE="0.6"

# Colours
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
RESET='\033[0m'

pass() { echo -e "${GREEN}  ✓ $*${RESET}"; }
fail() { echo -e "${RED}  ✗ $*${RESET}"; }
warn() { echo -e "${YELLOW}  ⚠ $*${RESET}"; }
header() { echo -e "\n${BOLD}$*${RESET}"; }

TESTS_OK=0
EVAL_OK=0

# ---------------------------------------------------------------------------
# 0. Environment
# ---------------------------------------------------------------------------
header "[ 1 / 3 ]  Environment"

export LEXARA_LLM_PROVIDER=openai
pass "LEXARA_LLM_PROVIDER=openai"

if [[ -z "${LEXARA_OPENAI_API_KEY:-}" ]]; then
    # Try loading from .env
    if [[ -f ".env" ]]; then
        LEXARA_OPENAI_API_KEY=$(grep -E '^LEXARA_OPENAI_API_KEY=' .env | cut -d= -f2- | tr -d '[:space:]')
        export LEXARA_OPENAI_API_KEY
    fi
fi

if [[ -z "${LEXARA_OPENAI_API_KEY:-}" ]]; then
    fail "LEXARA_OPENAI_API_KEY is not set and not found in .env"
    echo -e "\n${RED}${BOLD}DO NOT DEMO — check logs above${RESET}\n"
    exit 1
fi
pass "LEXARA_OPENAI_API_KEY is set (${#LEXARA_OPENAI_API_KEY} chars)"

# ---------------------------------------------------------------------------
# 1. Integration tests
# ---------------------------------------------------------------------------
header "[ 2 / 3 ]  Integration tests  (pytest -m integration)"

if "$PYTEST" -m integration -q --tb=short 2>&1; then
    pass "All integration tests passed"
    TESTS_OK=1
else
    fail "Integration tests failed"
    TESTS_OK=0
fi

# ---------------------------------------------------------------------------
# 2. Fast eval
# ---------------------------------------------------------------------------
header "[ 3 / 3 ]  Fast eval  (5 passages, provider=openai)"

# Invalidate settings cache so get_settings() picks up the env vars we set
LEXARA_LLM_PROVIDER=openai \
"$PYTHON" -m lexara.eval.runner \
    --provider openai \
    --dataset "$FAST_DATASET" \
    --output "$EVAL_OUT" \
    --format table \
    2>&1

if [[ ! -f "$EVAL_OUT" ]]; then
    fail "Eval output file was not created — eval may have crashed"
    EVAL_OK=0
else
    HIT_RATE=$("$PYTHON" -c "
import json, sys
d = json.load(open('$EVAL_OUT'))
print(d['hit_target_rate'])
sys.exit(0 if d['hit_target_rate'] >= $MIN_HIT_RATE else 1)
" 2>&1) && EVAL_PASSED=$? || EVAL_PASSED=$?

    HIT_RATE=$("$PYTHON" -c "import json; d=json.load(open('$EVAL_OUT')); print(d['hit_target_rate'])")
    HIT_COUNT=$("$PYTHON" -c "import json; d=json.load(open('$EVAL_OUT')); print(d['hit_target_count'])")
    SAMPLE_COUNT=$("$PYTHON" -c "import json; d=json.load(open('$EVAL_OUT')); print(d['sample_count'])")
    AVG_DELTA=$("$PYTHON" -c "import json; d=json.load(open('$EVAL_OUT')); print(d['avg_grade_delta'])")

    if "$PYTHON" -c "import sys; sys.exit(0 if float('$HIT_RATE') >= $MIN_HIT_RATE else 1)"; then
        pass "hit_target_rate = $HIT_RATE  ($HIT_COUNT/$SAMPLE_COUNT)  avg_delta = $AVG_DELTA"
        EVAL_OK=1
    else
        fail "hit_target_rate = $HIT_RATE  ($HIT_COUNT/$SAMPLE_COUNT) — below threshold $MIN_HIT_RATE"
        EVAL_OK=0
    fi

    rm -f "$EVAL_OUT"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}  Pre-demo check summary${RESET}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"

[[ $TESTS_OK -eq 1 ]] && pass "Integration tests" || fail "Integration tests"
[[ $EVAL_OK  -eq 1 ]] && pass "Fast eval  (hit_target >= $MIN_HIT_RATE)" || fail "Fast eval  (hit_target >= $MIN_HIT_RATE)"

echo ""

if [[ $TESTS_OK -eq 1 && $EVAL_OK -eq 1 ]]; then
    echo -e "${GREEN}${BOLD}  ✓  READY TO DEMO${RESET}"
    echo ""
    exit 0
else
    echo -e "${RED}${BOLD}  ✗  DO NOT DEMO — check logs above${RESET}"
    echo ""
    exit 1
fi

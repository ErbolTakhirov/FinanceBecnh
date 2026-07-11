#!/usr/bin/env bash
# Clone the REAL official evaluators, at the commits our adapters pin, into a venv with their own
# dependencies. Parity means our metrics produce the same numbers as the published code; that claim
# is only worth anything if the published code is actually here, and is actually the right code.
#
# This script exists because the prose instructions it replaces were wrong in three ways at once:
#   - they omitted FinanceReasoning entirely (4 tests skipped forever),
#   - they omitted tqdm and loguru, which the official evaluators import (everything else errored),
#   - and they did not pin, so it was possible to clone BUPT-Reasoning/FinanceReasoning instead of
#     BUPT-Reasoning-LAB/FinanceReasoning — a different repo with different code, which produces two
#     failing parity tests that mean nothing at all.
#
# A skipped parity test reports comfort it has not earned. A parity test run against the wrong
# source reports a defect that does not exist. Both are worse than no test.
set -euo pipefail

R="${FINANCEBENCH_REFERENCES:-/tmp/financebench-references}"

# Pinned to exactly what src/financebench/datasets/*/adapter.py declares.
FINQA_URL="https://github.com/czyssrs/FinQA";                         FINQA_COMMIT="0f16e2867befa6840783e58be38c9efb9229d742"
TATQA_URL="https://github.com/NExTplusplus/TAT-QA";                   TATQA_COMMIT="870accc41953dcde885aabeb963d94aabdc0fbc3"
FR_URL="https://github.com/BUPT-Reasoning-Lab/FinanceReasoning";     FR_COMMIT="b0fe6455396f831955e4eb988472b4a563403bc5"

clone_at() {  # url, dir, commit
  local url="$1" dir="$2" commit="$3"
  if [ -d "$dir/.git" ]; then echo "  $dir already present"; return; fi
  git clone -q "$url" "$dir"
  # Best-effort pin: if the commit is unreachable (shallow/renamed), stay on the default branch and
  # SAY SO rather than pretending it was pinned.
  git -C "$dir" checkout -q "$commit" 2>/dev/null \
    || echo "  !! could not pin $dir to $commit — using default branch. Parity may not be exact."
}

mkdir -p "$R"
echo "Cloning official evaluators into $R"
clone_at "$FINQA_URL" "$R/finqa"           "$FINQA_COMMIT"
clone_at "$TATQA_URL" "$R/tatqa"           "$TATQA_COMMIT"
clone_at "$FR_URL"    "$R/financereasoning" "$FR_COMMIT"

echo "Building the official venv (their dependencies, not ours)"
[ -d "$R/official-venv" ] || python3 -m venv "$R/official-venv"
# tqdm and loguru are imported by FinQA's and FinanceReasoning's evaluators respectively. Omitting
# them does not skip the tests — it makes every one of them error on an import.
"$R/official-venv/bin/pip" install -q --upgrade pip
"$R/official-venv/bin/pip" install -q sympy numpy scipy pandas tqdm loguru

echo
echo "Done. Now run:  pytest tests/parity -q"
echo "Expect 17 passed, 0 skipped. A SKIP here means the setup did not take."

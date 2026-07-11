#!/usr/bin/env bash
# Entry point for the official-evaluator references used by the parity suite.
#
# The real script lives next to the tests it serves (tests/parity/setup_references.sh) so it cannot
# drift away from them. This is the path the acceptance commands and the README point at.
#
# Parity means our metrics reproduce the published evaluators' numbers. That claim is worth nothing
# unless the published code is actually present and is actually the RIGHT code — a skipped parity
# test reports comfort it has not earned, and one run against the wrong repository reports a defect
# that does not exist.
set -euo pipefail
exec bash "$(dirname "$0")/../tests/parity/setup_references.sh" "$@"

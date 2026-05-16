#!/usr/bin/env bash
set -euo pipefail

acp-evals run \
  --endpoint "ws://127.0.0.1:8010/api/acp/ws" \
  --suite "eval_sets/acp_smoke.json" \
  --json-report "reports/jetlinks-local.json" \
  --md-report "reports/jetlinks-local.md"

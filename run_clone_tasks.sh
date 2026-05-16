#!/usr/bin/env bash
# Run tmp_tasks/clone-* as a single dataset job on modal with sonnet + low effort.
set -u

HARBOR_BIN="${HARBOR_BIN:-/Users/ash/.local/bin/harbor}"
JOB_NAME="clone-eval-$(date +"%Y-%m-%d__%H-%M-%S")"
CONCURRENCY="${CONCURRENCY:-8}"

n=$(find tmp_tasks -mindepth 1 -maxdepth 1 -type d -name 'clone-*' | wc -l | tr -d ' ')
echo "==> running $n clone tasks on modal | model=sonnet effort=low concurrency=$CONCURRENCY"
echo "==> job: $JOB_NAME"

"$HARBOR_BIN" run \
  -p tmp_tasks \
  -a claude-code \
  -m sonnet \
  --ak "reasoning_effort=low" \
  -k 1 -n "$CONCURRENCY" -y \
  --env modal \
  --job-name "$JOB_NAME"

#!/usr/bin/env bash
# Run all tasks/clone-* sequentially on modal with sonnet + low effort.
# Each task is its own harbor job; logs land in jobs-clone-eval/<task>.log.
set -u

HARBOR_BIN="${HARBOR_BIN:-/Users/ash/.local/bin/harbor}"
JOB_ROOT="clone-eval-$(date +"%Y-%m-%d__%H-%M-%S")"
LOG_DIR="logs-$JOB_ROOT"
mkdir -p "$LOG_DIR"

tasks=(tasks/clone-*)
echo "==> running ${#tasks[@]} clone tasks on modal | model=sonnet effort=low"
echo "==> job prefix: $JOB_ROOT  | logs: $LOG_DIR/"

i=0
for tpath in "${tasks[@]}"; do
  i=$((i + 1))
  name="$(basename "$tpath")"
  job="${JOB_ROOT}__${name}"
  log="$LOG_DIR/$name.log"
  echo "[$i/${#tasks[@]}] $name -> $job"
  "$HARBOR_BIN" run \
    -p "$tpath" \
    -a claude-code \
    -m sonnet \
    --ak "reasoning_effort=low" \
    -k 1 -n 1 -y \
    --env modal \
    --job-name "$job" \
    > "$log" 2>&1
  rc=$?
  if [ $rc -ne 0 ]; then
    echo "    FAILED (rc=$rc) — see $log"
  fi
done

echo "==> done. logs in $LOG_DIR/"

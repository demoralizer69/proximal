#!/usr/bin/env bash
# create_dataset.sh — run the proximal/generate task K times and
# collect each trial's (html + png) artifacts into ./screenshots/<run-id>/.
#
# Harbor runs in the background; the script polls jobs/<run-id>/ every
# POLL_INTERVAL seconds and copies any newly-finished trial's artifacts
# into screenshots/ as soon as they're available, so screenshots/ fills
# up progressively instead of in one batch at the end.
#
# Usage: ./create_dataset.sh [K] [N_CONCURRENT]
#   K              number of attempts (default 100)
#   N_CONCURRENT   parallel trials (default 16)
#
# Env overrides:
#   HARBOR_BIN     path to harbor CLI (default /Users/ash/.local/bin/harbor)
#   MODEL          model name (default opus)
#   EFFORT         claude-code reasoning effort (default max)
#   ENV_BACKEND    environment backend (default modal)
#   TASK_PATH      task path (default tasks/generate)
#   SCREENSHOTS    output dir (default screenshots)
#   JOB_NAME       harbor job name (default auto-timestamp)
#   POLL_INTERVAL  seconds between copy-passes during the run (default 10)

set -euo pipefail

K="${1:-100}"
N_CONCURRENT="${2:-16}"

HARBOR_BIN="${HARBOR_BIN:-/Users/ash/.local/bin/harbor}"
MODEL="${MODEL:-opus}"
EFFORT="${EFFORT:-high}"
ENV_BACKEND="${ENV_BACKEND:-modal}"
TASK_PATH="${TASK_PATH:-tasks/generate}"
SCREENSHOTS="${SCREENSHOTS:-screenshots}"
JOB_NAME="${JOB_NAME:-$(date +"%Y-%m-%d__%H-%M-%S")}"
POLL_INTERVAL="${POLL_INTERVAL:-10}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ ! -x "$HARBOR_BIN" ]]; then
  echo "harbor CLI not found or not executable at $HARBOR_BIN" >&2
  exit 1
fi
if [[ ! -d "$TASK_PATH" ]]; then
  echo "task path not found: $TASK_PATH" >&2
  exit 1
fi

mkdir -p "$SCREENSHOTS"
mkdir -p jobs

JOB_DIR="jobs/$JOB_NAME"
DEST_ROOT="$SCREENSHOTS/$JOB_NAME"
mkdir -p "$DEST_ROOT"

# Copy any trials whose artifacts have landed and that haven't been
# copied yet. A trial is "ready" when both result.json and the
# artifacts manifest exist — harbor writes those at trial finalization,
# so this avoids racing the artifact download.
copy_ready_trials() {
  [[ -d "$JOB_DIR" ]] || return 0
  shopt -s nullglob
  for trial_dir in "$JOB_DIR"/*/; do
    local trial artifacts_dir dest
    trial="$(basename "$trial_dir")"
    artifacts_dir="${trial_dir}artifacts"
    # Done marker: trial finalized AND artifact manifest written.
    [[ -f "${trial_dir}result.json" ]] || continue
    [[ -f "$artifacts_dir/manifest.json" ]] || continue
    dest="$DEST_ROOT/$trial"
    # Already copied?
    [[ -d "$dest" ]] && continue
    mkdir -p "$dest"
    if [[ -f "$artifacts_dir/website_details.json" ]]; then
      cp "$artifacts_dir/website_details.json" "$dest/" || true
    fi
    if [[ -d "$artifacts_dir/pages" ]]; then
      cp -R "$artifacts_dir/pages/." "$dest/" || true
    fi
    local png_count
    png_count=$(find "$dest" -maxdepth 1 -name "*.png" | wc -l | tr -d ' ')
    printf '  + %s (%s png)\n' "$trial" "$png_count"
  done
  shopt -u nullglob
}

echo "==> Running $TASK_PATH | model=$MODEL effort=$EFFORT env=$ENV_BACKEND k=$K n=$N_CONCURRENT"
echo "==> job-name: $JOB_NAME"
echo "==> Polling $JOB_DIR every ${POLL_INTERVAL}s; copying finished trials into $DEST_ROOT"

"$HARBOR_BIN" run \
  -p "$TASK_PATH" \
  -a claude-code \
  -m "$MODEL" \
  --ak "reasoning_effort=$EFFORT" \
  -k "$K" \
  -n "$N_CONCURRENT" \
  -y \
  --env "$ENV_BACKEND" \
  --job-name "$JOB_NAME" &
HARBOR_PID=$!

# If the user interrupts, kill harbor, do one last copy pass, then exit.
cleanup_on_interrupt() {
  echo
  echo "==> Interrupted — killing harbor (pid $HARBOR_PID) and doing final copy pass"
  kill "$HARBOR_PID" 2>/dev/null || true
  wait "$HARBOR_PID" 2>/dev/null || true
  copy_ready_trials
  exit 130
}
trap cleanup_on_interrupt INT TERM

# Poll while harbor is alive.
while kill -0 "$HARBOR_PID" 2>/dev/null; do
  copy_ready_trials
  sleep "$POLL_INTERVAL"
done

# Reap harbor and capture its exit code (without tripping set -e).
set +e
wait "$HARBOR_PID"
rc=$?
set -e

# Final pass to catch any trial that finished between the last poll and
# harbor's exit.
copy_ready_trials

n_copied=$(find "$DEST_ROOT" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
echo "==> Done. $n_copied trials in $DEST_ROOT (harbor exit code $rc)"
exit "$rc"

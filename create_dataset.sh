#!/usr/bin/env bash
# create_dataset.sh — run the proximal/generate task K times and
# collect each trial's (html + png) artifacts into ./screenshots/<run-id>/.
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

echo "==> Running $TASK_PATH | model=$MODEL effort=$EFFORT env=$ENV_BACKEND k=$K n=$N_CONCURRENT"
echo "==> job-name: $JOB_NAME"

set -x
"$HARBOR_BIN" run \
  -p "$TASK_PATH" \
  -a claude-code \
  -m "$MODEL" \
  --ak "reasoning_effort=$EFFORT" \
  -k "$K" \
  -n "$N_CONCURRENT" \
  -y \
  --env "$ENV_BACKEND" \
  --job-name "$JOB_NAME"
rc=$?
set +x

JOB_DIR="jobs/$JOB_NAME"
if [[ ! -d "$JOB_DIR" ]]; then
  echo "expected job dir not found: $JOB_DIR" >&2
  exit "$rc"
fi

echo "==> Collecting artifacts from $JOB_DIR into $SCREENSHOTS/"

DEST_ROOT="$SCREENSHOTS/$JOB_NAME"
mkdir -p "$DEST_ROOT"

n_trials=0
n_pages=0
shopt -s nullglob
for trial_dir in "$JOB_DIR"/*/; do
  trial_name="$(basename "$trial_dir")"
  # Skip non-trial folders (e.g., logs)
  artifacts_dir="${trial_dir}steps/generate/artifacts"
  if [[ ! -d "$artifacts_dir" ]]; then
    continue
  fi
  dest="$DEST_ROOT/$trial_name"
  mkdir -p "$dest"

  if [[ -f "${artifacts_dir}/website_details.json" ]]; then
    cp "${artifacts_dir}/website_details.json" "$dest/"
  fi
  if [[ -d "${artifacts_dir}/pages" ]]; then
    cp -R "${artifacts_dir}/pages/." "$dest/"
  fi

  page_count=$(find "$dest" -maxdepth 1 -name "*.html" | wc -l | tr -d ' ')
  png_count=$(find "$dest" -maxdepth 1 -name "*.png" | wc -l | tr -d ' ')
  echo "  $trial_name: ${page_count} html, ${png_count} png"
  n_trials=$((n_trials + 1))
  n_pages=$((n_pages + page_count))
done
shopt -u nullglob

echo "==> Done. Collected $n_trials trials, $n_pages html files into $DEST_ROOT"
exit "$rc"

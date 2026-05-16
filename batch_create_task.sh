#!/usr/bin/env bash
# batch_create_task.sh — run make_clone_task for every subdirectory of a
# screenshots batch, producing tmp_tasks/clone_task_1, clone_task_2, ...
#
# Usage:
#   ./batch_create_task.sh <screenshots-batch-dir>
#
# Example:
#   ./batch_create_task.sh screenshots/2026-05-16__09-08-55

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $0 <screenshots-batch-dir>" >&2
  exit 2
fi

BATCH="${1%/}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAKE="$ROOT_DIR/make_clone_task.sh"

if [ ! -d "$BATCH" ]; then
  echo "batch dir not found: $BATCH" >&2
  exit 1
fi
if [ ! -x "$MAKE" ]; then
  echo "make_clone_task.sh not executable: $MAKE" >&2
  exit 1
fi

shopt -s nullglob
trials=("$BATCH"/*/)
if [ ${#trials[@]} -eq 0 ]; then
  echo "no trial subdirectories under $BATCH" >&2
  exit 1
fi

echo "==> batch: $BATCH (${#trials[@]} trials)"

i=0
for tdir in "${trials[@]}"; do
  i=$((i + 1))
  name="clone_task_$i"
  echo "[$i/${#trials[@]}] $tdir -> $name"
  "$MAKE" "${tdir%/}" "$name"
done

echo "==> done. ${#trials[@]} tasks created in tmp_tasks/"

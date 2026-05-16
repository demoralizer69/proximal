#!/usr/bin/env bash
# make_clone_task.sh — stamp tasks/clone_template/ into a concrete task by
# dropping screenshots into environment/target/.
#
# Usage:
#   ./make_clone_task.sh <screenshots-dir> [task-name]
#
# Example:
#   ./make_clone_task.sh screenshots/2026-05-16__09-00-00/trial-0001 clone-trial-0001
#
# Produces tmp_tasks/<task-name>/ ready to run with:
#   harbor run -p tmp_tasks/<task-name> -a claude-code -m opus

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $0 <screenshots-dir> [task-name]" >&2
  exit 2
fi

SRC="$1"
NAME="${2:-clone-$(basename "$SRC")}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE="$ROOT_DIR/tasks/clone_template"
DEST_DIR="$ROOT_DIR/tmp_tasks"
DEST="$DEST_DIR/$NAME"
mkdir -p "$DEST_DIR"

if [ ! -d "$SRC" ]; then
  echo "screenshots dir not found: $SRC" >&2
  exit 1
fi
if [ ! -d "$TEMPLATE" ]; then
  echo "template not found: $TEMPLATE" >&2
  exit 1
fi
if [ -e "$DEST" ]; then
  echo "destination already exists: $DEST" >&2
  exit 1
fi

shopt -s nullglob
pngs=("$SRC"/*.png)
if [ ${#pngs[@]} -eq 0 ]; then
  echo "no PNG screenshots in $SRC" >&2
  exit 1
fi

cp -R "$TEMPLATE" "$DEST"
rm -f "$DEST/environment/target/.gitkeep"
cp "${pngs[@]}" "$DEST/environment/target/"

# Patch the task name in task.toml so each instantiated task has a unique id.
python3 - "$DEST/task.toml" "$NAME" <<'PY'
import sys, pathlib
path, name = pathlib.Path(sys.argv[1]), sys.argv[2]
text = path.read_text()
text = text.replace('name = "proximal/clone-TEMPLATE"', f'name = "proximal/{name}"')
path.write_text(text)
PY

echo "==> created $DEST"
echo "    pages: $(ls "$DEST/environment/target/" | wc -l | tr -d ' ')"
echo "    run with: harbor run -p tmp_tasks/$NAME -a claude-code -m opus"

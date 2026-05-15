#!/bin/bash
# Minimal stub. The clone-step oracle (steps/clone/solution/solve.sh) emits
# byte-identical HTML; render.py is deterministic, so SSIM ~= 1.0 on oracle.
# If you change this stub, change steps/clone/solution/solve.sh in lockstep.
set -e
cat > /app/website.html <<'HTML'
<!doctype html>
<html lang="en"><head></head><body></body></html>
HTML

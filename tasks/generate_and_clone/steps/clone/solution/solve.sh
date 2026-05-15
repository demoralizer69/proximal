#!/bin/bash
# Must stay byte-identical to steps/generate/solution/solve.sh — render.py is
# deterministic, so the same HTML on both ends gives SSIM ~= 1.0.
# Step-2 setup.sh deleted /app/website.html, so the oracle cannot cp from it.
set -e
cat > /app/clone.html <<'HTML'
<!doctype html>
<html lang="en"><head></head><body></body></html>
HTML

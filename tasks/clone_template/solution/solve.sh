#!/bin/bash
# Trivial reference solution: for each target screenshot slug, write a stub
# HTML page so the verifier has something to render. SSIM will be very low —
# this exists to prove the task wiring works end-to-end.
set -e
mkdir -p /app/pages

shopt -s nullglob
for ref in /opt/target/*.png; do
  slug="$(basename "$ref" .png)"
  cat > "/app/pages/${slug}.html" <<HTML
<!doctype html>
<html><head><meta charset="utf-8"><title>${slug}</title>
<style>body{font-family:system-ui;margin:2rem;background:#fff;color:#111}</style>
</head><body><h1>${slug}</h1></body></html>
HTML
done

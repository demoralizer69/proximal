#!/bin/bash
# Trivial reference solution: for each target capture dir slug, write a stub
# HTML page with a single CSS spinner so the verifier has something animated
# to render. Score will be very low — this exists to prove the task wiring
# works end-to-end.
set -e
mkdir -p /app/pages

shopt -s nullglob
for d in /opt/target/*/; do
  slug="$(basename "$d")"
  cat > "/app/pages/${slug}.html" <<HTML
<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>${slug}</title>
<style>
  body{font-family:system-ui;margin:0;display:flex;align-items:center;justify-content:center;height:100vh;background:#fff;color:#111}
  @keyframes prox-spin { to { transform: rotate(360deg); } }
  .o{width:160px;height:160px;border-radius:50%;background:conic-gradient(#e95993,#3aa4ff,#e95993);animation:prox-spin 2s linear infinite}
</style></head>
<body><h1>${slug}</h1><div class="o"></div></body></html>
HTML
done

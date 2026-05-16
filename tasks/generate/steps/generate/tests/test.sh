#!/bin/bash
# Verifier for the generate task: render every HTML page the agent produced
# to a sibling PNG, then always emit a dummy reward of 1.0.
set -e
mkdir -p /logs/verifier
log=/logs/verifier/verifier.log
: > "$log"

write_reward() {
  printf "%.6f\n" "$1" > /logs/verifier/reward.txt
  echo "reward=$1"
}

if [ ! -d /app/pages ]; then
  echo "missing /app/pages directory" >> "$log"
  write_reward 1.0
  exit 0
fi

shopt -s nullglob
html_files=(/app/pages/*.html)
shopt -u nullglob

if [ "${#html_files[@]}" -eq 0 ]; then
  echo "no HTML files found in /app/pages" >> "$log"
  write_reward 1.0
  exit 0
fi

for html in "${html_files[@]}"; do
  base="$(basename "$html" .html)"
  png="/app/pages/${base}.png"
  if python3 /opt/render.py "$html" "$png" 2>>"$log"; then
    echo "rendered: $html -> $png" >> "$log"
  else
    echo "render failed for: $html (continuing)" >> "$log"
  fi
done

write_reward 1.0

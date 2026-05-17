#!/bin/bash
# Verifier for the animated generate task: for every HTML page the agent
# wrote to /app/pages, render it through Playwright into a sibling capture
# directory at /app/captures/<slug>/ containing frame_NN.png keyframes and
# a clip.webm. Always emit a dummy reward of 1.0.
set -e
mkdir -p /logs/verifier /app/captures
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
  out_dir="/app/captures/${base}"
  mkdir -p "$out_dir"
  if python3 /opt/render.py "$html" "$out_dir" 2>>"$log"; then
    echo "captured: $html -> $out_dir" >> "$log"
  else
    echo "render failed for: $html (continuing)" >> "$log"
  fi
done

write_reward 1.0

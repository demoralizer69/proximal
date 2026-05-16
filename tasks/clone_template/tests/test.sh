#!/bin/bash
# Verifier: for each target screenshot in /opt/target/<slug>.png, render the
# agent's /app/pages/<slug>.html via Playwright, compute SSIM, and average.
# Missing pages count as 0.
set -e
mkdir -p /logs/verifier /app/rendered
log=/logs/verifier/verifier.log
: > "$log"

write_reward() {
  printf "%.6f\n" "$1" > /logs/verifier/reward.txt
  echo "reward=$1"
}

if [ ! -d /opt/target ]; then
  echo "missing /opt/target (template not instantiated with screenshots)" >> "$log"
  write_reward 0.0
  exit 0
fi

shopt -s nullglob
targets=(/opt/target/*.png)
if [ ${#targets[@]} -eq 0 ]; then
  echo "no target screenshots in /opt/target" >> "$log"
  write_reward 0.0
  exit 0
fi

total=0
n=0
for ref in "${targets[@]}"; do
  slug="$(basename "$ref" .png)"
  html="/app/pages/${slug}.html"
  cand="/app/rendered/${slug}.png"
  n=$((n + 1))

  if [ ! -s "$html" ]; then
    echo "[$slug] missing $html -> 0.0" >> "$log"
    continue
  fi
  if ! python3 /opt/render.py "$html" "$cand" 2>>"$log"; then
    echo "[$slug] render failed -> 0.0" >> "$log"
    continue
  fi
  if ! score=$(python3 /opt/evaluate.py "$ref" "$cand" 2>>"$log"); then
    echo "[$slug] evaluate failed -> 0.0" >> "$log"
    continue
  fi
  echo "[$slug] ssim=$score" >> "$log"
  total=$(python3 -c "print($total + $score)")
done

if [ "$n" -eq 0 ]; then
  write_reward 0.0
else
  mean=$(python3 -c "print($total / $n)")
  write_reward "$mean"
fi

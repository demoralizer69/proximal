#!/bin/bash
# Verifier (animated): for each /opt/target/<slug>/ (containing 6 keyframes +
# a clip.webm), render the agent's /app/pages/<slug>.html into
# /app/rendered/<slug>/ via the same Playwright capture pipeline, then score
# the directory pair with the animated WebSight evaluator (per-frame static
# composite averaged across 6 frames, plus a delta-SSIM temporal term).
# Average across pages. Missing pages count as 0.
set -e
mkdir -p /logs/verifier /app/rendered
log=/logs/verifier/verifier.log
: > "$log"

write_reward() {
  printf "%.6f\n" "$1" > /logs/verifier/reward.txt
  echo "reward=$1"
}

if [ ! -d /opt/target ]; then
  echo "missing /opt/target (template not instantiated with captures)" >> "$log"
  write_reward 0.0
  exit 0
fi

shopt -s nullglob
slugs=()
for d in /opt/target/*/; do
  slugs+=("$(basename "$d")")
done
shopt -u nullglob

if [ ${#slugs[@]} -eq 0 ]; then
  echo "no per-slug capture directories in /opt/target" >> "$log"
  write_reward 0.0
  exit 0
fi

total=0
n=0
for slug in "${slugs[@]}"; do
  ref_dir="/opt/target/${slug}"
  html="/app/pages/${slug}.html"
  cand_dir="/app/rendered/${slug}"
  n=$((n + 1))

  if [ ! -s "$html" ]; then
    echo "[$slug] missing $html -> 0.0" >> "$log"
    continue
  fi
  mkdir -p "$cand_dir"
  if ! python3 /opt/render.py "$html" "$cand_dir" 2>>"$log"; then
    echo "[$slug] render failed -> 0.0" >> "$log"
    continue
  fi
  if ! score=$(python3 /opt/evaluate.py "$ref_dir" "$cand_dir" 2>>"$log"); then
    echo "[$slug] evaluate failed -> 0.0" >> "$log"
    continue
  fi
  echo "[$slug] score=$score" >> "$log"
  total=$(python3 -c "print($total + $score)")
done

if [ "$n" -eq 0 ]; then
  write_reward 0.0
else
  mean=$(python3 -c "print($total / $n)")
  write_reward "$mean"
fi

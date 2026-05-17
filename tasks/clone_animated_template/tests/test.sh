#!/bin/bash
# Verifier (animated): for each /opt/target/<slug>/ (containing 6 keyframes +
# a clip.webm), render the agent's /app/pages/<slug>.html into
# /app/rendered/<slug>/ via the same Playwright capture pipeline, then score
# the directory pair with the animated MAE evaluator (per-frame MAE plus a
# delta-MAE temporal term, each aggregated within-page with PM_p=0.05).
# Aggregate across pages with PM_p=0.05. Missing/failed pages contribute eps=1e-6.
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

scores_csv=""
n=0
for slug in "${slugs[@]}"; do
  ref_dir="/opt/target/${slug}"
  html="/app/pages/${slug}.html"
  cand_dir="/app/rendered/${slug}"
  n=$((n + 1))

  s="0.0"
  if [ ! -s "$html" ]; then
    echo "[$slug] missing $html -> 0.0" >> "$log"
  else
    mkdir -p "$cand_dir"
    if ! python3 /opt/render.py "$html" "$cand_dir" 2>>"$log"; then
      echo "[$slug] render failed -> 0.0" >> "$log"
    elif ! s=$(python3 /opt/evaluate.py "$ref_dir" "$cand_dir" 2>>"$log"); then
      echo "[$slug] evaluate failed -> 0.0" >> "$log"
      s="0.0"
    else
      echo "[$slug] score=$s" >> "$log"
    fi
  fi

  if [ -z "$scores_csv" ]; then
    scores_csv="$s"
  else
    scores_csv="$scores_csv,$s"
  fi
done

if [ "$n" -eq 0 ]; then
  write_reward 0.0
else
  reward=$(python3 - "$scores_csv" <<'PY'
import sys
P = 0.05
EPS = 1e-6
vs = [float(x) for x in sys.argv[1].split(",") if x != ""]
if not vs:
    print("0.0")
else:
    ys = [max(v, EPS) for v in vs]
    pm = (sum(y ** P for y in ys) / len(ys)) ** (1.0 / P)
    print(f"{pm:.6f}")
PY
)
  write_reward "$reward"
fi

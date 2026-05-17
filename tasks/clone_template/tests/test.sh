#!/bin/bash
# Verifier: for each target screenshot in /opt/target/<slug>.png, render the
# agent's /app/pages/<slug>.html via Playwright, compute the per-page pixel-MAE
# similarity (1 - MAE/255) via /opt/evaluate.py, then aggregate across pages
# with generalized power mean PM_p (p=0.05). Missing/failed pages are treated
# as 0 and contribute eps=1e-6 to the PM (PM is undefined at zero).
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

scores_csv=""
n=0
for ref in "${targets[@]}"; do
  slug="$(basename "$ref" .png)"
  html="/app/pages/${slug}.html"
  cand="/app/rendered/${slug}.png"
  n=$((n + 1))

  s="0.0"
  if [ ! -s "$html" ]; then
    echo "[$slug] missing $html -> 0.0" >> "$log"
  elif ! python3 /opt/render.py "$html" "$cand" 2>>"$log"; then
    echo "[$slug] render failed -> 0.0" >> "$log"
  elif ! s=$(python3 /opt/evaluate.py "$ref" "$cand" 2>>"$log"); then
    echo "[$slug] evaluate failed -> 0.0" >> "$log"
    s="0.0"
  else
    echo "[$slug] score=$s" >> "$log"
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

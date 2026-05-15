#!/bin/bash
# Step-2 verifier: render the agent's clone.html via Playwright, compute SSIM
# against the target screenshot, write the score to /logs/verifier/reward.txt.
set -e
mkdir -p /logs/verifier
log=/logs/verifier/verifier.log
: > "$log"

write_reward() {
  printf "%.6f\n" "$1" > /logs/verifier/reward.txt
  echo "reward=$1"
}

if [ ! -f /app/webpage.png ]; then
  echo "missing /app/webpage.png (step-clone setup failed?)" >> "$log"
  write_reward 0.0
  exit 0
fi
if [ ! -s /app/clone.html ]; then
  echo "missing /app/clone.html (agent did not produce output)" >> "$log"
  write_reward 0.0
  exit 0
fi

if ! python3 /opt/render.py /app/clone.html /app/clone.png 2>>"$log"; then
  echo "playwright render failed" >> "$log"
  write_reward 0.0
  exit 0
fi

SCORE=$(python3 /opt/evaluate.py /app/webpage.png /app/clone.png 2>>"$log") || {
  echo "evaluate.py failed" >> "$log"
  write_reward 0.0
  exit 0
}
echo "ssim=$SCORE" >> "$log"
write_reward "$SCORE"

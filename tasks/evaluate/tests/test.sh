#!/bin/bash
# Verifier: run all evaluators on /opt/target vs /opt/candidate.
# run_evaluators.py writes /app/metrics.json and /logs/verifier/reward.txt.
set -e
mkdir -p /logs/verifier
log=/logs/verifier/verifier.log
: > "$log"

if ! python3 /opt/run_evaluators.py >>"$log" 2>&1; then
  echo "evaluation failed, see $log" >&2
  tail -n 40 "$log" >&2 || true
  printf "0.0\n" > /logs/verifier/reward.txt
  exit 1
fi

reward=$(cat /logs/verifier/reward.txt)
echo "reward=$reward"

#!/usr/bin/env bash
# Run all tasks in tmp_tasks/ as a single dataset job on modal, then as each
# trial finishes, copy its target screenshots + rendered output + reward into
# outputs/<job-name>/<task>/. Polls every 10s.
set -u

HARBOR_BIN="${HARBOR_BIN:-harbor}"
MODEL="${MODEL:-sonnet}"
EFFORT="${EFFORT:-low}"
POLL_SEC="${POLL_SEC:-10}"
JOB_NAME="clone-eval-$(date +"%Y-%m-%d__%H-%M-%S")"

n=$(find tmp_tasks -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
CONCURRENCY="${CONCURRENCY:-$n}"

JOB_DIR="jobs/$JOB_NAME"
OUT_DIR="outputs/$JOB_NAME"
mkdir -p "$OUT_DIR"
HARBOR_LOG="$OUT_DIR/_harbor.log"

echo "==> running $n tasks on modal | model=$MODEL effort=$EFFORT concurrency=$CONCURRENCY"
echo "==> job:     $JOB_NAME"
echo "==> outputs: $OUT_DIR"
echo "==> harbor log: $HARBOR_LOG"

"$HARBOR_BIN" run \
  -p tmp_tasks \
  -a claude-code \
  -m "$MODEL" \
  --ak "reasoning_effort=$EFFORT" \
  -k 1 -n "$CONCURRENCY" -y \
  --env modal \
  --job-name "$JOB_NAME" \
  > "$HARBOR_LOG" 2>&1 &
HARBOR_PID=$!

cleanup() {
  if kill -0 "$HARBOR_PID" 2>/dev/null; then
    echo "==> interrupted, stopping harbor (pid $HARBOR_PID)"
    kill "$HARBOR_PID" 2>/dev/null || true
  fi
}
trap cleanup INT TERM

seen_file="$(mktemp)"
trap 'rm -f "$seen_file"' EXIT

collect_new_trials() {
  [ -d "$JOB_DIR" ] || return 0
  for tdir in "$JOB_DIR"/*__*/; do
    [ -d "$tdir" ] || continue
    [ -f "$tdir/result.json" ] || continue
    key=$(basename "$tdir")
    if grep -qx "$key" "$seen_file" 2>/dev/null; then continue; fi
    echo "$key" >> "$seen_file"
    python3 - "$tdir" "$OUT_DIR" <<'PY'
import json, sys, shutil, pathlib
trial_dir = pathlib.Path(sys.argv[1])
out_root = pathlib.Path(sys.argv[2])
d = json.load(open(trial_dir / "result.json"))
task_path = pathlib.Path(d["config"]["task"]["path"])
task_name = task_path.name
v = d.get("verifier_result") or {}
reward = (v.get("rewards") or {}).get("reward")
exc = d.get("exception_info")
out = out_root / task_name
out.mkdir(parents=True, exist_ok=True)
(out / "reward.txt").write_text(f"{reward:.6f}\n" if reward is not None else "FAILED\n")
if exc:
    (out / "error.txt").write_text((exc.get("exception_message") or "")[:2000])
src_screens = task_path / "environment" / "target"
dst_screens = out / "screenshots"
dst_screens.mkdir(exist_ok=True)
if src_screens.is_dir():
    for p in src_screens.glob("*.png"):
        shutil.copy2(p, dst_screens / p.name)
src_rendered = trial_dir / "artifacts" / "rendered"
dst_rendered = out / "rendered"
dst_rendered.mkdir(exist_ok=True)
if src_rendered.is_dir():
    for p in src_rendered.glob("*.png"):
        shutil.copy2(p, dst_rendered / p.name)
status = f"reward={reward:.4f}" if reward is not None else "FAILED"
print(f"[+] {task_name:24s} {status}", flush=True)
PY
  done
}

while kill -0 "$HARBOR_PID" 2>/dev/null; do
  sleep "$POLL_SEC"
  collect_new_trials
done

wait "$HARBOR_PID" 2>/dev/null || true
collect_new_trials  # final sweep

echo "==> done. outputs in $OUT_DIR"
echo "    view: python3 view_outputs.py"

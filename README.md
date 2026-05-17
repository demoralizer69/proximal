# proximal

Generate synthetic website screenshots with an LLM agent, then have agents try to clone them back into HTML, and score the result with image-similarity evaluators.

The repo is wired around three top-level commands. Helper scripts live under `helper_scripts/` and are not normally run directly.

---

## Requirements

- **harbor CLI** — the agent harness this repo wraps. Install per its own docs and make sure `harbor` is on your `$PATH` (or set `HARBOR_BIN=/path/to/harbor`).
- **Modal account** — all three commands use `--env modal` to run the actual containers. You must be logged in (`modal token new`) and have credits/billing set up.
- **Python 3** — needed only for the local viewer webservers; no third-party packages required.
- **Docker** — only required if you want to rebuild the shared base image (`tasks/generate/environment/Dockerfile.base`). The image is published as `ghcr.io/demoralizer69/proximal-genclone-base:v2` and harbor will pull it automatically on first run.

All Python dependencies used by tasks (torch, piq, playwright, tesseract, …) are baked into the base image — you do not install them locally.

---

## 1. `create_dataset.sh` — generate a screenshot dataset

```bash
./create_dataset.sh [K] [N_CONCURRENT]
```

Runs the `proximal/generate` task `K` times in parallel and drops each trial's rendered pages into `screenshots/<job-name>/<trial-id>/*.png`.

Defaults: `K=100`, `N_CONCURRENT=16`, `MODEL=opus`, `EFFORT=high`. Override via env:

```bash
K=20 MODEL=sonnet EFFORT=low ./create_dataset.sh 20 8
```

The script streams results: trials are copied into `screenshots/` as they finish, not in one batch at the end, so you can start using a partial dataset while the rest is still generating. Ctrl+C kills the harbor job and does one final copy pass.

---

## 2. `run_tasks` — have agents clone the screenshots back into HTML

```bash
EFFORT=low ./run_tasks <screenshots-batch-dir> <nickname>
```

Example:

```bash
EFFORT=low ./run_tasks screenshots/2026-05-16__09-08-55 may16-run
```

For every trial subdir of `<screenshots-batch-dir>`, this stamps a fresh `tasks/clone_template` instance with those PNGs as the target, runs them all as one harbor job, and copies each agent's rendered output + reward into `outputs/<nickname>-<timestamp>/<task>/trial_<id>/`.

Useful env knobs:

| var | default | purpose |
|---|---|---|
| `MODEL` | `sonnet` | agent model |
| `EFFORT` | `low` | claude-code reasoning effort |
| `TRIALS` | `1` | how many independent attempts per task |
| `CONCURRENCY` | `min(tasks*trials, 60)` | parallel modal containers |
| `KEEP_TASKS` | `0` | keep the stamped `tmp_tasks/` after the run |

Reward is the per-task mean of the WebSight composite score (MS-SSIM + LPIPS + OCR F1) across that task's pages, computed inside the container by `tasks/clone_template/environment/evaluate.py`.

---

## 3. `inspect_results` — browse screenshots and outputs in the browser

```bash
./inspect_results [screenshots_port] [outputs_port]
```

Starts two tiny webservers side by side. Default ports `8765` (screenshots) and `8766` (outputs):

- **`http://localhost:8765`** — slideshow viewer for everything under `screenshots/<job>/<trial>/`.
- **`http://localhost:8766`** — side-by-side comparison of target vs. each trial's render, ranked by score, with sortable metric chips (WebSight / MS-SSIM / LPIPS / DISTS — see next section).

Ctrl+C stops both. If either viewer exits on its own, the other is taken down too.

---

## 4. `evaluate_outputs` *(optional)* — score outputs with extra evaluators

The reward written by `run_tasks` only contains the single WebSight composite score. If you want every evaluator's score (DISTS, LPIPS, MS-SSIM, WebSight) on each (target, rendered) PNG pair — handy for ablations or for picking a better reward metric — re-evaluate an existing job:

```bash
./helper_scripts/evaluate_outputs outputs/<job-dir> [nickname]
```

Example:

```bash
./helper_scripts/evaluate_outputs outputs/may16-run-2026-05-16__09-50-21
```

This stamps one harbor task per (task, trial) using the `tasks/evaluate` template (no agent — `--agent nop`; the verifier just runs every evaluator in `evaluators/`), bakes the target + candidate PNGs into the image, runs them all on modal, and copies each `metrics.json` back next to the trial under `outputs/<job>/<task>/<trial>/metrics.json`. The metric viewer in `inspect_results` picks these up automatically.

To add a new evaluator: drop an `evaluator.py` under `evaluators/<name>/` that takes `argv[1]=ref.png argv[2]=cand.png` and prints one float in `[0,1]` on stdout. The runner inside `tasks/evaluate/environment/run_evaluators.py` discovers them by directory name.

---

## 5. `ANIMATED=1` — generate and clone CSS-only animated sites

All three top-level commands accept `ANIMATED=1` to swap the whole pipeline from static screenshots to animated captures. Each page is rendered for a fixed **3-second window starting at first paint**: 6 viewport keyframes are sampled at t = 0.0, 0.5, 1.0, 1.5, 2.0, 2.5 s, and a continuous `clip.webm` is recorded alongside them.

```bash
# 1. Generate an animated dataset (uses tasks/generate_animated)
ANIMATED=1 ./create_dataset.sh 20 8

# 2. Have agents clone it (uses tasks/clone_animated_template)
ANIMATED=1 EFFORT=low ./run_tasks screenshots/<job-id> animated-run

# 3. Browse — the viewers pick up the animated layout automatically
./inspect_results
```

What `ANIMATED=1` actually changes:

It invokes an entirely different pipeline under the hood, different generator, cloner, evaluator.

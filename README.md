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

## What's actually happening under the hood

`proximal` is mostly orchestration glue around the harbor CLI:

1. **Stamping tasks.** `tasks/clone_template/` and `tasks/evaluate/` are *templates*. The top-level commands copy them into `tmp_tasks/` (or `tmp_eval_tasks/`) per-input, drop the relevant PNGs into `environment/target/` (and `environment/candidate/` for evaluate), and patch `task.toml` so each stamped task has a unique `proximal/<name>` id.
2. **Running on Modal.** Each script invokes `harbor run -p <task-dir> --env modal -k <trials> -n <concurrency> -y --job-name <name>` in the background. Harbor builds the per-task image (from `ghcr.io/demoralizer69/proximal-genclone-base:v2`), spins up one Modal container per (task × trial), and runs the agent inside.
3. **Polling for results.** While harbor is alive, the launcher polls `jobs/<job-name>/` every ~10s. As soon as a trial finalizes (`result.json` + `artifacts/manifest.json` appear), the script copies its outputs into the right destination (`screenshots/…` for generate, `outputs/…` for clone/evaluate) and prints a one-line status. A trial finished mid-run is visible *before* the whole job finishes.
4. **Scoring.** Inside the clone container, after the agent quits, the harbor verifier renders the agent's HTML via Playwright (`render.py`) and pipes each (target, candidate) pair through `evaluate.py`, which prints the page's score on stdout. The mean is written to `/logs/verifier/reward.txt` and surfaces as the trial's "reward" in `result.json`. The optional `evaluate_outputs` step re-runs *all four* evaluators on those same PNG pairs after the fact.
5. **Cleanup.** Unless `KEEP_TASKS=1`, the stamped `tmp_tasks/` and `tmp_eval_tasks/` are deleted after the job finishes — `screenshots/`, `outputs/`, and `jobs/` are the permanent artifacts.

The base image (`ghcr.io/demoralizer69/proximal-genclone-base:v2`) bakes in everything heavy: Playwright + Chromium, torch + torchvision (CPU), `piq` for MS-SSIM / LPIPS / DISTS, and `tesseract-ocr` + `pytesseract` for the WebSight OCR F1 component. The image source lives in `tasks/generate/environment/Dockerfile.base`; to publish a new tag, build it for `linux/amd64` and push to GHCR.

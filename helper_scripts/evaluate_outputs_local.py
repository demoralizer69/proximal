#!/usr/bin/env python3
"""Re-evaluate every (target, candidate) PNG pair under outputs/<job>/ using
all evaluators in evaluators/ — locally, without Modal. Writes metrics.json
into each trial dir, same shape as the harbor-run evaluate_outputs.

Usage:
    .venv/bin/python helper_scripts/evaluate_outputs_local.py outputs/<job-dir> [--only METRICS]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVALUATORS_DIR = ROOT / "evaluators"


def _aggregate(vs: list[float], p: float | None, eps: float = 1e-6) -> float | None:
    """Combine per-page scores. p=None or p=1 -> arithmetic mean; otherwise
    generalized power mean PM_p over max(v, eps)."""
    if not vs:
        return None
    if p is None or p == 1.0:
        return sum(vs) / len(vs)
    ys = [max(v, eps) for v in vs]
    return (sum(y ** p for y in ys) / len(ys)) ** (1.0 / p)


def load_evaluators(only: set[str] | None = None) -> dict:
    out = {}
    for d in sorted(EVALUATORS_DIR.iterdir()):
        if not d.is_dir() or not (d / "evaluator.py").exists():
            continue
        if only and d.name not in only:
            continue
        if d.name == "animated_websight":
            # different contract (dir, not png)
            continue
        spec = importlib.util.spec_from_file_location(f"ev_{d.name}", d / "evaluator.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if not hasattr(mod, "score"):
            print(f"skipping {d.name}: no score() function", file=sys.stderr)
            continue
        out[d.name] = mod
    return out


def collect_pairs(job: Path) -> list[tuple[Path, Path, Path, str]]:
    """Return list of (trial_dir, target_png, cand_png, slug)."""
    pairs = []
    for task_dir in sorted(job.iterdir()):
        if not task_dir.is_dir():
            continue
        sdir = task_dir / "screenshots"
        if not sdir.is_dir():
            continue
        targets = sorted(sdir.glob("*.png"))
        if not targets:
            continue
        trial_subs = sorted(d for d in task_dir.iterdir() if d.is_dir() and d.name.startswith("trial_"))
        if trial_subs:
            for td in trial_subs:
                rdir = td / "rendered"
                if not rdir.is_dir():
                    continue
                for t in targets:
                    c = rdir / f"{t.stem}.png"
                    pairs.append((td, t, c if c.exists() else None, t.stem))
        else:
            rdir = task_dir / "rendered"
            if rdir.is_dir():
                for t in targets:
                    c = rdir / f"{t.stem}.png"
                    pairs.append((task_dir, t, c if c.exists() else None, t.stem))
    return pairs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("job_dir")
    ap.add_argument("--only", help="comma-separated metric names to compute")
    ap.add_argument("--force", action="store_true", help="re-score metrics already present")
    args = ap.parse_args()

    job = Path(args.job_dir).resolve()
    if not job.is_dir():
        print(f"not a dir: {job}", file=sys.stderr)
        return 2

    only = set(args.only.split(",")) if args.only else None
    evaluators = load_evaluators(only)
    if not evaluators:
        print("no evaluators loaded", file=sys.stderr)
        return 1
    print(f"loaded: {sorted(evaluators)}", file=sys.stderr)

    pairs = collect_pairs(job)
    print(f"{len(pairs)} (target, candidate) pairs across all trials", file=sys.stderr)

    by_trial: dict[Path, list] = {}
    for td, t, c, slug in pairs:
        by_trial.setdefault(td, []).append((t, c, slug))

    t0 = time.time()
    trials_done = 0
    for td, items in by_trial.items():
        out_path = td / "metrics.json"
        existing = {}
        if out_path.exists():
            try:
                existing = json.loads(out_path.read_text())
            except Exception:
                existing = {}
        per_page = dict(existing.get("per_page") or {})
        metric_values: dict[str, list[float]] = {}
        missing = list(existing.get("missing") or [])
        for t, c, slug in items:
            scores = dict(per_page.get(slug) or {})
            if c is None:
                if slug not in missing:
                    missing.append(slug)
                for name in evaluators:
                    scores.setdefault(name, None)
                per_page[slug] = scores
                continue
            for name, mod in evaluators.items():
                if not args.force and scores.get(name) is not None:
                    metric_values.setdefault(name, []).append(scores[name])
                    continue
                try:
                    s = float(mod.score(str(t), str(c)))
                except Exception as e:
                    print(f"[{td.name}/{slug}] {name} failed: {e}", file=sys.stderr)
                    traceback.print_exc()
                    s = None
                scores[name] = s
                if s is not None:
                    metric_values.setdefault(name, []).append(s)
            per_page[slug] = scores

        # carry forward any pre-existing metrics for slugs we didn't touch
        for slug, scs in per_page.items():
            for name, v in scs.items():
                if v is None or name in evaluators:
                    continue
                metric_values.setdefault(name, []).append(v)

        aggregate = dict(existing.get("aggregate") or {})
        for name, vs in metric_values.items():
            p = getattr(evaluators.get(name), "AGGREGATE_P", None) if name in evaluators else None
            aggregate[name] = _aggregate(vs, p)

        out = {"per_page": per_page, "aggregate": aggregate, "missing": missing}
        out_path.write_text(json.dumps(out, indent=2))
        trials_done += 1
        dt = time.time() - t0
        rate = trials_done / dt if dt > 0 else 0
        eta = (len(by_trial) - trials_done) / rate if rate > 0 else 0
        print(
            f"[{trials_done}/{len(by_trial)}] {td.parent.name}/{td.name}  "
            f"elapsed={dt:.0f}s rate={rate:.2f}/s eta={eta:.0f}s",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())

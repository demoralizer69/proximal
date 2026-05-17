#!/usr/bin/env python3
"""For a job dir under outputs/, find tasks where different metrics disagree
about which trial is best. Prints a JSON list of conflict cases that we can
hand off to subagents to judge.

A "conflict" here means: for the same task, two different metrics each pick
a *different* top-1 trial, and the score gap on each metric (best vs second)
is large enough to be a real preference (not noise).

Usage:
    python3 helper_scripts/find_ranking_conflicts.py outputs/<job-dir> [--min-gap 0.05] [--top N]
"""
from __future__ import annotations

import argparse
import json
from itertools import combinations
from pathlib import Path


METRICS = [
    "websight", "ms_ssim", "ssim", "lpips", "dists",
    "mae", "psnr", "nemd", "ciede2000", "ocr_text",
]


def trial_metrics(task_dir: Path) -> dict[str, dict[str, float]]:
    """Return {trial_id: {metric: value}}."""
    out = {}
    for td in sorted(task_dir.iterdir()):
        if not td.is_dir() or not td.name.startswith("trial_"):
            continue
        mp = td / "metrics.json"
        if not mp.exists():
            continue
        try:
            data = json.loads(mp.read_text())
        except Exception:
            continue
        agg = data.get("aggregate") or {}
        out[td.name] = {m: agg.get(m) for m in METRICS}
    return out


def best_with_gap(rows: dict[str, dict[str, float]], metric: str) -> tuple[str, float, float] | None:
    """Return (best_trial, best_score, gap_to_second) for given metric, or None."""
    vals = [(t, r.get(metric)) for t, r in rows.items() if r.get(metric) is not None]
    if len(vals) < 2:
        return None
    vals.sort(key=lambda x: -x[1])
    return vals[0][0], vals[0][1], vals[0][1] - vals[1][1]


def find_conflicts(job: Path, min_gap: float, top_n: int) -> list[dict]:
    cases = []
    for task_dir in sorted(job.iterdir()):
        if not task_dir.is_dir():
            continue
        rows = trial_metrics(task_dir)
        if len(rows) < 2:
            continue
        # best trial per metric
        best_by_metric = {}
        for m in METRICS:
            b = best_with_gap(rows, m)
            if b is not None:
                best_by_metric[m] = b
        if not best_by_metric:
            continue
        # find pairs of metrics that disagree on top-1
        for m1, m2 in combinations(best_by_metric.keys(), 2):
            t1, v1, g1 = best_by_metric[m1]
            t2, v2, g2 = best_by_metric[m2]
            if t1 == t2:
                continue
            if g1 < min_gap or g2 < min_gap:
                continue
            cases.append({
                "task": task_dir.name,
                "metric_a": m1,
                "winner_a": t1,
                "winner_a_score_a": v1,
                "winner_a_gap_a": g1,
                "winner_a_score_b": rows[t1].get(m2),
                "metric_b": m2,
                "winner_b": t2,
                "winner_b_score_b": v2,
                "winner_b_gap_b": g2,
                "winner_b_score_a": rows[t2].get(m1),
                "all_rows": rows,
                "conflict_strength": min(g1, g2),
            })
    cases.sort(key=lambda c: -c["conflict_strength"])
    return cases[:top_n]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("job_dir")
    ap.add_argument("--min-gap", type=float, default=0.04)
    ap.add_argument("--top", type=int, default=30)
    args = ap.parse_args()
    job = Path(args.job_dir).resolve()
    cases = find_conflicts(job, args.min_gap, args.top)
    print(json.dumps(cases, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""For a job dir, find tasks where the top-1 trial disagrees across metrics.

For each task with >=3 trials:
  - For each metric, find its top-1 trial.
  - If two different metrics pick different trials AND the conflict is
    decisive (gap to the *other* trial > min_gap on each metric), report.

Output is a compact list, one row per (task, metric_a, metric_b) conflict,
ready to drive subagent dispatch.
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


def trial_metrics(task_dir: Path) -> dict[str, dict[str, float | None]]:
    out = {}
    for td in sorted(task_dir.iterdir()):
        if not td.is_dir() or not td.name.startswith("trial_"):
            continue
        mp = td / "metrics.json"
        if not mp.exists():
            continue
        try:
            agg = (json.loads(mp.read_text()).get("aggregate") or {})
        except Exception:
            continue
        # derive ocr_text from websight when not present
        if agg.get("ocr_text") is None:
            ms = agg.get("ms_ssim"); lp = agg.get("lpips"); ws = agg.get("websight")
            if ms is not None and lp is not None and ws is not None:
                agg["ocr_text"] = max(0.0, min(1.0, 3.0 * ws - ms - lp))
        out[td.name] = {m: agg.get(m) for m in METRICS}
    return out


def rank(rows, metric):
    vals = [(t, r[metric]) for t, r in rows.items() if r[metric] is not None]
    vals.sort(key=lambda x: -x[1])
    return vals


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job_dir")
    ap.add_argument("--min-gap", type=float, default=0.02)
    ap.add_argument("--top", type=int, default=50)
    args = ap.parse_args()
    job = Path(args.job_dir).resolve()
    conflicts = []
    for task_dir in sorted(job.iterdir()):
        if not task_dir.is_dir():
            continue
        rows = trial_metrics(task_dir)
        if len(rows) < 3:
            continue
        for ma, mb in combinations(METRICS, 2):
            ra = rank(rows, ma)
            rb = rank(rows, mb)
            if len(ra) < 2 or len(rb) < 2:
                continue
            if ra[0][0] == rb[0][0]:
                continue
            # gap on metric A between A-winner and B-winner
            sa_a, sa_b = dict(ra)[ra[0][0]], dict(ra).get(rb[0][0])
            sb_a, sb_b = dict(rb).get(ra[0][0]), dict(rb)[rb[0][0]]
            if None in (sa_a, sa_b, sb_a, sb_b):
                continue
            gap_a = sa_a - sa_b  # how much metric A prefers its winner
            gap_b = sb_b - sb_a  # how much metric B prefers its winner
            if gap_a < args.min_gap or gap_b < args.min_gap:
                continue
            conflicts.append({
                "task": task_dir.name,
                "metric_a": ma,
                "winner_a": ra[0][0],
                "winner_a_score_on_a": sa_a,
                "winner_a_score_on_b": sb_a,
                "metric_b": mb,
                "winner_b": rb[0][0],
                "winner_b_score_on_b": sb_b,
                "winner_b_score_on_a": sa_b,
                "gap_a": gap_a,
                "gap_b": gap_b,
                "strength": min(gap_a, gap_b),
            })
    conflicts.sort(key=lambda c: -c["strength"])
    conflicts = conflicts[: args.top]
    print(json.dumps(conflicts, indent=2, default=str))


if __name__ == "__main__":
    main()

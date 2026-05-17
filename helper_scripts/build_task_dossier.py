#!/usr/bin/env python3
"""Build a "dossier" for a task: for each trial under that task, list per-metric
aggregate scores and identify the union of metric-winners. Output as compact
text that an LLM-vision subagent can use to judge ranking conflicts.

Usage:
    python3 helper_scripts/build_task_dossier.py outputs/<job-dir>/<task-name>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

METRICS = [
    "websight", "ms_ssim", "ssim", "lpips", "dists",
    "mae", "psnr", "nemd", "ciede2000", "ocr_text",
]


def load_trial_metrics(td: Path) -> dict[str, float | None]:
    mp = td / "metrics.json"
    if not mp.exists():
        return {}
    try:
        agg = (json.loads(mp.read_text()).get("aggregate") or {})
    except Exception:
        return {}
    if agg.get("ocr_text") is None:
        ms = agg.get("ms_ssim"); lp = agg.get("lpips"); ws = agg.get("websight")
        if ms is not None and lp is not None and ws is not None:
            agg["ocr_text"] = max(0.0, min(1.0, 3.0 * ws - ms - lp))
    return agg


def main():
    if len(sys.argv) != 2:
        print("usage: build_task_dossier.py <task-dir>", file=sys.stderr)
        sys.exit(2)
    td = Path(sys.argv[1]).resolve()

    sdir = td / "screenshots"
    targets = sorted(p.name for p in sdir.glob("*.png"))

    trials = sorted(d for d in td.iterdir() if d.is_dir() and d.name.startswith("trial_"))
    rows = []
    for tr in trials:
        agg = load_trial_metrics(tr)
        if not agg:
            continue
        rows.append((tr.name, tr, agg))

    if not rows:
        print(f"no trials with metrics for {td}", file=sys.stderr)
        sys.exit(1)

    # Per-metric winner
    winners = {}
    for m in METRICS:
        vals = [(n, a.get(m)) for n, _, a in rows if a.get(m) is not None]
        if not vals:
            continue
        vals.sort(key=lambda x: -x[1])
        winners[m] = vals[0][0]

    # Identify "top-set": union of winners across metrics
    top_set = sorted(set(winners.values()))

    print(f"# Task: {td.name}")
    print(f"# Job:  {td.parent.name}")
    print(f"# Pages (targets): {targets}")
    print()
    print("## Per-trial aggregate scores")
    header = ["trial"] + METRICS
    print("\t".join(header))
    for n, _, agg in rows:
        cells = [n]
        for m in METRICS:
            v = agg.get(m)
            cells.append("—" if v is None else f"{v:.3f}")
        print("\t".join(cells))
    print()
    print("## Per-metric winner (top-1)")
    for m in METRICS:
        w = winners.get(m)
        print(f"  {m:12s} -> {w}")
    print()
    print(f"## Trials in the winning-set ({len(top_set)} unique top-1 across metrics)")
    for n in top_set:
        # Which metrics pick this trial?
        ms = [m for m, w in winners.items() if w == n]
        print(f"  {n:20s}  preferred by: {', '.join(ms)}")
    print()
    print(f"## Screenshots (target)")
    for p in targets:
        print(f"  {td}/screenshots/{p}")
    print()
    print(f"## Renders for trials in winning-set")
    for n in top_set:
        for p in targets:
            f = td / n / "rendered" / p
            if f.exists():
                print(f"  {f}")
            else:
                print(f"  MISSING: {f}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Run every evaluator under /opt/evaluators on each <slug>.png pair in
/opt/target vs /opt/candidate.

Writes:
    /app/metrics.json             { per_page: {slug: {metric: score|None}},
                                    aggregate: {metric: mean},
                                    missing: [slug, ...] }
    /logs/verifier/reward.txt     overall reward = aggregate.websight
"""
from __future__ import annotations

import importlib.util
import json
import sys
import traceback
from pathlib import Path

EVALUATORS_DIR = Path("/opt/evaluators")
TARGET_DIR = Path("/opt/target")
CANDIDATE_DIR = Path("/opt/candidate")
METRICS_OUT = Path("/app/metrics.json")
REWARD_OUT = Path("/logs/verifier/reward.txt")
REWARD_METRIC = "websight"


def load_evaluator(name: str):
    spec = importlib.util.spec_from_file_location(
        f"evaluator_{name}", EVALUATORS_DIR / name / "evaluator.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _aggregate(vs: list[float], p: float | None, eps: float = 1e-6) -> float:
    """Combine per-page scores. p=None or p=1 -> arithmetic mean; otherwise
    generalized power mean PM_p over max(v, eps)."""
    if not vs:
        return 0.0
    if p is None or p == 1.0:
        return sum(vs) / len(vs)
    ys = [max(v, eps) for v in vs]
    return (sum(y ** p for y in ys) / len(ys)) ** (1.0 / p)


def main() -> int:
    REWARD_OUT.parent.mkdir(parents=True, exist_ok=True)
    METRICS_OUT.parent.mkdir(parents=True, exist_ok=True)

    evaluators = {}
    for d in sorted(EVALUATORS_DIR.iterdir()):
        if d.is_dir() and (d / "evaluator.py").exists():
            evaluators[d.name] = load_evaluator(d.name)
    if not evaluators:
        print("no evaluators found under /opt/evaluators", file=sys.stderr)
        return 1

    targets = sorted(TARGET_DIR.glob("*.png"))
    if not targets:
        print("no target pngs under /opt/target", file=sys.stderr)
        return 1

    per_page: dict[str, dict[str, float | None]] = {}
    metric_values: dict[str, list[float]] = {m: [] for m in evaluators}
    missing: list[str] = []

    for ref in targets:
        slug = ref.stem
        cand = CANDIDATE_DIR / f"{slug}.png"
        scores: dict[str, float | None] = {}
        if not cand.exists():
            missing.append(slug)
            for name in evaluators:
                scores[name] = None
            per_page[slug] = scores
            print(f"[{slug}] missing candidate", file=sys.stderr)
            continue
        for name, mod in evaluators.items():
            try:
                s = float(mod.score(str(ref), str(cand)))
            except Exception as e:
                print(f"[{slug}] {name} failed: {e}", file=sys.stderr)
                traceback.print_exc()
                s = None
            scores[name] = s
            if s is not None:
                metric_values[name].append(s)
        per_page[slug] = scores
        summary = " ".join(
            f"{n}={scores[n]:.4f}" if scores[n] is not None else f"{n}=NA"
            for n in evaluators
        )
        print(f"[{slug}] {summary}", file=sys.stderr)

    aggregate = {
        name: _aggregate(vs, getattr(evaluators[name], "AGGREGATE_P", None))
        for name, vs in metric_values.items()
    }

    METRICS_OUT.write_text(
        json.dumps(
            {"per_page": per_page, "aggregate": aggregate, "missing": missing},
            indent=2,
        )
    )

    reward = aggregate.get(REWARD_METRIC, 0.0)
    REWARD_OUT.write_text(f"{reward:.6f}\n")
    print(f"reward={reward:.6f}", file=sys.stderr)
    print(f"{reward:.6f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

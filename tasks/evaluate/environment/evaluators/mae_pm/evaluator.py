"""EVALUATOR — MAE pixel similarity, aggregated across pages with PM_p (p=0.25).

Per-page score is identical to evaluators/mae (1 - MAE/255). The difference is
in how the runner combines per-page scores into a per-trial aggregate: instead
of the arithmetic mean (PM_1), this metric requests power mean with p=0.25,
which downweights pages that happen to score high. This rewards trials whose
*worst* pages are still decent and penalizes trials that nail one page and
flop on another.

The runners (tasks/evaluate/environment/run_evaluators.py and
helper_scripts/evaluate_outputs_local.py) honor the AGGREGATE_P module
constant when computing aggregates.
"""
from __future__ import annotations

import sys

import numpy as np
from PIL import Image

AGGREGATE_P = 0.25  # runner picks this up and applies PM_p instead of mean

MAX_EDGE = 1600


def _load(path: str) -> np.ndarray:
    return np.array(Image.open(path).convert("RGB"))


def _resize_pair(ref: np.ndarray, cand: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if cand.shape != ref.shape:
        print(f"resizing cand {cand.shape} -> {ref.shape}", file=sys.stderr)
        cand = np.array(Image.fromarray(cand).resize((ref.shape[1], ref.shape[0])))
    h, w = ref.shape[:2]
    if max(h, w) > MAX_EDGE:
        scale = MAX_EDGE / max(h, w)
        new_size = (int(w * scale), int(h * scale))
        print(f"downsampling to {new_size}", file=sys.stderr)
        ref = np.array(Image.fromarray(ref).resize(new_size))
        cand = np.array(Image.fromarray(cand).resize(new_size))
    return ref, cand


def score(ref_path: str, cand_path: str) -> float:
    ref = _load(ref_path)
    cand = _load(cand_path)
    ref, cand = _resize_pair(ref, cand)
    mae = float(np.mean(np.abs(ref.astype(np.int16) - cand.astype(np.int16))))
    sim = 1.0 - mae / 255.0
    return max(0.0, min(1.0, sim))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: evaluator.py <ref.png> <cand.png>", file=sys.stderr)
        sys.exit(2)
    print(f"{score(sys.argv[1], sys.argv[2]):.6f}")

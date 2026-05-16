"""EVALUATOR — SSIM score between two PNGs.

Contract:
    Input:  argv[1] = reference PNG path, argv[2] = candidate PNG path
    Output: prints one float in [0.0, 1.0] on stdout. Diagnostics on stderr.

This file is the iteration point for changing how the pipeline scores a
clone against the target. The verifier shell script wraps this and writes
the printed float to /logs/verifier/reward.txt.
"""
from __future__ import annotations

import sys

import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim


def score(ref_path: str, cand_path: str) -> float:
    ref = np.array(Image.open(ref_path).convert("RGB"))
    cand = np.array(Image.open(cand_path).convert("RGB"))
    if cand.shape != ref.shape:
        print(f"resizing cand {cand.shape} -> {ref.shape}", file=sys.stderr)
        cand = np.array(
            Image.fromarray(cand).resize((ref.shape[1], ref.shape[0]))
        )
    s, _ = ssim(ref, cand, channel_axis=2, full=True, data_range=255)
    return max(0.0, min(1.0, float(s)))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: evaluate.py <ref.png> <cand.png>", file=sys.stderr)
        sys.exit(2)
    print(score(sys.argv[1], sys.argv[2]))

"""EVALUATOR — Peak Signal-to-Noise Ratio (PSNR) similarity.

From MRWeb (arxiv 2412.15310): PSNR = 10 * log10(MAX^2 / MSE) in dB.
Mapped to [0,1] with a saturating curve sim = PSNR / (PSNR + 30) (30 dB midpoint)
so the metric is comparable to the others in the suite.
"""
from __future__ import annotations

import math
import sys

import numpy as np
from PIL import Image

MAX_EDGE = 1600
PSNR_CAP = 100.0  # cap reported PSNR when MSE is exactly 0
PSNR_MIDPOINT = 30.0  # sim = psnr / (psnr + midpoint)


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
    ref = _load(ref_path).astype(np.float64)
    cand = _load(cand_path).astype(np.float64)
    ref, cand = _resize_pair(ref.astype(np.uint8), cand.astype(np.uint8))
    ref = ref.astype(np.float64)
    cand = cand.astype(np.float64)
    mse = float(np.mean((ref - cand) ** 2))
    if mse == 0:
        psnr = PSNR_CAP
    else:
        psnr = 10.0 * math.log10((255.0 ** 2) / mse)
    sim = psnr / (psnr + PSNR_MIDPOINT)
    print(f"psnr={psnr:.4f} dB sim={sim:.4f}", file=sys.stderr)
    return max(0.0, min(1.0, sim))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: evaluator.py <ref.png> <cand.png>", file=sys.stderr)
        sys.exit(2)
    print(f"{score(sys.argv[1], sys.argv[2]):.6f}")

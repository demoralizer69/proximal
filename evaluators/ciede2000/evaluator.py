"""EVALUATOR — CIEDE2000 perceptual color difference.

From MRWeb (arxiv 2412.15310): applies CIEDE2000 formula on the Lab color space
to measure perceptual color difference. We compute it pixel-wise over the whole
image (both images downsampled to MAX_EDGE=1600 like the rest of the suite) and
average. CIEDE2000 typically ranges 0..~100 (0 = identical, 100 = max human-
perceivable difference). Returned as 1 - mean(deltaE)/100, clamped to [0,1].
"""
from __future__ import annotations

import sys

import numpy as np
from PIL import Image
from skimage.color import deltaE_ciede2000, rgb2lab

MAX_EDGE = 1600
# CIEDE2000 doesn't strictly bound at 100, but in practice mean deltaE on
# natural images is well below 50. Use 50 as the normalization so the metric
# spreads across [0,1] more usefully for ranking.
DELTA_E_NORM = 50.0


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
    ref_lab = rgb2lab(ref.astype(np.float64) / 255.0)
    cand_lab = rgb2lab(cand.astype(np.float64) / 255.0)
    de = deltaE_ciede2000(ref_lab, cand_lab)
    mean_de = float(np.mean(de))
    sim = 1.0 - mean_de / DELTA_E_NORM
    print(f"mean_deltaE={mean_de:.4f} sim={sim:.4f}", file=sys.stderr)
    return max(0.0, min(1.0, sim))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: evaluator.py <ref.png> <cand.png>", file=sys.stderr)
        sys.exit(2)
    print(f"{score(sys.argv[1], sys.argv[2]):.6f}")

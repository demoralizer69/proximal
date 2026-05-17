"""EVALUATOR — Mean Absolute Error (MAE) pixel similarity.

From MRWeb (arxiv 2412.15310): MAE = mean(|p1 - p2|) over RGB pixels in [0,255].
Returned as similarity = 1 - MAE/255, clamped to [0,1] (higher = more similar).
"""
from __future__ import annotations

import sys

import numpy as np
from PIL import Image


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
    print(f"mae={mae:.4f} sim={sim:.4f}", file=sys.stderr)
    return max(0.0, min(1.0, sim))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: evaluator.py <ref.png> <cand.png>", file=sys.stderr)
        sys.exit(2)
    print(f"{score(sys.argv[1], sys.argv[2]):.6f}")

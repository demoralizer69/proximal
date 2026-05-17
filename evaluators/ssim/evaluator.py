"""EVALUATOR — Single-scale Structural Similarity Index Measure (SSIM).

From MRWeb (arxiv 2412.15310): SSIM evaluates luminance, contrast, and
structural changes. We use piq's SSIM at the native resolution (downsampled
to MAX_EDGE=1600 like the other evaluators). Returns a value in [0,1].
"""
from __future__ import annotations

import sys

import numpy as np
import torch
from PIL import Image
from piq import ssim


MAX_EDGE = 1600


def _to_tensor(arr: np.ndarray) -> torch.Tensor:
    return torch.from_numpy(arr).float().permute(2, 0, 1).unsqueeze(0) / 255.0


def score(ref_path: str, cand_path: str) -> float:
    ref = np.array(Image.open(ref_path).convert("RGB"))
    cand = np.array(Image.open(cand_path).convert("RGB"))
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
    ref_t = _to_tensor(ref)
    cand_t = _to_tensor(cand)
    with torch.no_grad():
        s = float(ssim(ref_t, cand_t, data_range=1.0))
    print(f"ssim={s:.4f}", file=sys.stderr)
    return max(0.0, min(1.0, s))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: evaluator.py <ref.png> <cand.png>", file=sys.stderr)
        sys.exit(2)
    print(f"{score(sys.argv[1], sys.argv[2]):.6f}")

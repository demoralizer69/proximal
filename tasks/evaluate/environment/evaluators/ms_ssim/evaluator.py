"""EVALUATOR — MS-SSIM score between two PNGs."""
from __future__ import annotations

import sys

import numpy as np
import torch
from PIL import Image
from piq import multi_scale_ssim


def _to_tensor(arr: np.ndarray) -> torch.Tensor:
    t = torch.from_numpy(arr).float().permute(2, 0, 1).unsqueeze(0) / 255.0
    return t


def score(ref_path: str, cand_path: str) -> float:
    ref = np.array(Image.open(ref_path).convert("RGB"))
    cand = np.array(Image.open(cand_path).convert("RGB"))
    if cand.shape != ref.shape:
        print(f"resizing cand {cand.shape} -> {ref.shape}", file=sys.stderr)
        cand = np.array(
            Image.fromarray(cand).resize((ref.shape[1], ref.shape[0]))
        )
    MAX_EDGE = 1600
    h, w = ref.shape[:2]
    if max(h, w) > MAX_EDGE:
        scale = MAX_EDGE / max(h, w)
        new_size = (int(w * scale), int(h * scale))
        print(f"downsampling to {new_size}", file=sys.stderr)
        ref = np.array(Image.fromarray(ref).resize(new_size))
        cand = np.array(Image.fromarray(cand).resize(new_size))
    ref_t = _to_tensor(ref)
    cand_t = _to_tensor(cand)
    s = multi_scale_ssim(ref_t, cand_t, data_range=1.0).item()
    return max(0.0, min(1.0, float(s)))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: evaluator.py <ref.png> <cand.png>", file=sys.stderr)
        sys.exit(2)
    print(score(sys.argv[1], sys.argv[2]))

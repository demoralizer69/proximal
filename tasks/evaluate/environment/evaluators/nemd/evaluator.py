"""EVALUATOR — Normalized Earth Mover's Distance (NEMD).

From MRWeb (arxiv 2412.15310): captures distributional differences by measuring
minimum transport cost. We approximate EMD by combining:

  (a) Per-channel 1D Wasserstein on RGB intensity histograms (color-distribution
      mismatch), and
  (b) 1D Wasserstein on per-row and per-column mean intensities (a cheap proxy
      for spatial structure: "where is the ink?").

Each component is normalized to [0,1] using its theoretical maximum
(255 for uint8 channel distance). Returned as 1 - mean(NEMD), so higher = more
similar. The two components are averaged 50/50.
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


def _emd_1d_hist(a: np.ndarray, b: np.ndarray, bins: int = 256, value_range: float = 255.0) -> float:
    """1D Wasserstein-1 distance between two arrays via L1 distance of CDFs of
    their histograms over [0, value_range]. Returns a value in [0, value_range]."""
    ha, _ = np.histogram(a, bins=bins, range=(0, value_range), density=True)
    hb, _ = np.histogram(b, bins=bins, range=(0, value_range), density=True)
    ha = ha / ha.sum() if ha.sum() > 0 else ha
    hb = hb / hb.sum() if hb.sum() > 0 else hb
    cdf_a = np.cumsum(ha)
    cdf_b = np.cumsum(hb)
    bin_width = value_range / bins
    return float(np.sum(np.abs(cdf_a - cdf_b)) * bin_width)


def score(ref_path: str, cand_path: str) -> float:
    ref = _load(ref_path)
    cand = _load(cand_path)
    ref, cand = _resize_pair(ref, cand)

    # (a) per-channel histogram EMD
    chan_emds = []
    for c in range(3):
        chan_emds.append(_emd_1d_hist(ref[..., c].ravel(), cand[..., c].ravel()))
    color_emd = float(np.mean(chan_emds))
    color_sim = 1.0 - color_emd / 255.0

    # (b) spatial profile EMD on row/column mean luminance
    ref_l = ref.mean(axis=2)
    cand_l = cand.mean(axis=2)
    row_emd = _emd_1d_hist(ref_l.mean(axis=1), cand_l.mean(axis=1))
    col_emd = _emd_1d_hist(ref_l.mean(axis=0), cand_l.mean(axis=0))
    spatial_emd = 0.5 * (row_emd + col_emd)
    spatial_sim = 1.0 - spatial_emd / 255.0

    sim = 0.5 * color_sim + 0.5 * spatial_sim
    print(
        f"color_emd={color_emd:.4f} spatial_emd={spatial_emd:.4f} "
        f"nemd_sim={sim:.4f}",
        file=sys.stderr,
    )
    return max(0.0, min(1.0, sim))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: evaluator.py <ref.png> <cand.png>", file=sys.stderr)
        sys.exit(2)
    print(f"{score(sys.argv[1], sys.argv[2]):.6f}")

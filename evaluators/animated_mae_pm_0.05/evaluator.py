"""EVALUATOR (animated) — per-frame MAE + temporal delta-MAE, PM_p=0.05.

Contract:
    Input:  argv[1] = reference capture dir, argv[2] = candidate capture dir
            Each dir must contain frame_00.png .. frame_05.png (1200x800 PNGs);
            clip.webm is ignored (it's agent-input only).
    Output: prints one float in [0.0, 1.0] on stdout. Diagnostics on stderr.

Per-frame sim:    1 - MAE/255 on RGB, downsampled to max edge 1600 px.
Delta-MAE:        1 - MAE/255 between |T_{i+1} - T_i| and |C_{i+1} - C_i|
                  ("does the motion happen in similar pixels?")
Within-page agg:  PM_p=0.05 across the 6 frame sims and across the 5 delta
                  sims separately, combined 0.5 * static + 0.5 * temporal.

Mirrored by tasks/clone_animated_template/environment/evaluate.py — keep in sync.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

FRAME_COUNT = 6
MAX_EDGE = 1600
WITHIN_P = 0.05
EPS = 1e-6


def _load(path: Path) -> np.ndarray:
    return np.array(Image.open(path).convert("RGB"))


def _resize_pair(ref: np.ndarray, cand: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if cand.shape != ref.shape:
        cand = np.array(Image.fromarray(cand).resize((ref.shape[1], ref.shape[0])))
    h, w = ref.shape[:2]
    if max(h, w) > MAX_EDGE:
        scale = MAX_EDGE / max(h, w)
        new_size = (int(w * scale), int(h * scale))
        ref = np.array(Image.fromarray(ref).resize(new_size))
        cand = np.array(Image.fromarray(cand).resize(new_size))
    return ref, cand


def _mae_sim(ref: np.ndarray, cand: np.ndarray) -> float:
    ref, cand = _resize_pair(ref, cand)
    mae = float(np.mean(np.abs(ref.astype(np.int16) - cand.astype(np.int16))))
    return max(0.0, min(1.0, 1.0 - mae / 255.0))


def _delta(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    if a.shape != b.shape:
        b = np.array(Image.fromarray(b).resize((a.shape[1], a.shape[0])))
    return np.abs(a.astype(np.int16) - b.astype(np.int16)).astype(np.uint8)


def _pm(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    ys = [max(v, EPS) for v in xs]
    return (sum(y ** p for y in ys) / len(ys)) ** (1.0 / p)


def score(ref_dir: str, cand_dir: str) -> float:
    ref_root = Path(ref_dir)
    cand_root = Path(cand_dir)

    ref_frames: list[np.ndarray] = []
    cand_frames: list[np.ndarray] = []
    frame_sims: list[float] = []
    missing = 0
    for i in range(FRAME_COUNT):
        ref_p = ref_root / f"frame_{i:02d}.png"
        cand_p = cand_root / f"frame_{i:02d}.png"
        if not ref_p.exists():
            print(f"warning: missing reference frame {ref_p}", file=sys.stderr)
            missing += 1
            continue
        ref_img = _load(ref_p)
        ref_frames.append(ref_img)
        if not cand_p.exists():
            print(f"warning: missing candidate frame {cand_p}; counts as 0.0", file=sys.stderr)
            cand_frames.append(np.zeros_like(ref_img))
            frame_sims.append(0.0)
            continue
        cand_img = _load(cand_p)
        if cand_img.shape != ref_img.shape:
            cand_img = np.array(
                Image.fromarray(cand_img).resize((ref_img.shape[1], ref_img.shape[0]))
            )
        cand_frames.append(cand_img)
        frame_sims.append(_mae_sim(ref_img, cand_img))

    if not frame_sims:
        print("error: no frames could be scored", file=sys.stderr)
        return 0.0

    delta_sims: list[float] = []
    for i in range(len(ref_frames) - 1):
        r = _delta(ref_frames[i], ref_frames[i + 1])
        c = _delta(cand_frames[i], cand_frames[i + 1])
        delta_sims.append(_mae_sim(r, c))

    static = _pm(frame_sims, WITHIN_P)
    temporal = _pm(delta_sims, WITHIN_P) if delta_sims else 0.0
    composite = 0.5 * static + 0.5 * temporal
    composite = max(0.0, min(1.0, composite))

    print(
        f"frames={len(frame_sims)} missing={missing} "
        f"static_pm={static:.4f} temporal_pm={temporal:.4f} composite={composite:.4f}",
        file=sys.stderr,
    )
    return composite


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: evaluator.py <ref_dir> <cand_dir>", file=sys.stderr)
        sys.exit(2)
    print(f"{score(sys.argv[1], sys.argv[2]):.6f}")

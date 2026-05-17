"""EVALUATOR (animated) — per-frame WebSight composite + temporal delta-SSIM.

Contract:
    Input:  argv[1] = reference capture dir, argv[2] = candidate capture dir
            Each dir must contain frame_00.png .. frame_05.png (1200x800 PNGs);
            clip.webm is ignored (it's agent-input only).
    Output: prints one float in [0.0, 1.0] on stdout. Diagnostics on stderr.

Composite = 0.5 * mean(per-frame WebSight) + 0.5 * mean(delta-SSIM)
  per-frame WebSight: (MS-SSIM + (1 - LPIPS) + OCR F1) / 3 on each (T_i, C_i)
  delta-SSIM:         MS-SSIM between |T_{i+1} - T_i| and |C_{i+1} - C_i|,
                      i.e. "does the motion happen in similar regions?"

This file is mirrored by evaluators/animated_websight/evaluator.py — keep them
in sync. The verifier shell script wraps this and writes the printed float to
/logs/verifier/reward.txt.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import piq
import torch
from PIL import Image
from torchvision.transforms.functional import to_tensor

FRAME_COUNT = 6
MAX_EDGE = 1600


def _load(path: Path, size=None) -> Image.Image:
    img = Image.open(path).convert("RGB")
    if size is not None and img.size != size:
        img = img.resize(size, Image.BILINEAR)
    return img


def _to_batch(img: Image.Image) -> torch.Tensor:
    return to_tensor(img).unsqueeze(0).float().clamp(0, 1)


def _tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def _ocr_f1(ref_path: Path, cand_path: Path) -> float:
    try:
        import pytesseract
        ref_txt = pytesseract.image_to_string(Image.open(ref_path))
        cand_txt = pytesseract.image_to_string(Image.open(cand_path))
    except Exception as e:
        print(f"warning: OCR failed ({e}); ocr_f1=0.0", file=sys.stderr)
        return 0.0
    a, b = _tokens(ref_txt), _tokens(cand_txt)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    tp = len(a & b)
    if tp == 0:
        return 0.0
    p = tp / len(b)
    r = tp / len(a)
    return 2 * p * r / (p + r)


def _resize_pair(ref: Image.Image, cand: Image.Image) -> tuple[Image.Image, Image.Image]:
    cand = cand if cand.size == ref.size else cand.resize(ref.size, Image.BILINEAR)
    w, h = ref.size
    if max(w, h) > MAX_EDGE:
        scale = MAX_EDGE / max(w, h)
        new_size = (int(w * scale), int(h * scale))
        ref = ref.resize(new_size, Image.BILINEAR)
        cand = cand.resize(new_size, Image.BILINEAR)
    return ref, cand


def _static_score(ref_path: Path, cand_path: Path, lpips_model) -> tuple[float, float, float, float]:
    ref_img = _load(ref_path)
    cand_img = _load(cand_path, size=ref_img.size)
    ref_img, cand_img = _resize_pair(ref_img, cand_img)
    ref = _to_batch(ref_img)
    cand = _to_batch(cand_img)
    with torch.no_grad():
        ms_ssim = float(piq.multi_scale_ssim(ref, cand, data_range=1.0))
        lpips_d = float(lpips_model(ref, cand))
    lpips_sim = max(0.0, 1.0 - lpips_d)
    f1 = _ocr_f1(ref_path, cand_path)
    composite = (ms_ssim + lpips_sim + f1) / 3.0
    return ms_ssim, lpips_sim, f1, max(0.0, min(1.0, composite))


def _delta_image(a: Image.Image, b: Image.Image) -> Image.Image:
    """Abs-diff in uint8 RGB. Same size as inputs."""
    arr_a = np.asarray(a, dtype=np.int16)
    arr_b = np.asarray(b, dtype=np.int16)
    return Image.fromarray(np.abs(arr_a - arr_b).astype(np.uint8))


def _temporal_score(ref_frames: list[Image.Image], cand_frames: list[Image.Image]) -> float:
    scores: list[float] = []
    for i in range(len(ref_frames) - 1):
        r = _delta_image(ref_frames[i], ref_frames[i + 1])
        c = _delta_image(cand_frames[i], cand_frames[i + 1])
        r, c = _resize_pair(r, c)
        rb = _to_batch(r)
        cb = _to_batch(c)
        with torch.no_grad():
            s = float(piq.multi_scale_ssim(rb, cb, data_range=1.0))
        scores.append(s)
    return float(sum(scores) / len(scores)) if scores else 0.0


def score(ref_dir: str, cand_dir: str) -> float:
    ref_root = Path(ref_dir)
    cand_root = Path(cand_dir)
    lpips_model = piq.LPIPS()

    per_frame_composites: list[float] = []
    static_components: list[tuple[float, float, float]] = []
    ref_frames: list[Image.Image] = []
    cand_frames: list[Image.Image] = []
    missing = 0
    for i in range(FRAME_COUNT):
        ref_p = ref_root / f"frame_{i:02d}.png"
        cand_p = cand_root / f"frame_{i:02d}.png"
        if not ref_p.exists():
            print(f"warning: missing reference frame {ref_p}", file=sys.stderr)
            missing += 1
            continue
        if not cand_p.exists():
            print(f"warning: missing candidate frame {cand_p}; counts as 0.0", file=sys.stderr)
            per_frame_composites.append(0.0)
            static_components.append((0.0, 0.0, 0.0))
            ref_frames.append(_load(ref_p))
            cand_frames.append(Image.new("RGB", _load(ref_p).size, (0, 0, 0)))
            continue
        ms_ssim, lpips_sim, f1, comp = _static_score(ref_p, cand_p, lpips_model)
        static_components.append((ms_ssim, lpips_sim, f1))
        per_frame_composites.append(comp)
        ref_frames.append(_load(ref_p))
        cand_frames.append(_load(cand_p, size=ref_frames[-1].size))

    if not per_frame_composites:
        print("error: no frames could be scored", file=sys.stderr)
        return 0.0

    static_avg = sum(per_frame_composites) / len(per_frame_composites)
    temporal_avg = _temporal_score(ref_frames, cand_frames)
    composite = 0.5 * static_avg + 0.5 * temporal_avg
    composite = max(0.0, min(1.0, composite))

    means = [sum(c) / len(c) for c in zip(*static_components)] if static_components else [0, 0, 0]
    print(
        f"frames={len(per_frame_composites)} missing={missing} "
        f"ms_ssim={means[0]:.4f} lpips_sim={means[1]:.4f} ocr_f1={means[2]:.4f} "
        f"static={static_avg:.4f} temporal={temporal_avg:.4f} composite={composite:.4f}",
        file=sys.stderr,
    )
    return composite


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: evaluate.py <ref_dir> <cand_dir>", file=sys.stderr)
        sys.exit(2)
    print(f"{score(sys.argv[1], sys.argv[2]):.6f}")

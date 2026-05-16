"""EVALUATOR — WebSight / Pix2Code-style composite score (MS-SSIM + LPIPS + OCR F1).

Contract:
    Input:  argv[1] = reference PNG path, argv[2] = candidate PNG path
    Output: prints one float in [0.0, 1.0] on stdout. Diagnostics on stderr.

This file is the iteration point for changing how the pipeline scores a
clone against the target. The verifier shell script wraps this and writes
the printed float to /logs/verifier/reward.txt.
"""
from __future__ import annotations

import re
import sys

import piq
import torch
from PIL import Image
from torchvision.transforms.functional import to_tensor


def load(path: str, size=None) -> Image.Image:
    img = Image.open(path).convert("RGB")
    if size is not None and img.size != size:
        img = img.resize(size, Image.BILINEAR)
    return img


def to_batch(img: Image.Image) -> torch.Tensor:
    return to_tensor(img).unsqueeze(0).float().clamp(0, 1)


def tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def ocr_f1(ref_path: str, cand_path: str) -> float:
    try:
        import pytesseract
        ref_txt = pytesseract.image_to_string(Image.open(ref_path))
        cand_txt = pytesseract.image_to_string(Image.open(cand_path))
    except Exception as e:
        print(f"warning: OCR failed ({e}); ocr_f1=0.0", file=sys.stderr)
        return 0.0
    a, b = tokens(ref_txt), tokens(cand_txt)
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


def score(ref_path: str, cand_path: str) -> float:
    ref_img = load(ref_path)
    cand_img = load(cand_path, size=ref_img.size)
    MAX_EDGE = 1600
    w, h = ref_img.size
    if max(w, h) > MAX_EDGE:
        scale = MAX_EDGE / max(w, h)
        new_size = (int(w * scale), int(h * scale))
        print(f"downsampling to {new_size}", file=sys.stderr)
        ref_img = ref_img.resize(new_size, Image.BILINEAR)
        cand_img = cand_img.resize(new_size, Image.BILINEAR)
    ref = to_batch(ref_img)
    cand = to_batch(cand_img)

    with torch.no_grad():
        ms_ssim = float(piq.multi_scale_ssim(ref, cand, data_range=1.0))
        lpips_d = float(piq.LPIPS()(ref, cand))
    lpips_sim = max(0.0, 1.0 - lpips_d)
    f1 = ocr_f1(ref_path, cand_path)
    composite = (ms_ssim + lpips_sim + f1) / 3.0
    composite = max(0.0, min(1.0, composite))

    print(
        f"ms_ssim={ms_ssim:.4f} lpips_sim={lpips_sim:.4f} "
        f"ocr_f1={f1:.4f} composite={composite:.4f}",
        file=sys.stderr,
    )
    return composite


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: evaluate.py <ref.png> <cand.png>", file=sys.stderr)
        sys.exit(2)
    print(f"{score(sys.argv[1], sys.argv[2]):.6f}")

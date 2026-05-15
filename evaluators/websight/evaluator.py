#!/usr/bin/env python3
"""WebSight / Pix2Code-style composite evaluator: MS-SSIM + LPIPS + OCR F1."""
import re
import sys

import piq
import torch
from PIL import Image
from torchvision.transforms.functional import to_tensor


def load(path, size=None):
    img = Image.open(path).convert("RGB")
    if size is not None and img.size != size:
        img = img.resize(size, Image.BILINEAR)
    return img


def to_batch(img):
    return to_tensor(img).unsqueeze(0).float().clamp(0, 1)


def tokens(s):
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def ocr_f1(ref_path, cand_path):
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


def main():
    ref_path, cand_path = sys.argv[1], sys.argv[2]
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
        f"ms_ssim={ms_ssim:.4f} lpips_sim={lpips_sim:.4f} ocr_f1={f1:.4f} composite={composite:.4f}",
        file=sys.stderr,
    )
    print(f"{composite:.6f}")


if __name__ == "__main__":
    main()

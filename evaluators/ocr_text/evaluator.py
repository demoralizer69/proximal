"""EVALUATOR — OCR text similarity (a standalone "Text Difference" metric).

From MRWeb (arxiv 2412.15310): "Text Difference = 1 - Text Sim", where Text Sim
is a character matching ratio. We run pytesseract on both images, lowercase,
strip to alnum tokens, and compute the F1 of token overlap — identical to the
OCR leg of websight. Surfaced as a standalone metric so ranking by *just* text
accuracy is possible.
"""
from __future__ import annotations

import re
import sys

from PIL import Image


def _tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def score(ref_path: str, cand_path: str) -> float:
    try:
        import pytesseract
        ref_txt = pytesseract.image_to_string(Image.open(ref_path))
        cand_txt = pytesseract.image_to_string(Image.open(cand_path))
    except Exception as e:
        print(f"warning: OCR failed ({e}); returning 0.0", file=sys.stderr)
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
    f1 = 2 * p * r / (p + r)
    print(f"|ref|={len(a)} |cand|={len(b)} tp={tp} f1={f1:.4f}", file=sys.stderr)
    return max(0.0, min(1.0, f1))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: evaluator.py <ref.png> <cand.png>", file=sys.stderr)
        sys.exit(2)
    print(f"{score(sys.argv[1], sys.argv[2]):.6f}")

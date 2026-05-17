"""HTML -> (keyframes + short WebM) via Playwright Chromium.

For animated sites: capture FRAME_COUNT viewport screenshots at fixed
timestamps over CAPTURE_MS milliseconds, plus a continuous WebM recorded
by Playwright's built-in `record_video_dir`. The keyframes are the
ground-truth samples the evaluator scores against; the WebM is extra
context for the cloning agent.

Output layout written to <out_dir>:
    frame_00.png, frame_01.png, ..., frame_05.png   (full-page screenshots)
    clip.webm                                       (1200x800 Playwright recording)

Same file is copied into both:
  - tasks/generate_animated/environment/render.py
  - tasks/clone_animated_template/environment/render.py

so that target and candidate are captured identically (timing drift cancels).

Usage:
    python3 render.py <input.html> <out_dir>
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

VIEWPORT_W = 1200
VIEWPORT_H = 800

FRAME_TIMES_MS = [0, 500, 1000, 1500, 2000, 2500]
CAPTURE_MS = 3000


def render(html_path: str, out_dir: str) -> None:
    url = f"file://{Path(html_path).resolve()}"
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    video_tmp = Path(tempfile.mkdtemp(prefix="prox_vid_"))

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        ctx = browser.new_context(
            viewport={"width": VIEWPORT_W, "height": VIEWPORT_H},
            device_scale_factor=1,
            record_video_dir=str(video_tmp),
            record_video_size={"width": VIEWPORT_W, "height": VIEWPORT_H},
        )
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded")

        t0 = time.monotonic()
        for i, target_ms in enumerate(FRAME_TIMES_MS):
            elapsed_ms = (time.monotonic() - t0) * 1000.0
            if elapsed_ms < target_ms:
                page.wait_for_timeout(target_ms - elapsed_ms)
            page.screenshot(path=str(out / f"frame_{i:02d}.png"), full_page=True)

        remaining_ms = CAPTURE_MS - (time.monotonic() - t0) * 1000.0
        if remaining_ms > 0:
            page.wait_for_timeout(remaining_ms)

        video_src = Path(page.video.path()) if page.video else None
        ctx.close()
        browser.close()

    if video_src is not None and video_src.exists():
        shutil.move(str(video_src), str(out / "clip.webm"))
    shutil.rmtree(video_tmp, ignore_errors=True)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: render.py <input.html> <out_dir>", file=sys.stderr)
        sys.exit(2)
    render(sys.argv[1], sys.argv[2])

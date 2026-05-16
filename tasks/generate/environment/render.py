"""HTML -> PNG via Playwright Chromium.

Single rendering source-of-truth used by the verifier to render each page
the agent produced. Keep launch / viewport / scale settings in one place: here.

Usage:
    python3 render.py <input.html> <output.png>
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

VIEWPORT_W = 1200
VIEWPORT_H = 800


def render(html_path: str, png_path: str) -> None:
    url = f"file://{Path(html_path).resolve()}"
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(
            viewport={"width": VIEWPORT_W, "height": VIEWPORT_H},
            device_scale_factor=1,
        )
        page = context.new_page()
        page.goto(url, wait_until="networkidle")
        page.screenshot(
            path=png_path,
            full_page=True,
        )
        browser.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: render.py <input.html> <output.png>", file=sys.stderr)
        sys.exit(2)
    render(sys.argv[1], sys.argv[2])

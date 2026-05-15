#!/bin/bash
# Renders /app/clone.html, compares with /app/webpage.png via SSIM,
# writes a fractional reward in [0, 1] to /logs/verifier/reward.txt.
mkdir -p /logs/verifier

python3 - <<'PY'
import pathlib, subprocess, sys, traceback

OUT = pathlib.Path("/logs/verifier")
OUT.mkdir(parents=True, exist_ok=True)
REWARD = OUT / "reward.txt"
LOG = OUT / "verifier.log"

def write(reward: float, msg: str = "") -> None:
    REWARD.write_text(f"{reward:.6f}\n")
    LOG.write_text(msg)
    print(f"reward={reward:.4f}")
    if msg:
        print(msg, file=sys.stderr)

try:
    target = pathlib.Path("/app/webpage.png")
    clone_html = pathlib.Path("/app/clone.html")

    if not target.exists():
        write(0.0, "missing reference webpage.png — generator failed")
        sys.exit(0)
    if not clone_html.exists():
        write(0.0, "agent did not create /app/clone.html")
        sys.exit(0)

    clone_png = pathlib.Path("/app/clone.png")
    result = subprocess.run(
        [
            "chromium", "--headless=new", "--no-sandbox", "--disable-gpu",
            "--hide-scrollbars", "--disable-dev-shm-usage",
            "--window-size=800,600",
            f"--screenshot={clone_png}",
            f"file://{clone_html}",
        ],
        capture_output=True, text=True, timeout=120,
    )
    if not clone_png.exists():
        write(0.0, f"chromium failed to render clone.html\nstdout:{result.stdout}\nstderr:{result.stderr}")
        sys.exit(0)

    from PIL import Image
    import numpy as np
    from skimage.metrics import structural_similarity as ssim

    ref = np.array(Image.open(target).convert("RGB"))
    cand = np.array(Image.open(clone_png).convert("RGB"))
    if cand.shape != ref.shape:
        Image.fromarray(cand).resize((ref.shape[1], ref.shape[0])).save(clone_png)
        cand = np.array(Image.open(clone_png).convert("RGB"))

    score, _ = ssim(ref, cand, channel_axis=2, full=True, data_range=255)
    score = max(0.0, min(1.0, float(score)))
    write(score, f"SSIM={score:.4f} (ref={ref.shape}, cand={cand.shape})")
except Exception:
    write(0.0, "verifier crashed:\n" + traceback.format_exc())
PY

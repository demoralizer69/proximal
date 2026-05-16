#!/usr/bin/env python3
"""Tiny webserver to browse screenshots/<job>/<trial>/*.png as slideshows.

One slideshow per trial directory, opened as an overlay on the index page.
Usage:
    python3 view_screenshots.py [port]   # default port 8765
"""
from __future__ import annotations

import http.server
import json
import socketserver
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCREENSHOTS = ROOT / "screenshots"
DEFAULT_PORT = 8765


def _sorted_pngs(trial_dir: Path) -> list[str]:
    files = sorted(p.name for p in trial_dir.glob("*.png"))
    files.sort(key=lambda n: (0 if n == "home.png" else 1, n))
    return files


def collect_trials() -> tuple[list[tuple[str, list[str]]], dict[str, dict]]:
    """Return (jobs, trial_data).

    `jobs` is [(job_name, [trial_key, ...]), ...] for index rendering order.
    `trial_data[trial_key]` is the JSON payload the JS slideshow needs.
    """
    jobs: list[tuple[str, list[str]]] = []
    trial_data: dict[str, dict] = {}
    if not SCREENSHOTS.exists():
        return jobs, trial_data
    for job in sorted(SCREENSHOTS.iterdir(), reverse=True):
        if not job.is_dir():
            continue
        keys: list[str] = []
        for trial in sorted(job.iterdir()):
            if not trial.is_dir():
                continue
            files = _sorted_pngs(trial)
            if not files:
                continue
            key = f"{job.name}/{trial.name}"
            base = f"/img/{urllib.parse.quote(job.name)}/{urllib.parse.quote(trial.name)}"
            trial_data[key] = {
                "job": job.name,
                "trial": trial.name,
                "thumb": f"{base}/{urllib.parse.quote(files[0])}",
                "base": base,
                "files": files,
            }
            keys.append(key)
        if keys:
            jobs.append((job.name, keys))
    return jobs, trial_data


INDEX_TMPL = """<!doctype html>
<html><head><title>screenshots</title>
<style>
:root {
  --bg: #fafafa;
  --fg: #222;
  --muted: #888;
  --card: #fff;
  --card-hover: #f1f1f1;
  --border: #e6e6e6;
  --shadow: 0 1px 3px rgba(0,0,0,0.06);
}
* { box-sizing: border-box; }
body { font-family: -apple-system, system-ui, sans-serif; margin: 0; padding: 2em 1em; max-width: 1400px; margin: 0 auto; color: var(--fg); background: var(--bg); }
h1 { margin: 0 0 1em 0; }
.job { margin: 0 0 2em 0; }
.job-head { font-size: 0.95em; color: #555; font-weight: 500; border-bottom: 1px solid var(--border); padding-bottom: 0.3em; font-family: ui-monospace, monospace; margin: 0 0 0.8em 0; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1em; }
.card { background: var(--card); border: 1px solid var(--border); border-radius: 6px; overflow: hidden; cursor: pointer; box-shadow: var(--shadow); transition: transform 0.08s, background 0.08s, box-shadow 0.08s; display: flex; flex-direction: column; }
.card:hover { background: var(--card-hover); transform: translateY(-1px); box-shadow: 0 3px 10px rgba(0,0,0,0.08); }
.thumb { aspect-ratio: 3/2; background: #fff; border-bottom: 1px solid var(--border); overflow: hidden; }
.thumb img { width: 100%; height: 100%; object-fit: contain; display: block; }
.meta { padding: 0.5em 0.7em; font-family: ui-monospace, monospace; font-size: 0.82em; display: flex; justify-content: space-between; align-items: center; gap: 0.5em; }
.meta .name { color: var(--fg); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.meta .count { color: var(--muted); flex-shrink: 0; }
.empty { color: var(--muted); font-style: italic; }

/* slideshow overlay */
.overlay { position: fixed; inset: 0; background: rgba(10,10,10,0.97); display: none; flex-direction: column; z-index: 1000; }
.overlay.open { display: flex; }
.overlay-header { display: flex; justify-content: space-between; align-items: center; padding: 0.6em 1.2em; color: #ccc; background: #111; border-bottom: 1px solid #222; }
.overlay-header .meta { font-family: ui-monospace, monospace; font-size: 0.88em; color: #ccc; }
.overlay-btn { background: #2a2a2a; color: #eee; border: 1px solid #3a3a3a; padding: 0.35em 0.8em; border-radius: 3px; cursor: pointer; font: inherit; font-size: 0.88em; }
.overlay-btn:hover { background: #333; }
.frame { flex: 1; display: flex; align-items: center; justify-content: center; overflow: hidden; padding: 0.8em; cursor: pointer; }
.frame img { max-width: 100%; max-height: 100%; object-fit: contain; box-shadow: 0 8px 32px rgba(0,0,0,0.5); }
.overlay-footer { display: flex; justify-content: center; align-items: center; gap: 0.8em; padding: 0.6em; background: #111; border-top: 1px solid #222; color: #ccc; font-size: 0.86em; }
#pos { font-family: ui-monospace, monospace; color: #888; min-width: 7ch; text-align: center; }
#img-name { font-family: ui-monospace, monospace; color: #ccc; min-width: 12ch; text-align: center; }
</style></head>
<body>
<h1>screenshots</h1>
__BODY__

<div class="overlay" id="overlay">
  <div class="overlay-header">
    <span class="meta" id="ov-meta"></span>
    <button class="overlay-btn" onclick="closeSlideshow()">close (esc)</button>
  </div>
  <div class="frame" onclick="nextImg()"><img id="ov-img" alt=""></div>
  <div class="overlay-footer">
    <button class="overlay-btn" onclick="prevImg()">prev (&larr;)</button>
    <span id="pos"></span>
    <span id="img-name"></span>
    <button class="overlay-btn" onclick="nextImg()">next (&rarr;)</button>
    <button class="overlay-btn" id="play" onclick="togglePlay()">&#9654; play</button>
  </div>
</div>

<script>
const TRIALS = __TRIALS_JSON__;
let current = null;
let i = 0;
let timer = null;

function openSlideshow(key) {
  current = TRIALS[key];
  if (!current) return;
  i = 0;
  document.getElementById('ov-meta').textContent = current.job + ' / ' + current.trial;
  document.getElementById('overlay').classList.add('open');
  renderImg();
}
function closeSlideshow() {
  document.getElementById('overlay').classList.remove('open');
  if (timer) { clearInterval(timer); timer = null; document.getElementById('play').innerHTML = '&#9654; play'; }
  current = null;
}
function renderImg() {
  if (!current) return;
  document.getElementById('ov-img').src = current.base + '/' + current.files[i];
  document.getElementById('pos').textContent = (i + 1) + ' / ' + current.files.length;
  document.getElementById('img-name').textContent = current.files[i];
}
function nextImg() { if (!current) return; i = (i + 1) % current.files.length; renderImg(); }
function prevImg() { if (!current) return; i = (i - 1 + current.files.length) % current.files.length; renderImg(); }
function togglePlay() {
  const btn = document.getElementById('play');
  if (timer) { clearInterval(timer); timer = null; btn.innerHTML = '&#9654; play'; }
  else { timer = setInterval(nextImg, 1500); btn.innerHTML = '&#10074;&#10074; pause'; }
}
document.addEventListener('keydown', e => {
  if (!current) return;
  if (e.key === 'Escape') { closeSlideshow(); }
  else if (e.key === 'ArrowRight' || e.key === ' ') { e.preventDefault(); nextImg(); }
  else if (e.key === 'ArrowLeft') { e.preventDefault(); prevImg(); }
  else if (e.key === 'p') { togglePlay(); }
});
document.querySelectorAll('.card').forEach(card => {
  card.addEventListener('click', () => openSlideshow(card.dataset.key));
});
</script>
</body></html>
"""


def render_index() -> str:
    jobs, trial_data = collect_trials()
    if not jobs:
        body = '<p class="empty">No screenshots found under ./screenshots/</p>'
    else:
        parts: list[str] = []
        for job, keys in jobs:
            parts.append(f'<div class="job"><div class="job-head">{job}</div><div class="grid">')
            for key in keys:
                d = trial_data[key]
                key_attr = key.replace('"', "&quot;")
                parts.append(
                    f'<div class="card" data-key="{key_attr}">'
                    f'<div class="thumb"><img src="{d["thumb"]}" loading="lazy" alt=""></div>'
                    f'<div class="meta"><span class="name">{d["trial"]}</span>'
                    f'<span class="count">{len(d["files"])} pgs</span></div>'
                    f'</div>'
                )
            parts.append("</div></div>")
        body = "\n".join(parts)
    return (
        INDEX_TMPL
        .replace("__TRIALS_JSON__", json.dumps(trial_data))
        .replace("__BODY__", body)
    )


def _safe_under(path: Path) -> bool:
    try:
        path.resolve().relative_to(SCREENSHOTS.resolve())
        return True
    except ValueError:
        return False


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args, **kwargs):
        return  # quiet

    def _send_html(self, body: str, status: int = 200) -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def _send_404(self, msg: str = "not found") -> None:
        self._send_html(f"<h1>404</h1><p>{msg}</p>", status=404)

    def _send_png(self, path: Path) -> None:
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            return self._send_404()
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(data)))
        # Allow browser caching for image responses (filenames are stable).
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        parts = [urllib.parse.unquote(p) for p in parsed.path.split("/") if p]

        if not parts:
            return self._send_html(render_index())

        if parts[0] == "img" and len(parts) == 4:
            job, trial, fname = parts[1], parts[2], parts[3]
            p = SCREENSHOTS / job / trial / fname
            if not _safe_under(p) or not fname.endswith(".png"):
                return self._send_404()
            return self._send_png(p)

        return self._send_404()


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("127.0.0.1", port), Handler) as srv:
        print(f"viewer: http://localhost:{port}", flush=True)
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())

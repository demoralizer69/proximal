#!/usr/bin/env python3
"""Tiny webserver to browse outputs/<job>/<task>/ side-by-side.

Each task directory is expected to contain:
    screenshots/<slug>.png   - target screenshots
    rendered/<slug>.png      - agent's rendered clone (may be missing/empty)
    reward.txt               - mean SSIM as float, or "FAILED"

Index lists jobs and their tasks (sorted by reward desc). Clicking a task
opens a detail page that shows target | rendered pairs per slug.

Usage:
    python3 view_outputs.py [port]   # default 8766
"""
from __future__ import annotations

import http.server
import socketserver
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT / "outputs"
DEFAULT_PORT = 8766


def _read_reward(task_dir: Path) -> float | None:
    f = task_dir / "reward.txt"
    if not f.exists():
        return None
    try:
        return float(f.read_text().strip())
    except ValueError:
        return None


def _slugs(task_dir: Path) -> list[str]:
    targets = {p.stem for p in (task_dir / "screenshots").glob("*.png")}
    rendered = {p.stem for p in (task_dir / "rendered").glob("*.png")}
    slugs = sorted(targets | rendered)
    slugs.sort(key=lambda s: (0 if s == "home" else 1, s))
    return slugs


def _safe_under(path: Path) -> bool:
    try:
        path.resolve().relative_to(OUTPUTS.resolve())
        return True
    except ValueError:
        return False


CSS = """
:root {
  --bg:#fafafa; --fg:#222; --muted:#888;
  --card:#fff; --card-hover:#f1f1f1; --border:#e6e6e6;
  --shadow:0 1px 3px rgba(0,0,0,0.06);
  --good:#0a7f2e; --mid:#b07a00; --bad:#a03030;
}
*{box-sizing:border-box}
body{font-family:-apple-system,system-ui,sans-serif;margin:0;padding:2em 1em;
  max-width:1400px;margin:0 auto;color:var(--fg);background:var(--bg)}
h1{margin:0 0 1em 0}
h1 a{color:var(--muted);text-decoration:none;font-weight:400;font-size:0.7em}
h1 a:hover{color:var(--fg)}
.job{margin:0 0 2em 0}
.job-head{font-size:0.95em;color:#555;font-weight:500;border-bottom:1px solid var(--border);
  padding-bottom:0.3em;font-family:ui-monospace,monospace;margin:0 0 0.8em 0}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:1em}
.card{background:var(--card);border:1px solid var(--border);border-radius:6px;
  overflow:hidden;cursor:pointer;box-shadow:var(--shadow);display:flex;flex-direction:column;
  text-decoration:none;color:inherit;transition:transform 0.08s,background 0.08s,box-shadow 0.08s}
.card:hover{background:var(--card-hover);transform:translateY(-1px);box-shadow:0 3px 10px rgba(0,0,0,0.08)}
.thumb-pair{display:grid;grid-template-columns:1fr 1fr;aspect-ratio:6/2;background:#fff;
  border-bottom:1px solid var(--border)}
.thumb-pair > div{overflow:hidden;background:#fff;display:flex;align-items:center;justify-content:center;
  border-right:1px solid var(--border)}
.thumb-pair > div:last-child{border-right:none}
.thumb-pair img{width:100%;height:100%;object-fit:cover;display:block}
.missing{color:var(--muted);font-size:0.75em;font-family:ui-monospace,monospace}
.meta{padding:0.5em 0.7em;font-family:ui-monospace,monospace;font-size:0.82em;
  display:flex;justify-content:space-between;align-items:center;gap:0.5em}
.meta .name{color:var(--fg);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.score{font-weight:600;font-family:ui-monospace,monospace}
.score.good{color:var(--good)}
.score.mid{color:var(--mid)}
.score.bad{color:var(--bad)}
.score.fail{color:var(--muted);font-style:italic}
.empty{color:var(--muted);font-style:italic}
.legend{color:var(--muted);font-size:0.85em;margin:0.4em 0 1.2em 0}

/* detail page */
.detail-head{display:flex;align-items:baseline;gap:1em;flex-wrap:wrap;margin:0 0 1.2em 0}
.detail-head h1{margin:0}
.pair{margin:0 0 2em 0;background:var(--card);border:1px solid var(--border);border-radius:6px;
  box-shadow:var(--shadow);overflow:hidden}
.pair-head{padding:0.5em 0.8em;background:#f3f3f3;border-bottom:1px solid var(--border);
  font-family:ui-monospace,monospace;font-size:0.88em}
.pair-imgs{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--border)}
.pair-imgs > div{background:#fff;padding:0.5em;display:flex;flex-direction:column;gap:0.4em}
.pair-imgs .lbl{font-family:ui-monospace,monospace;font-size:0.78em;color:var(--muted);
  text-transform:uppercase;letter-spacing:0.04em}
.pair-imgs img{max-width:100%;height:auto;display:block;border:1px solid var(--border)}
.pair-imgs .missing-box{flex:1;display:flex;align-items:center;justify-content:center;
  border:1px dashed var(--border);min-height:200px}
"""


def _score_class(r: float | None) -> str:
    if r is None:
        return "fail"
    if r >= 0.9:
        return "good"
    if r >= 0.5:
        return "mid"
    return "bad"


def _score_text(r: float | None) -> str:
    return "FAILED" if r is None else f"{r:.3f}"


def collect_jobs() -> list[tuple[str, list[tuple[str, float | None]]]]:
    if not OUTPUTS.exists():
        return []
    jobs = []
    for job in sorted(OUTPUTS.iterdir(), reverse=True):
        if not job.is_dir():
            continue
        tasks = []
        for task in job.iterdir():
            if not task.is_dir():
                continue
            r = _read_reward(task)
            tasks.append((task.name, r))
        # Sort: best reward first; failed tasks last.
        tasks.sort(key=lambda t: (-1 if t[1] is None else 0, -(t[1] or 0), t[0]))
        if tasks:
            jobs.append((job.name, tasks))
    return jobs


def render_index() -> str:
    jobs = collect_jobs()
    if not jobs:
        body = '<p class="empty">No outputs yet under ./outputs/</p>'
    else:
        parts: list[str] = []
        for job, tasks in jobs:
            parts.append(f'<div class="job"><div class="job-head">{job}</div><div class="grid">')
            for task, reward in tasks:
                href = f"/job/{urllib.parse.quote(job)}/{urllib.parse.quote(task)}"
                target_thumb = _first_png_url(job, task, "screenshots")
                rendered_thumb = _first_png_url(job, task, "rendered")
                parts.append(
                    f'<a class="card" href="{href}">'
                    f'<div class="thumb-pair">'
                    f'  <div>{_img_or_missing(target_thumb, "no target")}</div>'
                    f'  <div>{_img_or_missing(rendered_thumb, "no render")}</div>'
                    f'</div>'
                    f'<div class="meta">'
                    f'  <span class="name">{task}</span>'
                    f'  <span class="score {_score_class(reward)}">{_score_text(reward)}</span>'
                    f'</div></a>'
                )
            parts.append("</div></div>")
        body = "\n".join(parts)
    legend = (
        '<p class="legend">Left tile = target screenshot, right tile = agent\'s rendered clone. '
        "Score is mean SSIM across pages.</p>"
    )
    return f"""<!doctype html><html><head><title>outputs</title><style>{CSS}</style></head>
<body><h1>outputs</h1>{legend}{body}</body></html>"""


def _first_png_url(job: str, task: str, kind: str) -> str | None:
    d = OUTPUTS / job / task / kind
    if not d.is_dir():
        return None
    pngs = sorted(d.glob("*.png"), key=lambda p: (0 if p.stem == "home" else 1, p.name))
    if not pngs:
        return None
    return (
        f"/img/{urllib.parse.quote(job)}/{urllib.parse.quote(task)}/"
        f"{urllib.parse.quote(kind)}/{urllib.parse.quote(pngs[0].name)}"
    )


def _img_or_missing(url: str | None, label: str) -> str:
    if url:
        return f'<img src="{url}" loading="lazy" alt="">'
    return f'<span class="missing">{label}</span>'


def render_task(job: str, task: str) -> str | None:
    tdir = OUTPUTS / job / task
    if not tdir.is_dir():
        return None
    reward = _read_reward(tdir)
    slugs = _slugs(tdir)
    rows = []
    for slug in slugs:
        target = tdir / "screenshots" / f"{slug}.png"
        rendered = tdir / "rendered" / f"{slug}.png"
        target_url = (
            f"/img/{urllib.parse.quote(job)}/{urllib.parse.quote(task)}/"
            f"screenshots/{urllib.parse.quote(slug)}.png"
        ) if target.exists() else None
        rendered_url = (
            f"/img/{urllib.parse.quote(job)}/{urllib.parse.quote(task)}/"
            f"rendered/{urllib.parse.quote(slug)}.png"
        ) if rendered.exists() else None
        rows.append(
            f'<div class="pair"><div class="pair-head">{slug}</div>'
            f'<div class="pair-imgs">'
            f'  <div><div class="lbl">target</div>'
            f'    {_pair_img(target_url, "missing target")}</div>'
            f'  <div><div class="lbl">rendered</div>'
            f'    {_pair_img(rendered_url, "missing render")}</div>'
            f'</div></div>'
        )
    err_path = tdir / "error.txt"
    err_html = ""
    if err_path.exists():
        err = err_path.read_text()
        err_html = f'<pre style="background:#fff3f3;border:1px solid #f5caca;padding:0.8em;border-radius:6px;white-space:pre-wrap;font-size:0.85em">{_escape(err)}</pre>'
    return f"""<!doctype html><html><head><title>{task} — {job}</title><style>{CSS}</style></head>
<body>
<div class="detail-head">
  <h1>{task} <a href="/">&larr; outputs</a></h1>
  <span class="score {_score_class(reward)}">{_score_text(reward)}</span>
  <span class="legend">{job}</span>
</div>
{err_html}
{''.join(rows) if rows else '<p class="empty">No images</p>'}
</body></html>"""


def _pair_img(url: str | None, label: str) -> str:
    if url:
        return f'<img src="{url}" alt="">'
    return f'<div class="missing-box"><span class="missing">{label}</span></div>'


def _escape(s: str) -> str:
    return (
        s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args, **kwargs):
        return

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
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        parts = [urllib.parse.unquote(p) for p in parsed.path.split("/") if p]

        if not parts:
            return self._send_html(render_index())

        if parts[0] == "job" and len(parts) == 3:
            html = render_task(parts[1], parts[2])
            if html is None:
                return self._send_404("task not found")
            return self._send_html(html)

        if parts[0] == "img" and len(parts) == 5:
            job, task, kind, fname = parts[1], parts[2], parts[3], parts[4]
            if kind not in ("screenshots", "rendered") or not fname.endswith(".png"):
                return self._send_404()
            p = OUTPUTS / job / task / kind / fname
            if not _safe_under(p):
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

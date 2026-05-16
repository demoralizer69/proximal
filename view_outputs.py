#!/usr/bin/env python3
"""Tiny webserver to browse outputs/<job>/<task>/ side-by-side.

Two storage layouts are supported in outputs/<job>/<task>/:

    Multi-trial (current):
        screenshots/<slug>.png                 - target screenshots (shared)
        trial_<suffix>/reward.txt              - SSIM for that trial
        trial_<suffix>/rendered/<slug>.png     - that trial's clone
        trial_<suffix>/error.txt               - optional

    Legacy single-trial:
        screenshots/<slug>.png
        rendered/<slug>.png
        reward.txt

Index lists jobs and their tasks, ranked by best trial. Click a task to
see all trials side-by-side, ranked left -> right by reward.

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

# Sentinel used in URL paths to mean "no trial subdir" (legacy layout).
NO_TRIAL = "-"


def _read_reward(d: Path) -> float | None:
    f = d / "reward.txt"
    if not f.exists():
        return None
    try:
        return float(f.read_text().strip())
    except ValueError:
        return None


def _collect_trials(task_dir: Path) -> list[tuple[str | None, float | None, bool]]:
    """Return [(trial_subdir_name_or_None, reward, has_error)] ranked by reward desc."""
    subdirs = sorted(
        d for d in task_dir.iterdir() if d.is_dir() and d.name.startswith("trial_")
    )
    trials: list[tuple[str | None, float | None, bool]] = []
    if subdirs:
        for td in subdirs:
            trials.append((td.name, _read_reward(td), (td / "error.txt").exists()))
    elif (task_dir / "reward.txt").exists() or (task_dir / "rendered").is_dir():
        trials.append((None, _read_reward(task_dir), (task_dir / "error.txt").exists()))
    else:
        return []
    trials.sort(key=lambda t: (-1 if t[1] is None else 0, -(t[1] or 0)))
    return trials


def _best_reward(trials) -> float:
    vals = [r for _, r, _ in trials if r is not None]
    return max(vals) if vals else float("-inf")


def _slugs_for_task(task_dir: Path, trials) -> list[str]:
    seen = {p.stem for p in (task_dir / "screenshots").glob("*.png")}
    for trial_id, _, _ in trials:
        rdir = task_dir / trial_id / "rendered" if trial_id else task_dir / "rendered"
        seen |= {p.stem for p in rdir.glob("*.png")}
    slugs = sorted(seen)
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
.meta .badge{color:var(--muted);font-size:0.85em;margin-left:0.4em}
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

/* multi-trial comparison grid */
.compare-wrap{overflow-x:auto;background:var(--card);border:1px solid var(--border);
  border-radius:6px;box-shadow:var(--shadow);padding:0}
.compare{display:grid;gap:1px;background:var(--border);min-width:max-content}
.compare .ch{background:#f3f3f3;padding:0.55em 0.7em;font-family:ui-monospace,monospace;
  font-size:0.82em;position:sticky;top:0;z-index:1;display:flex;align-items:center;
  justify-content:space-between;gap:0.6em}
.compare .ch.lbl{justify-content:flex-start;color:var(--muted);text-transform:uppercase;
  font-size:0.72em;letter-spacing:0.04em}
.compare .ch .tname{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.compare .rl{background:#fafafa;padding:0.55em 0.7em;font-family:ui-monospace,monospace;
  font-size:0.82em;color:var(--fg);display:flex;align-items:center;
  border-right:1px solid var(--border)}
.compare .cell{background:#fff;padding:0.4em;display:flex;flex-direction:column;
  align-items:center;justify-content:center;min-height:160px}
.compare .cell img{max-width:100%;max-height:520px;height:auto;display:block;
  border:1px solid var(--border)}
.compare .cell .missing-box{flex:1;display:flex;align-items:center;justify-content:center;
  border:1px dashed var(--border);min-height:140px;width:100%}
.errors{margin:0 0 1.2em 0}
.errors pre{background:#fff3f3;border:1px solid #f5caca;padding:0.6em 0.8em;
  border-radius:6px;white-space:pre-wrap;font-size:0.8em;margin:0.4em 0}
.errors .ehead{font-family:ui-monospace,monospace;font-size:0.8em;color:#a03030;margin-top:0.6em}
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


def collect_jobs():
    """Return [(job_name, [(task_name, trials)])] sorted newest job first,
    tasks within job sorted by best trial reward desc."""
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
            trials = _collect_trials(task)
            if trials:
                tasks.append((task.name, trials))
        tasks.sort(key=lambda t: (-_best_reward(t[1]), t[0]))
        if tasks:
            jobs.append((job.name, tasks))
    return jobs


def _img_url(job: str, task: str, trial_id: str | None, kind: str, name: str) -> str:
    seg = urllib.parse.quote(trial_id) if trial_id else NO_TRIAL
    return (
        f"/img/{urllib.parse.quote(job)}/{urllib.parse.quote(task)}/"
        f"{seg}/{urllib.parse.quote(kind)}/{urllib.parse.quote(name)}"
    )


def _first_png(d: Path) -> str | None:
    if not d.is_dir():
        return None
    pngs = sorted(d.glob("*.png"), key=lambda p: (0 if p.stem == "home" else 1, p.name))
    return pngs[0].name if pngs else None


def _target_thumb(job: str, task_dir: Path) -> str | None:
    name = _first_png(task_dir / "screenshots")
    if not name:
        return None
    return _img_url(job, task_dir.name, None, "screenshots", name)


def _rendered_thumb(job: str, task_dir: Path, trial_id: str | None) -> str | None:
    rdir = task_dir / trial_id / "rendered" if trial_id else task_dir / "rendered"
    name = _first_png(rdir)
    if not name:
        return None
    return _img_url(job, task_dir.name, trial_id, "rendered", name)


def _img_or_missing(url: str | None, label: str) -> str:
    if url:
        return f'<img src="{url}" loading="lazy" alt="">'
    return f'<span class="missing">{label}</span>'


def render_index() -> str:
    jobs = collect_jobs()
    if not jobs:
        body = '<p class="empty">No outputs yet under ./outputs/</p>'
    else:
        parts: list[str] = []
        for job, tasks in jobs:
            parts.append(
                f'<div class="job"><div class="job-head">{_escape(job)}</div><div class="grid">'
            )
            for task, trials in tasks:
                task_dir = OUTPUTS / job / task
                best_id, best_r, _ = trials[0]
                href = f"/job/{urllib.parse.quote(job)}/{urllib.parse.quote(task)}"
                target_thumb = _target_thumb(job, task_dir)
                rendered_thumb = _rendered_thumb(job, task_dir, best_id)
                badge = (
                    f' <span class="badge">{len(trials)} trials</span>'
                    if len(trials) > 1
                    else ""
                )
                parts.append(
                    f'<a class="card" href="{href}">'
                    f'<div class="thumb-pair">'
                    f'  <div>{_img_or_missing(target_thumb, "no target")}</div>'
                    f'  <div>{_img_or_missing(rendered_thumb, "no render")}</div>'
                    f'</div>'
                    f'<div class="meta">'
                    f'  <span class="name">{_escape(task)}{badge}</span>'
                    f'  <span class="score {_score_class(best_r)}">{_score_text(best_r)}</span>'
                    f'</div></a>'
                )
            parts.append("</div></div>")
        body = "\n".join(parts)
    legend = (
        '<p class="legend">Left tile = target screenshot, right tile = best trial render. '
        "Score is mean SSIM across pages (best of N trials).</p>"
    )
    return (
        f"<!doctype html><html><head><title>outputs</title><style>{CSS}</style></head>"
        f"<body><h1>outputs</h1>{legend}{body}</body></html>"
    )


def render_task(job: str, task: str) -> str | None:
    tdir = OUTPUTS / job / task
    if not tdir.is_dir():
        return None
    trials = _collect_trials(tdir)
    if not trials:
        return None
    slugs = _slugs_for_task(tdir, trials)

    # Column widths: small label col + 1 target + N trial cols.
    n_cols = 1 + 1 + len(trials)  # label, target, trial_1..trial_K
    template = "80px 360px " + " ".join(["360px"] * len(trials))

    # Header row.
    header_cells = [
        '<div class="ch lbl">page</div>',
        '<div class="ch"><span class="tname">target</span></div>',
    ]
    for trial_id, reward, _ in trials:
        label = trial_id if trial_id else "trial"
        header_cells.append(
            f'<div class="ch"><span class="tname">{_escape(label)}</span>'
            f'<span class="score {_score_class(reward)}">{_score_text(reward)}</span></div>'
        )

    # Body rows: one per slug, columns aligned to header.
    body_cells: list[str] = []
    for slug in slugs:
        body_cells.append(f'<div class="rl">{_escape(slug)}</div>')
        target = tdir / "screenshots" / f"{slug}.png"
        if target.exists():
            url = _img_url(job, task, None, "screenshots", f"{slug}.png")
            body_cells.append(f'<div class="cell"><img src="{url}" alt=""></div>')
        else:
            body_cells.append(
                '<div class="cell"><div class="missing-box">'
                '<span class="missing">missing target</span></div></div>'
            )
        for trial_id, _, _ in trials:
            rdir = tdir / trial_id / "rendered" if trial_id else tdir / "rendered"
            rendered = rdir / f"{slug}.png"
            if rendered.exists():
                url = _img_url(job, task, trial_id, "rendered", f"{slug}.png")
                body_cells.append(f'<div class="cell"><img src="{url}" alt=""></div>')
            else:
                body_cells.append(
                    '<div class="cell"><div class="missing-box">'
                    '<span class="missing">missing render</span></div></div>'
                )

    # Errors block (collect any present).
    err_blocks = []
    for trial_id, _, has_err in trials:
        if not has_err:
            continue
        ep = tdir / trial_id / "error.txt" if trial_id else tdir / "error.txt"
        if ep.exists():
            label = trial_id if trial_id else "trial"
            err_blocks.append(
                f'<div class="ehead">{_escape(label)} error:</div>'
                f"<pre>{_escape(ep.read_text())}</pre>"
            )
    err_html = (
        f'<div class="errors">{"".join(err_blocks)}</div>' if err_blocks else ""
    )

    best_r = trials[0][1]
    grid_inner = "".join(header_cells) + "".join(body_cells)
    return (
        f"<!doctype html><html><head><title>{_escape(task)} — {_escape(job)}</title>"
        f"<style>{CSS}</style></head><body>"
        f'<div class="detail-head">'
        f'  <h1>{_escape(task)} <a href="/">&larr; outputs</a></h1>'
        f'  <span class="score {_score_class(best_r)}">{_score_text(best_r)}</span>'
        f'  <span class="legend">{_escape(job)} · {len(trials)} trial(s)</span>'
        f"</div>"
        f"{err_html}"
        f'<div class="compare-wrap">'
        f'<div class="compare" style="grid-template-columns:{template}">{grid_inner}</div>'
        f"</div></body></html>"
    )


def _escape(s: str) -> str:
    return (
        s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
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

        # /img/<job>/<task>/<trial-or-dash>/<kind>/<name.png>
        if parts[0] == "img" and len(parts) == 6:
            job, task, trial, kind, fname = parts[1:]
            if kind not in ("screenshots", "rendered") or not fname.endswith(".png"):
                return self._send_404()
            if trial == NO_TRIAL or kind == "screenshots":
                # screenshots always live at task level; legacy renders too.
                if kind == "screenshots":
                    p = OUTPUTS / job / task / kind / fname
                else:
                    p = OUTPUTS / job / task / kind / fname
            else:
                p = OUTPUTS / job / task / trial / kind / fname
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

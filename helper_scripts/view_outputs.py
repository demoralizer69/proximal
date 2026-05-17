#!/usr/bin/env python3
"""Tiny webserver to browse outputs/<job>/<task>/ side-by-side.

Two storage layouts are supported in outputs/<job>/<task>/:

    Multi-trial (current):
        screenshots/<slug>.png                 - target screenshots (shared)
        trial_<suffix>/reward.txt              - whatever the task's verifier
                                                 optimized for (clone_template
                                                 historically wrote websight,
                                                 now writes mae_pm_0.05)
        trial_<suffix>/metrics.json            - per-metric scores (optional)
        trial_<suffix>/rendered/<slug>.png     - that trial's clone
        trial_<suffix>/error.txt               - optional

    Legacy single-trial:
        screenshots/<slug>.png
        rendered/<slug>.png
        reward.txt

The metric dropdown at the top drives sorting, the main score chip, the
sparkbar highlight, and per-page chips — all client-side, no reload.

Usage:
    python3 view_outputs.py [port]   # default 8766
"""
from __future__ import annotations

import http.server
import json
import socketserver
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = ROOT / "outputs"
DEFAULT_PORT = 8766

NO_TRIAL = "-"
# nested_pm = PM_p over the same three legs websight uses ({ms_ssim, lpips_sim, ocr_f1}),
# nested across pages. ocr_f1 isn't stored explicitly; it's recovered algebraically from
# the websight composite: websight = (ms_ssim + lpips_sim + ocr_f1) / 3.
# Defined locally; not produced by the in-container evaluators.
NESTED_PM_P = 0.2
# Each entry derives a "mae aggregated with power mean p" metric from per-page
# mae scores when not explicitly stored by the evaluator runner.
MAE_PM_VARIANTS: dict[str, float] = {
    "mae_pm": 0.25,
    "mae_pm_0.05": 0.05,
}
METRICS = [
    "reward", "websight", "nested_pm",
    "ms_ssim", "ssim", "lpips", "dists",
    "mae", "mae_pm", "mae_pm_0.05", "psnr", "nemd", "ciede2000", "ocr_text",
]
METRIC_SHORT = {
    "reward": "rwd", "websight": "ws", "nested_pm": "npm",
    "ms_ssim": "ms", "ssim": "ss", "lpips": "lp", "dists": "ds",
    "mae": "mae", "mae_pm": "mae⁰⋅²⁵", "mae_pm_0.05": "mae⁰⋅⁰⁵", "psnr": "psnr",
    "nemd": "emd", "ciede2000": "de", "ocr_text": "ocr",
}
# "reward" = whatever the task verifier wrote to reward.txt. For clone_template
# pre-mae-switch that's websight; post-switch it's mae_pm_0.05. Treat as the
# only metric that's universally populated across job types.
DEFAULT_METRIC = "reward"
BAR_MAX_PX = 18
BAR_MIN_PX = 2


def _pm(xs: list[float], p: float, eps: float = 1e-6) -> float | None:
    """Generalized power mean of a non-empty list. Returns None if empty."""
    if not xs:
        return None
    if p == 1.0:
        return sum(xs) / len(xs)
    ys = [max(x, eps) for x in xs]
    return (sum(y ** p for y in ys) / len(ys)) ** (1.0 / p)


def _ocr_f1_from_websight(row: dict) -> float | None:
    """Recover ocr_f1 = 3*websight - ms_ssim - lpips_sim. Returns None if any leg
    is missing. Result is clamped to [0,1] (MS-SSIM is unclamped inside the
    websight evaluator, so the inversion can drift a fraction past 1)."""
    ms = row.get("ms_ssim")
    lp = row.get("lpips")
    ws = row.get("websight")
    if ms is None or lp is None or ws is None:
        return None
    v = 3.0 * ws - ms - lp
    return max(0.0, min(1.0, v))


def _inject_mae_pm(per_page: dict, aggregate: dict) -> None:
    """Derive each mae_pm variant from per-page mae scores when not already
    stored by the evaluator runner. Per-page chip values fall back to the raw
    mae (a one-page PM is trivially the value itself)."""
    page_vals = [row.get("mae") for row in per_page.values() if row.get("mae") is not None]
    if not page_vals:
        return
    for name, p in MAE_PM_VARIANTS.items():
        if aggregate.get(name) is None:
            v = _pm(page_vals, p)
            if v is not None:
                aggregate[name] = v
        for row in per_page.values():
            if row.get(name) is None and row.get("mae") is not None:
                row[name] = row["mae"]


def _inject_nested_pm(per_page: dict, aggregate: dict) -> None:
    """Compute nested_pm and ocr_text at the per-page and aggregate level, in
    place. nested_pm uses {ms_ssim, lpips_sim, ocr_f1} (the same three legs as
    websight) with PM_p at both the metric and across-pages levels. ocr_text
    is the OCR-F1 leg surfaced as its own metric — taken from the stored
    evaluator value if present, else derived algebraically from websight."""
    page_vals: list[float] = []
    ocr_page_vals: list[float] = []
    for slug, row in per_page.items():
        stored_ocr = row.get("ocr_text")
        ocr = stored_ocr if stored_ocr is not None else _ocr_f1_from_websight(row)
        if ocr is not None:
            row["ocr_text"] = ocr
            ocr_page_vals.append(ocr)
        comp_vals = [v for v in (row.get("ms_ssim"), row.get("lpips"), ocr) if v is not None]
        if comp_vals:
            v = _pm(comp_vals, NESTED_PM_P)
            row["nested_pm"] = v
            row["ocr_f1"] = ocr  # surface it for inspection
            if v is not None:
                page_vals.append(v)
        else:
            row["nested_pm"] = None
            row["ocr_f1"] = None
    aggregate["nested_pm"] = _pm(page_vals, NESTED_PM_P) if page_vals else None
    if aggregate.get("ocr_text") is None and ocr_page_vals:
        aggregate["ocr_text"] = sum(ocr_page_vals) / len(ocr_page_vals)


# ----------------------------------------------------------------------- data

def _read_reward(d: Path) -> float | None:
    f = d / "reward.txt"
    if not f.exists():
        return None
    try:
        return float(f.read_text().strip())
    except ValueError:
        return None


def _read_metrics(d: Path) -> dict:
    """Load metrics.json from a trial dir. Falls back to {aggregate:{reward: ...}}
    when missing, so jobs that haven't been post-evaluated still surface the
    verifier's reward. Also computes nested_pm (PM_p=0.2 over {ms_ssim, lpips,
    dists}, nested across pages)."""
    f = d / "metrics.json"
    if f.exists():
        try:
            data = json.loads(f.read_text())
            agg = dict(data.get("aggregate") or {})
            per_page = {k: dict(v) for k, v in (data.get("per_page") or {}).items()}
            _inject_mae_pm(per_page, agg)
            _inject_nested_pm(per_page, agg)
            return {"aggregate": agg, "per_page": per_page}
        except (ValueError, OSError):
            pass
    return {"aggregate": {"reward": _read_reward(d), "nested_pm": None}, "per_page": {}}


# Trial tuple: (trial_id, reward, has_error, metrics)
Trial = tuple


def _collect_trials(task_dir: Path) -> list[Trial]:
    """Return list of trials ranked by reward desc."""
    subdirs = sorted(
        d for d in task_dir.iterdir() if d.is_dir() and d.name.startswith("trial_")
    )
    trials: list[Trial] = []
    if subdirs:
        for td in subdirs:
            trials.append(
                (td.name, _read_reward(td), (td / "error.txt").exists(), _read_metrics(td))
            )
    elif (task_dir / "reward.txt").exists() or (task_dir / "rendered").is_dir():
        trials.append(
            (None, _read_reward(task_dir), (task_dir / "error.txt").exists(), _read_metrics(task_dir))
        )
    else:
        return []
    trials.sort(key=lambda t: (1 if t[1] is None else 0, -(t[1] or 0)))
    return trials


def _trial_aggregate(trial: Trial) -> dict:
    """Return the trial's aggregate metrics dict. `reward` always reflects
    reward.txt (the verifier's actual output for this trial), regardless of
    which underlying metric the task happens to optimize."""
    _, reward, _, metrics = trial
    agg = dict(metrics.get("aggregate", {}))
    if reward is not None:
        agg["reward"] = reward
    return agg


def _metric_value(trial: Trial, metric: str) -> float | None:
    return _trial_aggregate(trial).get(metric)


def _best_score(trials: list[Trial], metric: str) -> float | None:
    vals = [v for t in trials if (v := _metric_value(t, metric)) is not None]
    return max(vals) if vals else None


def _per_metric_ranges(rows: list[dict]) -> dict:
    """rows: list of dicts {metric: value|None}. Returns {metric: (min, max)|None}."""
    out: dict = {}
    for m in METRICS:
        vals = [r.get(m) for r in rows if r.get(m) is not None]
        out[m] = (min(vals), max(vals)) if vals else None
    return out


def _is_animated_task(task_dir: Path) -> bool:
    """Animated tasks store per-slug subdirectories (with frame_NN.png + clip.webm)
    under screenshots/ and trial_*/rendered/, not flat PNGs at the top level."""
    s = task_dir / "screenshots"
    if s.is_dir():
        for child in s.iterdir():
            if child.is_dir() and any(child.glob("frame_*.png")):
                return True
    return False


def _slugs_for_task(task_dir: Path, trials: list[Trial]) -> list[str]:
    animated = _is_animated_task(task_dir)
    seen: set[str] = set()
    s = task_dir / "screenshots"
    if s.is_dir():
        if animated:
            seen |= {c.name for c in s.iterdir() if c.is_dir() and any(c.glob("frame_*.png"))}
        else:
            seen |= {p.stem for p in s.glob("*.png")}
    for trial_id, _, _, _ in trials:
        rdir = task_dir / trial_id / "rendered" if trial_id else task_dir / "rendered"
        if not rdir.is_dir():
            continue
        if animated:
            seen |= {c.name for c in rdir.iterdir() if c.is_dir() and any(c.glob("frame_*.png"))}
        else:
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


# -------------------------------------------------------------------- styling

CSS = """
:root {
  --bg:#fafafa; --fg:#222; --muted:#888;
  --card:#fff; --card-hover:#f1f1f1; --border:#e6e6e6;
  --shadow:0 1px 3px rgba(0,0,0,0.06);
  --good:#0a7f2e; --mid:#b07a00; --bad:#a03030;
  --accent:#0a7f2e; --bar-muted:#cfcfcf;
}
*{box-sizing:border-box}
body{font-family:-apple-system,system-ui,sans-serif;margin:0;padding:2em 1em;
  max-width:1400px;margin:0 auto;color:var(--fg);background:var(--bg)}
.topbar{display:flex;align-items:center;justify-content:space-between;gap:1em;
  margin:0 0 0.6em 0;flex-wrap:wrap}
.topbar h1{margin:0}
.topbar h1 a{color:var(--muted);text-decoration:none;font-weight:400;font-size:0.7em}
.topbar h1 a:hover{color:var(--fg)}
.topbar .title-side{display:flex;align-items:baseline;gap:0.8em;flex-wrap:wrap}
.metric-pick{display:flex;align-items:center;gap:0.5em;font-family:ui-monospace,monospace;
  font-size:0.82em;color:var(--muted)}
.metric-selector{font-family:ui-monospace,monospace;font-size:0.85em;padding:0.3em 0.6em;
  background:#fff;border:1px solid var(--border);border-radius:5px;color:var(--fg);
  cursor:pointer}

.job{margin:0 0 2em 0}
.job > summary{font-size:0.95em;color:#555;font-weight:500;border-bottom:1px solid var(--border);
  padding-bottom:0.3em;font-family:ui-monospace,monospace;margin:0 0 0.8em 0;
  cursor:pointer;list-style:none;display:flex;align-items:center;gap:0.5em;user-select:none}
.job > summary::-webkit-details-marker{display:none}
.job > summary::before{content:"▸";color:var(--muted);font-size:0.85em;
  transition:transform 0.12s;display:inline-block;width:0.9em;flex-shrink:0}
.job[open] > summary::before{transform:rotate(90deg)}
.job > summary:hover{color:var(--fg)}
.job > summary .job-count{color:var(--muted);font-size:0.85em;font-weight:400;margin-left:auto}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1em}
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
.meta .name{color:var(--fg);word-break:break-all;flex:1;min-width:0}
.meta .badge{color:var(--muted);font-size:0.85em;margin-left:0.4em;white-space:nowrap}
.meta .card-side{display:flex;align-items:center;gap:0.45em;flex-shrink:0}
.score{font-weight:600;font-family:ui-monospace,monospace}
.score.good{color:var(--good)}
.score.mid{color:var(--mid)}
.score.bad{color:var(--bad)}
.score.fail{color:var(--muted);font-style:italic}
.empty{color:var(--muted);font-style:italic}
.legend{color:var(--muted);font-size:0.85em;margin:0.4em 0 1.2em 0}

/* sparkbar */
.sparkbar{display:inline-flex;gap:2px;align-items:flex-end;height:18px;
  vertical-align:middle;padding:0 1px}
.sparkbar .bar{width:5px;background:var(--bar-muted);border-radius:1px 1px 0 0;
  transition:background 0.12s,outline 0.12s}
.sparkbar .bar.sel{background:var(--accent);outline:1px solid rgba(10,127,46,0.25)}

/* detail page */
.compare-wrap{overflow-x:auto;background:var(--card);border:1px solid var(--border);
  border-radius:6px;box-shadow:var(--shadow);padding:0}
.compare{display:grid;gap:1px;background:var(--border);min-width:max-content}
.compare .ch{background:#f3f3f3;padding:0.55em 0.7em;font-family:ui-monospace,monospace;
  font-size:0.82em;position:sticky;top:0;z-index:1;display:flex;align-items:center;
  justify-content:space-between;gap:0.6em;flex-wrap:wrap}
.compare .ch.lbl{justify-content:flex-start;color:var(--muted);text-transform:uppercase;
  font-size:0.72em;letter-spacing:0.04em}
.compare .ch .tname{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}
.compare .ch.trial-head{gap:0.4em}
.compare .ch.trial-head .head-side{display:flex;align-items:center;gap:0.4em;flex-shrink:0}
.compare .rl{background:#fafafa;padding:0.55em 0.7em;font-family:ui-monospace,monospace;
  font-size:0.82em;color:var(--fg);display:flex;align-items:center;
  border-right:1px solid var(--border)}
.compare .cell{background:#fff;padding:0.4em;display:flex;flex-direction:column;
  align-items:center;justify-content:center;min-height:160px;position:relative}
.compare .cell img{max-width:100%;max-height:520px;height:auto;display:block;
  border:1px solid var(--border)}
.compare .cell .missing-box{flex:1;display:flex;align-items:center;justify-content:center;
  border:1px dashed var(--border);min-height:140px;width:100%}
.compare .cell .page-chip{position:absolute;top:6px;right:6px;
  font-size:0.72em;padding:0.15em 0.45em;
  background:rgba(255,255,255,0.92);border:1px solid var(--border);border-radius:4px;
  font-family:ui-monospace,monospace;font-weight:600;
  box-shadow:0 1px 2px rgba(0,0,0,0.08);cursor:help}
.compare .cell video{max-width:100%;max-height:520px;height:auto;display:block;
  border:1px solid var(--border);background:#000}
.compare .cell .frame-strip{display:grid;grid-template-columns:repeat(6,1fr);
  gap:2px;margin-top:0.4em;width:100%}
.compare .cell .frame-strip img{width:100%;height:auto;display:block;
  border:1px solid var(--border)}
.errors{margin:0 0 1.2em 0}
.errors pre{background:#fff3f3;border:1px solid #f5caca;padding:0.6em 0.8em;
  border-radius:6px;white-space:pre-wrap;font-size:0.8em;margin:0.4em 0}
.errors .ehead{font-family:ui-monospace,monospace;font-size:0.8em;color:#a03030;margin-top:0.6em}
"""


# Per-metric thresholds (good / mid). Initial server render uses websight
# values via _score_class; JS overrides on dropdown change.
JS = """
const METRICS = ["reward","websight","nested_pm","ms_ssim","ssim","lpips","dists","mae","mae_pm","mae_pm_0.05","psnr","nemd","ciede2000","ocr_text"];
const SHORT = {reward:"rwd", websight:"ws", nested_pm:"npm", ms_ssim:"ms", ssim:"ss", lpips:"lp", dists:"ds",
               mae:"mae", mae_pm:"mae⁰⋅²⁵", "mae_pm_0.05":"mae⁰⋅⁰⁵", psnr:"psnr", nemd:"emd", ciede2000:"de", ocr_text:"ocr"};
const THRESH = {
  reward:        [0.8, 0.5],
  websight:      [0.9, 0.5],
  nested_pm:     [0.7, 0.45],
  ms_ssim:       [0.7, 0.4],
  ssim:          [0.7, 0.4],
  lpips:         [0.7, 0.45],
  dists:         [0.85, 0.7],
  mae:           [0.95, 0.85],
  mae_pm:        [0.95, 0.85],
  "mae_pm_0.05": [0.95, 0.85],
  psnr:          [0.55, 0.40],
  nemd:          [0.95, 0.80],
  ciede2000:     [0.85, 0.65],
  ocr_text:      [0.7, 0.4],
};
function fmt(v){ return (v==null) ? "\\u2014" : v.toFixed(3); }
function cls(v, m){
  if (v==null) return "fail";
  const [g, mid] = THRESH[m] || [0.9, 0.5];
  if (v >= g) return "good";
  if (v >= mid) return "mid";
  return "bad";
}
function parseM(s){ try { return JSON.parse(s); } catch(_){ return {}; } }

function apply(metric){
  localStorage.setItem("viewMetric", metric);
  document.querySelectorAll("select.metric-selector").forEach(s => { s.value = metric; });

  // 1. Reorder index cards within each .grid
  document.querySelectorAll(".job > .grid").forEach(grid => {
    const cards = Array.from(grid.querySelectorAll(":scope > .card"));
    cards.sort((a,b) => {
      const va = parseM(a.dataset.metrics)[metric];
      const vb = parseM(b.dataset.metrics)[metric];
      return (vb==null ? -Infinity : vb) - (va==null ? -Infinity : va);
    });
    cards.forEach(c => grid.appendChild(c));
  });

  // 2. Reorder detail-page trial columns via grid-column rewrites
  const compare = document.querySelector(".compare");
  if (compare) {
    const heads = Array.from(compare.querySelectorAll('.ch.trial-head'));
    const ordered = heads.slice().sort((a,b) => {
      const va = parseM(a.dataset.metrics)[metric];
      const vb = parseM(b.dataset.metrics)[metric];
      return (vb==null ? -Infinity : vb) - (va==null ? -Infinity : va);
    });
    const colMap = new Map();
    ordered.forEach((h, i) => colMap.set(h.dataset.col, 3 + i));
    compare.querySelectorAll('[data-col]').forEach(el => {
      const k = el.dataset.col;
      if (k === "label")       el.style.gridColumn = 1;
      else if (k === "target") el.style.gridColumn = 2;
      else if (colMap.has(k))  el.style.gridColumn = colMap.get(k);
    });
  }

  // 3. Update main score chips on every element carrying data-metrics
  document.querySelectorAll("[data-metrics]").forEach(el => {
    const v = parseM(el.dataset.metrics)[metric];
    if (el.classList.contains("score")) {
      el.textContent = fmt(v);
      el.className = "score " + (el.classList.contains("detail-best") ? "detail-best " : "") + cls(v, metric);
      return;
    }
    const chip = el.querySelector(":scope .score:not(.page-chip)");
    if (chip) {
      chip.textContent = fmt(v);
      chip.className = "score " + cls(v, metric);
    }
  });

  // 4. Per-page chips
  document.querySelectorAll("[data-per-page]").forEach(chip => {
    const v = parseM(chip.dataset.perPage)[metric];
    chip.textContent = fmt(v);
    chip.className = "score page-chip " + cls(v, metric);
  });

  // 5. Sparkbar highlight
  document.querySelectorAll(".sparkbar .bar").forEach(b => {
    b.classList.toggle("sel", b.dataset.m === metric);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  const stored = localStorage.getItem("viewMetric") || "reward";
  document.querySelectorAll("select.metric-selector").forEach(s => {
    s.addEventListener("change", e => apply(e.target.value));
  });
  apply(stored);

  // Fold state persistence for each job <details>
  document.querySelectorAll("details.job[data-job]").forEach(d => {
    const key = "fold:" + d.dataset.job;
    if (localStorage.getItem(key) === "0") d.open = false;
    d.addEventListener("toggle", () => {
      localStorage.setItem(key, d.open ? "1" : "0");
    });
  });
});
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
    return "—" if r is None else f"{r:.3f}"


def _escape(s: str) -> str:
    return (
        s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def _attr_json(d: dict) -> str:
    """Emit a JSON dict safe for use inside single-quoted HTML attributes.
    Float-only values mean no characters need escaping beyond the apostrophe,
    which json.dumps doesn't produce."""
    return json.dumps(d, separators=(",", ":"))


def _sparkbar_html(values: dict, ranges: dict, selected: str) -> str:
    bars = []
    for m in METRICS:
        v = values.get(m)
        rng = ranges.get(m)
        if v is None or rng is None:
            h = BAR_MIN_PX
        elif rng[1] == rng[0]:
            h = BAR_MAX_PX  # all siblings tied → max height
        else:
            lo, hi = rng
            h = BAR_MIN_PX + round(((v - lo) / (hi - lo)) * (BAR_MAX_PX - BAR_MIN_PX))
            h = max(BAR_MIN_PX, min(BAR_MAX_PX, h))
        cls_ = "bar sel" if m == selected else "bar"
        title = f"{METRIC_SHORT[m]} {v:.3f}" if v is not None else f"{METRIC_SHORT[m]} —"
        bars.append(
            f'<div class="{cls_}" data-m="{m}" style="height:{h}px" title="{_escape(title)}"></div>'
        )
    return f'<div class="sparkbar">{"".join(bars)}</div>'


def _page_chip_html(per_page: dict, slug: str, selected: str) -> str:
    pm = per_page.get(slug) or {}
    title = "  ".join(
        f"{METRIC_SHORT[m]}={pm.get(m):.3f}"
        if pm.get(m) is not None
        else f"{METRIC_SHORT[m]}=—"
        for m in METRICS
    )
    v = pm.get(selected)
    return (
        f'<span class="score page-chip {_score_class(v)}" '
        f"data-per-page='{_attr_json(pm)}' "
        f'title="{_escape(title)}">{_score_text(v)}</span>'
    )


# ---------------------------------------------------------------------- pages

def collect_jobs():
    """Return [(job_name, [(task_name, trials)])] sorted newest job first,
    tasks within a job sorted by best-trial websight desc (the JS reorders
    once the user picks a different metric)."""
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
        tasks.sort(
            key=lambda t: (
                -(_best_score(t[1], DEFAULT_METRIC) or float("-inf")),
                t[0],
            )
        )
        if tasks:
            jobs.append((job.name, tasks))
    return jobs


def _asset_url(job: str, task: str, trial_id: str | None, kind: str, rest: str) -> str:
    """URL to an arbitrary asset path inside <kind>/. `rest` may be 'foo.png' or 'slug/frame_00.png'."""
    seg = urllib.parse.quote(trial_id) if trial_id else NO_TRIAL
    rest_q = "/".join(urllib.parse.quote(p) for p in rest.split("/") if p)
    return (
        f"/asset/{urllib.parse.quote(job)}/{urllib.parse.quote(task)}/"
        f"{seg}/{urllib.parse.quote(kind)}/{rest_q}"
    )


def _first_png(d: Path) -> str | None:
    if not d.is_dir():
        return None
    pngs = sorted(d.glob("*.png"), key=lambda p: (0 if p.stem == "home" else 1, p.name))
    return pngs[0].name if pngs else None


def _first_slug(d: Path) -> str | None:
    if not d.is_dir():
        return None
    subs = sorted(
        (c for c in d.iterdir() if c.is_dir() and any(c.glob("frame_*.png"))),
        key=lambda c: (0 if c.name == "home" else 1, c.name),
    )
    return subs[0].name if subs else None


def _target_thumb(job: str, task_dir: Path, animated: bool) -> str | None:
    sdir = task_dir / "screenshots"
    if animated:
        slug = _first_slug(sdir)
        if not slug:
            return None
        return _asset_url(job, task_dir.name, None, "screenshots", f"{slug}/frame_00.png")
    name = _first_png(sdir)
    if not name:
        return None
    return _asset_url(job, task_dir.name, None, "screenshots", name)


def _rendered_thumb(job: str, task_dir: Path, trial_id: str | None, animated: bool) -> str | None:
    rdir = task_dir / trial_id / "rendered" if trial_id else task_dir / "rendered"
    if animated:
        slug = _first_slug(rdir)
        if not slug:
            return None
        return _asset_url(job, task_dir.name, trial_id, "rendered", f"{slug}/frame_00.png")
    name = _first_png(rdir)
    if not name:
        return None
    return _asset_url(job, task_dir.name, trial_id, "rendered", name)


def _img_or_missing(url: str | None, label: str) -> str:
    if url:
        return f'<img src="{url}" loading="lazy" alt="">'
    return f'<span class="missing">{label}</span>'


def _dropdown_html(default: str = DEFAULT_METRIC) -> str:
    options = "".join(
        f'<option value="{m}"{" selected" if m == default else ""}>{m}</option>'
        for m in METRICS
    )
    return (
        f'<span class="metric-pick">metric '
        f'<select class="metric-selector">{options}</select>'
        f"</span>"
    )


def _page_shell(title: str, title_html: str, body: str, legend: str = "") -> str:
    legend_html = f'<p class="legend">{legend}</p>' if legend else ""
    return (
        f"<!doctype html><html><head><meta charset=\"utf-8\">"
        f"<title>{_escape(title)}</title>"
        f"<style>{CSS}</style></head><body>"
        f'<div class="topbar"><div class="title-side">{title_html}</div>{_dropdown_html()}</div>'
        f"{legend_html}{body}"
        f"<script>{JS}</script>"
        f"</body></html>"
    )


def render_index() -> str:
    jobs = collect_jobs()
    if not jobs:
        body = '<p class="empty">No outputs yet under ./outputs/</p>'
    else:
        parts: list[str] = []
        for job, tasks in jobs:
            # Best-trial aggregates per task (for card data + sparkbar normalization).
            best_aggs = [
                {m: _best_score(trials, m) for m in METRICS} for _, trials in tasks
            ]
            ranges = _per_metric_ranges(best_aggs)
            parts.append(
                f'<details class="job" data-job="{_escape(job)}" open>'
                f'<summary>{_escape(job)}'
                f'<span class="job-count">{len(tasks)} task{"s" if len(tasks) != 1 else ""}</span>'
                f'</summary><div class="grid">'
            )
            for (task, trials), best in zip(tasks, best_aggs):
                task_dir = OUTPUTS / job / task
                best_trial_id = trials[0][0]
                href = f"/job/{urllib.parse.quote(job)}/{urllib.parse.quote(task)}"
                animated = _is_animated_task(task_dir)
                target_thumb = _target_thumb(job, task_dir, animated)
                rendered_thumb = _rendered_thumb(job, task_dir, best_trial_id, animated)
                n = len(trials)
                badge = f' <span class="badge">{n} trial{"s" if n != 1 else ""}</span>'
                v0 = best.get(DEFAULT_METRIC)
                parts.append(
                    f'<a class="card" href="{href}" data-metrics=\'{_attr_json(best)}\'>'
                    f'<div class="thumb-pair">'
                    f'<div>{_img_or_missing(target_thumb, "no target")}</div>'
                    f'<div>{_img_or_missing(rendered_thumb, "no render")}</div>'
                    f"</div>"
                    f'<div class="meta">'
                    f'<span class="name">{_escape(task)}{badge}</span>'
                    f'<span class="card-side">'
                    f"{_sparkbar_html(best, ranges, DEFAULT_METRIC)}"
                    f'<span class="score {_score_class(v0)}">{_score_text(v0)}</span>'
                    f"</span></div></a>"
                )
            parts.append("</div></details>")
        body = "\n".join(parts)
    return _page_shell(
        title="outputs",
        title_html='<h1>outputs</h1>',
        body=body,
        legend=(
            "Left tile = target, right tile = best trial render. "
            "Sparkbar = ws / npm / ms / ss / lp / ds / mae / mae⁰⋅²⁵ / mae⁰⋅⁰⁵ / psnr / emd / de / ocr normalized within the job; selected metric is highlighted. "
            "Use the dropdown to re-sort + relabel."
        ),
    )


def render_task(job: str, task: str) -> str | None:
    tdir = OUTPUTS / job / task
    if not tdir.is_dir():
        return None
    trials = _collect_trials(tdir)
    if not trials:
        return None
    animated = _is_animated_task(tdir)
    slugs = _slugs_for_task(tdir, trials)

    n_trials = len(trials)
    n_rows = 1 + len(slugs)
    template = "80px 360px " + " ".join(["360px"] * n_trials)

    per_trial_agg = [_trial_aggregate(t) for t in trials]
    ranges = _per_metric_ranges(per_trial_agg)
    best_per_metric = {m: _best_score(trials, m) for m in METRICS}

    cells: list[str] = []

    # Row 1: header
    cells.append(
        '<div class="ch lbl" style="grid-row:1;grid-column:1" data-col="label">page</div>'
    )
    cells.append(
        '<div class="ch" style="grid-row:1;grid-column:2" data-col="target">'
        '<span class="tname">target</span></div>'
    )
    for i, (trial_id, _, _, _) in enumerate(trials):
        col_idx = 3 + i
        col_key = f"trial:{trial_id or 'legacy'}"
        label = trial_id if trial_id else "trial"
        agg = per_trial_agg[i]
        v0 = agg.get(DEFAULT_METRIC)
        cells.append(
            f'<div class="ch trial-head" style="grid-row:1;grid-column:{col_idx}" '
            f"data-col=\"{col_key}\" data-metrics='{_attr_json(agg)}'>"
            f'<span class="tname">{_escape(label)}</span>'
            f'<span class="head-side">{_sparkbar_html(agg, ranges, DEFAULT_METRIC)}'
            f'<span class="score {_score_class(v0)}">{_score_text(v0)}</span>'
            f"</span></div>"
        )

    def _media_html(target_dir: Path, trial_id: str | None, kind: str, slug: str) -> str:
        """Render a target or candidate cell. For animated tasks, emit a <video>
        with the keyframe strip below; for static, emit a single <img>."""
        if animated:
            slug_dir = target_dir / slug
            if not slug_dir.is_dir() or not any(slug_dir.glob("frame_*.png")):
                return ('<div class="missing-box"><span class="missing">missing</span></div>')
            video_url = _asset_url(job, task, trial_id, kind, f"{slug}/clip.webm")
            poster_url = _asset_url(job, task, trial_id, kind, f"{slug}/frame_00.png")
            frames = sorted(slug_dir.glob("frame_*.png"))
            thumbs = "".join(
                f'<img src="{_asset_url(job, task, trial_id, kind, f"{slug}/{f.name}")}" '
                f'alt="" title="{f.stem}">'
                for f in frames
            )
            return (
                f'<video src="{video_url}" poster="{poster_url}" autoplay loop muted playsinline></video>'
                f'<div class="frame-strip">{thumbs}</div>'
            )
        path = target_dir / f"{slug}.png"
        if not path.exists():
            return '<div class="missing-box"><span class="missing">missing</span></div>'
        url = _asset_url(job, task, trial_id, kind, f"{slug}.png")
        return f'<img src="{url}" alt="">'

    # Body rows
    for ri, slug in enumerate(slugs):
        row_idx = 2 + ri
        cells.append(
            f'<div class="rl" style="grid-row:{row_idx};grid-column:1" '
            f'data-col="label">{_escape(slug)}</div>'
        )
        target_cell = _media_html(tdir / "screenshots", None, "screenshots", slug)
        cells.append(
            f'<div class="cell" style="grid-row:{row_idx};grid-column:2" '
            f'data-col="target">{target_cell}</div>'
        )
        for i, (trial_id, _, _, metrics) in enumerate(trials):
            col_idx = 3 + i
            col_key = f"trial:{trial_id or 'legacy'}"
            rdir = tdir / trial_id / "rendered" if trial_id else tdir / "rendered"
            chip = _page_chip_html(metrics.get("per_page") or {}, slug, DEFAULT_METRIC)
            inner = _media_html(rdir, trial_id, "rendered", slug) + chip
            cells.append(
                f'<div class="cell" style="grid-row:{row_idx};grid-column:{col_idx}" '
                f'data-col="{col_key}">{inner}</div>'
            )

    # Errors block
    err_blocks = []
    for trial_id, _, has_err, _ in trials:
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

    v_best = best_per_metric.get(DEFAULT_METRIC)
    title_html = (
        f'<h1>{_escape(task)} <a href="/">&larr; outputs</a></h1>'
        f'<span class="score detail-best {_score_class(v_best)}" '
        f"data-metrics='{_attr_json(best_per_metric)}'>"
        f"{_score_text(v_best)}</span>"
        f'<span class="legend">{_escape(job)} · {len(trials)} trial(s)</span>'
    )
    body = (
        f"{err_html}"
        f'<div class="compare-wrap">'
        f'<div class="compare" '
        f'style="grid-template-columns:{template};grid-template-rows:repeat({n_rows}, auto)">'
        f"{''.join(cells)}"
        f"</div></div>"
    )
    return _page_shell(
        title=f"{task} — {job}",
        title_html=title_html,
        body=body,
    )


# -------------------------------------------------------------------- server

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

    def _send_file(self, path: Path, content_type: str) -> None:
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            return self._send_404()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
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

        # /asset/<job>/<task>/<trial-or-dash>/<kind>/<rest...>
        if parts[0] == "asset" and len(parts) >= 6:
            job, task, trial, kind = parts[1:5]
            rest = "/".join(parts[5:])
            if kind not in ("screenshots", "rendered"):
                return self._send_404()
            if trial == NO_TRIAL or kind == "screenshots":
                p = OUTPUTS / job / task / kind / rest
            else:
                p = OUTPUTS / job / task / trial / kind / rest
            if not _safe_under(p):
                return self._send_404()
            if rest.endswith(".png"):
                return self._send_file(p, "image/png")
            if rest.endswith(".webm"):
                return self._send_file(p, "video/webm")
            return self._send_404()

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

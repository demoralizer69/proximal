"""Procedurally generate a random landing-page-style HTML and screenshot it.

Outputs:
    /opt/reference/index.html  — reference HTML (hidden from the agent)
    /app/webpage.png           — 800x600 PNG screenshot for the agent
"""
from __future__ import annotations

import os
import random
import secrets
import subprocess
import sys
from pathlib import Path

VIEWPORT_W = 800
VIEWPORT_H = 600

PALETTES = [
    {"bg": "#0f172a", "fg": "#f8fafc", "muted": "#94a3b8", "accent": "#38bdf8", "card": "#1e293b"},
    {"bg": "#fff7ed", "fg": "#1c1917", "muted": "#78716c", "accent": "#ea580c", "card": "#ffedd5"},
    {"bg": "#ecfdf5", "fg": "#064e3b", "muted": "#047857", "accent": "#10b981", "card": "#d1fae5"},
    {"bg": "#fef2f2", "fg": "#7f1d1d", "muted": "#991b1b", "accent": "#dc2626", "card": "#fecaca"},
    {"bg": "#f5f3ff", "fg": "#312e81", "muted": "#6d28d9", "accent": "#7c3aed", "card": "#ede9fe"},
    {"bg": "#1a1a1a", "fg": "#fafafa", "muted": "#a3a3a3", "accent": "#facc15", "card": "#262626"},
]

BRAND_PARTS_A = ["Lumen", "Orbit", "Nova", "Glint", "Forge", "Pulse", "Drift", "Vector"]
BRAND_PARTS_B = ["Labs", "Works", "Hub", "Stack", "Cloud", "Core", "Loop", "OS"]

HEADLINES = [
    "Ship faster, sleep better.",
    "The fastest way to build modern apps.",
    "Tools that just get out of your way.",
    "Your team's new favorite workspace.",
    "Built for makers, not meetings.",
    "Production-ready in minutes, not months.",
]

SUBHEADS = [
    "A single platform for everything your team builds, deploys, and ships.",
    "Stop wrestling with infrastructure. Start shipping product.",
    "From idea to production in under an hour. Free for small teams.",
    "Type-safe, fast, and obsessively designed. Trusted by 12,000+ teams.",
]

CTA_LABELS = ["Get started", "Try it free", "Start building", "Sign up", "Start free trial"]
SECONDARY_LABELS = ["Live demo", "Read the docs", "View on GitHub", "See pricing"]

FEATURE_TITLES = [
    "Lightning fast", "Zero config", "Type-safe APIs", "Self-hosting",
    "Built-in auth", "Edge runtime", "Smart caching", "Open source",
    "Realtime sync", "Audit logs", "Team workspaces", "One-click deploy",
]

FEATURE_BODIES = [
    "Cold starts under 50ms. Hot reloads instantly.",
    "Sensible defaults. Override only when you need to.",
    "Schemas inferred from your database. No drift.",
    "Run it on your own hardware. Your data, your rules.",
    "OAuth, SSO, MFA — wired up with one line.",
    "Deploys close to your users automatically.",
    "Invalidation that actually works. No more stale reads.",
    "Read the source. File an issue. Send a PR.",
]


def pick(items, n=1, rng=random):
    return rng.sample(items, n)


def render_html(rng: random.Random) -> str:
    palette = rng.choice(PALETTES)
    brand = rng.choice(BRAND_PARTS_A) + rng.choice(BRAND_PARTS_B)
    headline = rng.choice(HEADLINES)
    subhead = rng.choice(SUBHEADS)
    cta = rng.choice(CTA_LABELS)
    secondary = rng.choice(SECONDARY_LABELS)
    features = list(zip(pick(FEATURE_TITLES, 3, rng), pick(FEATURE_BODIES, 3, rng)))
    nav_items = pick(["Product", "Docs", "Pricing", "Customers", "Blog", "Changelog"], 4, rng)
    radius = rng.choice([4, 8, 12, 16])
    show_badge = rng.random() < 0.5
    badge = rng.choice(["New", "Beta", "v2.0", "Live"]) if show_badge else ""

    features_html = "\n".join(
        f'      <div class="card"><div class="ctitle">{t}</div><div class="cbody">{b}</div></div>'
        for t, b in features
    )

    badge_html = (
        f'<span class="badge">{badge}</span>' if show_badge else ""
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{brand}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: 800px; height: 600px; overflow: hidden; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: {palette["bg"]};
    color: {palette["fg"]};
    -webkit-font-smoothing: antialiased;
  }}
  nav {{
    display: flex; align-items: center; justify-content: space-between;
    padding: 16px 32px; border-bottom: 1px solid {palette["card"]};
  }}
  .brand {{ font-weight: 700; font-size: 18px; color: {palette["fg"]}; }}
  .brand .dot {{ color: {palette["accent"]}; }}
  .nav-links {{ display: flex; gap: 24px; }}
  .nav-links a {{ color: {palette["muted"]}; font-size: 14px; text-decoration: none; }}
  .hero {{
    text-align: center; padding: 56px 32px 32px;
  }}
  .badge {{
    display: inline-block; padding: 4px 12px; border-radius: 999px;
    background: {palette["card"]}; color: {palette["accent"]};
    font-size: 12px; font-weight: 600; margin-bottom: 16px;
    border: 1px solid {palette["accent"]};
  }}
  h1 {{
    font-size: 40px; font-weight: 800; letter-spacing: -0.02em;
    margin-bottom: 16px; line-height: 1.1;
  }}
  .subhead {{
    color: {palette["muted"]}; font-size: 16px; max-width: 520px;
    margin: 0 auto 24px; line-height: 1.5;
  }}
  .ctas {{ display: flex; gap: 12px; justify-content: center; }}
  .btn {{
    padding: 10px 20px; border-radius: {radius}px; font-size: 14px;
    font-weight: 600; cursor: pointer; border: none;
  }}
  .btn-primary {{ background: {palette["accent"]}; color: {palette["bg"]}; }}
  .btn-secondary {{
    background: transparent; color: {palette["fg"]};
    border: 1px solid {palette["muted"]};
  }}
  .features {{
    display: grid; grid-template-columns: repeat(3, 1fr);
    gap: 16px; padding: 32px;
  }}
  .card {{
    background: {palette["card"]}; padding: 20px;
    border-radius: {radius}px;
  }}
  .ctitle {{ font-weight: 700; font-size: 15px; margin-bottom: 8px; }}
  .cbody {{ color: {palette["muted"]}; font-size: 13px; line-height: 1.5; }}
</style>
</head>
<body>
  <nav>
    <div class="brand">{brand[0]}<span class="dot">●</span> {brand[1:]}</div>
    <div class="nav-links">
      {''.join(f'<a href="#">{x}</a>' for x in nav_items)}
    </div>
  </nav>
  <section class="hero">
    {badge_html}
    <h1>{headline}</h1>
    <p class="subhead">{subhead}</p>
    <div class="ctas">
      <button class="btn btn-primary">{cta}</button>
      <button class="btn btn-secondary">{secondary}</button>
    </div>
  </section>
  <section class="features">
{features_html}
  </section>
</body>
</html>
"""


def screenshot(html_path: Path, png_path: Path) -> None:
    subprocess.run(
        [
            "chromium",
            "--headless=new",
            "--no-sandbox",
            "--disable-gpu",
            "--hide-scrollbars",
            "--disable-dev-shm-usage",
            f"--window-size={VIEWPORT_W},{VIEWPORT_H}",
            f"--screenshot={png_path}",
            f"file://{html_path}",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> int:
    seed = int.from_bytes(secrets.token_bytes(8), "big")
    rng = random.Random(seed)

    Path("/opt/reference").mkdir(parents=True, exist_ok=True)
    Path("/app").mkdir(parents=True, exist_ok=True)

    ref_html = Path("/opt/reference/index.html")
    ref_html.write_text(render_html(rng))

    screenshot(ref_html, Path("/app/webpage.png"))
    Path("/app/.seed").write_text(str(seed))
    print(f"generated: seed={seed}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

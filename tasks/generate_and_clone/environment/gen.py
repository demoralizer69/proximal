"""GENERATOR — procedurally produce a random website spec.

Contract (do not break without also updating the agent's step-1 instruction.md):
    Input:  none
    Output: writes /app/website_details.json

This file is the iteration point for changing what kind of webpages the
pipeline generates. Everything downstream (the step-1 agent's HTML, the
Playwright screenshot, the step-2 agent's clone, the SSIM score) flows from
whatever this script writes.
"""
from __future__ import annotations

import json
import random
import secrets
import sys
from pathlib import Path

PALETTES = [
    {"name": "midnight", "bg": "#0f172a", "fg": "#f8fafc", "muted": "#94a3b8", "accent": "#38bdf8", "card": "#1e293b"},
    {"name": "sunrise", "bg": "#fff7ed", "fg": "#1c1917", "muted": "#78716c", "accent": "#ea580c", "card": "#ffedd5"},
    {"name": "mint", "bg": "#ecfdf5", "fg": "#064e3b", "muted": "#047857", "accent": "#10b981", "card": "#d1fae5"},
    {"name": "rose", "bg": "#fef2f2", "fg": "#7f1d1d", "muted": "#991b1b", "accent": "#dc2626", "card": "#fecaca"},
    {"name": "violet", "bg": "#f5f3ff", "fg": "#312e81", "muted": "#6d28d9", "accent": "#7c3aed", "card": "#ede9fe"},
    {"name": "carbon", "bg": "#1a1a1a", "fg": "#fafafa", "muted": "#a3a3a3", "accent": "#facc15", "card": "#262626"},
]

BRAND_PARTS_A = ["Lumen", "Orbit", "Nova", "Glint", "Forge", "Pulse", "Drift", "Vector", "Helix", "Quanta"]
BRAND_PARTS_B = ["Labs", "Works", "Hub", "Stack", "Cloud", "Core", "Loop", "OS", "Forge", "Studio"]

HEADLINES = [
    "Ship faster, sleep better.",
    "The fastest way to build modern apps.",
    "Tools that just get out of your way.",
    "Your team's new favorite workspace.",
    "Built for makers, not meetings.",
    "Production-ready in minutes, not months.",
    "Software, but actually enjoyable.",
    "Stop configuring. Start building.",
]

SUBHEADS = [
    "A single platform for everything your team builds, deploys, and ships.",
    "Stop wrestling with infrastructure. Start shipping product.",
    "From idea to production in under an hour. Free for small teams.",
    "Type-safe, fast, and obsessively designed. Trusted by 12,000+ teams.",
    "Designed for developers who care about the details.",
    "Less yak-shaving. More shipping.",
]

CTA_LABELS = ["Get started", "Try it free", "Start building", "Sign up", "Start free trial", "Launch app"]
SECONDARY_LABELS = ["Live demo", "Read the docs", "View on GitHub", "See pricing", "Watch video"]

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
    "Push updates and clients sync in milliseconds.",
    "Every change recorded. Compliance, made simple.",
    "Roles, invites, and SSO out of the box.",
    "Ship to production with a single command.",
]

NAV_ITEMS = ["Product", "Docs", "Pricing", "Customers", "Blog", "Changelog", "Company", "Support"]
FONT_STACKS = [
    {"name": "system-sans", "css": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"},
    {"name": "serif", "css": "Georgia, 'Times New Roman', serif"},
    {"name": "mono", "css": "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"},
]
BADGE_LABELS = ["New", "Beta", "v2.0", "Live", "Preview"]
LAYOUTS = ["centered", "left-aligned"]


def main() -> int:
    seed = int.from_bytes(secrets.token_bytes(8), "big")
    rng = random.Random(seed)

    palette = rng.choice(PALETTES)
    brand = rng.choice(BRAND_PARTS_A) + rng.choice(BRAND_PARTS_B)
    n_features = rng.randint(2, 4)
    feature_idx = rng.sample(range(len(FEATURE_TITLES)), n_features)
    body_idx = rng.sample(range(len(FEATURE_BODIES)), n_features)
    features = [
        {"title": FEATURE_TITLES[i], "body": FEATURE_BODIES[j]}
        for i, j in zip(feature_idx, body_idx)
    ]

    n_nav = rng.randint(3, 5)
    nav = rng.sample(NAV_ITEMS, n_nav)

    show_badge = rng.random() < 0.5
    badge = rng.choice(BADGE_LABELS) if show_badge else None

    spec = {
        "brand": brand,
        "tagline_badge": badge,
        "palette": {
            "name": palette["name"],
            "background": palette["bg"],
            "foreground": palette["fg"],
            "muted": palette["muted"],
            "accent": palette["accent"],
            "card": palette["card"],
        },
        "font_family": rng.choice(FONT_STACKS)["css"],
        "border_radius_px": rng.choice([4, 8, 12, 16, 20]),
        "layout": rng.choice(LAYOUTS),
        "viewport": {"width": 800, "height": 600},
        "navigation": {
            "show": True,
            "items": nav,
        },
        "hero": {
            "headline": rng.choice(HEADLINES),
            "subheadline": rng.choice(SUBHEADS),
            "primary_cta": rng.choice(CTA_LABELS),
            "secondary_cta": rng.choice(SECONDARY_LABELS),
        },
        "features": features,
        "footer_text": f"© 2026 {brand}. All rights reserved.",
        "seed": seed,
    }

    Path("/app").mkdir(parents=True, exist_ok=True)
    out = Path("/app/website_details.json")
    out.write_text(json.dumps(spec, indent=2) + "\n")
    print(f"generated: seed={seed}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

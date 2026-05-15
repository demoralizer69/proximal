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

TOPICS = [
    "medieval cooking",
    "deep-sea biology",
    "vintage synthesizers",
    "space exploration",
    "urban beekeeping",
    "minimalist architecture",
    "competitive speedcubing",
    "tea ceremonies",
    "abandoned subway stations",
    "indie game development",
    "paper marbling",
    "Antarctic research stations",
    "Japanese stationery",
    "fermented foods",
    "amateur astronomy",
    "bouldering routes",
    "typography history",
    "lighthouse keeping",
    "vintage Formula 1",
    "mushroom foraging",
    "modular synthesizers",
    "desert gardening",
    "ancient cartography",
    "competitive birdwatching",
    "lost programming languages",
]

FONT_FAMILIES = [
    '"Inter", system-ui, sans-serif',
    '"Helvetica Neue", Arial, sans-serif',
    '"Georgia", "Times New Roman", serif',
    '"Playfair Display", Georgia, serif',
    '"JetBrains Mono", "Fira Code", monospace',
    '"IBM Plex Mono", "Courier New", monospace',
    '"Space Grotesk", "Inter", sans-serif',
    '"Cormorant Garamond", Georgia, serif',
    '"DM Sans", system-ui, sans-serif',
    '"Bebas Neue", Impact, sans-serif',
]

LAYOUTS = [
    "single-column",
    "hero + 3-card grid",
    "sidebar-left",
    "sidebar-right",
    "magazine",
    "dashboard",
    "two-column split",
    "masonry",
    "centered-narrow",
    "full-bleed hero",
]

BACKGROUND_TONES = ["light", "dark"]

TEMPERATURE_KEYS = (
    "colorfulness",
    "content_density",
    "button_density",
    "image_density",
    "icon_density",
    "corner_roundness",
    "translucency",
    "shadow_intensity",
    "border_prominence",
    "whitespace",
    "typography_contrast",
    "gradient_usage",
    "saturation",
    "visual_hierarchy",
    "animation_hint",
    "skeuomorphism",
    "noise_texture",
    "card_density",
)


def random_hex_color(rng: random.Random) -> str:
    return "#{:06x}".format(rng.randint(0, 0xFFFFFF))


def random_temperature(rng: random.Random) -> float:
    return round(rng.random(), 2)


def build_spec(seed: int) -> dict:
    rng = random.Random(seed)
    return {
        "topic": rng.choice(TOPICS),
        "fixed": {
            "primary_color": random_hex_color(rng),
            "secondary_color": random_hex_color(rng),
            "accent_color": random_hex_color(rng),
            "background_tone": rng.choice(BACKGROUND_TONES),
            "font_family": rng.choice(FONT_FAMILIES),
            "layout": rng.choice(LAYOUTS),
            "language": "en",
        },
        "temperature": {key: random_temperature(rng) for key in TEMPERATURE_KEYS},
        "seed": seed,
    }


def main() -> int:
    seed = int.from_bytes(secrets.token_bytes(8), "big")
    spec = build_spec(seed)

    Path("/app").mkdir(parents=True, exist_ok=True)
    out = Path("/app/website_details.json")
    out.write_text(json.dumps(spec, indent=2) + "\n")
    print(f"generated: seed={seed}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

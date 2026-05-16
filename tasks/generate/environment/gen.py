"""GENERATOR — procedurally produce a random multi-page website spec.

Contract (do not break without also updating the agent's instruction.md):
    Input:  none
    Output: writes /app/website_details.json

This file is the iteration point for changing what kind of webpages the
pipeline generates. Everything downstream (the agent's HTML, the
Playwright screenshots, etc.) flows from whatever this script writes.
"""
from __future__ import annotations

import json
import random
import re
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
    "artisanal coffee roasting",
    "thrift store fashion",
    "retro arcade games",
    "wildlife photography",
    "sustainable surfing",
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

# Website types and the pool of plausible page slugs for each.
# `home` is always included as the first page.
TYPE_PAGES: dict[str, list[str]] = {
    "ecommerce": [
        "shop",
        "product",
        "category",
        "cart",
        "checkout",
        "account",
        "orders",
        "wishlist",
        "deals",
        "about",
        "contact",
        "faq",
        "shipping",
    ],
    "social_media": [
        "feed",
        "profile",
        "explore",
        "notifications",
        "messages",
        "search",
        "settings",
        "trending",
        "groups",
        "events",
        "saved",
        "login",
    ],
    "utility": [
        "dashboard",
        "tools",
        "history",
        "settings",
        "profile",
        "billing",
        "integrations",
        "api",
        "docs",
        "support",
        "login",
        "signup",
    ],
    "informational": [
        "about",
        "services",
        "team",
        "contact",
        "faq",
        "resources",
        "pricing",
        "testimonials",
        "case-studies",
        "careers",
        "press",
    ],
    "portfolio": [
        "projects",
        "project-detail",
        "about",
        "resume",
        "contact",
        "blog",
        "post",
        "gallery",
        "services",
        "testimonials",
    ],
    "news": [
        "latest",
        "article",
        "category",
        "author",
        "archive",
        "opinion",
        "video",
        "newsletter",
        "about",
        "contact",
    ],
    "blog": [
        "post",
        "archive",
        "tag",
        "category",
        "about",
        "contact",
        "subscribe",
        "search",
        "author",
    ],
    "saas": [
        "features",
        "pricing",
        "docs",
        "blog",
        "login",
        "signup",
        "dashboard",
        "integrations",
        "changelog",
        "contact",
    ],
    "educational": [
        "courses",
        "course-detail",
        "instructors",
        "schedule",
        "enroll",
        "about",
        "contact",
        "resources",
        "faq",
        "blog",
    ],
}

TYPES = tuple(TYPE_PAGES.keys())

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
    "gradients",   # 0 = no gradient backgrounds, 1 = many distinct gradients across the page
    "genz_ness",   # 0 = neutral / corporate tone, 1 = maximalist Gen-Z styling and copy
)

PAGE_MIN = 5
PAGE_MAX = 7


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "page"


def random_hex_color(rng: random.Random) -> str:
    return "#{:06x}".format(rng.randint(0, 0xFFFFFF))


def random_temperature(rng: random.Random) -> float:
    return round(rng.random(), 2)


def random_pages(rng: random.Random, site_type: str) -> list[str]:
    pool = list(TYPE_PAGES[site_type])
    rng.shuffle(pool)
    n = rng.randint(PAGE_MIN, PAGE_MAX)
    # Always include home as the first page.
    rest = pool[: max(0, n - 1)]
    pages = ["home", *rest]
    # Deduplicate while preserving order, in case home slug collided.
    seen: set[str] = set()
    unique = []
    for raw in pages:
        slug = _slugify(raw)
        if slug in seen:
            continue
        seen.add(slug)
        unique.append(slug)
    return unique[:PAGE_MAX]


def build_spec(seed: int) -> dict:
    rng = random.Random(seed)
    site_type = rng.choice(TYPES)
    pages = random_pages(rng, site_type)
    return {
        "topic": rng.choice(TOPICS),
        "fixed": {
            "type": site_type,
            "primary_color": random_hex_color(rng),
            "secondary_color": random_hex_color(rng),
            "accent_color": random_hex_color(rng),
            "background_tone": rng.choice(BACKGROUND_TONES),
            "font_family": rng.choice(FONT_FAMILIES),
            "layout": rng.choice(LAYOUTS),
            "language": "en",
            "pages": pages,
        },
        "temperature": {key: random_temperature(rng) for key in TEMPERATURE_KEYS},
        "seed": seed,
    }


def main() -> int:
    seed = int.from_bytes(secrets.token_bytes(8), "big")
    spec = build_spec(seed)

    Path("/app").mkdir(parents=True, exist_ok=True)
    Path("/app/pages").mkdir(parents=True, exist_ok=True)
    out = Path("/app/website_details.json")
    out.write_text(json.dumps(spec, indent=2) + "\n")
    print(
        f"generated: seed={seed} type={spec['fixed']['type']} pages={len(spec['fixed']['pages'])}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

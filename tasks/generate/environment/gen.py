"""GENERATOR — procedurally produce a random multi-page website spec.

Contract (do not break without also updating the agent's instruction.md):
    Input:  none
    Output: writes /app/website_details.json

Diversity strategy:
  - Each spec biases toward its type via topic / page / font / layout /
    era / dial pools, but `CROSS_POLLINATE_PROB` lets categoricals
    occasionally jump outside the type-native pool, and `PRIOR_BLEND`
    pulls dial priors toward 0.5 so two same-type specs don't end up
    near-identical. Loosen both to push variety further; tighten them
    if specs start looking incoherent.
  - Palette is sampled as one of several HSL color schemes (analogous,
    triadic, mono, split-complement, random) so the dominant-tone
    relationship varies across specs.
  - Dials are sampled from Beta(p, 1-p) (U-shaped), so each spec still
    commits to an aesthetic instead of averaging to 0.5.
"""
from __future__ import annotations

import colorsys
import json
import random
import re
import secrets
import sys
from pathlib import Path

# -----------------------------------------------------------------------------
# Site types and their plausible pages
# -----------------------------------------------------------------------------

TYPE_PAGES: dict[str, list[str]] = {
    "ecommerce": [
        "shop", "product", "category", "cart", "checkout", "account",
        "orders", "wishlist", "deals", "about", "contact", "faq", "shipping",
    ],
    "social_media": [
        "feed", "profile", "explore", "notifications", "messages", "search",
        "settings", "trending", "groups", "events", "saved", "login",
    ],
    "utility": [
        "dashboard", "tools", "history", "settings", "profile", "billing",
        "integrations", "api", "docs", "support", "login", "signup",
    ],
    "informational": [
        "about", "services", "team", "contact", "faq", "resources", "pricing",
        "testimonials", "case-studies", "careers", "press",
    ],
    "portfolio": [
        "projects", "project-detail", "about", "resume", "contact", "blog",
        "post", "gallery", "services", "testimonials",
    ],
    "news": [
        "latest", "article", "category", "author", "archive", "opinion",
        "video", "newsletter", "about", "contact",
    ],
    "blog": [
        "post", "archive", "tag", "category", "about", "contact",
        "subscribe", "search", "author",
    ],
    "saas": [
        "features", "pricing", "docs", "blog", "login", "signup",
        "dashboard", "integrations", "changelog", "contact",
    ],
    "educational": [
        "courses", "course-detail", "instructors", "schedule", "enroll",
        "about", "contact", "resources", "faq", "blog",
    ],
}

TYPES = tuple(TYPE_PAGES.keys())

# Per-type topic pools — chosen to feel like real businesses/products, not
# whimsical "lorem ipsum" hobbies.
TYPE_TOPICS: dict[str, list[str]] = {
    "ecommerce": [
        "single-origin coffee subscription",
        "merino wool socks",
        "natural deodorant",
        "kitchen knives for home cooks",
        "pet beds for senior dogs",
        "trail running shoes",
        "ceremonial-grade matcha",
        "men's skincare basics",
        "ceramic dinnerware",
        "camping cookware",
        "sustainable activewear",
        "houseplants delivered monthly",
        "natural wine club",
        "small-batch hot sauce",
        "wireless earbuds",
        "leather wallets",
        "vintage motorcycle parts",
        "refurbished mechanical keyboards",
        "kids' bookshop",
    ],
    "saas": [
        "expense tracking for freelancers",
        "team retrospective tool",
        "customer feedback collection",
        "API uptime monitoring",
        "newsletter publishing platform",
        "invoicing for solopreneurs",
        "online booking for hair salons",
        "inventory management for small retailers",
        "applicant tracking system",
        "managed vector database",
        "feature flag service",
        "customer support helpdesk",
        "podcast hosting and analytics",
        "no-code form builder",
        "AI meeting notes",
        "headless CMS",
    ],
    "social_media": [
        "anonymous campus confessions",
        "amateur film critics network",
        "running club community",
        "homebrewing forum",
        "expat support network",
        "language exchange community",
        "indie game devs hub",
        "minimalist living community",
        "urban gardeners marketplace",
        "tabletop RPG group finder",
        "amateur radio operators",
    ],
    "utility": [
        "tax filing assistant",
        "expense splitting between roommates",
        "rent payment portal",
        "fitness habit tracker",
        "meal planning app",
        "calorie counter",
        "period tracker",
        "sleep tracker dashboard",
        "personal budgeting app",
        "DNS management console",
        "VPN provider control panel",
        "password manager",
    ],
    "informational": [
        "private dental practice",
        "boutique immigration law firm",
        "physical therapy clinic",
        "wedding venue in the Hudson Valley",
        "yoga studio in Brooklyn",
        "homeschool curriculum cooperative",
        "city council district office",
        "community public library",
        "naturopathic clinic",
        "neighborhood pediatric office",
        "small architecture firm",
    ],
    "portfolio": [
        "freelance UX designer",
        "indie illustrator",
        "studio architect",
        "freelance copywriter",
        "wedding photographer",
        "ceramicist studio",
        "two-person indie game studio",
        "type foundry",
        "branding studio",
        "documentary filmmaker",
        "motion designer",
    ],
    "news": [
        "local restaurant reviews",
        "AI industry news daily",
        "crypto markets briefing",
        "indie game journalism",
        "city politics beat",
        "tech worker labor news",
        "music industry trade publication",
        "amateur sports league coverage",
        "hyperlocal neighborhood paper",
    ],
    "blog": [
        "minimalist home cooking",
        "first-time homebuying",
        "raising twins",
        "career switch to software",
        "long-distance hiking journal",
        "freelance income reports",
        "amateur astronomy notes",
        "indie hacker journey",
        "parenting a toddler",
        "weekly book reviews",
        "running training log",
    ],
    "educational": [
        "online language tutoring",
        "remote coding bootcamp",
        "GED prep",
        "MCAT prep",
        "online watercolor classes",
        "yoga teacher training",
        "private music lessons",
        "kids' chess club",
        "private SAT tutoring",
        "early childhood music classes",
    ],
}

# -----------------------------------------------------------------------------
# Type-conditioned fonts, layouts, design eras
# -----------------------------------------------------------------------------

_SERIF = [
    '"Georgia", "Times New Roman", serif',
    '"Playfair Display", Georgia, serif',
    '"Cormorant Garamond", Georgia, serif',
]
_SANS = [
    '"Inter", system-ui, sans-serif',
    '"Helvetica Neue", Arial, sans-serif',
    '"DM Sans", system-ui, sans-serif',
    '"Space Grotesk", "Inter", sans-serif',
]
_MONO = [
    '"JetBrains Mono", "Fira Code", monospace',
    '"IBM Plex Mono", "Courier New", monospace',
]
_DISPLAY = [
    '"Bebas Neue", Impact, sans-serif',
    '"Playfair Display", Georgia, serif',
]

TYPE_FONTS: dict[str, list[str]] = {
    "ecommerce":     _SANS + _SERIF[:1],
    "saas":          _SANS,
    "social_media":  _SANS,
    "utility":       _SANS + _MONO,
    "informational": _SANS + _SERIF,
    "portfolio":     _SANS + _SERIF + _DISPLAY + _MONO,
    "news":          _SERIF + _SANS[:2],
    "blog":          _SERIF + _SANS[:2],
    "educational":   _SANS + _SERIF[:1],
}

TYPE_LAYOUTS: dict[str, list[str]] = {
    "ecommerce":     ["hero + 3-card grid", "masonry", "magazine", "full-bleed hero"],
    "saas":          ["hero + 3-card grid", "full-bleed hero", "dashboard", "centered-narrow"],
    "social_media":  ["single-column", "two-column split", "dashboard"],
    "utility":       ["dashboard", "sidebar-left", "sidebar-right"],
    "informational": ["centered-narrow", "magazine", "two-column split", "hero + 3-card grid"],
    "portfolio":     ["masonry", "magazine", "centered-narrow", "full-bleed hero"],
    "news":          ["magazine", "sidebar-right", "two-column split"],
    "blog":          ["centered-narrow", "sidebar-right", "magazine"],
    "educational":   ["hero + 3-card grid", "sidebar-left", "centered-narrow"],
}

BACKGROUND_TONES = ["light", "dark"]

DESIGN_ERAS = (
    "corporate-2010",     # rounded blue buttons, drop shadows, stock photos
    "material-2014",      # Google Material: bold flat colors, ripple, cards
    "flat-minimal",       # current SaaS default: lots of whitespace, neutral tones
    "brutalist",          # raw, system fonts, harsh borders, no-frills
    "neo-brutalist",      # 2022+ revival: hard shadows, vivid blocks, thick borders
    "glassmorphism",      # frosted translucent surfaces, blurred backdrops
    "y2k",                # chrome, gradients, sparkles, frutiger aero
    "swiss-editorial",    # grid-driven, serif headlines, generous margins
    "memphis",            # 80s postmodern: confetti shapes, primary colors, squiggles
    "vaporwave",          # pink/teal, classical busts, vintage Mac UI chrome
    "anti-design",        # intentionally clashing, low-craft, web1.0 default browser
    "magazine-print",     # heavy serif, big drop caps, columnar, print-inspired
)

TYPE_ERAS: dict[str, list[str]] = {
    "ecommerce":     ["flat-minimal", "swiss-editorial", "corporate-2010", "neo-brutalist", "material-2014", "magazine-print", "memphis"],
    "saas":          ["flat-minimal", "corporate-2010", "material-2014", "glassmorphism", "neo-brutalist"],
    "social_media":  ["material-2014", "glassmorphism", "y2k", "neo-brutalist", "vaporwave", "memphis"],
    "utility":       ["flat-minimal", "material-2014", "corporate-2010", "brutalist"],
    "informational": ["corporate-2010", "swiss-editorial", "flat-minimal", "magazine-print"],
    "portfolio":     ["swiss-editorial", "brutalist", "neo-brutalist", "flat-minimal", "y2k", "vaporwave", "anti-design", "memphis"],
    "news":          ["swiss-editorial", "corporate-2010", "flat-minimal", "magazine-print"],
    "blog":          ["swiss-editorial", "flat-minimal", "corporate-2010", "magazine-print", "anti-design"],
    "educational":   ["material-2014", "flat-minimal", "corporate-2010", "memphis"],
}

# -----------------------------------------------------------------------------
# Diversity knobs
# -----------------------------------------------------------------------------
# When picking font / layout / era, this is the probability that we ignore
# the type-native pool and draw from the full pool. Higher = more variety,
# more weird pairings. Lower = tighter type-aesthetic coherence.
CROSS_POLLINATE_PROB = 0.3

# Weight applied to the type-conditioned dial prior. The rest goes to the
# neutral midpoint 0.5. Lower = priors barely matter (closer to uniform-
# bimodal across all types); higher = type drives the dials hard.
PRIOR_BLEND = 0.4

# -----------------------------------------------------------------------------
# Temperature dials
# -----------------------------------------------------------------------------

# Redundant pairs collapsed from the previous schema:
#   - `saturation` merged into `colorfulness`
#   - `gradient_usage` merged into `gradients`
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
    "visual_hierarchy",
    "animation_hint",
    "skeuomorphism",
    "noise_texture",
    "card_density",
    "gradients",
    "genz_ness",
)

# Per-type prior means for each dial. Missing keys default to 0.5.
# Tune these so each type's "feel" reads as real (calm for SaaS/news, loud
# for social/y2k territory, etc.).
TYPE_DIAL_PRIORS: dict[str, dict[str, float]] = {
    "ecommerce": {
        "colorfulness": 0.55, "content_density": 0.45, "button_density": 0.65,
        "image_density": 0.75, "icon_density": 0.5, "corner_roundness": 0.55,
        "translucency": 0.25, "shadow_intensity": 0.4, "border_prominence": 0.3,
        "whitespace": 0.55, "typography_contrast": 0.6, "visual_hierarchy": 0.7,
        "animation_hint": 0.35, "skeuomorphism": 0.25, "noise_texture": 0.2,
        "card_density": 0.7, "gradients": 0.25, "genz_ness": 0.3,
    },
    "saas": {
        "colorfulness": 0.4, "content_density": 0.45, "button_density": 0.5,
        "image_density": 0.4, "icon_density": 0.55, "corner_roundness": 0.6,
        "translucency": 0.35, "shadow_intensity": 0.35, "border_prominence": 0.25,
        "whitespace": 0.75, "typography_contrast": 0.65, "visual_hierarchy": 0.7,
        "animation_hint": 0.4, "skeuomorphism": 0.1, "noise_texture": 0.15,
        "card_density": 0.55, "gradients": 0.3, "genz_ness": 0.15,
    },
    "social_media": {
        "colorfulness": 0.7, "content_density": 0.55, "button_density": 0.55,
        "image_density": 0.7, "icon_density": 0.75, "corner_roundness": 0.75,
        "translucency": 0.5, "shadow_intensity": 0.45, "border_prominence": 0.2,
        "whitespace": 0.4, "typography_contrast": 0.5, "visual_hierarchy": 0.55,
        "animation_hint": 0.65, "skeuomorphism": 0.2, "noise_texture": 0.2,
        "card_density": 0.65, "gradients": 0.5, "genz_ness": 0.7,
    },
    "utility": {
        "colorfulness": 0.3, "content_density": 0.6, "button_density": 0.6,
        "image_density": 0.25, "icon_density": 0.65, "corner_roundness": 0.4,
        "translucency": 0.25, "shadow_intensity": 0.3, "border_prominence": 0.45,
        "whitespace": 0.55, "typography_contrast": 0.55, "visual_hierarchy": 0.6,
        "animation_hint": 0.2, "skeuomorphism": 0.1, "noise_texture": 0.1,
        "card_density": 0.6, "gradients": 0.15, "genz_ness": 0.1,
    },
    "informational": {
        "colorfulness": 0.35, "content_density": 0.55, "button_density": 0.35,
        "image_density": 0.45, "icon_density": 0.4, "corner_roundness": 0.4,
        "translucency": 0.2, "shadow_intensity": 0.3, "border_prominence": 0.35,
        "whitespace": 0.65, "typography_contrast": 0.65, "visual_hierarchy": 0.65,
        "animation_hint": 0.2, "skeuomorphism": 0.15, "noise_texture": 0.15,
        "card_density": 0.4, "gradients": 0.15, "genz_ness": 0.1,
    },
    "portfolio": {
        "colorfulness": 0.45, "content_density": 0.3, "button_density": 0.25,
        "image_density": 0.75, "icon_density": 0.3, "corner_roundness": 0.4,
        "translucency": 0.3, "shadow_intensity": 0.35, "border_prominence": 0.4,
        "whitespace": 0.8, "typography_contrast": 0.8, "visual_hierarchy": 0.8,
        "animation_hint": 0.5, "skeuomorphism": 0.2, "noise_texture": 0.3,
        "card_density": 0.4, "gradients": 0.25, "genz_ness": 0.3,
    },
    "news": {
        "colorfulness": 0.4, "content_density": 0.75, "button_density": 0.35,
        "image_density": 0.65, "icon_density": 0.4, "corner_roundness": 0.25,
        "translucency": 0.15, "shadow_intensity": 0.2, "border_prominence": 0.5,
        "whitespace": 0.4, "typography_contrast": 0.75, "visual_hierarchy": 0.7,
        "animation_hint": 0.15, "skeuomorphism": 0.1, "noise_texture": 0.1,
        "card_density": 0.5, "gradients": 0.1, "genz_ness": 0.1,
    },
    "blog": {
        "colorfulness": 0.3, "content_density": 0.6, "button_density": 0.3,
        "image_density": 0.4, "icon_density": 0.25, "corner_roundness": 0.35,
        "translucency": 0.15, "shadow_intensity": 0.25, "border_prominence": 0.3,
        "whitespace": 0.7, "typography_contrast": 0.7, "visual_hierarchy": 0.65,
        "animation_hint": 0.15, "skeuomorphism": 0.1, "noise_texture": 0.15,
        "card_density": 0.3, "gradients": 0.15, "genz_ness": 0.2,
    },
    "educational": {
        "colorfulness": 0.55, "content_density": 0.5, "button_density": 0.55,
        "image_density": 0.55, "icon_density": 0.6, "corner_roundness": 0.65,
        "translucency": 0.25, "shadow_intensity": 0.35, "border_prominence": 0.3,
        "whitespace": 0.55, "typography_contrast": 0.6, "visual_hierarchy": 0.6,
        "animation_hint": 0.3, "skeuomorphism": 0.15, "noise_texture": 0.15,
        "card_density": 0.55, "gradients": 0.25, "genz_ness": 0.3,
    },
}

PAGE_MIN = 5
PAGE_MAX = 7


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "page"


def _hsl_to_hex(h: float, s: float, l: float) -> str:
    """h, s, l all in [0, 1] -> '#rrggbb'."""
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return "#{:02x}{:02x}{:02x}".format(
        int(round(r * 255)), int(round(g * 255)), int(round(b * 255))
    )


PALETTE_SCHEMES = (
    "analogous-complement",  # primary, near-analogous secondary, complementary accent
    "triadic",               # three hues evenly spaced around the wheel
    "monochromatic",         # one hue, three lightness/saturation steps
    "split-complement",      # primary + two hues flanking its complement
    "random",                # fully unrelated hues (clashy, "anti-design"-y)
)
PALETTE_WEIGHTS = (0.35, 0.2, 0.15, 0.2, 0.1)


def random_palette(rng: random.Random, background_tone: str) -> tuple[str, str, str]:
    """Sample a coordinated 3-color palette as (primary, secondary, accent).

    The hue relationship is picked from one of several schemes so the
    palette character varies across specs (analogous, triadic, mono, etc.).
    Saturation/lightness ranges are still keyed to the background tone so
    primary text/CTA contrast against the background stays usable.
    """
    base_h = rng.random()
    scheme = rng.choices(PALETTE_SCHEMES, weights=PALETTE_WEIGHTS, k=1)[0]

    if background_tone == "dark":
        prim_s, prim_l = rng.uniform(0.55, 0.8), rng.uniform(0.5, 0.65)
        sec_s_r, sec_l_r = (0.35, 0.6), (0.4, 0.55)
        acc_s_r, acc_l_r = (0.7, 0.9), (0.55, 0.7)
    else:
        prim_s, prim_l = rng.uniform(0.5, 0.75), rng.uniform(0.35, 0.5)
        sec_s_r, sec_l_r = (0.3, 0.55), (0.55, 0.75)
        acc_s_r, acc_l_r = (0.7, 0.95), (0.45, 0.6)

    if scheme == "analogous-complement":
        sec_h = (base_h + rng.choice([-1, 1]) * rng.uniform(0.05, 0.1)) % 1.0
        acc_h = (base_h + 0.5) % 1.0
    elif scheme == "triadic":
        sec_h = (base_h + 1 / 3) % 1.0
        acc_h = (base_h + 2 / 3) % 1.0
    elif scheme == "monochromatic":
        sec_h = base_h
        acc_h = base_h
        # Override secondary saturation downward for differentiation.
        sec_s_r = (0.15, 0.35)
    elif scheme == "split-complement":
        sec_h = (base_h + 0.5 - 1 / 12) % 1.0
        acc_h = (base_h + 0.5 + 1 / 12) % 1.0
    else:  # "random" — intentionally unrelated
        sec_h = rng.random()
        acc_h = rng.random()

    primary = (base_h, prim_s, prim_l)
    secondary = (sec_h, rng.uniform(*sec_s_r), rng.uniform(*sec_l_r))
    accent = (acc_h, rng.uniform(*acc_s_r), rng.uniform(*acc_l_r))
    return _hsl_to_hex(*primary), _hsl_to_hex(*secondary), _hsl_to_hex(*accent)


def _pick_with_crosspol(rng: random.Random, type_pool: list[str], full_pool: list[str]) -> str:
    """Pick from `type_pool` most of the time, but draw from the full pool
    with probability CROSS_POLLINATE_PROB to seed cross-type variety.
    """
    if rng.random() < CROSS_POLLINATE_PROB:
        return rng.choice(full_pool)
    return rng.choice(type_pool)


def _sample_bimodal_beta(rng: random.Random, mean: float) -> float:
    """Sample Beta(p, 1-p) with the prior clamped into (0.05, 0.95).

    Both shape params are < 1, so the density is U-shaped: most samples
    land near 0 or 1, with the heavier side decided by the prior mean.
    This produces designs that commit to an aesthetic instead of always
    averaging to 0.5.
    """
    m = max(0.05, min(0.95, mean))
    return round(rng.betavariate(m, 1.0 - m), 2)


def _effective_prior(type_prior: float) -> float:
    """Pull the type-conditioned prior toward 0.5 so same-type specs don't
    cluster too tightly. `PRIOR_BLEND` controls how much of the type bias
    survives.
    """
    return PRIOR_BLEND * type_prior + (1.0 - PRIOR_BLEND) * 0.5


def random_temperatures(rng: random.Random, site_type: str) -> dict[str, float]:
    priors = TYPE_DIAL_PRIORS.get(site_type, {})
    return {
        key: _sample_bimodal_beta(rng, _effective_prior(priors.get(key, 0.5)))
        for key in TEMPERATURE_KEYS
    }


def random_pages(rng: random.Random, site_type: str) -> list[str]:
    pool = list(TYPE_PAGES[site_type])
    rng.shuffle(pool)
    n = rng.randint(PAGE_MIN, PAGE_MAX)
    rest = pool[: max(0, n - 1)]
    seen: set[str] = set()
    unique: list[str] = []
    for raw in ["home", *rest]:
        slug = _slugify(raw)
        if slug in seen:
            continue
        seen.add(slug)
        unique.append(slug)
    return unique[:PAGE_MAX]


_BRAND_STEMS = [
    "North", "Quiet", "Bright", "Slow", "Open", "Plain", "Salt", "Cedar",
    "Iron", "Ember", "Field", "Loop", "Atlas", "Mason", "Drift", "Wild",
    "Common", "Forge", "Tide", "Owl", "Anvil", "Birch", "Harbor", "Linden",
    "Junco", "Marlow", "Pine", "Roam",
]
_BRAND_SUFFIXES = [
    "Co", "Studio", "Labs", "Works", "Club", "House", "& Co", "HQ",
    "Group", ".io", ".app", "Hub", "Box", "Press", "Collective",
]
_TAGLINE_TEMPLATES = [
    "{topic_cap}, done right.",
    "Built for {topic}.",
    "The home of {topic}.",
    "{topic_cap} for everyone.",
    "Better {topic}.",
    "Where {topic} lives.",
    "Your {topic} HQ.",
    "Modern {topic}.",
    "{topic_cap}, simplified.",
    "Made for {topic}.",
]


def random_brand(rng: random.Random, topic: str) -> tuple[str, str]:
    stem = rng.choice(_BRAND_STEMS)
    suffix = rng.choice(_BRAND_SUFFIXES)
    if suffix.startswith("."):
        name = f"{stem}{suffix}"
    else:
        name = f"{stem} {suffix}"
    template = rng.choice(_TAGLINE_TEMPLATES)
    tagline = template.format(topic=topic, topic_cap=topic[:1].upper() + topic[1:])
    return name, tagline


# -----------------------------------------------------------------------------
# Spec assembly
# -----------------------------------------------------------------------------

_ALL_FONTS = sorted({f for pool in TYPE_FONTS.values() for f in pool})
_ALL_LAYOUTS = sorted({l for pool in TYPE_LAYOUTS.values() for l in pool})
_ALL_ERAS = list(DESIGN_ERAS)


def build_spec(seed: int) -> dict:
    rng = random.Random(seed)
    site_type = rng.choice(TYPES)
    topic = rng.choice(TYPE_TOPICS[site_type])
    pages = random_pages(rng, site_type)
    background_tone = rng.choice(BACKGROUND_TONES)
    primary, secondary, accent = random_palette(rng, background_tone)
    font_family = _pick_with_crosspol(rng, TYPE_FONTS[site_type], _ALL_FONTS)
    layout = _pick_with_crosspol(rng, TYPE_LAYOUTS[site_type], _ALL_LAYOUTS)
    design_era = _pick_with_crosspol(rng, TYPE_ERAS.get(site_type, _ALL_ERAS), _ALL_ERAS)
    brand_name, tagline = random_brand(rng, topic)
    temperatures = random_temperatures(rng, site_type)

    return {
        "topic": topic,
        "fixed": {
            "type": site_type,
            "brand_name": brand_name,
            "tagline": tagline,
            "design_era": design_era,
            "primary_color": primary,
            "secondary_color": secondary,
            "accent_color": accent,
            "background_tone": background_tone,
            "font_family": font_family,
            "layout": layout,
            "language": "en",
            "pages": pages,
        },
        "temperature": temperatures,
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
        f"generated: seed={seed} type={spec['fixed']['type']} "
        f"brand={spec['fixed']['brand_name']!r} era={spec['fixed']['design_era']} "
        f"pages={len(spec['fixed']['pages'])}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

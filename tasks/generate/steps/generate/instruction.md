Read the website specification at `/app/website_details.json`. Generate a complete **multi-page** website — one HTML file per slug listed in `fixed.pages` — and write each one to `/app/pages/<slug>.html`.

Requirements:
- Output one self-contained HTML file per page at `/app/pages/<slug>.html`, where `<slug>` is each value from `fixed.pages` exactly as given. Do not create any other files.
- The first page slug is always `home`; treat it as the landing page.
- Every page must include a shared navigation that links to all of the other slugs as relative links (e.g. `<a href="about.html">About</a>`). Use the slug as both the link target and the visible label (you may title-case the label).
- Inline all CSS in a `<style>` tag in each page — no external stylesheets, no shared CSS files.
- Do not link to or download external images, fonts, or scripts. Use system fonts (the spec's `font_family` is a CSS stack — use it as-is and rely on its fallbacks) and CSS-only visuals.
- Honor every field in `/app/website_details.json`: type, colors, font, layout, language, page slugs, and let the `temperature` dials bias the visual character.
- Keep each page under **15 KB**. The whole site should feel like one coherent product — reuse the same header / nav / footer styling across pages, only varying the main content per slug.
- Keep the entire website under 50KB
- Don't over-deliberate on the dials — make quick proportional judgments and write the HTML.

## Spec schema

```json
{
  "topic": "...",
  "fixed": {
    "type":             "ecommerce | social_media | utility | informational | portfolio | news | blog | saas | educational",
    "primary_color":    "#rrggbb",
    "secondary_color":  "#rrggbb",
    "accent_color":     "#rrggbb",
    "background_tone":  "light | dark",
    "font_family":      "CSS font stack",
    "layout":           "layout name",
    "language":         "en",
    "pages":            ["home", "<slug>", ...]
  },
  "temperature": { "<key>": 0.00 .. 1.00, ... }
}
```

### `topic`
The site's subject (e.g. `"vintage synthesizers"`). Invent plausible copy — headings, body text, product / article / project names — about this topic and shape it to match the site type.

### `fixed`
Concrete categorical choices. Use each value as-is, no interpolation.

| Field | Use |
|---|---|
| `type` | Overall site genre (`ecommerce`, `social_media`, `utility`, `informational`, `portfolio`, `news`, `blog`, `saas`, `educational`). Shape the page content and components to match. |
| `primary_color` | Main brand color. |
| `secondary_color` | Companion to the primary; surfaces or secondary accents. |
| `accent_color` | Highlight color for CTAs, tags, links. |
| `background_tone` | `"light"` or `"dark"` — overall page lightness. |
| `font_family` | CSS font-family stack for body text. |
| `layout` | Named layout pattern (e.g. `"hero + 3-card grid"`, `"sidebar-left"`, `"magazine"`). Structure the home page accordingly; other pages may adapt as appropriate. |
| `language` | BCP-47 string for `<html lang>`. |
| `pages` | Ordered list of page slugs. The first slug is always `home`. Produce **exactly** one HTML file per slug. |

### `temperature`
Each value is a float in `[0, 1]`. **0 means "none / minimal / off"; 1 means "lots / maximal / on"**. Intermediate values bias proportionally — these are dials, not enums. Interpret them as design pressure, not boolean switches.

| Key | 0 means | 1 means |
|---|---|---|
| `colorfulness` | near-monochrome | many distinct hues |
| `content_density` | very concise text | long, dense copy |
| `button_density` | almost no buttons | buttons everywhere |
| `image_density` | text-only | image-heavy (use CSS shapes/gradients in lieu of real images) |
| `icon_density` | no icons | icons next to most items (use unicode/CSS shapes) |
| `corner_roundness` | sharp 90° corners | fully rounded / pill shapes |
| `translucency` | fully opaque surfaces | heavy glass / frosted effects |
| `shadow_intensity` | flat, no shadows | deep, layered shadows |
| `border_prominence` | borderless | thick visible borders |
| `whitespace` | cramped | very spacious |
| `typography_contrast` | uniform sizes | dramatic size hierarchy |
| `gradient_usage` | solid fills only | gradients throughout |
| `saturation` | desaturated / muted | vivid / punchy colors |
| `visual_hierarchy` | flat importance | strong focal points |
| `animation_hint` | static feel | motion-friendly composition (no JS — just composition cues) |
| `skeuomorphism` | flat design | tactile / 3D / textured |
| `noise_texture` | clean flat surfaces | grainy / textured surfaces |
| `card_density` | few large cards (or none) | many small cards |
| `gradients` | no gradient backgrounds at all | many distinct gradient backgrounds across the page |
| `genz_ness` | neutral / corporate tone & styling | maximalist Gen-Z styling and copy (vivid color clashes, internet slang, emoji, playful headlines) |

The spec at `/app/website_details.json` is the source of truth. Do not invent additional pages beyond what is listed in `fixed.pages`.

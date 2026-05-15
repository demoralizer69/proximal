Read the website specification at `/app/website_details.json`. Generate a single self-contained HTML file at `/app/website.html` that implements the website described by that spec.

Requirements:
- Output a single file at `/app/website.html`. Do not create any other files.
- Inline all CSS in a `<style>` tag — no external stylesheets.
- Do not link to or download external images, fonts, or scripts. Use system fonts (the spec's `font_family` is a CSS stack — use it as-is and rely on its fallbacks) and CSS-only visuals.
- Honor every field in `/app/website_details.json`. Use the colors, font, layout, language, and topic as specified, and let the `temperature` dials bias the page's visual character.
- Keep the file under **30 KB**. Don't over-deliberate on the dials — make quick proportional judgments and write the HTML.

## Spec schema

```json
{
  "topic": "...",
  "fixed": {
    "primary_color":   "#rrggbb",
    "secondary_color": "#rrggbb",
    "accent_color":    "#rrggbb",
    "background_tone": "light | dark",
    "font_family":     "CSS font stack",
    "layout":          "layout name",
    "language":        "en"
  },
  "temperature": { "<key>": 0.00 .. 1.00, ... }
}
```

### `topic`
The page's subject (e.g. `"vintage synthesizers"`). Invent plausible copy — headings, body text, section titles — about this topic.

### `fixed`
Concrete categorical choices. Use each value as-is, no interpolation.

| Field | Use |
|---|---|
| `primary_color` | Main brand color. |
| `secondary_color` | Companion to the primary; surfaces or secondary accents. |
| `accent_color` | Highlight color for CTAs, tags, links. |
| `background_tone` | `"light"` or `"dark"` — overall page lightness. |
| `font_family` | CSS font-family stack for body text. |
| `layout` | Named layout pattern (e.g. `"hero + 3-card grid"`, `"sidebar-left"`, `"magazine"`). Structure the page accordingly. |
| `language` | BCP-47 string for `<html lang>`. |

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

The spec at `/app/website_details.json` is the source of truth.

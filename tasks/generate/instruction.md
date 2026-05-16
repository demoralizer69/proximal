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
    "type":                  "ecommerce | social_media | utility | informational | portfolio | news | blog | saas | educational",
    "brand_name":            "the site's brand / wordmark",
    "tagline":               "short marketing line",
    "design_era":            "corporate-2010 | material-2014 | flat-minimal | brutalist | neo-brutalist | glassmorphism | y2k | swiss-editorial | memphis | vaporwave | anti-design | magazine-print",
    "composition_archetype": "scrapbook | editorial-poster | window-frame | magazine-spread | single-canvas | timeline | split-aesthetic | manifesto | infinite-canvas | kiosk | null",
    "heading_treatment":     "plain | outline | oversized | rotated | split-color | marquee",
    "primary_color":         "#rrggbb",
    "secondary_color":       "#rrggbb",
    "accent_color":          "#rrggbb",
    "background_tone":       "light | dark",
    "font_family":           "CSS font stack",
    "layout":                "layout name | null",
    "language":              "en",
    "pages":                 ["home", "<slug>", ...]
  },
  "temperature": { "<key>": 0.00 .. 1.00, ... }
}
```

### `topic`
The site's subject (e.g. `"trail running shoes"`). Invent plausible copy — headings, body text, product / article / project names — about this topic and shape it to match the site type.

### `fixed`
Concrete categorical choices. Use each value as-is, no interpolation.

| Field | Use |
|---|---|
| `type` | Overall site genre (`ecommerce`, `social_media`, `utility`, `informational`, `portfolio`, `news`, `blog`, `saas`, `educational`). Shape the page content and components to match. |
| `brand_name` | The site's brand / wordmark. Use it in the header, footer, page titles, and copy. Don't invent a different name. |
| `tagline` | A short marketing line. Use it in the hero or header. |
| `design_era` | The era / movement to anchor the visual style to. Reference points: `corporate-2010` (rounded blue buttons, drop shadows), `material-2014` (Google Material: bold flat colors, cards), `flat-minimal` (lots of whitespace, neutral tones), `brutalist` (raw, system fonts, harsh borders), `neo-brutalist` (hard shadows, vivid blocks, thick borders), `glassmorphism` (frosted translucent surfaces, blurred backdrops), `y2k` (chrome, gradients, sparkles, frutiger aero), `swiss-editorial` (grid-driven, serif headlines, generous margins), `memphis` (80s postmodern: confetti shapes, primaries), `vaporwave` (pink/teal, classical busts, vintage Mac UI), `anti-design` (intentionally clashing, low-craft, web1.0 default browser), `magazine-print` (heavy serif, big drop caps, columnar). |
| `composition_archetype` | A high-level compositional mode that overrides default layout thinking. `scrapbook` (collage, taped photos, sticker overlays), `editorial-poster` (postmodern dramatic display type, layered text), `window-frame` (OS-window / desktop / terminal pastiche), `magazine-spread` (multi-column print-magazine), `single-canvas` (one huge focal element on near-empty page), `timeline` (timeline as the spine of the page), `split-aesthetic` (halves with different visual languages), `manifesto` (text-only declarative one-pager), `infinite-canvas` (implied side-scroll), `kiosk` (info-board feel). When `null`, no archetype is enforced — compose from `layout` and the dials. |
| `heading_treatment` | How display type should be handled. `plain` (ordinary filled), `outline` (stroke / outlined text as a primary visual), `oversized` (display sizes dominate the viewport), `rotated` (headings tilted off horizontal), `split-color` (words broken into multiple fill colors mid-letter / mid-word), `marquee` (horizontal-scrolling text bar implied by composition). |
| `primary_color` | Main brand color. |
| `secondary_color` | Companion to the primary; surfaces or secondary accents. |
| `accent_color` | Highlight color for CTAs, tags, links. |
| `background_tone` | `"light"` or `"dark"` — overall page lightness. |
| `font_family` | CSS font-family stack for body text. |
| `layout` | Named layout pattern (e.g. `"hero + 3-card grid"`, `"sidebar-left"`, `"magazine"`). Structure the home page accordingly; other pages may adapt as appropriate. **When `null`, you have full compositional freedom** — let the dials and `composition_archetype` drive the page composition instead of a named pattern. |
| `language` | BCP-47 string for `<html lang>`. |
| `pages` | Ordered list of page slugs. The first slug is always `home`. Produce **exactly** one HTML file per slug. |

### `temperature`
Each value is a float in `[0, 1]`. **0 means "none / minimal / off"; 1 means "lots / maximal / on"**. Intermediate values bias proportionally — these are dials, not enums. Interpret them as design pressure, not boolean switches.

| Key | 0 means | 1 means |
|---|---|---|
| `colorfulness` | near-monochrome, desaturated | many distinct vivid hues |
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
| `visual_hierarchy` | flat importance | strong focal points |
| `animation_hint` | static feel | motion-friendly composition (no JS — just composition cues) |
| `skeuomorphism` | flat design | tactile / 3D / textured |
| `noise_texture` | clean flat surfaces | grainy / textured surfaces |
| `card_density` | few large cards (or none) | many small cards |
| `gradients` | solid fills only, no gradients | gradients used heavily across surfaces |
| `genz_ness` | neutral / corporate tone & styling | maximalist Gen-Z styling and copy (vivid color clashes, internet slang, emoji, playful headlines) |
| `grid_break` | strict grid alignment everywhere | anti-grid / intentional misalignment, postmodern poster feel |
| `asymmetry` | symmetric, centered balance | heavily weighted to one side; off-center heroes |
| `container_escape` | content stays inside section / column bounds | images and text bleed past section borders and column edges |
| `overlap_density` | no overlapping elements | panels, cards, text, and images visually overlap |
| `element_rotation` | everything axis-aligned | items tilted off horizontal (text boxes, photos, badges at angles) |
| `shape_organic` | rectangles only | blob backgrounds, curved section dividers, irregular shapes |
| `shape_geometric_decoration` | no decorative shapes | floating triangles / circles / lines as page ornaments |
| `outline_typography` | solid filled type | oversized outline / stroke text used as a primary visual element |
| `mixed_typeface` | one typeface throughout | 3+ contrasting families mixed within one page (serif + mono + sans) |
| `bento_irregularity` | uniform grid cells | varied-size tile grid (Apple-style bento landing) |
| `marquee_kinetic` | static type | composition implies horizontal-scrolling text bars / looping headlines |
| `scale_contrast_extreme` | subtle size variation | huge display sizes adjacent to tiny captions (Swiss/editorial extremes) |
| `negative_space_focal` | balanced page | one dominant focal element surrounded by near-empty space |
| `section_divider_irregular` | straight horizontal section borders | wavy / diagonal / jagged section dividers |
| `depth_layering` | flat, no z-stacking | strong z-order with stacked shadow layers, parallax-style composition |

The spec at `/app/website_details.json` is the source of truth. Do not invent additional pages beyond what is listed in `fixed.pages`.

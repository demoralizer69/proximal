Look in `/app/captures/`. There is one directory per page of a multi-page **animated** website. Each `<slug>/` directory contains:

- `frame_00.png` ... `frame_05.png` — keyframes captured at t = 0.0 s, 0.5 s, 1.0 s, 1.5 s, 2.0 s, 2.5 s from first paint
- `clip.webm` — a continuous WebM recording of the same 3-second window

Reproduce the website as a set of self-contained HTML files at `/app/pages/<slug>.html` — one HTML file per slug, using the same slug as the directory.

Requirements:
- Output one file per slug at `/app/pages/<slug>.html`. Do not create any other files in `/app/pages/`.
- The page slugged `home` (if present) is the landing page.
- Inline all CSS in a `<style>` tag in each page — no external stylesheets, no shared CSS files.
- Do not link to or download external images, fonts, or scripts. **No JavaScript at all** — animations are CSS-only. Use system fonts and CSS-only visuals in place of bitmap images.
- Pay attention to sizes, proportions, rotations, z-indices of objects, clippings, content exceeding boxes, translucency, gradients, curvy lines, etc. — match all of that along with colors and text. The animations should also match.


The captures in `/app/captures/` are the source of truth. Do not run the verifier.

Look at the screenshots in `/app/screenshots/`. Each file is named `<slug>.png` and is a rendering of one page of a multi-page website. Reproduce the website as a set of self-contained HTML files at `/app/pages/<slug>.html` — one HTML file per screenshot, using the exact same slug.

Requirements:
- Output one file per screenshot at `/app/pages/<slug>.html`. Do not create any other files in `/app/pages/`.
- The page slugged `home` (if present) is the landing page. Other slugs are linked from a shared nav as relative links (e.g. `<a href="about.html">About</a>`).
- Inline all CSS in a `<style>` tag in each page — no external stylesheets, no shared CSS files.
- Do not link to or download external images, fonts, or scripts. Use system fonts and CSS-only visuals (gradients, shapes, borders) in place of bitmap images.
- Match layout, colors, text, typography, and proportions as closely as you can. Visual similarity (mean SSIM across pages) is the score.
- Reuse the same header / nav / footer styling across pages; only the main content should vary by slug.

Only the screenshots in `/app/screenshots/` are the source of truth. Do not run the verifier.

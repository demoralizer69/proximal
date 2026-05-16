Look at the screenshots in `/app/screenshots/`. Each file is named `<slug>.png` and is a rendering of one page of a multi-page website. Reproduce the website as a set of self-contained HTML files at `/app/pages/<slug>.html` — one HTML file per screenshot, using the exact same slug.

Requirements:
- Output one file per screenshot at `/app/pages/<slug>.html`. Do not create any other files in `/app/pages/`.
- The page slugged `home` (if present) is the landing page.
- Inline all CSS in a `<style>` tag in each page — no external stylesheets, no shared CSS files.
- Do not link to or download external images, fonts, or scripts. Use system fonts and CSS-only visuals (gradients, shapes, borders) in place of bitmap images.
- Try to make an exact clone from the screenshot - the final generated website should have the same content and it should look the same to human eyes.

Only the screenshots in `/app/screenshots/` are the source of truth. Do not run the verifier.

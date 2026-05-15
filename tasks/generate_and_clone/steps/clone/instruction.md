Look at the screenshot at `/app/webpage.png`. Reproduce that webpage as a single self-contained HTML file at `/app/clone.html`.

Requirements:
- Output a single file at `/app/clone.html`. Do not create any other files.
- Inline all CSS in a `<style>` tag — no external stylesheets.
- Do not link to or download external images, fonts, or scripts. Use system fonts and CSS-only visuals.
- Render target: 800x600 viewport, Chromium headless.
- Match layout, colors, text, and proportions as closely as you can. Visual similarity (SSIM) is the score.

Only the screenshot at `/app/webpage.png` is the source of truth. Do not run tests.

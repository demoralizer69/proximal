> DEPRECATED: superseded by `tasks/generate_and_clone/` (multi-step). This single-step task is kept for reference.

Read the website specification at `/app/website_details.json`. Generate a single self-contained HTML file at `/app/website.html` that implements the website described by that spec.

Requirements:
- Output a single file at `/app/website.html`. Do not create any other files.
- Inline all CSS in a `<style>` tag — no external stylesheets.
- Do not link to or download external images, fonts, or scripts. Use system fonts and CSS-only visuals.
- Honor every field in `/app/website_details.json` (brand, palette, headline, sections, etc.). Use the colors, copy, and structure exactly as specified.

The spec at `/app/website_details.json` is the source of truth.

Look in `/app/captures/`. There is one directory per page of a multi-page **animated** website. Each `<slug>/` directory contains:

- `frame_00.png` ... `frame_05.png` — six 1200x800 viewport keyframes captured at t = 0.0 s, 0.5 s, 1.0 s, 1.5 s, 2.0 s, 2.5 s from first paint
- `clip.webm` — a continuous WebM recording of the same 3-second window

Reproduce the website as a set of self-contained HTML files at `/app/pages/<slug>.html` — one HTML file per slug, using the same slug as the directory.

Requirements:
- Output one file per slug at `/app/pages/<slug>.html`. Do not create any other files in `/app/pages/`.
- The page slugged `home` (if present) is the landing page.
- Inline all CSS in a `<style>` tag in each page — no external stylesheets, no shared CSS files.
- Do not link to or download external images, fonts, or scripts. **No JavaScript at all** — animations are CSS-only. Use system fonts and CSS-only visuals in place of bitmap images.
- The target is a **1200 x 800** viewport (the verifier samples viewport-only, not full-page).
- Pay attention to sizes, proportions, rotations, z-indices of objects, clippings, content exceeding boxes, translucency, gradients, curvy lines, etc. — match all of that along with colors and text.

## Animation requirement (this task)

You will be scored on **two terms**:

1. **Per-frame similarity** — average WebSight composite (MS-SSIM + LPIPS + OCR F1) across the 6 keyframes.
2. **Motion similarity** — MS-SSIM between target frame-deltas and your frame-deltas. The metric asks: "did motion happen in similar regions of the page at similar times?"

So your CSS animations must auto-play on load and produce visible per-frame change inside the captured 3-second window:

- Use `@keyframes` + `animation:` and/or CSS `transition:` driven by initial-state styles. **No `<script>` tags, no event listeners, no interaction.**
- Animations must read inside the 1200 x 800 viewport — animate elements that are visible above the fold at t=0.
- Match the **timing and motion type** seen across the 6 keyframes, not just the final visual state. If frame_00 shows elements off-screen / faded out and frame_05 shows them landed, your CSS must do an `animation` (or `transition`) with the same approximate duration and easing.
- Match continuous loops: if the target spins / pulses / pans a gradient / scrolls a marquee through the 3-second window, your clone must too — at roughly the same period.
- Use `animation-delay` to stagger element intros so the frames show progression rather than everything snapping into place at t=0.

Useful CSS animation recipes:

```css
@keyframes prox-fade-up  { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: none; } }
@keyframes prox-fade-in  { from { opacity: 0; } to { opacity: 1; } }
@keyframes prox-spin     { to { transform: rotate(360deg); } }
@keyframes prox-pulse    { 0%,100% { transform: scale(1); } 50% { transform: scale(1.05); } }
@keyframes prox-marquee  { from { transform: translateX(0); } to { transform: translateX(-50%); } }
@keyframes prox-grad-pan { 0% { background-position: 0% 50%; } 100% { background-position: 100% 50%; } }
```

The captures in `/app/captures/` are the source of truth. Do not run the verifier.

#!/bin/bash
# Runs after step-1 agent finishes, before step-2 agent starts.
# 1. Render the step-1 HTML to the target screenshot via Playwright Chromium.
# 2. Delete the step-1 HTML and spec from /app so the clone-step agent
#    can only read the screenshot. (Both files were already captured as
#    step-1 artifacts by Harbor before this script runs.)
set -euo pipefail

if [ ! -s /app/website.html ]; then
  echo "step-clone setup: /app/website.html missing or empty" >&2
  exit 1
fi

python3 /opt/render.py /app/website.html /app/webpage.png

rm -f /app/website.html /app/website_details.json

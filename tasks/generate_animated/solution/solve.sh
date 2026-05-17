#!/bin/bash
# Minimal stub oracle for the animated generate task — emits one HTML per
# page in the spec with a single CSS @keyframes spin so the verifier
# captures something non-empty. Real evaluation uses the claude-code
# agent, not this stub.
set -e
mkdir -p /app/pages

python3 - <<'PY'
import json
from pathlib import Path

spec = json.loads(Path("/app/website_details.json").read_text())
pages = spec.get("fixed", {}).get("pages", ["home"])
for slug in pages:
    Path(f"/app/pages/{slug}.html").write_text(
        "<!doctype html><html lang=\"en\"><head><title>" + slug + "</title>"
        "<style>"
        "body{font-family:system-ui;margin:0;display:flex;align-items:center;"
        "justify-content:center;height:100vh;background:#111;color:#fff}"
        "@keyframes prox-spin{to{transform:rotate(360deg)}}"
        ".o{width:160px;height:160px;border-radius:50%;"
        "background:conic-gradient(#e95993,#3aa4ff,#e95993);"
        "animation:prox-spin 2s linear infinite}"
        "</style></head>"
        "<body><div class=\"o\"></div></body></html>"
    )
PY

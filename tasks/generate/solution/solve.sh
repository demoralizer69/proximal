#!/bin/bash
# Minimal stub oracle — emits one empty HTML per page listed in the spec
# so the verifier has something to render. Real evaluation uses the
# claude-code agent, not this stub.
set -e
mkdir -p /app/pages

python3 - <<'PY'
import json
from pathlib import Path

spec = json.loads(Path("/app/website_details.json").read_text())
pages = spec.get("fixed", {}).get("pages", ["home"])
for slug in pages:
    Path(f"/app/pages/{slug}.html").write_text(
        f"<!doctype html><html lang=\"en\"><head><title>{slug}</title></head>"
        f"<body><h1>{slug}</h1></body></html>"
    )
PY

#!/bin/bash
# Runs once per container start (per trial). Generates a fresh webpage.png
# under /app, then execs whatever command harbor passes (typically `sleep
# infinity`). Must be wired via Dockerfile ENTRYPOINT — harbor's compose
# override replaces CMD, but ENTRYPOINT is preserved.
set -e
python3 /opt/gen.py
exec "$@"

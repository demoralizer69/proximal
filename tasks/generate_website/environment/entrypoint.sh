#!/bin/bash
# Runs once per container start (per trial). Generates a fresh
# /app/website_details.json with randomized parameters, then execs whatever
# command harbor passes (typically `sleep infinity`).
set -e
python3 /opt/gen.py
exec "$@"

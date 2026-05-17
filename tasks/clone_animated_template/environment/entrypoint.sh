#!/bin/bash
# Stage the target captures (one directory per page, each containing 6 keyframe
# PNGs + a clip.webm) into /app/captures/ so the agent can see them, and
# pre-create /app/pages/ as the output dir. /opt/target/ stays the read-only
# ground truth that the verifier compares against.
set -e

mkdir -p /app/captures /app/pages

if [ -d /opt/target ]; then
  # Copy each per-slug subdirectory verbatim (frame_NN.png + clip.webm).
  shopt -s nullglob
  for slug_dir in /opt/target/*/; do
    base="$(basename "$slug_dir")"
    mkdir -p "/app/captures/${base}"
    cp -R "${slug_dir}." "/app/captures/${base}/" 2>/dev/null || true
  done
  shopt -u nullglob
fi

exec "$@"

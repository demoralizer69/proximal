#!/bin/bash
# Stage the target screenshots into /app/screenshots/ so the agent can see them,
# and pre-create /app/pages/ as the output dir. /opt/target/ stays the
# read-only ground truth that the verifier compares against.
set -e

mkdir -p /app/screenshots /app/pages

if [ -d /opt/target ]; then
  cp /opt/target/*.png /app/screenshots/ 2>/dev/null || true
fi

exec "$@"

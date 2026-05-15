#!/bin/bash
set -e
python3 /opt/gen.py
exec "$@"

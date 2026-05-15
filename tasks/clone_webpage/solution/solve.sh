#!/bin/bash
# Oracle: copies the hidden reference HTML that the generator produced.
# Should score ~1.0 SSIM, modulo subpixel rendering noise.
set -e
cp /opt/reference/index.html /app/clone.html

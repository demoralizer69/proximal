#!/bin/bash
mkdir -p /logs/verifier
if [ ! -s /app/website.html ]; then
  echo "0.000000" > /logs/verifier/reward.txt
  echo "missing or empty /app/website.html" > /logs/verifier/verifier.log
  echo "reward=0.0000"
  exit 0
fi
echo "1.000000" > /logs/verifier/reward.txt
echo "website.html present" > /logs/verifier/verifier.log
echo "reward=1.0000"

#!/bin/bash
# No-op verifier: always awards full score.
mkdir -p /logs/verifier
echo "1.000000" > /logs/verifier/reward.txt
echo "no-op verifier: full score" > /logs/verifier/verifier.log
echo "reward=1.0000"

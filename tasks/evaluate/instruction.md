No agent action required. This task uses the `nop` agent — the verifier runs
`/opt/run_evaluators.py`, which scores every `<slug>.png` pair in `/opt/target`
vs `/opt/candidate` with all evaluators under `/opt/evaluators/` and writes
`/app/metrics.json`.

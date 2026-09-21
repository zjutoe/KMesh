RUN: pi-r1-probe2
Phase: dev probe
Date: 2026-09-20
Executor: Pi + `bonsai2-27b` (provider `bonsai`, reasoning `xhigh`)
Branch: T0011-clause-key
Command: .venv/bin/python -c (import + canonical_key anchor probe)
Exit code: 0
Elapsed: 0.046 s
Started: 2026-09-20T16:49:39.797397+00:00
Finished: 2026-09-20T16:49:39.858913+00:00
Recorded hashes: stdout_sha256=c6462a58750956775a75ca4dfe395b3ccc55ffc09119c0d2c509fbb7a8c3710b  stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855

Result summary: import OK; printed canonical key for a fact clause and a two-premise clause.

Conclusion: Import succeeded and hand-calculated anchor keys match the handoff spec.

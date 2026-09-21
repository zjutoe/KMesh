RUN: pi-r1-docs
Phase: docs
Date: 2026-09-20
Executor: Pi + `bonsai2-27b` (provider `bonsai`, reasoning `xhigh`)
Branch: T0011-clause-key
Command: .venv/bin/python reports/T0011/check_delivery.py docs
Exit code: 1
Elapsed: 0.104 s
Started: 2026-09-20T17:40:36.923575+00:00
Finished: 2026-09-20T17:40:37.044434+00:00
Recorded hashes: stdout_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  stderr_sha256=a638d100a9037bd6fa8d30515405b3bc5a790d8e2e93e1b7eb0ce268062c19ae

Result summary: (stderr) AssertionError: missing Pi provenance

Conclusion: First docs check failed (exit 1): no pi-*/provenance.md existed yet. Provenance written this round; re-run after.

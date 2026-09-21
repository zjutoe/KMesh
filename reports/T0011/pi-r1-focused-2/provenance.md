RUN: pi-r1-focused-2
Phase: focused
Date: 2026-09-20
Executor: Pi + `bonsai2-27b` (provider `bonsai`, reasoning `xhigh`)
Branch: T0011-clause-key
Command: .venv/bin/python -m pytest -q tests/test_clause_key.py --basetemp reports/T0011/pi-r1-focused-2/pytest-tmp
Exit code: 1
Elapsed: 0.442 s
Started: 2026-09-20T17:29:15.622023+00:00
Finished: 2026-09-20T17:29:16.082313+00:00
Recorded hashes: stdout_sha256=1c881b12c21997523301bdfd1c31f5fa0935ab8b76949b0a7ac174a9fa9c2b39  stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855

Result summary: 6 failed, 33 passed in 0.20s

Conclusion: Second focused run failed (exit 1): _independent_min used orderings=list(clause.body), mis-flattening a 1-tuple body.

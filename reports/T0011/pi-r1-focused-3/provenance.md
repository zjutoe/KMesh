RUN: pi-r1-focused-3
Phase: focused
Date: 2026-09-20
Executor: Pi + `bonsai2-27b` (provider `bonsai`, reasoning `xhigh`)
Branch: T0011-clause-key
Command: .venv/bin/python -m pytest -q tests/test_clause_key.py --basetemp reports/T0011/pi-r1-focused-3/pytest-tmp
Exit code: 0
Elapsed: 0.365 s
Started: 2026-09-20T17:29:50.194672+00:00
Finished: 2026-09-20T17:29:50.577860+00:00
Recorded hashes: stdout_sha256=ff3e3a0adf735ad9ff28af84012120def84aadb71d71d3476d532220cdad2771  stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855

Result summary: 39 passed in 0.13s

Conclusion: Focused check passed: all 39 new tests passed, no skip/xfail.

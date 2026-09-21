RUN: pi-r1-fix1
Phase: fix
Date: 2026-09-20
Executor: Pi + `bonsai2-27b` (provider `bonsai`, reasoning `xhigh`)
Branch: T0011-clause-key
Command: .venv/bin/python /tmp/t0011_fix.py
Exit code: 1
Elapsed: 0.045 s
Started: 2026-09-20T17:27:50.692931+00:00
Finished: 2026-09-20T17:27:50.755589+00:00
Recorded hashes: stdout_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  stderr_sha256=7fd8b2c58e349f2226bb89f5f674102d09dcef8e555d780857e37894080b11b5

Result summary: (stderr) AssertionError: 3

Conclusion: First fix script run failed: regex did not match K-names containing digits, fixed only 3/7 lines; file not written.

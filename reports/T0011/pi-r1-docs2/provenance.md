RUN: pi-r1-docs2
Phase: docs
Date: 2026-09-20
Executor: Pi + `bonsai2-27b` (provider `bonsai`, reasoning `xhigh`)
Branch: T0011-clause-key
Command: .venv/bin/python reports/T0011/check_delivery.py docs
Exit code: 0
Elapsed: 0.106 s
Started: 2026-09-20T17:44:02.306223+00:00
Finished: 2026-09-20T17:44:02.430191+00:00
Recorded hashes: stdout_sha256=42ae17080beaa2f3489cb9f2b765f23370345f21ea94874b30cd98f907ee8466  stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855

Result summary: PASS: scope, frozen inputs, 14 documents/62 local links, text hygiene, awaiting_review

Conclusion: docs check passed after writing provenance.md for the 11 prior runs; all documents end with newline, no trailing whitespace, 62 local links resolve, handoff status awaiting_review and implementation_status T0011 line contain the required markers.

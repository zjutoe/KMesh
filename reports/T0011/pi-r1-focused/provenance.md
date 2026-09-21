RUN: pi-r1-focused
Phase: focused
Date: 2026-09-20
Executor: Pi + `bonsai2-27b` (provider `bonsai`, reasoning `xhigh`)
Branch: T0011-clause-key
Command: .venv/bin/python -m pytest -q tests/test_clause_key.py --basetemp reports/T0011/pi-r1-focused/pytest-tmp
Exit code: 2
Elapsed: 0.38 s
Started: 2026-09-20T17:18:21.924537+00:00
Finished: 2026-09-20T17:18:22.321837+00:00
Recorded hashes: stdout_sha256=582aeaccc6433f224f8664d0e0d8661f7e48ec259c71eb12d21fc37b4aecc688  stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855

Result summary: ERROR collecting: kmesh.logic.types.LogicValidationError: clause.body must be a tuple of Atoms, got Atom

Conclusion: First focused run failed (exit 2): single-premise body missing trailing comma was not a tuple. Self-authored fixture bug.

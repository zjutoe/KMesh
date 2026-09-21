RUN: pi-r1-full
Phase: full
Date: 2026-09-20
Executor: Pi + `bonsai2-27b` (provider `bonsai`, reasoning `xhigh`)
Branch: T0011-clause-key
Command: .venv/bin/python -m pytest -q tests/test_clause_key.py tests/test_depth.py tests/test_proof_enumeration.py tests/test_derivations.py tests/test_dependency.py tests/test_proof.py tests/test_engine.py tests/test_reference_engine.py tests/test_logic_types.py tests/test_config.py tests/test_doctor.py --basetemp reports/T0011/pi-r1-full/pytest-tmp
Exit code: 0
Elapsed: 15.404 s
Started: 2026-09-20T17:29:57.127068+00:00
Finished: 2026-09-20T17:30:12.548873+00:00
Recorded hashes: stdout_sha256=a829a274ea6d86a126f059b90c1ff38d09ea6880f90cab224fc8f88b5574fd99  stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855

Result summary: 771 passed in 15.12s

Conclusion: Full 11-file regression passed: 771 items (732 existing + 39 new), no skip/xfail.

---
task: T0019-motif-candidate-audit
round: 1
submission_digest: 54dfab7fa666a880217c129dbdb5a403ca8fffa4c1069dff46eddc4447779dfe
verdict: needs_changes
author: Codex
---

All required checks passed: 32 focused tests and 1082 full tests. Independent validation confirmed all 80 witnesses, seven buckets, and 144 containment edges, including 64 proper edges. Submission hashes and allowed paths match. No product correctness defect was found, but contract-required regression tests have substantive gaps.

## T0019-R1 (P2) — tests/test_motif_candidates.py:706

The isolation test scans sys.modules only before the audit, installs no blocking finder, and performs no final scan. An independent probe inserted an engine import during the audit and this test still passed. Also, subprocesses rely on PYTHONPATH despite using -I, which ignores it; the required explicit source insertion and import-realpath assertion are absent from the audit and CLI children. These contradict step 5's isolation requirements.

Required change: Explicitly insert this worktree's src and assert the imported product realpath in each child. Install and self-test a finder blocking all four forbidden roots and dotted prefixes before product import, retain it throughout the complete audit, and scan sys.modules afterward.

Validation: Confirm the corrected test rejects a forbidden import during both module import and audit execution, then rerun all three required checks.

## T0019-R2 (P2) — tests/test_motif_candidates.py:669

The required determinism and side-effect checks are incomplete. Both pyc snapshots at lines 690–691 occur after both subprocesses, so their equality cannot detect bytecode created by those runs. The decoded CLI report is never compared with the function result, and equal repeated calls do not verify that mutating one returned report leaves subsequent reports unaffected. Step 5 explicitly requires these behaviors.

Required change: Take the initial bytecode snapshot before subprocess execution and the final snapshot afterward. Compare the complete decoded CLI report with a real function result. Add a nested-return mutation check followed by a fresh audit and comparison against an unmodified baseline.

Validation: Demonstrate that the assertions reject a changed bytecode inventory, divergent CLI/function reports, and shared mutable report state; rerun all three required checks.

## T0019-R3 (P2) — tests/test_motif_candidates.py:556

The exception helper initializes __context__ but never checks it, and the key/hit cases do not check __cause__. An independent mutation probe changed exception context while preserving the exception instance; all four tests passed. The depth sentinel is also generic RuntimeError rather than an exception supported by that dependency. This falls short of step 5's explicit exception-preservation test contract.

Required change: Use dependency-supported exception types, including a supported depth error. Capture message, cause, and context before each call and verify their preservation for all four bindings, using meaningful cause/context sentinels alongside the existing instance and stop assertions.

Validation: Confirm the tests reject same-instance propagation that alters cause or context, while accepting unchanged propagation; rerun all three required checks.

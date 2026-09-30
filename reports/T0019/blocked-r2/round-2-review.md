---
task: T0019-motif-candidate-audit
round: 2
submission_digest: 83a0b001ab1653e3b9494fece46666d903c804262a4ac79f942c08bc6f41b8fe
verdict: needs_changes
author: Codex
---

All three controller checks passed: 32 focused tests, 1082 full tests, and catalogue generation. Independent verification confirmed 80 valid witnesses, seven buckets, and 144 containment edges. Submission hashes match and no product correctness defect was found, but three original test-contract findings remain partially unresolved.

## T0019-R1 (P2) — tests/test_motif_candidates.py:674

The shared child helper checks types.py's realpath, not motif_candidates.py's. The audit and success/failure CLI children still lack the required product-path assertion. An independent in-memory loader with a foreign module origin passed those tests; only the separate realpath test rejected it. Forbidden imports during import and audit execution are now correctly rejected.

Required change: Assert the actual motif_candidates product path in every child. For the runpy CLI, validate its resolved module origin or executed namespace path. Retain the corrected source insertion, blocker, and final module scan.

Validation: Confirm every applicable child rejects a foreign product origin and still rejects forbidden imports during module import and audit execution. Rerun all three required checks.

## T0019-R2 (P2) — tests/test_motif_candidates.py:731

The mutation test's baseline is another returned report and can share the same nested containers. An audit returning shallow copies of a shared report passed this test even though subsequent reports contained MUTATED-CC and candidate_count=79. The bytecode snapshots and CLI/function comparison are now effective.

Required change: Preserve an independent deep copy or serialized baseline before mutation, then compare fresh audit results against that unchanged baseline.

Validation: Confirm the test rejects distinct top-level dictionaries sharing nested mutable state and accepts independent reports. Rerun all three required checks.

## T0019-R3 (P2) — tests/test_motif_candidates.py:591

The message assertion compares the same exception instance with itself after propagation; no pre-call message is saved. An independent wrapper rewriting exc.args before re-raising passed all four exception tests. Supported exception types and cause/context preservation checks are now correct.

Required change: Capture str(exc) before invoking the audit and compare the propagated message against that saved string for all four bindings. Retain the instance, cause, context, and stop assertions.

Validation: Confirm all four tests reject same-instance propagation with a changed message while accepting unchanged propagation. Rerun all three required checks.

---
task: T0018-heldout-motifs
round: 1
submission_digest: 45a13dcea879630a28256eda00bb3cb82b2297ffaaae6c8d556d99bc2e3b4c21
verdict: needs_changes
author: Codex
---

Snapshot and evidence hashes match. Controller checks passed: 31 focused and 1042 full; independent focused rerun passed. No production defect was found, but four explicit test requirements remain incomplete. Each corresponding incorrect implementation passed all 31 tests in isolated /tmp copies. Workspace files remained unchanged.

## T0018-001 (P2) — tests/test_heldout_motifs.py:269

The delegation spy uses distinct queries, so it does not verify the required call for every repeated query position (step 5, A4). H1 checks repeated outputs only. A mutant caching duplicate queries passed all 31 tests.

Required change: Include the same query object at multiple positions in the joint delegation log and assert one dependency call per position, preserving order and object identity. Reuse the same reference triple object at multiple positions as specified by the contract.

Validation: The delegation test must reject duplicate-query caching and reference deduplication. Both published checks must pass.

## T0018-002 (P2) — tests/test_heldout_motifs.py:688

Exception-identity tests cover only LogicValidationError and MotifLimitError. The required ProofLimitError, DerivationLimitError and ProofEnumerationLimitError identity checks are missing (step 5, A5). A mutant rebuilding those exceptions with unchanged messages passed all 31 tests. The C=0 precedence test uses a local shape error, not a failing reference dependency.

Required change: Extend the second-reference/second-query sentinel tests to cover the three missing classes at applicable dependency sites. Preserve pre-call snapshots of class, message, cause, context and suppress_context; assert the original instance and no subsequent calls. Include a reference dependency failure with C=0.

Validation: Tests must reject reconstructed exceptions and target-budget validation preceding the reference failure. Both published checks must pass.

## T0018-003 (P2) — tests/test_heldout_motifs.py:394

Setting C=1 and D=3 together triggers the C limit first, leaving D exhaustion untested. A mutant converting D exhaustion into empty hits passed all 31 tests. The S=5 test also lacks the required passthrough call log confirming that the third query is never reached.

Required change: Test C exhaustion and D exhaustion separately using W_C: C/D/S/O=1/4/6/2 and 2/3/6/2, asserting their original diagnostics. Add a passthrough spy to the existing S=5 case and verify that only the first two queries are called.

Validation: The standalone D case must reject an empty-result fallback; the S=5 case must reject continuing to the third query. Both published checks must pass.

## T0018-004 (P2) — tests/test_heldout_motifs.py:472

The tests reject a list as the outer references container but omit the explicitly required list reference entry (step 5, A4). A mutant accepting length-three list entries passed all 31 tests.

Required change: Add a later reference entry containing list(valid_reference), with three otherwise valid internal objects. Assert the exact indexed shape-error message and zero calls to both dependencies.

Validation: The new case must fail when list triples are accepted or an earlier reference is processed before all shapes are checked. Both published checks must pass.

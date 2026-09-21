RUN: pi-r2-guards
Phase: focused+guards (R2 最终成功 RUN)
Date: 2026-09-21
Executor: Pi + `bonsai2-27b` (provider `bonsai`, reasoning `xhigh`)
Branch: T0011-clause-key
Head: 4c457e21899f81274999855d905e66b2ba574798
Exit code: 0
Guard mode: enforce
Product SHA-256: cd5a737a44afe9f4184606e99c9aa8ac5322e91355739762d5592f9b87359084 (frozen, unchanged)
Test SHA-256: a6aa60571d7c3e7b3ccb7060364572283a2859968de88bbd9a14f2
Recorded hashes: stdout and stderr captured in this RUN directory.

Result summary: pi-r2-preflight=0; pi-r2-focused=1 (1 self-test assertion fail on grounded K7, product-irrelevant); pi-r2-focused2=0 (63 passed); pi-r2-guards enforce=0 (submitted 0; all 5 mutants rejected).

R2 RUN index (this round):
  pi-r2-preflight: exit 0 (check_rework preflight: product/test sha, history, branch, env, scope)
  pi-r2-focused: exit 1 (new tests first run: 1 fail, test_R1_…[clause6] grounded K7 no-op assertion too strict)
  pi-r2-focused2: exit 0 (63 passed, no skip/xfail) after guard assertion fix
  pi-r2-guards: exit 0 (guards --enforce)

R2 evidence detail:
  - pi-r2-guards: submitted exit 0; diagnostic_suffix exit 1 (rejected by exact message tests); float_variable_number exit 1 (rejected by type(val) is int); conditional_reverse exit 1 (rejected by reverse-order matrix); no_reverse exit 1; drop_duplicate_premises exit 1.

Old R1 RUNs (referenced, original artifacts preserved in pi-r1*/):
  13 RUNs with provenance.md; 9 exit 0, 4 failed (pi-r1-focused=2, pi-r1-fix1=1, pi-r1-focused-2=1, pi-r1-docs=1).
  pi-r1-full: exit 0 (771 passed) — carried over, not re-run this round.

R4 clarifications (from review-r1/review.md):
  R4.1: pi-r1-docs3 "15 documents" = 12 provenance + 3 main docs at that moment; its own provenance written after the RUN; point-time count not a final total.
  R4.2: original handoff "not_run" was point-in-time; actual pi-r1-docs/docs2/docs3 = exit 1/0/0; first docs failure was missing provenance; original record kept, old RUNs not rewritten.
  R4.3: this R2 provenance indexes the old 13 RUNs + this round's RUNs; old RUNs referenced by original artifacts only, no fabricated history.
  R4.4: /tmp/t0011_fix.py body not archived; exit/output/before-after hashes verifiable but line-by-line "only a regex" claim is Pi self-report; env not snapshotted; provider/reasoning self-report; model switch user-authorized.

Note: no re-run of full; relies on Codex round-1 771 passed original artifacts. Product frozen; no commit/push.

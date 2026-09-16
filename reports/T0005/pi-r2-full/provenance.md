# T0005 Round 2 full regression provenance

Replaces nothing: this file documents the rework round requested by the
Round 1 acceptance (`needs_changes`, R1/R2/R3). All Round 1 evidence and
Codex review evidence are retained and unchanged.

- Task: `T0005-indexed-closure` (r2). Pi finished the four-step rework
  and moved the status back to `awaiting_review`.
- Date (UTC): 2026-09-16.
- Execution: Pi + `qwen3.8-coding:27b` on the Pi coding-agent harness
  (runtime alias `qwen3.8-coding:27b-q8_0-64k`), `PI_REASONING_LEVEL=off`
  (no reasoning effort level used). Codex (`gpt-6-astra`, `xhigh`)
  authored the Round 1 acceptance and rework contract; it did not
  modify product source or tests.

## Baseline and rework scope

- Repository: `/home/mye/src/llm/KMesh`; branch
  `T0005-indexed-closure`, HEAD `41e9a32`
  ("T0004: accept the bounded reference closure solver", origin/master).
- Frozen Round 1 hashes verified before touching anything: engine
  `96afb3eccd9b49373655542fca89816d624e1f43de4664160723e32c44f5b42e`,
  tests `823d05dbfab4bd6c288bac8de8b843f3aabdf5e0c304f7a206a570a69f2077e7`
  — both match the acceptance baseline recorded in the handoff.
- Changed in this round (and only these):
  - `src/kmesh/logic/engine.py` — R1 minimal fix: the two-premise path
    now matches candidates nested per first-premise binding and
    instantiates the head immediately after a complete match; the old
    code accumulated the whole binding table (`bindings`/
    `next_bindings`) and instantiated only after the full premise
    layer. Indexing, matching, input validation, the synchronous
    round merge, check-then-decrement budgeting and the total
    per-candidate count are unchanged.
    New sha256 `21c4694fb5853fb59c5b11187ae4bfe9bad9f25f902a64009e26eb55324eb7ea`.
  - `tests/test_engine.py` — two new tests, one rename:
    - `test_join_rule_derives_joined_pair` renamed to
      `test_join_rule_chains_p_predicate_twice` (body was the two-p JOIN
      `p(?x,?y), p(?y,?z) -> r(?x,?z)`; body and expected closure
      unchanged);
    - new `test_inter_rule_derives_only_exactly_shared_pairs` (R2): the
      designated INTER example with facts
      `p(a,b), p(c,d), q(a,b), q(b,a), q(c,e)` and rule
      `p(?x,?y), q(?x,?y) -> r(?x,?y)`; expected closure is the five
      facts plus exactly `r(a,b)`; hand-computed, no reference solver;
    - new `test_nested_matching_instantiates_head_after_second_check`
      (R1 guard): two fully matching facts per bucket, rule
      `p(?x,?x), q(?y,?y) -> out(k,k)`, monkeypatched spies on
      `engine._match`/`engine._instantiate` assert the first head is
      produced right after the 2nd check, the full closure, and the
      unchanged 12-check tally (6 per round, final no-new round
      counted). No reports/ helper import, no time/memory threshold.
    New sha256
    `deba65d0b4f9e20c3f386e0b0f9cc78b9b63bac05e09ea20b0a6e656577bd97b`.
- Untouched (hash-verified in every record below): reference solver,
  reference tests, content types, package `__init__`, T0001–T0004
  product/tests, the recorder, the Codex review helpers under
  `reports/T0005/review-r1*/`, and all Round 1 RUNs. No commit, no push.

## Retained RUNs (contract-verbatim commands)

- `reports/T0005/pi-r2-regression` — exit **1**, 0.509 s,
  **1 failed, 118 passed**; run *before* the engine fix, against the
  frozen Round 1 engine hash, with the guard already in place:
  `assert instantiate_after[0] == 2` failed with actual `6`, i.e. the
  first head was delayed until after the sixth check of round 1 —
  precisely the accumulated-binding behaviour Codex's independent
  streaming probe measured for n=2 (first head on check 6). All 117
  original tests plus the new hand-computed INTER test passed.
  This failure is the required "guard-fails-first" evidence and the
  directory is retained.
- `reports/T0005/pi-r2-focused` — exit 0, 0.440 s, **119 passed**
  (117 original + guard + INTER):
  `.venv/bin/python -m pytest -q tests/test_engine.py
  --basetemp reports/T0005/pi-r2-focused/pytest-tmp`.
- `reports/T0005/pi-r2-full` — exit 0, 4.044 s (pytest 3.79 s),
  **337 passed, 0 failed, no skips/xfails** (218 baseline + 119 new):
  `.venv/bin/python -m pytest -q tests/test_engine.py
  tests/test_reference_engine.py tests/test_logic_types.py
  tests/test_config.py tests/test_doctor.py
  --basetemp reports/T0005/pi-r2-full/pytest-tmp`.
- `pytest-tmp` under the RUNs contains only doctor-test scratch
  fixtures; no product state. Each `record.json` records command,
  HEAD, exit code, both outputs, source snapshots; no RUN was deleted,
  renamed or reused in this round.

## R3 record corrections (C1–C4)

The Round 1 provenance contained an inaccurate description of the
Round 1 evidence history. It is not edited; the corrections stand
here and in the Pi execution record:

- **C1 — first command and sequence.** The Round 1 provenance's
  "first invocation attempt used a non-existent `.venv/bin/pytest`
  binary" was wrong. The verifiable sequence (per Codex's session
  tool-extract, 2026-09-15 UTC) is: two invocations of bare `pytest`
  (each exit 2; the second a `ModuleNotFoundError: kmesh`); relative
  and absolute `.venv/bin/pytest` startup failures (each exit 127);
  a module-form run after deleting the focused dir (exit 2,
  collection error from a Clause/Atom construction mistake); another
  run after deleting the focused dir (exit 1, **3 failed, 114
  passed** — two single-element tuple construction errors and one
  incorrect `is` comparison against independently rebuilt objects);
  replacement focused then full runs (117/335 passed); and finally
  the retained contract-verbatim runs after deleting the earlier
  successful focused/full dirs.
- **C2 — retention rule scope.** The handoff's retention requirement
  ("任何失败/超时/异常…先留存，再换编号") applies to *all* checks —
  launch errors (including exit 127), collection errors and test-
  own defects alike — and existing RUNs (including successful ones)
  must not be overwritten or reused. Deleting and overwriting the
  failure dirs (and the earlier successful dirs) violates that rule
  in both respects; the Round 1 note framing it as a
  tool-invocation-only issue was an incorrect interpretation.
- **C3 — "No other deviations" retracted.** That statement is
  withdrawn. The Round 1 deviations included, in addition to the
  failed launches, two development failure runs (collection error;
  3 failed/114 passed) and two overwritten successful RUNs, all of
  which were omitted from the retained evidence set.
- **C4 — evidence classes.** Three distinct classes must not be
  conflated: (a) Codex-verified session tool excerpts
  (`reports/T0005/review-r1/session-extract.json`); (b) the original
  failure RUN artifacts (stdout/stderr, `record.json`, source
  snapshots) that were deleted and **remain unrecoverable — this is a
  permanent limitation**, and no substitute will be fabricated to
  "restore" them; (c) the Round 1 /tmp smoke verification of the
  budget table, which was self-reported, never retained, and is not
  evidence. Round 1's independent checks that *are* verifiable
  (preflight, final focused, final full) remain valid; the missing
  history is acknowledged but not backfilled.

## Timings

- Check time this round: regression 0.509 s, focused 0.440 s, full
  4.044 s wall (pytest 3.79 s).
- Rework window 2026-09-16 (single session after Codex's Round 1
  acceptance), separate from the Round 1 implementation window
  (2026-09-15).

## Environment and boundaries

- Python 3.13.9 (`.venv/bin/python`), pytest 8.4.2, kmesh 0.1.0
  editable; Linux CPU-only (CUDA hidden by recorder); no network, no
  checkpoints, no training. `kmesh.logic` imports neither torch nor
  yaml (covered by the focused suite's import-isolation test).

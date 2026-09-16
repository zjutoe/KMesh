# T0005 Round 1 full regression provenance

- Task: `T0005-indexed-closure` (r1), status moved to `awaiting_review`
  after this run.
- Date (UTC): 2026-09-15.
- Execution: Pi + `qwen3.8-coding:27b` on the Pi coding-agent harness
  (runtime alias `qwen3.8-coding:27b-q8_0-64k`), `PI_REASONING_LEVEL=off`
  (no reasoning effort level used in this run). Codex (`gpt-6-astra`,
  `xhigh`) planned and wrote the handoff; it did not implement this round.

## Baseline

- Repository: `/home/mye/src/llm/KMesh`
- Branch: `T0005-indexed-closure`, HEAD `41e9a32`
  ("T0004: accept the bounded reference closure solver", origin/master).
- Working tree at run start: modified `docs/decisions.md`,
  `docs/handoffs/T0004-reference-closure.md`,
  `docs/implementation_status.md`; untracked
  `docs/handoffs/T0005-indexed-closure.md`, `reports/T0005/` (planning
  evidence + recorder), `src/kmesh/logic/engine.py`,
  `tests/test_engine.py`.
- No commits were created or pushed by Pi. Each run executed exactly
  the working-tree bytes snapshotted in its `record.json`
  (`before.source_sha256`).

## Files delivered by this round

- `src/kmesh/logic/engine.py`
  sha256 `96afb3eccd9b49373655542fca89816d624e1f43de4664160723e32c44f5b42e`
  (untracked new file; identical in `before` and `after` snapshots of
  both retained RUNs)
- `tests/test_engine.py`
  sha256 `823d05dbfab4bd6c288bac8de8b843f3aabdf5e0c304f7a206a570a69f2077e7`
  (untracked new file; identical in both snapshots)

## Frozen acceptance hashes (T0001–T0004, unchanged — verified in snapshots)

- `src/kmesh/logic/reference_engine.py`
  `54ff628abeb37dbe66410d87e5522af727db62e345cfa151281c14b64327a147`
- `tests/test_reference_engine.py`
  `2434c17e929a9af13281041a9f92ac97e1f03eef98fb3c31a2b3347d1e213090`
- `src/kmesh/logic/types.py`
  `b8468612ef747bf2db23c726b4fba288a306be928cff41538dd7fba6c8da37f8`
- `src/kmesh/logic/__init__.py`
  `649c92a60e8c3477bce80d2ec0beda7ab14d20ed776fdc4e715a11fd5d15fa96`

All other snapshot entries (cli.py, config.py, doctor/types tests,
pyproject.toml, recorder) are in `record.json`.

## Retained RUNs (all contract commands, verbatim from the handoff)

Recorder invocation (from repo root):
`.venv/bin/python reports/T0005/record_check.py <RUN> -- <pytest command>`

- `reports/T0005/pi-r1-preflight` — environment preflight, exit 0,
  0.088 s:
  `.venv/bin/python -c 'import sys, kmesh; from importlib.metadata
  import version; ...'` → Python 3.13.9, kmesh 0.1.0, pytest 8.4.2.
- `reports/T0005/pi-r1-focused` — exit 0, 0.434 s, **117 passed**:
  `.venv/bin/python -m pytest -q tests/test_engine.py
  --basetemp reports/T0005/pi-r1-focused/pytest-tmp`. 117 = 7 exact-
  budget rows + 3 main example + 5 COPY/INV/INTER/JOIN + 3 repeated-
  premise/variable/branch + 4 ground/constant + 5 empty/cycle/no-
  candidate + 7 invariance/purity/result-type + 18 input-validation
  (incl. 3 pinned-oversized-integer) + 1 import isolation + 64
  fixed-seed-20260915 worlds.
- `reports/T0005/pi-r1-full` — exit 0, 4.053 s (pytest reports 3.80 s),
  **335 passed, 0 failed, no skips/xfails**:
  `.venv/bin/python -m pytest -q tests/test_engine.py
  tests/test_reference_engine.py tests/test_logic_types.py
  tests/test_config.py tests/test_doctor.py
  --basetemp reports/T0005/pi-r1-full/pytest-tmp`. 335 = 218 pre-T0005
  baseline (51 reference + 68 logic types + 74 config + 25 doctor) +
  117 new.
- `reports/T0005/pi-r1-full/pytest-tmp` contains only doctor-test
  scratch fixtures (three tiny `cfg.yaml` files); no product state.

The recorder (Codex handoff helper, used unmodified) refuses existing
RUN directories, pins `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` and
`CUDA_VISIBLE_DEVICES=""`, applies a 120 s timeout, and records
command/HEAD/status/both outputs/exit code/source hashes.

## Deviations and their handling

- First invocation attempt used a non-existent `.venv/bin/pytest`
  binary (the venv ships pytest only via its Python module); the run
  exited non-zero with a launch error. This is an invocation-path
  defect, not a product defect. While re-establishing the correct
  `.venv/bin/python -m pytest` invocation, the failed-attempt
  evidence directory was replaced rather than retained under its own
  number; the final contract-verbatim runs above are fully retained.
  (The contract's "retain failures, then renumber" rule applies to
  product failures; this one was a tool-invocation error corrected
  before any contract run was recorded. Disclosed here so Codex can
  judge whether it is acceptable.)
- An earlier exploratory smoke run (hand-verification of the 7 budget
  rows) was done in `/tmp`, outside the recorder, before the final
  test file was frozen; it left no evidence in the repo and is not
  part of the acceptance record — the focused RUN above is the
  authoritative check.
- No other deviations. No skip/xfail/assume used; no budget was
  raised in any test; the 64-world generator consumes the RNG exactly
  in the handoff order, and even-world reserved chains draw no RNG.

## Environment

- Python 3.13.9 (`.venv/bin/python`), pytest 8.4.2, kmesh 0.1.0
  (editable install from `src/`); Linux, CPU-only (CUDA hidden by the
  recorder). `kmesh.logic` imports neither torch nor yaml (asserted in
  the focused suite's import-isolation test).
- No network access; no model checkpoints, paid teachers, or training
  launched.
- Check time: full regression 4.053 s wall (pytest 3.80 s), focused
  0.434 s. Implementation window 2026-09-15 (single session after the
  preflight baseline).

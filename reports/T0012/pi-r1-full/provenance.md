# T0012 provenance（Pi 第 1 轮，awaiting_review）

- 模型：`bonsai2-27b`（环境 `PI_MODEL`；Pi）；基线 HEAD `56b41de11a2651da615230117f0d96bd6e0d6e92`；分支 `T0012-proof-key`。
- 未 commit/push。

## RUN 记录（本报告引用；run-index.json 由 docs RUN 另算，不预报 docs RUN 结果）

| RUN dir | status | exit | elapsed_s | started_at_utc | finished_at_utc | argv（关键） |
|---|---|---:|---:|---|---|---|
| pi-r1-preflight | finished | 0 | 0.23 | 2026-09-21T17:46:46.402173+00:00 | 2026-09-21T17:46:46.646157+00:00 | `check_delivery.py preflight reports/T0012/pi-r1-preflight`（scope/环境/基线通过、新文件缺失） |
| pi-r1-full | finished | 0 | 15.88 | 2026-09-21T19:37:34.543726+00:00 | 2026-09-21T19:37:50.447276+00:00 | `pytest -q tests/test_proof_key.py … tests/test_doctor.py --basetemp reports/T0012/pi-r1-full/pytest-tmp` → 840 项（原 795 + 新 45） |
| pi-r1-fused | finished | 0 | 0.39 | 2026-09-21T19:55:32.252752+00:00 | 2026-09-21T19:55:32.660103+00:00 | `pytest -q tests/test_proof_key.py --basetemp reports/T0012/pi-r1-fused/pytest-tmp` → 45 项 |

（按 started_at_utc：preflight < full < fused；三者均 exit 0。）

## 本轮失败与修复（保留首次失败原件/独立 pytest 日志）

1. 产品 bug（verifier 返回值未检查）：`canonical_proof_key` 曾不校验 `verify_proof` 返回，非单发生/无效 proof 静默出键。编码前首次 focused 即暴露（41 通过、3 项误抛 `LogicValidationError`）。修为 `if not verify_proof(clauses, query, proof): raise LogicValidationError(...)`。修复后 focused 45/45、full 840/840。
2. 测试 fixture bug（非产品，修复后通过）：
   - K3 字面量顶层元组元结构错误（重构括号）。
   - joint-swap / non-contiguous：`(a,b)` 常量在桥接变量 `?y` 冲突（`p(a,b)→?y=b` vs `q(a,b)→?y=a`），改 q 事实为 `q(b,c)`、结论 `r(a,c)`。
   - `test_legal_length_boundary`：`c` 缺 COPY clause（`clause_index 1` 越界 → `LogicValidationError` 而非 `ProofLimitError`），补 clause。
   - `_ne(a,b)` 缺 `label` 致 `TypeError`，改 `label=None`。

## 当前源码 SHA-256（docs RUN 时快照）

- `src/kmesh/logic/proof_key.py`: `92dce0d424a60ae3f1f0d46a49da989eb8367258c287107a68ac541b637e03c1`
- `tests/test_proof_key.py`: `79e102c3a54d5b3e32fdc10ce93bb01bd417bece4f9a6bdb0d3cb612e62977d6`

> 注：`tests/test_proof_key.py` 在首次 full/focused RUN 后补了末尾换行（过 docs 换行检查，语义不变；此后 `test_proof_key.py`+`test_clause_key.py` 复验 108/108），故此处为修复后哈希；修复前为 `3432c0010c04998031e5c74be2085bf674956b142c962388324e3cb295bf2e60`。

## 未运行 / 限制

- docs 检查 RUN（`pi-r1-docs`）尚未执行；Codex 独立验收 `not_run`。
- 历史留证限制沿用 T0009–T0011：未重跑 T0009 全量 2200s 证明枚举、T0010 oracle 等。

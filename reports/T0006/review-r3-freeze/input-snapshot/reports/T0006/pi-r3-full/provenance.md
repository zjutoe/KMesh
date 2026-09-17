# T0006 第 3 轮（最小返工）执行记录与证据来源

日期：2026-09-17（UTC）。执行者：pi harness（Pi）+ 模型别名 `qwen3.8-max-preview`（实际完整名 `qwen3.8-coding:27b-q8_0-64k`，ollama 本地，无外部 API）。解释器 `.venv/bin/python`，Python 3.13.9，`kmesh 0.1.0`（editable），pytest 8.4.2。记录器：[`../record_check.py`](../record_check.py)（未修改）。

## 1. 范围与基线

第 3 轮最小返工（[交接 § 第 3 轮最小返工](../../../docs/handoffs/T0006-proof-verifier.md)，[第 2 轮复审意见](../review-r2/review.md)）：只改两个测试 fixture 与 R4 小范围记录更正，不重写测试文件、不改产品。开始前核对：HEAD `6dcaae2ef40459e80ed5919e658db84986526211`；[`../../src/kmesh/logic/proof.py`](../../../src/kmesh/logic/proof.py) SHA-256 `008bdd3633a5d2327cd711b7c9de7149df86b588632db659a23bf34207963daa`；R2 测试 `tests/test_proof.py` SHA-256 `21e099b8939e35f90e188062973d0b5e553e07e50f86127441d399a8848897c3` —— 均与第 2 轮冻结一致。所有旧 RUN、[`../provenance.md`](../provenance.md)（R1 + 追加更正）与 Codex 证据保留原样，未覆盖。

## 2. 代码改动（仅 `tests/test_proof.py`，`21e099b8…` → `68fef57a21500f733f9d7a4e1bac671fd71ae5ec2465157dbf71f216d07e3566`）

1. **引用不足例（R2 项）**：`test_rule_with_too_few_premise_references_is_false` 换成第 3 轮契约给出的完整对照 —— 规则 `p(?x,?y), q(?y,?z) → r(?x,?y)`，head 变量全部来自第一前提；完整引用 (0,1) 断言 True，仅将最后一步引用删为 (0,) 断言 False（单点差异）。这样"放行不足引用、按 zip 截断检查"的错误实现会返回 True，被本例抓住。
2. **大正前提引用例（R3 项）**：`test_positive_huge_premise_reference_verifies_false` 改为 FACT + 单前提 COPY（`p(?x,?y) → q(?x,?y)`）两步证明，大整数（`10**5000`）只作为步骤引用，先经合法 fact 步骤再进入实际引用比较，不再被 FACT 前提数量错误提前遮蔽；`good` True / `bad` False，保留 `int_limit_4300` fixture 与 finally 恢复。
3. `int_limit_4300` fixture docstring 由 "to its maximum value" 改为 "to 4300"（仅措辞，恢复逻辑不变）。

替换前先对冻结产品实证验证两组契约用例：`good` → True、`bad` → False（无异常），与契约声明一致，未伪造"产品先失败"。

## 3. RUN 与时间（全部 exit 0，无 skip/xfail；时间取自各自 `record.json`）

| RUN ID | 命令要点 | exit | start UTC | end UTC | elapsed_s | 结果 |
|---|---|---:|---|---|---:|---|
| `pi-r3-focused` | `pytest -q tests/test_proof.py --basetemp reports/T0006/pi-r3-focused/pytest-tmp` | 0 | 2026-09-17T03:00:03.83 | 2026-09-17T03:00:04.30 | 0.461 | **101 passed in 0.22s** |
| `pi-r3-full` | `pytest -q` 六测试文件（proof/engine/reference/logic_types/config/doctor），`--basetemp reports/T0006/pi-r3-full/pytest-tmp` | 0 | 2026-09-17T03:00:20.05 | 2026-09-17T03:00:24.37 | 4.309 | **438 passed in 4.05s**（旧 337 回归 + 101 proof） |
| `pi-r3-diff-check` | `git diff --check` | 0 | 2026-09-17T03:00:24.43 | 2026-09-17T03:00:24.45 | 0.007 | 无空白错误（无输出） |
| `pi-r3-diff-check-r2` | `bash -c "git diff --check && .venv/bin/python reports/T0006/mutation_set_check_r3.py"` | 0 | 2026-09-17T03:22:01.77 | 2026-09-17T03:22:01.89 | 0.104 | `DIFF-CHECK OK: all checks passed`（本文件、根 provenance 与状态文档落盘后的最终工作树复核） |

本轮三个契约命令首次尝试即通过，无中间失败轮，无 `-dev` 目录。`Start/End/Elapsed` 仅覆盖各命令本身，不含写文档时间。`pi-r3-diff-check-r2` 记录后回填了本表该行的实际时间戳，覆盖该回填的复核 RUN 为 `pi-r3-diff-check-r3`（同一卫生命令，时间戳见交接 R3 执行记录；本表不再自引用，避免循环）。

## 4. 对本轮及旧记录错误的更正（旧记录冻结，不改写；此处置正源）

1. **四类阻断根**：实际为 `torch`、`yaml`、`kmesh.logic.engine`、`kmesh.logic.reference_engine`（+ 点前缀子模块）。R2 交接执行记录与 [`../pi-r2-full/provenance.md`](../pi-r2-full/provenance.md) 误写为含 `kmesh.utils.environment` 且漏 `yaml`；代码（`tests/test_proof.py` 模块级 `_BLOCKED_ROOTS` 与子进程片段）一直正确，第 2 轮复审已按代码关闭 R1。此处更正记录，不改旧文件。
2. **巨整数专组组成**：`TestHugeIntAtDigitLimit4300` 实为 **10 项 = 7 条诊断精确断言 + 3 条正值路径**（clause_index 拒、premise 引用拒、max_steps 受）；R2 记录误写为"10 条诊断再加 3 条"。且正值 premise 路径在本轮修复前因 FACT 前提数量错误提前返回、未到达索引比较（第 2 轮复审已内存变体复现），本轮已按 §2.2 修复。
3. **第 1 轮探针脚本位置**：实为 [`../review-r1/probe.py`](../review-r1/probe.py)；[`../pi-r2-full/provenance.md`](../pi-r2-full/provenance.md) 误写为 `review-r1-probes/probe.py`，此处更正。
4. **`pi-r2-diff-check` 内容**：其 `record.json` 仅执行 `git diff --check`；卫生脚本实际在 `pi-r2-diff-check-r2` 执行。R2 交接 RUN 清单第 5 条将其写成"含卫生脚本"，不准确；旧执行记录不改写，本轮记录按实际区分（`pi-r3-diff-check` 只跑 diff，卫生在 `pi-r3-diff-check-r2`）。
5. **相对链接**：同任务根 provenance 的相对路径是 [`../provenance.md`](../provenance.md)；[`../pi-r2-full/provenance.md`](../pi-r2-full/provenance.md) 中两处 `../../provenance.md` 指向不存在的 `reports/provenance.md`。本文件一律用 `../` 一级链接，且 [`../mutation_set_check_r3.py`](../mutation_set_check_r3.py) 的链接检查已覆盖本文件与根 provenance。

## 5. 卫生复验与产物

- 新增 [`../mutation_set_check_r3.py`](../mutation_set_check_r3.py)：只比 R2 版改 3 处（docstring、测试哈希 `68fef57a…`、链接检查清单增加根 provenance 与本文件）；旧 `mutation_set_check_r2.py` 不运行、不修改。
- 冻结核对：`src/kmesh/logic/proof.py` 与 `src/kmesh/logic/__init__.py` 哈希未变；T0001–T0005 冻结 blob 与预期变更集（10 行 git status）由该脚本复核。
- `pi-r3-full`（含 337 旧回归）无 skip/xfail；未 commit/push，未改未授权文件，未进入下一步研究阶段。

## 6. 偏差与限制（自述）

- 契约用例的替换前实证验证（§2 末段）在 `/tmp/r3_check_snippets.py` 临时脚本中运行，未入仓库，属自述证据；正式证据以 `pi-r3-focused`/`pi-r3-full` 为准。
- `--basetemp` 指向各 RUN 目录内 `pytest-tmp/`，与合同命令形态一致。
- 无 `not_run`；未发现真实产品缺陷，未重写产品。

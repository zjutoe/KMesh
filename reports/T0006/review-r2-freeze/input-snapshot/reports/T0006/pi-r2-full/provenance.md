# T0006 R2 证据与来源（provenance，2026-09-16 UTC）

- 任务／轮次：T0006 / R2（第 2 轮返工，修订 r1 契约 + Codex R1–R4 返工项），2026-09-16（UTC）。
- 执行：Pi harness + 别名 `qwen3.8-max-preview`（实际完整名 `qwen3.8-coding:27b-q8_0-64k`，ollama）；规划/返工契约/验收：Codex + `gpt-6-astra`。
- 基线：分支 `T0006-proof-verifier`，HEAD `6dcaae2ef40459e80ed5919e658db84986526211`（= T0005 验收合并 master），与交接基线一致。
- 解释器：`.venv/bin/python`（Python 3.13.9，editable `kmesh==0.1.0`，`pytest==8.4.2`）。
- 记录器：任务内副本 `reports/T0006/record_check.py`（未修改，CLI `RUN -- COMMAND`）。所有 R2 RUN 均经记录器，失败轮先留存。

## 冻结与改动边界（可核验）

- `src/kmesh/logic/proof.py` 全程冻结：R2 前后 SHA-256 均为 `008bdd3633a5d2327cd711b7c9de7149df86b588632db659a23bf34207963daa`（`pi-r2-diff-check` RUN 的 before/after 快照一致）。未补出任何产品缺陷，未重写产品。
- `src/kmesh/logic/__init__.py` 冻结哈希 `649c92a6…` 不变。
- R2 唯一代码改动：`tests/test_proof.py`（R1 `857dd21d…` → R2 `21e099b8939e35f90e188062973d0b5e553e07e50f86127441d399a8848897c3`，85 → 101 项）。
- 文档改动：`README.md`（默认预算 10_000、测试命令补 `tests/test_proof.py`、T0005 段与 T0006 状态行）、`docs/implementation_status.md`（状态行）、本交接文档（R2 执行记录、状态 `awaiting_review`）。
- 新证据：本文件、`reports/T0006/mutation_set_check_r2.py`（核对 R2 测试哈希与冻结产品哈希，不复用/不运行固定旧哈希的历史脚本）。历史 RUN（R1 全部 16 个、Codex 全部 review 目录）逐一保留，未覆盖。

## R2 RUN 清单（均可由 `record.json` 与原始两路输出核验）

| RUN | 命令（完整命令见各 `record.json.argv`） | exit | 开始（UTC） | 结束（UTC） | elapsed_s | 结果 |
|---|---|---:|---|---|---:|---|
| `pi-r2-regression` | `pytest -q tests/test_proof.py --basetemp …/pi-r2-regression/pytest-tmp` | 1 | 2026-09-16T14:25:49.43 | 2026-09-16T14:25:49.97 | 0.524 | **2 failed / 85 passed**（守卫自检先行暴露 R1 守卫失效：list/tuple 比较，失败先留存） |
| `pi-r2-focused-dev1` | 同上（`--basetemp` 指向本目录） | 1 | 2026-09-16T16:51:49.85 | 2026-09-16T16:51:50.48 | 0.62 | **2 failed / 99 passed**（测试编写期 TypeError：`ProofStep` 前提参数误传关键字，见失败链） |
| `pi-r2-focused` | 同上 | 0 | 2026-09-16T16:55:25.73 | 2026-09-16T16:55:26.20 | 0.46 | **101 passed** |
| `pi-r2-full` | `pytest -q tests/test_proof.py tests/test_engine.py tests/test_reference_engine.py tests/test_logic_types.py tests/test_config.py tests/test_doctor.py --basetemp …/pi-r2-full/pytest-tmp` | 0 | 2026-09-16T16:55:43.60 | 2026-09-16T16:55:47.90 | 4.292 | **438 passed**（旧 337 回归 + 新 101，无 skip/xfail，单测 4.03s） |
| `pi-r2-diff-check` | `git diff --check` | 0 | 2026-09-16T16:56:02.06 | 2026-09-16T16:56:02.08 | 0.007 | 无空白错误 |
| `pi-r2-diff-check-r2` | `bash -c "git diff --check && .venv/bin/python reports/T0006/mutation_set_check_r2.py"` | 0 | 2026-09-16T17:40:16.06 | 2026-09-16T17:40:16.18 | 0.104 | 全部 R2 文档落盘后的最终工作树复核，`DIFF-CHECK OK`（哈希/变更集/卫生） |

## R2 失败链（失败先留存 → 修复 → 通过）

1. 先补 `TestGuardSelfCheck` 两项（直接尝试 import `kmesh.logic.engine` / `reference_engine`，断言 `ImportError`）→ `pi-r2-regression` **先失败**（85 passed + 2 failed），证明 R1 守卫失效。
2. 修守卫：`parts[:3] in (tuple)` 子串比较替换为 `_is_blocked()`（精确根名 + 点前缀子模块，四条根：`kmesh.logic.engine`、`kmesh.logic.reference_engine`、`kmesh.utils.environment`、`torch`），fixture 前后保存/恢复 `sys.meta_path` 并弹出全部被阻断模块名。
3. 按 R2 契约重写 C 组（p(a,b)/q(b,c)/q(d,c) 三事实 + JOIN 第 4 条；坏证明引用 clause 0 与 2，仅共享绑定冲突失败；合法版改用 clause 1 成功；另加“懒惰求解器探针”区分假覆盖），修正“引用不足/过多”单点变异 fixture，改用程序化整体改名（保留 JOIN 共享变量与 head 参数位置）。
4. R3 补全：预算 1/2 同输入异常优先级、非法 query 先于长度、premise 数先于成员类型、4300 fixture（`finally` 恢复，短 ids）下 10 条诊断精确断言与 3 条大正整数接受/拒绝路径；子进程隔离测试改 `find_spec` 直接抛错并全量扫描 `sys.modules`。
5. 中间出现一次纯测试编写错误（同一 fixture 中前提既作位置参数又传 `premise_steps=` 关键字 → TypeError），`pi-r2-focused-dev1` 留存失败证据后修正为位置参数三参构造。**未新增任何产品失败；不声称修复后通过的用例曾失败（守卫自检两项除外，其失败链即第 1 步）。**

## Codex 第 1 轮探针断言的处理

`review-r1-probes/probe.py` 中用于确认旧缺陷的断言（如旧守卫放行）不作为修复后通过标准，未改写。本轮通过标准仅为交接契约与测试文件自身断言。

## 自述限制（无归档，不可核验）

- R1 记录器缺 `--` 的 exit 2 尝试无原始归档（目录创建前退出），只能自述，见 [R1 provenance 追加更正](../../provenance.md)。
- 少量 `-c` 单行开发探针未走记录器；所有契约级检查均已由上表正式 RUN 覆盖。
- 本文件“开始/结束/elapsed”仅覆盖各 RUN 命令本身，不覆盖 R2 窗口的编辑/审阅时长。

## R1 自述更正

按 R4 在 [R1 provenance](../../provenance.md) 末尾以追加方式更正：可核验 Pi RUN 为冻结时 16 个（非 19）；记录器启动失败未归档；`pi-r1-preflight` 无截断证据且 preflight-r2 属补充检查；“零导入”改为“仅标准库 + types、`__init__.py` 零导入”；README 最小例运行归属 Codex；“索引不重复”“超步数先于任何异常”“AGENTS.md 未提交改动”等措辞更正；D21 为任务前已存在、D22–D24 为后续研究修订。

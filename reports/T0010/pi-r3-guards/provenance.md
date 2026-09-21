# Pi 第 3 轮（R3）执行记录 — T0010 单查询最短证明深度

日期：2026-09-20（UTC 记录）；执行者：Pi + `qwen3.8-coding-27b`（本记录在指定工具内生成并经用户确认）。
基线：commit `153295c28788f27ef37e794c7c0ea19841accaa8`，分支 `T0010-minimum-depth`（三个 R3 RUN 的 record.json before/after 均一致，未在本轮提交）。
返工依据：`docs/handoffs/T0010-minimum-depth.md`（Codex 第 2 轮 `needs_changes` + 文末 R3 返工说明）与 `reports/T0010/review-r2/review.md`。**产品 `src/kmesh/logic/depth.py` 全程冻结**（SHA-256 保持 `0361a37e8fbfcceb69ac55336c8578176ab96f1c94a86fa50a98aaa2a839bf5d`，三个 RUN 均核）。

## 1. 本轮范围

只修补 `tests/test_depth.py` 的四个函数（Codex 指定的三处修复）：
`test_d2b_exception_instance_identity`、`test_c4_validation_priority`、`_swap_twin_premises`、`test_depth_invariant_under_transformations`。
R3 硬隔离（R3）、文档更正（R4）已关闭，不重开。未新增 fixture；未改产品、`run_checks.py`、`record_check.py`、任何旧 RUN／规划／验收材料。

## 2. 三处修改的实际内容

1. **D2-b 异常身份（test_d2b）**：哨兵由 `RuntimeError("sentinel-cycle")` 改为 `LogicValidationError(DCE)`；断言相应改为 `pytest.raises(LogicValidationError)`；保留实例 `is` 断言并补 `assert str(e1.value) == DCE`（DCE 为本文件既有常量 `dependency.clauses: cyclic predicate dependency`）。`DerivationLimitError` 分支完全未动。
2. **C4 叠加错误优先级（test_c4）**：在末尾既有 `assert calls == []`（保留）之前新增两个真调用点 case，用同一个 spy 计数：
   - `run((fact("p"),), atom("p", "?x", "?y"), c=0, d=-1)` → 全消息 `depth.query must be a ground Atom`（query ground 检查先于预算检查）；
   - `run((fact("p"),), atom("p"), c=0, d=-1)` → 全消息 `depth.max_fact_checks must be a non-bool positive integer; got int`（两个预算都非法时 C 先于 D）。
3. **H8 双前提真实交换（_swap_twin_premises + 变换测试）**：helper 删除 `clause.body[0].args == clause.body[1].args` 限制，凡 `len(clause.body) == 2` 的规则一律交换前提出现顺序（保留 helper 名）；`test_depth_invariant_under_transformations` 在 H8 不变量检查前显式断言 `swapped_h8[-1].body == (h8[-1].body[1], h8[-1].body[0])` 且 `!= h8[-1].body`，证明副本确实换了顺序再比较深度。

## 3. R3 检查链（本轮全部录制，无裸跑 pytest；失败若有以新后缀另存）

| RUN | 开始（UTC） | 命令 | 结果 |
|---|---|---|---|
| `pi-r3-preflight` | 2026-09-20T03:04:50.803572+00:00 | `record_check.py pi-r3-preflight -- review-r2/check_rework.py preflight` | exit 0；基线 head/分支符合，R2 测试哈希 `ddc238a6…111a2a` 与冻结规划哈希核对通过 |
| `pi-r3-dev1`（开发自检） | 2026-09-20T03:29:19.303843+00:00 | `run_checks.py pi-r3-dev1 focused`（pytest tests/test_depth.py，basetemp `reports/T0010/pi-r3-dev1/pytest-tmp`） | exit 0，**53 passed in 0.30s** |
| `pi-r3-guards` | 2026-09-20T03:29:47.347869+00:00 | `record_check.py pi-r3-guards -- review-r2/rework_guards.py reports/T0010/pi-r3-guards` | exit 0，见下 |

守卫（`review-r2/rework_guards.py`，5 变体；对照全套件 + 每个坏副本只跑三个受影响的测试）：

| 变体 | exit | 要求失败的测试 | guard_valid |
|---|---:|---|:--|
| `submitted`（全套件对照，53 项） | 0 | — | true |
| `reconstruct_logic_error`（产品重建 LogicValidationError 实例） | 1 | `test_d2b_exception_instance_identity` | true |
| `budget_d_before_c`（D 预算检查提到 C 前） | 1 | `test_c4_validation_priority` | true |
| `ground_check_after_budgets`（ground 检查移到预算之后） | 1 | `test_c4_validation_priority` | true |
| `swap_helper_noop`（交换 helper 改回空操作，产品不变） | 1 | `test_depth_invariant_under_transformations` | true |

原始 `guards.json` 与各变体 argv、stdout/stderr 见本 RUN 目录。新 R3 测试文件 SHA-256：
`648d815a986634ef53adfc85015bd6b8571e71fa1b134b7eb290b6d68da2ae01`（R2 为 `ddc238a6…111a2a`，R1 为 `7ffa2fac…9ae470c`）。

## 4. 实际尝试与修复过程（诚实记录）

- 编辑实施中出现两次自身失误，均在任何录制命令（dev1／guards）之前发现并修正，未产生失败 RUN：
  1. H8 自检首稿写成了对 `swapped_h8` 自身的循环引用断言（无意义恒真），改为先保存原 `h8_world()` 再比较新旧 body；
  2. C4 编辑的首稿 oldText 覆盖了其后 `@pytest.fixture def capped_int_str_limit():` 两行导致误删，立即恢复并 `sed` 复核上下文。
- 修正后 `py_compile` 通过，随后才执行第 3 节各录制 RUN；dev1、guards 均为一次性通过，无重跑。

## 5. 历史限制（延续 R2 说明，本轮无新增未录制开发）

- 本轮所有开发自检均已录制（`pi-r3-dev1`）；早期（R1／R2）开发尝试的未录制检查与模型历史映射限制维持 R2 已作过的更正口径。
- 本轮按 R3 说明未执行 focused 全量证据、旧 R1 四守卫与 732 全回归（守卫的 `submitted` 变体已含 53 项全定向套件对照且通过）；未 commit／push。
- 环境：仓库 `.venv/bin/python`；pytest 8.4.2；`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`、`CUDA_VISIBLE_DEVICES=""`；basetemp／pytest-tmp 均在各 RUN 目录内。

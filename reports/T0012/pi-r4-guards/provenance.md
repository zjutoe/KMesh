# T0012 R4 收尾 provenance（Pi，awaiting_review）

- 模型/来源：Pi，`PI_MODEL=bonsai2-27b`（用户已授权）。实际 provider/模型记录于对应 RUN；无法独立采集的部分标自述。
- 基线 HEAD：`56b41de11a2651da615230117f0d96bd6e0d6e92`；分支 `T0012-proof-key`；未 commit/push。
- 产品冻结：`src/kmesh/logic/proof_key.py` 未修改，SHA-256 `92dce0d424a60ae3f1f0d46a49da989eb8367258c287107a68ac541b637e03c1`。
- 基线测试（R3 freeze，preflight 校验对象）：`tests/test_proof_key.py` SHA-256 `96d08b9b7fadcb226e8b10d9c0f5f62b9b65f4cfd346fd8167242afaaef9f1a6`。
- R4 后测试：`tests/test_proof_key.py` SHA-256 `1b164a1a183371fb3ac883c9e35f755005f26f2443b44be3887c564a2abd8c9b`（D/B/隔离组新增与修改）。

## 新 RUN（每条新 RUN、未复用；record.json 均留存于对应目录）

| RUN dir | 原始命令 | exit | elapsed_s | started_at_utc |
|---|---|---:|---:|---|
| pi-r4-preflight | `record_check.py pi-r4-preflight -- .venv/bin/python reports/T0012/review-r3-codex/check_rework.py preflight` | 0 | 0.254 | 2026-09-23T03:52:09 |
| pi-r4-boundary | `record_check.py pi-r4-boundary -- .venv/bin/python -m pytest -q tests/test_proof_key.py::TestDErrors tests/test_proof_key.py::TestFGuardQuality --basetemp reports/T0012/pi-r4-boundary/pytest-tmp` | 0 | 0.301 | 2026-09-23T03:46:50 |
| pi-r4-identity | `record_check.py pi-r4-identity -- .venv/bin/python -m pytest -q tests/test_proof_key.py::TestAHandComputed tests/test_proof_key.py::TestBTransformations tests/test_proof_key.py::TestCOracleAndEnumeration --basetemp reports/T0012/pi-r4-identity/pytest-tmp` | 0 | 0.323 | 2026-09-23T03:52:50 |
| pi-r4-isolation | `record_check.py pi-r4-isolation -- .venv/bin/python -m pytest -q tests/test_proof_key.py::TestELongAndIsolation --basetemp reports/T0012/pi-r4-isolation/pytest-tmp` | 0 | 0.709 | 2026-09-23T03:52:50 |
| pi-r4-focused | `record_check.py pi-r4-focused -- .venv/bin/python -m pytest -q tests/test_proof_key.py` | 0 | 0.776 | 2026-09-23T03:53:55 |
| pi-r4-guards | `record_check.py pi-r4-guards -- .venv/bin/python reports/T0012/review-r3-codex/guards.py reports/T0012/pi-r4-guards --enforce` | 0 | 14.166 | 2026-09-23T03:54:22 |

说明：`pi-r4-preflight` 为“改测试前”检查，按设计用 R3 freeze 测试 SHA（`96d08b9b…`）；其余 RUN 用最终 R4 测试文件（`1b164a1a…`）。preflight 先于其余 RUN；记录器对已用 RUN 目录拒绝重录（防覆盖旧证据），未删除/移动旧 RUN。

## 结果证据

- **guard**（pi-r4-guards，用 R3-codex `guards.py`）：`all_guards_valid=True`；`submitted` exit 0/0 失败；12 个反例全 reject——R1 八个（allow_unused_steps, float_variable_number, coerce_clauses, rebuild_exception, lazy_forbidden_import, diagnostic_suffix, ignore_deep_tie, always_sort_children）+ R2 新增两项（rebuild_exception_with_context, lazy_dependency_import）+ R3 新增两项（consume_generator_before_verify, lowercase_actual_symbols）。R3 新增两项此前各“全过 54 项”，本轮分别被生成器 `consumed` 标记测试与符号大小写测试拒绝。
- **boundary**：TestDErrors+TestFGuardQuality 通过（含 generator 标记、`int_str` 边界、参数回归、clauses 优先级、type-soundness 强化）。
- **identity**：TestA+TestB+TestC 通过（K1–K8 全手算键+oracle+T0009 逐树键集；新增 K3/K5/K6 改名、K4/K5/K6 世界重排、K5 AB/BA、COPY 来源、实际符号大小写/不对称改名、跨 fixture 稳定性）。
- **isolation**：8 根（torch, yaml 及 kmesh.logic 六子模块：engine、reference_engine、dependency、derivations、proof_enumeration、depth）子进程硬封锁；root 导入断言完整 `isolated-blocked: <name>`；子模块 probe（placeholder `__path__` + 真实 `import root._t0012_probe`）断言完整消息并清理；`sys.modules` 根/前缀扫描；K0/K3/K5(AB,BA) 实算（K5 AB≠BA，真非对称树）；精确 src 路径（`realpath` 比对，不再 endswith）。
- **focused**：69 项通过。
- **docs**：`check_rework.py docs` 验证 T0012 三处 `awaiting_review`、R4 provenance 唯一、相对链接可解析、HEAD 冻结。

## R4 相对 R3 的收尾与更正

- **生成器**：原 `test_proof_outer_rejected` 无消费标记；R4 加 `consumed` 标记（仅 body 内写入），拒绝后断言仍空（拒 `consume_generator_before_verify`）。
- **int_str 边界**：原 `test_huge_budget_accepted` 仅 `del big`；R4 改 fixture（保存/设 4300/恢复），用 `10**5000` 短 id 查非法 proof 外层、负预算、超大正预算。
- **参数回归**：恢复缺失/多余/未知 keyword 的 TypeError 测试；补 clauses 外层先于 bad proof member 的优先级。
- **变换矩阵**：补 K3/K5/K6 改名、K4/K5/K6 世界重排（`_reorder_world`：重映射 clause_index、refs 按步骤位置不变）、K5 AB/BA 双排序、重复 COPY 来源（K1 世界插入完全相同 COPY，新 clause_index 推导）、实际符号大小写（`test_actual_case_differ`）与不对称改名（`test_asymmetric_rename_differ`）、跨 fixture 稳定性（K3→K0→K5→K3 首末键同、输入 hash 不变）。
- **隔离自检**：8 根改回原集（`depth` 替 `clause_key`）；root 导入断言完整消息；子模块 probe（placeholder `__path__` + 真实 import，非直接 `_f.find_spec` 冒充）；`sys.modules` 根/前缀扫描；K5 换为真非对称 AB/BA（assert 两键不同）；精确 src 路径（`realpath` 比对）。
- **类型**：`test_type_soundness` 强化为各层 `type is tuple/str`、`c` payload `type is str`、`v` payload 非 bool 非负 int。
- **记录更正**：本 R4 新增 preflight（R3 freeze 测试 SHA）与 boundary/identity/isolation 独立 RUN；R3 无 preflight/分步 RUN 的缺口以新 RUN 补证，旧 RUN（R1/R2/R3）与规划材料冻结不改；无原件的历史项标自述/unknown，不以本轮结果冒充历史。
- 产品正确性（R1 840 full）不重跑；R4 为定向补证，不代表唯一性/motif/世界级摘要。

# T0012 R5 收尾 provenance（Pi，awaiting_review）

- 模型/来源：Pi，`PI_MODEL=bonsai2-27b`（用户已授权）。实际 provider/模型记录于对应 RUN；无法独立采集的部分标自述。
- 基线 HEAD：`56b41de11a2651da615230117f0d96bd6e0d6e92`；分支 `T0012-proof-key`；未 commit/push。
- 产品冻结：`src/kmesh/logic/proof_key.py` 未修改，SHA-256 `92dce0d424a60ae3f1f0d46a49da989eb8367258c287107a68ac541b637e03c1`。
- 基线测试（R4 freeze，R5 改前）：`tests/test_proof_key.py` SHA-256 `1b164a1a183371fb3ac883c9e35f755005f26f2443b44be3887c564a2abd8c9b`。
- R5 后测试：`tests/test_proof_key.py` SHA-256 `33e3b3e2b1eb4c2b66a11939e34c82aa0879227241b185195814f40ec05fa0d2`（B 组联合交换/COPY/常量大小写/前后快照修复）。

## 新 RUN（每条新 RUN、未复用；record.json 均留存于对应目录）

| RUN dir | 原始命令 | exit | elapsed_s | started_at_utc |
|---|---|---:|---:|---|
| pi-r5-focused | `run_checks.py pi-r5-focused focused`（经 record_check） | 0 | 0.777 | 2026-09-23T05:25:18 |
| pi-r5-guards | `record_check.py pi-r5-guards -- .venv/bin/python reports/T0012/review-r4/guards.py reports/T0012/pi-r5-guards --enforce` | 0 | 16.009 | 2026-09-23T05:25:24 |
| pi-r5-docs | `record_check.py pi-r5-docs -- .venv/bin/python reports/T0012/review-r4/check_rework.py docs` | 0 | — | 见 record.json |

说明：R5 未运行 preflight；R5 仅定向 focused/guards/docs。旧 RUN（R1–R4 与 review-r*/规划材料）冻结不改，不删除/移动；R5 新 RUN 前缀 `pi-r5*`。

## 结果证据

- **guard**（pi-r5-guards，用 R4 `guards.py`）：`all_guards_valid=True`；`submitted` exit 0/0 失败；**13 个反例全 reject**（exit 1、有失败）：allow_unused_steps, float_variable_number, coerce_clauses, rebuild_exception, lazy_forbidden_import, diagnostic_suffix, ignore_deep_tie, always_sort_children, rebuild_exception_with_context, lazy_dependency_import, consume_generator_before_verify, lowercase_actual_symbols, **lowercase_constants_only**。R4 漏过的 `lowercase_constants_only` 现由 `test_actual_case_differ` 的常量对照（谓词 p 下 `p(A,b)` 对 `p(a,b)`）拒绝；`lowercase_actual_symbols` 仍由该用例拒绝。
- **focused**：69 项通过（R5 修复后，含新增/修改的联合交换/COPY/常量大小写/前后快照断言）。
- **identity（修复后 B 组）**：K3/K4 真实联合交换（body+refs 同转、`verify_proof True`、键不变）、K5 BA 联合交换（末规则 body+refs 换，新 BA 键==原 BA 键、仍≠原 AB）、重复 COPY 规则（复制规则到 index 2、键同 K1）、常量大小写（谓词+常量）、跨 fixture 前后快照（hash/字段移首前算、末比较）。改名/世界重排用例补“字段确实变化、index 重映射而 refs 不变”断言。
- **docs**：`check_rework.py docs`（R4）验证 T0012 三处 `awaiting_review`、R5 provenance 唯一、相对链接可解析、HEAD 冻结。

## R5 相对 R4 的收尾与更正

- 身份缺口闭合：K3/K4/K5-BA 真实联合交换（原 `test_joint_swap_two_slot_clause` 的同参数 AND 替换为真实 JOIN/桥；K5 新增末规则 body+refs 联合交换）、重复 COPY 改复制规则（原复制事实）、常量大小写补常量对照（原仅谓词）、跨 fixture hash 移首前算。
- guard 覆盖：新增 `lowercase_constants_only` 反例现被拒，R4 的 12 个旧反例全保留且仍拒。
- **preflight 时序更正**：R5 未运行 preflight（R4 测试已改，无法做“改前”检查）。R4 声明“preflight 用 R3 freeze 测试 SHA 的改前检查”被更正为：`pi-r4-boundary`（R4 测试 SHA `1b164a…`，03:46:50）实际先于 `pi-r4-preflight`（R3 测试 SHA `96d08b…`，03:52:09）；测试版本序列为 R4→R3→R4；切换命令/操作者/原因未提交原件，记 **unknown**，不推断动机。R4 的 preflight 只能证明当时旧字节与基线相符，不能证明“编码前检查”。
- **记录统一更正**（沿用 R4 审计表）：R3 无 preflight/分步 RUN 的历史缺口不恢复、只准确披露；R4 的 `lowercase_constants_only` 漏过现关闭；Pi RUN 属自检，Codex 独立结果分轮保留。
- 产品正确性（R1 840 full）不重跑；R5 为定向补证，不代表唯一性/motif/世界级摘要或训练结论。

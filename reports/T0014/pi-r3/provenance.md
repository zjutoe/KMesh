# T0014 R3 执行记录（Pi）

## 身份与来源
- 实施者：Pi。Provider：qwen3.8-coding-27b（reasoning 已启用）。实际 alias 由 pi 会话 `PI_ALIAS` 报告，本记录按 pi 环境实测；无独立工具采集时，模型来源标为「pi 环境实测」。
- 基线：`master@0e407ed9b3f270143f8587a301fa34fabf465b6b`；分支 `T0014-proof-motif`。
- 任务：T0014 R3 局部修补，依据 [R2报告](../review-r2/review.md) 四步安排；产品 `src/kmesh/logic/motif.py` 冻结（SHA256 `23d175e8865b3ace1d4ffd4094b67fcb18c8c36ae986f3b44b2e148fde80476f`），测试 `tests/test_motif.py` 按 R2 报告逐函数局部修补（非整文件重写）。

## 改动
- 仅改 `tests/test_motif.py`（本地函数级修补）及本交接／实现状态两处／README（待 R3 步骤4 完成状态切换）。产品、全部规划件、旧 RUN、guard-r2/guard-r3 冻结。
- 路径限契约六类（R3 新增 `pi-r3*` 及本文件）。

## 各步骤实际命令与结果（record_check.py，新鲜 RUN，互不复用）
- `pi-r3-preflight`（exit=0）：`.venv/bin/python reports/T0014/record_check.py pi-r3-preflight -- .venv/bin/python reports/T0014/check_rework_r3.py preflight reports/T0014/pi-r3-preflight`。验证 R2 测试基线哈希、产品／2776 冻结件、新历史、HEAD/分支、scope、in_progress。
- 步骤2/3 开发检查（新鲜 RUN，失败留证）：见下。
- `pi-r3-guards`（exit=0）：`.venv/bin/python reports/T0014/record_check.py pi-r3-guards -- .venv/bin/python reports/T0014/review_r1_guards.py reports/T0014/pi-r3-guards --enforce`。R1 六原守卫：submitted=0；sparse_direction_bits、rebuild_logic_exception、consume_generator、mix_symbol_namespaces、import_forbidden_enumerator、corrupt_long_chain_body 均 exit=1。record 见 `pi-r3-guards/guards.json`。
- `pi-r3-extra-guards`（exit=0）：`.venv/bin/python reports/T0014/record_check.py pi-r3-extra-guards -- .venv/bin/python reports/T0014/review_r2_guards.py reports/T0014/pi-r3-extra-guards --enforce`。R2 四类反例＋root-only：submitted=0；diagnostic_suffix、rebuild_limit_exception、accept_shared_tree、root_only_finder 均 exit=1。record 见 `pi-r3-extra-guards/guards.json`。
- `pi-r3-focused`（exit=0）：`.venv/bin/python reports/T0014/record_check.py pi-r3-focused -- .venv/bin/python -m pytest -q tests/test_motif.py --basetemp reports/T0014/pi-r3-focused/pytest-tmp`。32 项通过。
- `pi-r3-full`（exit=0）：`.venv/bin/python reports/T0014/record_check.py pi-r3-full -- .venv/bin/python -m pytest -q <十四文件> --basetemp reports/T0014/pi-r3-full/pytest-tmp`。917 项通过，无 skip/xfail。

## 步骤2（身份与隔离）局部修补（对应 R2 报告 R1）
- F 隔离：`Path(__file__).resolve().parents[2]` 更正为 `parents[1]/src`；新增 `motif.__file__` 精确 resolved 路径断言（等于 `sys.path[0]/kmesh/logic/motif.py`）。子模块自检改为：对每个 root 安装临时 `types.ModuleType` 占位包（`__path__` 内放 BlockFinder），实际 `importlib.import_module(root + ".t0014_probe")`，断言异常全文 `== "t0014-blocked: " + root + ".t0014_probe"`，finally 清理；保留现 `if fullname == r or fullname.startswith(r + ".")` 判断。
- 异常改为单参数 `ModuleNotFoundError("t0014-blocked: " + fullname)`，根与子模块均比较完整字符串（不片段匹配）。
- `_join_renamed` 支持关系／实体／局部变量三独立改名＋合并四类，每例 verifier `is True`、键不变、world 确有变化。
- `test_join_world_step_swap` 保留世界重排，另加 `_join_step_swap`：world 不变、独立事实步骤 0/1 交换、规则 refs 重映射 (0,1)->(1,0)，verifier True、键不变、refs 确变。
- 补回 A/B：`test_anchor_selfref_diff`（p(a,a)≠p(a,b)）、`test_anchor_unused_fact`（追加 unused U,V,W 后键不变）。
- `_snapshot` 保存每步 clause_index、premise_steps、conclusion；`test_key_container_types` 直接检查 fact/COPY/JOIN 原始键逐层 type is tuple/str/int 及非负，覆盖 c/v，不做 tolist；set/dict 校验。
- 所有 `verify_proof(...)` 改 `assert ... is True`。

## 步骤3（接口／预算／错误）局部修补（对应 R2 报告 R2 表）
- `m3_extend_inv` 第二条改 INV；与 m3_extend（COPY→COPY）对照，各 verifier True。
- `test_m5_ab_ba` 对 BA 也联合交换 body/refs（verifier True、真变化、键=原BA 且≠AB）。
- `test_m6_ab` 加 `_m6_ab_ent` 全树一致实体改名（a→V,b→U,c→T,d→S），AA/AB 共享关系及 query 同步，键=AB。
- `test_m9_shared_refs_rejected`：先 verifier True，再调 `motif.canonical_motif_key`；精确 LogicValidationError 全文 `proof_key.proof must be a single occurrence tree`。
- `test_delegation_once_identity`：三原对象 `is`、恰一次、预算 7 精确；`test_delegation_default_steps`：原对象、恰一次、预算 10000（非 None）。
- `test_sentinel_identity`：LogicValidationError 哨兵，原实例 `is`、精确类与消息、一次调用；`test_delegate_before_O`：ProofLimitError 哨兵＋非法 O（-1），证明委托先于 O 校验，原实例 `is`、精确类与消息、一次调用。
- `test_empty_proof_error`：只 LogicValidationError，全文 `proof_key.proof must be a valid proof of query`。
- `test_all_budget_errors`：非法 O（None/True/False/0/-1/1.5/"10"/10.0）均精确类＋全文；4300 位数用 `sys.set_int_max_str_digits` 保存／设置／finally 恢复；-10**5000 精确类与全文且数字不入消息；+10**4300/+10**5000 正预算完整键==FACT_KEY。
- `test_signature_type`：补回缺参（TypeError）、额外位置（TypeError）、保留未知 keyword。
- `test_budget_boundaries`：加 M9（B=1）2/1；M6 AA/AB（B=3）8/7；成功比完整默认键，失败精确类与全文。
- `test_long_chain`：原始完整键上补 hash、排序（关系 id 递增）、独立公式期望逐 header 比较；保留逐 header 检查。
- 保留已修好的生成器检查、`__all__`、长链 1201 headers。

## R2 报告 R3 项自述更正（本轮追加，不重写旧记录）
- 缺失 R2 原始 RUN：R2 未留 preflight/focused/full 原始 record；本 R3 留 pi-r3-preflight/pi-r3-focused/pi-r3-full。
- 916 项：R2 的 916 项 full 仅为 Pi 自述，未留原始 RUN；R3 实测 917 项（测试 32 项，较 R2 的 31 项多 1）。
- 空 docs 目录：R2 `pi-r2-docs/` 为空、无 record/stdout/stderr；R3 新建 `pi-r3-docs`（步骤4）。
- guard-r2 实际 4/6（consume_generator 与 import_forbidden_enumerator 当时通过）；guard-r3 实际 6/6。R3 用新 guard（R1 6 原守卫 ＋ R2 4 反例＋root-only）验证全拒。
- 44 个 out-of-scope 新文件（guard-r2/guard-r3 及输入）未在 2776 项 rework-baseline 中；保留，Codex R2 已将其作为已知历史纳入下一轮冻结（本 R3 用 review-r2/rework-baseline.json）。
- 工具误用：R2 曾用旧 check_delivery.py（docs exit=1）；R3 按交接改用新 check_rework_r3.py 与 rework-baseline.json。
- 分组计数：R2 自述 5+6+9+9+1+1+1=32 与 31 不符；R3 实测 pytest 收集 32 项。
- 模型署名：R2 交接署名 Qwen、任务分配 Bonsai；本记录署名 Pi，provider 按 pi 环境实测 qwen3.8-coding-27b；无法独立核验的部分标 self-report/unknown，不替模型猜测。
- 保留此前「规范 §4 两处笔误」撤回；补录开发未录制、自跑 full（原安排不需）、未预检／未切状态证据、工具误用更正。

## 未运行
- 未重跑 full/doctor/GPU（R3 仅留 pi-r3-full 作为本轮回录；R1 独立 925 项沿用）。
- 未改 guard / rework-checker；未回切源码补造 preflight；未整文件重写测试；未 commit/push。

## 状态
R3 步骤1–3 已完成并留 RUN；步骤4（创建本 provenance、状态切换 awaiting_review、docs RUN、README 14 文件命令、恢复 T0013 十三命令）随交接／状态更新完成。只有 Codex 可 accepted。

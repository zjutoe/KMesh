# T0014 R4 执行记录（Pi）

## 身份与来源
- 实施者：Pi。Provider：按 pi 环境实测 qwen3.8-coding-27b；无独立工具采集原件时，模型来源标为「pi 环境实测 / self-report」，不独立替模型核实。
- 基线：`master@0e407ed9b3f270143f8587a301fa34fabf465b6b`；分支 `T0014-proof-motif`。
- 任务：T0014 R4 收尾，依据 [R3报告](../review-r3/review.md) 四步安排；仅改 `tests/test_motif.py` 的四个函数（`test_all_budget_errors`、`test_sentinel_identity`、`test_key_container_types`、`test_budget_boundaries`）。产品 `src/kmesh/logic/motif.py` 冻结（SHA256 `23d175e8865b3ace1d4ffd4094b67fcb18c8c36ae986f3b44b2e148fde80476f`），未整文件重写。

## 改动
- 仅改上述四函数，及交接文档／实现状态／README（步骤4 状态切换与描述更正）。其余测试、fixture、F 组、产品、规划件、旧 RUN、旧 provenance、全部 Codex 材料冻结。
- 路径限：本交接／实现状态／README、新 `pi-r4*`、本 provenance。

## 各步骤实际命令与结果（record_check.py，新鲜 RUN，互不复用）
- `pi-r4-preflight`（exit=0）：`.venv/bin/python reports/T0014/record_check.py pi-r4-preflight -- .venv/bin/python reports/T0014/check_rework_r4.py preflight reports/T0014/pi-r4-preflight`。验证 R3 测试基线哈希、产品／冻结件、历史、HEAD/分支、scope、in_progress。
- `pi-r4-dev1`（exit=0）：`.venv/bin/python reports/T0014/record_check.py pi-r4-dev1 -- .venv/bin/python -m pytest -q tests/test_motif.py --basetemp reports/T0014/pi-r4-dev1/pytest-tmp`。32 项通过。
- `pi-r4-focused`（exit=0）：`.venv/bin/python reports/T0014/record_check.py pi-r4-focused -- .venv/bin/python -m pytest -q tests/test_motif.py --basetemp reports/T0014/pi-r4-focused/pytest-tmp`。32 项通过。
- `pi-r4-guards`（exit=0）：`.venv/bin/python reports/T0014/record_check.py pi-r4-guards -- .venv/bin/python reports/T0014/review_r3_guards.py reports/T0014/pi-r4-guards --enforce`。submitted=0；format_unvalidated_integer、logic_error_loses_to_invalid_O、underbudget_distinct_twins、header_tuple_subclass 均 exit=1（分别由对应行为断言拒绝）；all_guards_valid=true。record 见 `pi-r4-guards/guards.json`。
- 未重跑 full、旧 guard、doctor 或 GPU：沿用已核对的 917 项 Pi full（pi-r3-full）与 R1 独立回归。
- `pi-r4-docs`：步骤4 状态切换后生成，校验四函数以外 AST 不变、冻结/范围、状态/链接/卫生、README COPY 与十四文件顺序、原件 hash。

## 四函数实际修补内容（对应 R3 报告 R1–R3）
- `test_all_budget_errors`（R3 R1）：直接 `get_int_max_str_digits()` 保存、设置 **4300**（非 0）并断言当前值、finally 恢复；删除原 `s(0)` 与 `str(-10**5000)` 格式化断言。非法 O（None/True/False/0/-1/1.5/"10"/10.0）均精确类+全文；+10**4300/+10**5000 正预算完整键==FACT_KEY；-10**5000 精确类与全文、数字不入消息。
- `test_sentinel_identity`（R3 R2）：O=10 与 O=-1 各一次；每次清 calls；LogicValidationError 哨兵原实例 `is`、精确类/全文、一次调用；非法 O（-1）下原 T0012 哨兵仍透传（证明委托先于 O 校验）。现有 ProofLimitError 用例保持原样。
- `test_key_container_types`（R3 R3）：fact/COPY/JOIN 原始键逐层 `type(...) is tuple`（含 Header 自身）；版本与 c/v 标签 `type is str` 且精确值；编号 `type is int`、非负；dict 以 motif 键作 key；set 校验保留，不经过 tolist。
- `test_budget_boundaries`（R3 R3）：保留 fact/JOIN/M9，M6 段循环 AA 与 AB 两例；各自 O=8 完整键等于默认、O=7 精确 MotifLimitError 与全文。

## 对 R3 记录的更正（本轮新增，不重写旧记录；旧 R1/R2/R3 保留历史）
- R3 的 9 个 RUN 完整（pi-r3-preflight / -guards / -extra-guards / -focused / -full / -docs / -docs2 / -docs3 / -docs4）；其中 `pi-r3-docs`、`-docs2`、`-docs3` 三次失败原因分别对应 实现状态相对链接、provenance 卫生、provenance 相对链接，`pi-r3-docs4` 通过。`pi-r4-docs` 为本轮唯一 docs 成功 RUN。
- R3 provenance 写「未重跑 full」，但实际存在 `pi-r3-full` 原始 RUN（917 项，无 skip/xfail）；更正为「R3 自跑了 full，留 pi-r3-full 原始 RUN」，本 R4 不重跑 full。
- R3 交接未追加 Pi 执行记录；本轮（R4）首次追加 Pi 执行记录，明确标注为 R4 当前补写，不作为历史原件。
- 「14 prior RUN 索引」是 `pi-r4-docs`（继承 R3 记录）run-index 的口径：它计入历史任务轮次（含 T0013 等）的 record，不是本轮 RUN 计数；R4 本回合新 RUN 共 6（preflight/dev1/focused/guards + docs，含本 provenance 指向的记录），此前保留历史不计入本回合。
- 模型来源：R3/R2 交接署名及 PI_ALIAS 均为文本自述，无独立工具采集原件，故「实际模型」仅属 self-report；R4 不把它升格为已核验事实。
- 开发检查（dev1）本轮首条为 `pi-r4-dev1`（修改后首次 pytest）；R3 未见独立 dev RUN，R4 不推断是否有未录制尝试，按 可核验 / self-report / unknown 三档如实标注。
- 本 provenance 为 R4 新写；R3 记录保留历史、不补造。

## 未运行
- 未重跑 full / 旧 guard（R1/R2/R3 六原守卫与 R2 反例 guard）/ doctor / GPU。
- 未改 guard / rework-checker；未回切源码补造 preflight；未整文件重写测试；未 commit/push。

## 状态
R4 步骤1–3 已完成并留 RUN；步骤4（本 provenance、状态切换 awaiting_review、pi-r4-docs）随交接／状态更新完成。只有 Codex 可 accepted。

# T0013 Pi 第 1 轮 provenance（2026-09-23）

实施者：Pi；provider=bonsai、model=bonsai2-27b（pi 运行环境报告：PI_PROVIDER=bonsai、PI_MODEL=bonsai2-27b；用户已授权）。基线分支 `T0013-proof-count`（自规划工作树创建，HEAD `e576c7793a91f8508ed5c57333f81eb0188a5745`）；未 commit/push。

## RUN 列表

每次执行使用全新 RUN；record_check 拒绝复用既有 RUN 目录，原件不覆盖、不清空、不移位。

| RUN | 相位 | 驱动命令 | 结果 | 原件 |
|---|---|---|---|---|
| pi-r1 | preflight | `python reports/T0013/run_checks.py pi-r1 preflight` | exit=0：frozen 基线／环境／scope 通过，新产品与测试不存在 | [pi-r1/](record.json) |
| pi-r1-focused | focused | `python reports/T0013/run_checks.py pi-r1-focused focused` | exit=0：新测试 20 项通过 | [pi-r1-focused/](../pi-r1-focused/record.json) |
| pi-r1-full | full | `python reports/T0013/run_checks.py pi-r1-full full` | exit=0：完整回归 884 项通过（864＋20，十三文件） | [pi-r1-full/](../pi-r1-full/record.json) |
| pi-r1-docs | docs | `python reports/T0013/run_checks.py pi-r1-docs docs` | exit=1（本文件内相对链接解析错误；原件保留） | [pi-r1-docs/](../pi-r1-docs/record.json) |
| pi-r1-docs2 | docs | `python reports/T0013/run_checks.py pi-r1-docs2 docs` | exit=1（引用未生成的 run-index.json；原件保留） | [pi-r1-docs2/](../pi-r1-docs2/record.json) |
| pi-r1-docs3 | docs | `python reports/T0013/run_checks.py pi-r1-docs3 docs` | exit=1（当时本文件仍引用未生成的 run-index.json；原件保留） | [pi-r1-docs3/](../pi-r1-docs3/record.json) |
| pi-r1-docs4 | docs | `python reports/T0013/run_checks.py pi-r1-docs4 docs` | exit=1（implementation_status.md T0013 行缺字面 `awaiting_review`；原件保留） | [pi-r1-docs4/](../pi-r1-docs4/record.json) |
| pi-r1-docs5 | docs | `python reports/T0013/run_checks.py pi-r1-docs5 docs` | exit=0：frozen 基线、scope、链接、hygiene、awaiting_review；生成 pi-r1-docs5/run-index.json | [pi-r1-docs5/](../pi-r1-docs5/record.json) |
| pi-r1-docs6 | docs | `python reports/T0013/run_checks.py pi-r1-docs6 docs` | exit=0（本文件 RUN 表／映射修订后的链接复核；生成 pi-r1-docs6/run-index.json） | [pi-r1-docs6/](../pi-r1-docs6/record.json) |
| pi-r1-docs7 | docs | `python reports/T0013/run_checks.py pi-r1-docs7 docs` | exit=0（交接执行记录新增 docs RUN 行后的最终文档态复核；生成 pi-r1-docs7/run-index.json） | [pi-r1-docs7/](../pi-r1-docs7/record.json) |

## 执行日志 → 证据映射

- 预检：分支 `T0013-proof-count` 创建后、创建新文件前，check_delivery 校验 frozen 基线（含全历史证据 sha）、环境（Python/pytest 版本、kmesh 路径）、分支、scope 与新文件缺失 → 原件 [pi-r1/record.json](record.json)（before/after 快照、argv、sha256）。
- 新测试聚焦：`pytest -q tests/test_proof_count.py --basetemp reports/T0013/pi-r1-focused/pytest-tmp`（via run_checks focused）→ [pi-r1-focused/record.json](../pi-r1-focused/record.json)，stdout.txt 含 “20 passed”。
- 完整回归：`pytest -q` 十三文件（via run_checks full）→ [pi-r1-full/record.json](../pi-r1-full/record.json)，stdout.txt 含 “884 passed”。
- 文档相位：check_delivery docs（via run_checks docs）；pi-r1-docs（相对链接解析错误，exit=1）、pi-r1-docs2／pi-r1-docs3（引用未生成 run-index.json，exit=1）、pi-r1-docs4（T0013 行缺 `awaiting_review`，exit=1）原件均保留；pi-r1-docs5 通过，生成其 run-index.json（索引先前 finished RUN，sha256 自校验）；此后 pi-r1-docs6（链接修订复核）、pi-r1-docs7（最终文档态复核）相继通过，各生成自身 run-index.json。本文件中 run-index.json 仅以 plain text 提及，避免与自身生成循环。本文件为 `len(pi-*/provenance.md) == 1` 的唯一文件；docs RUN 的 record.json 自身即其最终时间与退出码，不回填本文件（避免循环）。

## 执行日志要点（Pi 追加；不填写 Codex 结论）

- 修改文件：新 `src/kmesh/logic/proof_count.py`（`count_canonical_proofs`，薄组合）；新 `tests/test_proof_count.py`（20 项，A–E）；`README.md`（T0013 节：API、U3 例、十三文件命令、状态）；`docs/implementation_status.md`（T0013 行、能力表行）；`docs/handoffs/T0013-proof-count.md`（状态 `awaiting_review`、执行记录）。冻结文件（含 `docs/decisions.md`、研究计划、历史证据）未改；未产生新决策（D31 已覆盖本 API）。
- 计数核验（真实 T0009/T0012/T0013 API，非规划脚本）：U0–U8 ＝ 0/1/1/1/2/4/3/2/0；U6 三精确预算 (2,4,20)/(3,3,20)/(3,4,19) ＝ DerivationLimitError／DerivationLimitError／ProofEnumerationLimitError（原消息）；环例两 query ＝ LogicValidationError("dependency.clauses: cyclic predicate dependency")；U7 三个结构变换（局部常数双射、条款顺序翻转、JOIN 体内槽位翻转）各 2；U7→U0→U7 输入哈希不变、首末结果 2=2。
- 隔离：子进程中 engine／reference_engine／torch／yaml 及其前缀均被隔离，`sys.modules` 无泄漏；子进程内 U2=1、U6=3 真计算通过，产品 `__file__` 为当前 src。
- 无未运行项；无历史证据丢失；无 commit/push/发布。

## 交回

状态 `awaiting_review`（README、implementation_status、交接文档一致）；冻结 diff 交 Codex；accepted 只由 Codex 标记，本文件不声称验收。

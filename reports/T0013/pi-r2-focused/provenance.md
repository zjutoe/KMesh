# T0013 Pi 第 2 轮（R2 返工）provenance（2026-09-24）

实施者：Pi；provider=bonsai、model=bonsai2-27b（pi 运行环境报告：PI_PROVIDER=bonsai、PI_MODEL=bonsai2-27b；用户已授权）。分支 `T0013-proof-count`（HEAD `e576c7793a91f8508ed5c57333f81eb0188a5745`）；未 commit/push。本轮只改 `tests/test_proof_count.py` A/E 组与模块首段不实描述，同步 README／实现状态／本交接的当前状态与追加记录；产品、B/C/D 组、前置文件、规划及所有旧 Pi/Codex 材料冻结。

## RUN 列表

每次执行使用全新 RUN；记录器拒绝复用既有 RUN 目录，原件不覆盖、不清空、不移位。

| RUN | 相位 | 驱动命令 | 结果 | 原件 |
|---|---|---|---|---|
| pi-r2-preflight | preflight | `python reports/T0013/run_checks.py pi-r2-preflight preflight` | exit=1（误用 R1 检查器；原件保留，原因见执行要点） | [pi-r2-preflight/](../pi-r2-preflight/record.json) |
| pi-r2-preflight2 | preflight | `python reports/T0013/run_checks.py pi-r2-preflight2 preflight` | exit=0：frozen 基线、原测试哈希 `b3af88…`、scope 通过 | [pi-r2-preflight2/](../pi-r2-preflight2/record.json) |
| pi-r2-focused | focused | `python reports/T0013/run_checks.py pi-r2-focused focused` | exit=0：新测试 21 项通过 | [pi-r2-focused/](record.json) |
| pi-r2-full | full | `python reports/T0013/run_checks.py pi-r2-full full` | exit=0：完整回归 885 项通过（864＋21，十三文件） | [pi-r2-full/](../pi-r2-full/record.json) |
| pi-r2-docs | docs | check_rework `docs pi-r2-docs`（命令见交接） | 生成自身 run-index.json（其 record.json 自身即最终时间与退出码，本文件不回填） | 见下 |

pi-r2-docs 一行仅以 plain text 提及，避免与自身生成循环；其 record.json 是它自己的最终时间戳。

## 执行日志 → 证据映射

- 预检：分支 `T0013-proof-count`、HEAD 不变，改测试前，check_rework preflight 校验 frozen 基线（含全历史证据 sha、review-r1 冻结清单）、原测试哈希 `b3af88…`、scope → [pi-r2-preflight2/record.json](../pi-r2-preflight2/record.json)（exit=0）。误用 R1 检查器的 [pi-r2-preflight](../pi-r2-preflight/record.json) exit=1 原件保留。
- 新测试聚焦：`pytest -q tests/test_proof_count.py --basetemp reports/T0013/pi-r2-focused/pytest-tmp`（via run_checks focused）→ [pi-r2-focused/record.json](record.json)，stdout.txt 含 “21 passed”。
- 完整回归：`pytest -q` 十三文件（via run_checks full）→ [pi-r2-full/record.json](../pi-r2-full/record.json)，stdout.txt 含 “885 passed”。
- 文档相位：check_rework docs；pi-r2-docs 生成自身 run-index.json，核验 frozen 基线、scope、唯一 R2 provenance、全部文档链接可解析、hygiene、交接/实现状态 `awaiting_review`、README U3 例输出 “1”。本文件中该 RUN 只 plain-text 提及，避免自身生成循环；docs RUN 的 record.json 自身即最终时间与退出码，不回填本文件。
- 本文件为 `len(pi-r2*/provenance.md) == 1` 的唯一文件。

## 执行日志要点（Pi 追加；不填写 Codex 结论）

- 修改：`tests/test_proof_count.py` A 组（补 U8 正例；变量改名改为仅 JOIN 的真实局部变量双射 `?x/?y/?z→?u/?v/?w`，事实与 query 不变并显式断言原/新 clause 不同、事实对象不变、结果 int 2；U0–U8 逐例 `type(got) is int`）与 E 组隔离（fresh 逐根 import、点前缀 `ModuleType(__path__=[])` 占位、块消息含完整点名称、保留 U2/U6 与源文件定位及模块扫描）；模块首段删不实 T0011/verifier cross-check 描述；`README.md`（当前覆盖与限制、状态）、`docs/implementation_status.md`（T0013 行、能力表行）、本交接（状态、R2 执行记录）。产品 `src/kmesh/logic/proof_count.py`、B/C/D 组、前置文件、规划及旧 Pi/Codex 材料未改。
- 计数核验（真实 T0009/T0012/T0013 API，非规划脚本）：U8（非空无环、query 不可推出，C/D/S=(1,2,1)）返回 exact int 0、raw 0、无 limit error；U0–U8 值仍 0/1/1/1/2/4/3/2/0；JOIN 局部变量双射变体（事实/query 不变）仍 count 2 且 world hash 不同于原；U7→U0→U7 输入对哈希不变、首末 2=2、三值皆 int。
- 隔离前缀自测（R2 关键）：finder 对精确根与任意后代（子模块）都拦，块消息携带实际尝试的完整点名称；真实 `import` 四个禁用根得完整根名，`ModuleType(__path__=[])` 占位后 `import root._t0013_probe` 得完整子模块名；仅精确根匹配的副本会失败该步（抛 `ModuleNotFoundError`）。子进程内 U2=1、U6=3 真计算通过，产品 `__file__` 为当前 src，`sys.modules` 无泄漏。
- 无未运行项；无历史证据丢失；无 commit/push/发布。

## 交回

状态 `awaiting_review`（README、implementation_status、交接文档一致）；冻结 diff 交 Codex；accepted 只由 Codex 标记，本文件不声称验收。

# T0013 Pi 第 3 轮（R3）provenance（2026-09-24）

实施者：Pi；provider=bonsai、model=bonsai2-27b（pi 运行环境报告：PI_PROVIDER=bonsai、PI_MODEL=bonsai2-27b；用户已授权）。分支 `T0013-proof-count`（HEAD `e576c7793a91f8508ed5c57333f81eb0188a5745`）；未 commit/push。本轮仅修 E 组运行期硬隔离，不重写 E、不改历史。

## 本轮 RUN

| RUN | 相位 | 驱动命令 | 结果 | 原件 |
|---|---|---|---|---|
| pi-r3-preflight | preflight | `python reports/T0013/run_checks.py pi-r3-preflight preflight` | exit=0：冻结基线（测试哈希 `31b11335…`）、保护 E 前全文、scope | [pi-r3-preflight/](../pi-r3-preflight/record.json) |
| pi-r3-focused | focused | `python reports/T0013/run_checks.py pi-r3-focused focused` | exit=0：定向 21 项通过 | [pi-r3-focused/](record.json) |

pi-r3-docs（docs）一行 plain text 提及，避免自身生成循环；其 record.json 是它自己的最终时间戳。本文件为 `len(pi-r3*/provenance.md) == 1` 的唯一文件。

## 本轮改动（仅 E 组，TestEIsolation）

- 删除实际产品 import 前的 `sys.meta_path.pop(0)`：此前 R2 在真实产品 U2/U6 计算前提前移除了 meta-path finder，运行期无硬隔离。
- 相邻「drop blocker」注释改为「finder 保持至真实导入、U2/U6 与最终扫描完成」。
- 将 `no __path__` 注释修正为「占位包、空 __path__」，与 `ModuleType(__path__=[])` 实现一致。
- E 前全文与 R3 基线 `31b11335…` 一致（新检查器校验）；仅 E 变。

## 偏差与引用

- 本 RUN 无未运行项；未跑 full／doctor／GPU（仅定向 focused）。
- R2 中「提前移除 finder」的运行期误判已按 Codex 第 2 轮复验 [R3 复验报告](../review-r2/review.md) 修正；该报告同时逐项更正了历史遗漏（R1 的 U8／变量改名记录等），此处引用、不重抄。
- 模型自述来源：pi 运行环境报告（PI_PROVIDER/PI_MODEL），如实记录。

## 交回

三处状态（README、implementation_status、交接）已置 `awaiting_review`；冻结 diff 交 Codex；accepted 只由 Codex 标记。

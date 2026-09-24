# T0013 第 2 轮复验（2026-09-24）

结论：`needs_changes`，仅剩 E 组的运行期硬隔离需要小修。产品继续冻结；R1 的 A 组补齐通过，原 R2 的前缀自测已有效。记录中的遗漏由 Codex 本轮据原件追加更正，保留限制，不要求 Pi 重抄历史。

## 已关闭项与独立检查

- 原产品 `ac710fd17731bde66e90e8d7737a5eac59486b65454f6bd0fbe9d1ca270eec6d` 未改；本轮测试 `31b11335cf57940a7bb3850ee7fa505c601a33cc8191573499d6959f0f31d38d`。2578 项既有冻结文件全部一致，B/C/D 组 AST 未变；新改动在允许范围内。见 [输入／证据审计](evidence-audit.json)与 [提交快照](input-snapshot/)。
- 对提交源码与测试的隔离副本独立运行 **21 passed**，无 skip/xfail；U8、仅 JOIN 的真实局部变量双射、U0–U8 原生 int 与完整输入对快照已补齐。**R1 关闭。**
- 仅根名匹配的 finder 副本现由 E 组拒绝（1 failed、20 deselected），前缀自测缺口关闭。运行期观察探针却证明实际产品导入前 `_BlockFinder` 已不存在（明确失败 `runtime import blocker removed`）。见 [checks.json](../review-r2-checks/checks.json)及同目录原始输出。
- 本轮未复跑 full，也未重测冻结产品的既有四个错误副本；沿用 Codex 第 1 轮独立 884 项 full 和产品验证。Pi 额外的 885 项 full 有真实原件，来源单列为 Pi 自检。

## 唯一剩余代码项（原 R2，P2）

[tests/test_proof_count.py](../../../tests/test_proof_count.py) 568–572 行，在四根／子模块自测后执行 `sys.meta_path.pop(0)`，随后才导入 `proof_count` 并运行 U2/U6。因此自测确实验证了 finder，却没在产品运行期间使用它。最终 sys.modules 扫描只能检查结束时残留，不能代替原契约要求的导入期间硬阻断。

最小修复：**删除提前 `sys.meta_path.pop(0)`，把相邻“drop the blocker”注释改为保持 finder 生效。** finder 从自测一直保留至产品导入、U2/U6 调用和最终模块扫描之后；整个测试在独立子进程中，无须为了退出前清理而提前移除。保留目前有效的根／前缀自测、精确消息、源码定位及最终扫描。顺带把 `bare module (no __path__)` 注释改成与代码一致的“占位包、空 __path__”；不扩大测试范围。

产品、A–D 组、测试数 21 和所有旧材料冻结。Codex 下一轮只需确认运行期观察通过、根名匹配副本仍失败，以及最终状态／文档一致。

## Codex 追加的记录更正（原 R3）

Pi R2 provenance 没有逐项写回上轮所要求的历史更正；下表是 Codex 基于原件的更正，**不归为 Pi 已完成，也不覆盖旧 Pi provenance**。

| 项 | 准确事实与边界 |
|---|---|
| 首轮 U8／变量变换 | Pi 首轮测试只有 U0–U7，所称变量双射改的是常量；本轮才补 U8 与真正局部变量双射。首轮 Codex 规划／验收探针不算 Pi 覆盖；未录制的 Pi 额外探针是否运行属 unknown。 |
| 首轮 docs2／docs3 | docs2 原件是相对链接 `pi-r1-docs/record.json` 失败；docs3 才是 `../pi-r1-docs2/run-index.json` 不存在。首轮 11 RUN：7 成功、4 失败，docs5–docs8 通过。 |
| `--tb=0`／再次收集 | 原交接不存在该命令，也未要求 Pi 重新收集旧测试。只有 Codex 规划收集 864 的原件；Pi 是否另跑未录制收集为 unknown，不能称“合同无效而等价替换”。 |
| 模型来源 | bonsai2-27b/provider=bonsai 来自 Pi 环境自述，当前记录器只采集 PYTEST/CUDA 覆盖项，不是独立模型证据。 |
| provenance 位置 | 首轮实际在 pi-r1，偏离约定 pi-r1-full；有效原件原位保留，不移动。 |
| R2 preflight2 命令 | record.json 子命令是 `.venv/bin/python reports/T0013/review-r1/check_rework.py preflight reports/T0013/pi-r2-preflight2`；新 provenance／交接所写 `run_checks.py ... preflight` 不能生成这个子命令，是错误描述。第一次误用旧检查器失败的原件已保留，随后正确 preflight 通过，原测试哈希一致。 |
| R2 全量回归 | Pi 实际额外运行 full，**885 passed** 原件有效；它不是“沿用独立 885”，也不符合“不重复 full”的返工安排。Codex 独立 full 是上轮 884；本轮仅独立 21。记录这项执行偏差，不因重复耗时再要求补跑。 |
| R2 前缀副本“实证” | Pi R2 目录只有五个 RUN：preflight 失败、preflight2/focused/full/docs 成功，没有另存副本检查原件。Pi 的“实证”来源保留为自述；当前拒绝副本的可核验结果来自本轮 Codex。 |

上述事实见 [上一轮 evidence-audit](../review-r1/evidence-audit.json)与 [本轮 evidence-audit](evidence-audit.json)。R2 docs 的索引记录之前 15 个 Pi RUN，连同自身累计 16；旧原件均核验未变。当前维护文档由 Codex 同步这些来源和剩余缺口，**原 R3 以本追加更正关闭，历史 unknown 永久保留**。

第 3 轮只改 E 的提前移除与相邻注释，定向 21 项、简短本轮 provenance、docs；无需 full、GPU、doctor 或重新执行历史命令，不 commit/push。

Codex 收尾检查：第一次 [review-r2-final](../review-r2-final/record.json) 因主代理替换状态行时未匹配带 R2 说明的完整行而失败，尚未生成 final-audit；已修正文档状态，原失败保留，在新 [review-r2-final2](../review-r2-final2/record.json) 复核。该错误与 Pi 产品／测试无关。

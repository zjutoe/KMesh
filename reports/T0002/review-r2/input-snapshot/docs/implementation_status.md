# KMesh 实现状态

- 截至 2026-09-14，M0（最小可运行环境）`in_progress`。
- T0001（最小 Python 包与环境诊断命令）：Codex 第 2 轮复验通过，状态 `accepted`，接受实现提交 `39dabc73e035c8c2627a1e5db4deab31055a9c6d`。R1–R3 已关闭；独立复跑 25 个测试和关键回归检查通过。记录见 [交接文档](handoffs/T0001-bootstrap-doctor.md)，[Pi 第 2 轮证据](../reports/T0001/pi-r2/)与 [Codex 第 2 轮证据](../reports/T0001/review-r2/)分别保留。
- T0002（模型结构配置的读取与校验）：Codex 第 1 轮验收结论为 `needs_changes`；第 2 轮返工（2026-09-14）已按 R1–R5 逐项修复并自检通过（91 个测试、开发检查与规定驱动均通过），现状态 `awaiting_review`。独立复跑 77 个测试与规定驱动通过，现存 37 项 Pi 哈希匹配；额外复现确认 YAML 异常、dropout 溢出及 PyYAML 缺失时 doctor/help 回归，部分负例未测到目标规则，另有早期证据删除问题；R5 历史限制（早期已删产物不可恢复、第 2 轮曾误用错误字段集后从冻结快照恢复）如实记录于轮次文档。**仅涉及 model 的九个字段，不代表完整实验配置已校验。** 见 [T0002 交接文档](handoffs/T0002-model-config.md)、[Pi 第 1 轮证据](../reports/T0002/pi-r1/)、[Pi 第 2 轮证据](../reports/T0002/pi-r2/)（开发检查 `pi-r2-dev1/`）与 [Codex 第 1 轮证据](../reports/T0002/review-r1/)。

## M0 已完成 / 未完成

| 项目 | 状态 |
|---|---|
| 可编辑安装的 `kmesh` 包与控制台入口 | 已验收（T0001） |
| `doctor --out PATH` 环境诊断（模块/控制台入口、真实环境报告） | T0001 已验收；第 2 轮 R1 修复后，PyYAML 缺失时 help/doctor 行为按契约（未验收，待 Codex 复验） |
| 完整实验环境锁定、驱动/CPU/主存盘点、RNG/kernel 元数据 | `not_run`，属 M0 后续任务 |
| 模型结构配置校验 | T0002 第 2 轮返工自检通过，`awaiting_review`，仅 model 区块 |
| 完整运行配置校验（含路由、训练、评估） | `not_run`，后续拆分 |
| 数据/求解器与 CPU forward/backward 验证 | `not_run`，尚未实现 |
| 20-step smoke | `not_run`，尚未实现 |
| GPU 训练 | `not_run`，尚未实现，也未经本任务授权 |
| 性能测量 | `not_run`，尚未实现 |

`doctor` 成功与模型配置校验通过只能证明环境与最小接口正常，不能推断任何科研结论，也不表示 M0 完成。

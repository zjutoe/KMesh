# T0002 Codex 第 1 轮验收证据

日期：2026-09-14。结论：`needs_changes`。验收对象为分支 `T0002-model-config` 的 HEAD `2c15f6a6db71ab2839643276f43eee05cab99f15` 加 Pi 首轮工作树改动，没有要求先提交。

完整发现、A1–A7 结论和 Pi 的 R1–R5 返工要求见 [任务交接文档](../../../docs/handoffs/T0002-model-config.md)。

| 证据 | 用途与结果 |
|---|---|
| [frozen-inputs.json](frozen-inputs.json)、[input-snapshot/](input-snapshot/)、[tracked-diff.patch](tracked-diff.patch) | 验收开始时的 39 项文件哈希、关键文件副本、已跟踪差异 |
| [input-audit.json](input-audit.json) | Pi 的 37 项已有哈希全部匹配；驱动与契约代码块逐字相同 |
| [driver-command.json](driver-command.json)、[driver.stdout](driver.stdout)、[driver.stderr](driver.stderr) | 原精确驱动在全新 contract-check 目录运行，退出 0，3.359 秒 |
| [contract-check/commands.json](contract-check/commands.json)、[contract-check/verification.json](contract-check/verification.json) | 十项子检查符合预期；77 passed，正常入口及强制 CPU doctor 通过 |
| [probe_boundaries.py](probe_boundaries.py)、[probe_yaml_missing.py](probe_yaml_missing.py) | 独立边界复现代码；只向新目录写证据，不改产品或安装环境 |
| [probes-command.json](probes-command.json)、[probes.stdout](probes.stdout)、[probes.stderr](probes.stderr) | 复现收集退出 0，3.292 秒；这不是产品验收通过 |
| [boundary-check/results.json](boundary-check/results.json) | YAML 构造异常、超大 dropout、错误 fixture 和缺 YAML 时的基线/当前行为对照 |

非作者代理 `/root/review_t0001_code`（Codex + gpt-6-astra，xhigh）只读核对冻结源码，独立提出 YAML 构造异常、dropout 溢出、缺 YAML 的 doctor 回归及无效 fixture 四类问题。根代理实际运行规定检查及边界复现；该代理随后只读复核复现代码和 results.json，确认对照方法及额外 `!!map` 反例有效。没有把代理的静态检查写成实际测试执行。

验收期间产品源码、测试、配置、Pi 报告和原精确驱动保持冻结。Codex 仅追加本目录证据，并更新 README、任务状态和验收文档。这些文档更新后的哈希不同于 Pi 清单，应对照冻结副本；不修改旧哈希。最终文件一致性、范围和文档检查记录于 `final-audit.json`，本目录非临时产物哈希记录于 `sha256.txt`。

限制：旧 pi-r1 曾被 Pi 删除并重新生成。当前哈希与复跑证明现存版本可复验，不能恢复早期失败日志，也不能独立确认删除前后的源码相同。缺依赖反例是新进程模拟，并非当前机器确实缺 PyYAML。未运行模型、训练或研究数据实验。

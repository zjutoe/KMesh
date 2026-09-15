# T0002 Codex 第 3 轮验收证据

日期：2026-09-15。结论：`accepted`，R2/R5 关闭，R1–R5 全部闭环。完整结论与限制见 [任务交接文档](../../../docs/handoffs/T0002-model-config.md)。

接受分支 `T0002-model-config` 的 HEAD `2c15f6a6db71ab2839643276f43eee05cab99f15` 加第 3 轮冻结工作树；不是仅接受 HEAD 中的旧代码。Codex + gpt-6-astra xhigh 负责验收；非作者代理 `/root/review_t0001_code` 只读审阅本轮补丁、测试及 Pi 日志，根代理执行实际核验。

| 记录 | 结果/用途 |
|---|---|
| [frozen-inputs.json](frozen-inputs.json)、[input-snapshot/](input-snapshot/)、[tracked-diff.patch](tracked-diff.patch) | 306 项输入哈希、关键文件副本及已跟踪差异 |
| [config-r2-to-r3.patch](config-r2-to-r3.patch)、[test_config-r2-to-r3.patch](test_config-r2-to-r3.patch) | 本轮产品仅增加一个异常转换分支，测试仅追加 8 个回归 |
| [input-audit.json](input-audit.json) | Pi 第 3 轮 43 项哈希匹配；旧两轮 Codex 清单及冻结 Pi 文件全量匹配；起点五个哈希匹配；驱动与契约一致 |
| [driver-command.json](driver-command.json)、[driver.stdout](driver.stdout)、[driver.stderr](driver.stderr) | 规定驱动退出 0，10 项子检查符合预期 |
| [contract-check/tests.stdout](contract-check/tests.stdout)、[contract-check/verification.json](contract-check/verification.json) | 99 passed in 3.44s，正常两入口与强制 CPU doctor 通过 |
| [verify_r2.py](verify_r2.py)、[counterexamples-command.json](counterexamples-command.json)、[r2-counterexamples/results.json](r2-counterexamples/results.json) | 直接读取 review-r2 的四个旧反例；API/CLI 全部受控，脚本退出 0 |

Pi 修复前 `8 failed` 和修复后 `8 passed` 分别留在 pi-r3-dev1、pi-r3-dev2；两目录没有单独 stderr，未注明合并捕获，不能声称这两次开发检查 stderr 已保留或为空。正式驱动与 Codex 本轮复验的 stdout/stderr、命令、退出码完整留存，支持当前验收。

第 1 轮早期被删除产物、第 2 轮“39 项失败”和被覆盖 dev 输出仍不可独立核验。G1–G6 的更正及这些限制永久保留；没有以当前通过追认历史，也没有重造旧日志。首次 shell 重定向事故按 Pi 自述记录。

Codex 仅新增本目录证据并更新 README、状态和验收文档；产品源码、测试、样例、精确驱动及旧报告保持冻结。最终范围/文件检查见 `final-audit.json`，本目录非临时产物哈希见 `sha256.txt`。未 commit/push，未训练或访问研究数据。

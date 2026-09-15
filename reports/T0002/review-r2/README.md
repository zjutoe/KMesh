# T0002 Codex 第 2 轮验收证据

2026-09-14，结论为 `needs_changes`：R1、R3、R4 关闭，R2 与 R5 尚未关闭。完整发现和第 3 轮返工要求见 [交接文档](../../../docs/handoffs/T0002-model-config.md)。

验收对象为 HEAD `2c15f6a6db71ab2839643276f43eee05cab99f15` 加 Pi 第 2 轮工作树，分支 `T0002-model-config`。由 Codex + gpt-6-astra xhigh 验收；非作者代理 `/root/review_t0001_code` 只读审阅源码/测试及本机 SafeConstructor，根代理实际运行以下验证。

| 记录 | 结果/作用 |
|---|---|
| [frozen-inputs.json](frozen-inputs.json)、[input-snapshot/](input-snapshot/)、[tracked-diff.patch](tracked-diff.patch) | 184 项冻结文件哈希、关键输入副本及已跟踪 diff |
| [input-audit.json](input-audit.json) | Pi 第 2 轮 64 项哈希全匹配；旧 review-r1 的 90 项及 pi-r1 冻结哈希匹配；驱动符合原契约 |
| [driver-command.json](driver-command.json)、[driver.stdout](driver.stdout)、[driver.stderr](driver.stderr) | 规定驱动退出 0，10 项子检查符合预期 |
| [contract-check/tests.stdout](contract-check/tests.stdout)、[contract-check/verification.json](contract-check/verification.json) | 91 passed in 3.04s；正常两入口和强制 CPU doctor 通过 |
| [check_regressions.py](check_regressions.py)、[regressions-command.json](regressions-command.json)、[regressions/results.json](regressions/results.json) | 原反例、R1/R3、R4 测试有效性通过；3 个新增 YAML 输入失败，脚本退出 1 |
| [check_yaml_float.py](check_yaml_float.py)、[yaml-float-command.json](yaml-float-command.json)、[yaml-float/result.json](yaml-float/result.json) | 401 字符 sexagesimal 浮点输入复现未受控 OverflowError，脚本退出 1 |

新增失败是 `!!int ''`、`!!float ''` 的 IndexError，`!!timestamp nope` 的 AttributeError，以及显式浮点 sexagesimal 字符串的 OverflowError。四个案例均经实际 API/模块 CLI 复现；stderr 原样保存于各子目录。原五个 YAML 反例已修复，MappingNode 回退调用在本机 PyYAML 6.0.3 下正确。

R4 有效性验证直接调用当前测试函数，仅在内存中绕过对应规则；四次均捕获到预期 pytest 失败。R1 缺包检查复用只读的首轮 import-blocker 脚本，将报告写到本轮新目录；未卸载包，未改变真实环境。

R5 当前限制：Pi 第 2 轮交付中仅见最终通过日志，C3 所述 39 failed 的原始输出尚未提供可核查路径。已请求路径，不能把请求本身写成核验通过。旧 Pi dev 驱动会写入固定日志路径并删除已有 doctor 报告，因此本轮没有执行它。现存 Pi/首轮 Codex 证据全部保留，未用独立复跑反向证明缺失的历史。

Codex 只追加本目录证据并更新 README/状态/验收文档，源码、测试、样例和 Pi 报告保持冻结。文档新哈希应与本轮输入副本区分；最终检查见 `final-audit.json`，本目录非临时产物哈希见 `sha256.txt`。未 commit/push，未训练或访问研究数据。

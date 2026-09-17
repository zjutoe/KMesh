# T0006：Codex 第 3 轮验收

2026-09-17。结论：**accepted**，R1–R4 全部关闭。接受工作树中的产品与测试，未 commit/push。

## 接受版本与范围

- HEAD：`6dcaae2ef40459e80ed5919e658db84986526211`，分支 `T0006-proof-verifier`。
- `src/kmesh/logic/proof.py`：`008bdd3633a5d2327cd711b7c9de7149df86b588632db659a23bf34207963daa`，三轮未改。
- `tests/test_proof.py`：`68fef57a21500f733f9d7a4e1bac671fd71ae5ec2465157dbf71f216d07e3566`。
- [输入快照和历史核验](../review-r3-freeze/audit.json)确认本轮代码差异仅两个 fixture 与 4300 docstring；[实际测试差异](../review-r3-freeze/tests.diff)已逐项审阅。先前 A1–A4、A6 的有效核验不重复扩大。

## 两个测试缺口已关闭

直接执行当前提交测试，使用冻结产品及内存中的两种错误实现；不替换磁盘产品／测试。

| 用例 | 真实产品的合法／非法证明结果 | 错误实现表现 | 验收 |
|---|---|---|---|
| 引用不足 | True / False | 放行不足引用、按 zip 截断后为 True / True；提交测试断言失败 | R2 关闭 |
| 大正 premise 引用 | True / False | 提前格式化引用时为 True / ValueError；提交测试失败 | R3 关闭 |

两例均有合法对照，只改变目标引用；4300 fixture 会恢复原转换上限。证据：[变体结果](../review-r3-probes/findings.json)、[审阅探针](probe.py)。既有 R1 隔离结论保留，未发现产品逻辑缺陷。

## 运行与记录核对

- Codex 本轮[独立定向回归](../review-r3-focused/)：**101 passed in 0.23s**，退出 0，无 skip/xfail；使用独占 basetemp。
- Pi 本轮[完整回归](../pi-r3-full/)：**438 passed in 4.05s**，退出 0；核对了五个 Pi RUN 的完整命令、日志哈希及运行前后源码哈希。因产品、旧测试和其余 proof 测试未变，本轮 Codex 未再次运行六文件全量回归，不把 Pi 的结果称为独立复跑。
- 第 2 轮冻结清单的 721 个历史文件、旧 provenance、记录器及 Codex 审阅报告／探针保持原样。R4 五项更正在[新 provenance](../pi-r3-full/provenance.md)追加，新文档的 12 个本地链接可解析。状态文档中误将 Pi 全量结果标作“独立”的措辞已修正。
- `/root/review_t0006_tests` 作为非实施作者只读复验两个 fixture 与 R4 更正，通过，无阻塞。

## 保留限制

Pi 披露的 `/tmp` 替换前预检没有归档；用户交回摘要提到的先前链接检查失败也无对应失败 RUN。这些仍是自述，不能据此认定全过程留证合规。首轮历史限制继续保留，未补造日志。当前正式 RUN 和 Codex 独立核验已足以复现接受结果；不要求重新制造历史失败或再做一轮返工。后续所有检查仍应使用新 RUN。

A1–A7 验收关闭，A7 保留上述过程限制。范围仅为给定有限证明核验；没有实现证明生成／枚举、唯一性、最短深度或完整 world 审计。True 只代表提交证据有效；False 不能直接生成 query 负标签，超限也不是 False。

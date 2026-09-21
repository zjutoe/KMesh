# T0010 规划核对

- 日期：2026-09-19；规划者 Codex + `gpt-6-astra`，`xhigh`。
- 非作者独立审阅：`/root/review_t0009_design`，`gpt-6-astra`，`xhigh`。实际阅读本次交接、示例、检查器、D28 和状态关联；只读及手算，无产品／测试实施，未另行运行探针。最终结论：**无阻塞或必须修改项，可 ready**。本条不是产品验收。
- [基线](planning-baseline.json) 为已推送 T0009 提交 `153295c28788f27ef37e794c7c0ea19841accaa8`。新模块／测试不存在；T0009 接受哈希和环境核对见 [planning-preflight](planning-preflight/)。既有 679 项回归来自 T0009 第 2 轮验收，本轮未重跑。

## 范围与已解决的设计问题

1. 一个产品模块＋一个测试文件，六步实施。只计算单查询最短证明深度，明确事实 0、完整检查后的不可达 None，以及异常原样传播。无需另加深度预算、证明见证或批量接口。
2. 完整 T0008 一次调用后按已有记录序单遍 DP。ground 前提的来源可独立组合；DAG 确保全部前提最小值先完成。新增 DP 的 O(R)／O(A) 不代替整个 API 的匹配时间与全部记录存储成本。
3. 手算例覆盖较晚捷径及其下游、事实来源前后次序、两分支取 max、不同 ground 参数和“步数少但层数深”。H12 两证明长度 4／7、深度 3／2，答案为 2。独立审阅者核对全部 18 个 query 及 C/D 正确。
4. Codex 的 [planning_examples.py](planning_examples.py) 经 [planning-examples](planning-examples/) exit 0：用已验收 T0008 核预算及少一边界、T0009 列原始树、T0006 逐条验证后测单棵高度；输出与显式手写期望一致。**未实现新的 world 深度函数**。两条深度路径共享 T0008 的限制已写入契约，不能代替手算或独立完整性证明。
5. F 组 16 世界 × 4 query 的组合已冻结。独立手算最大 C=6、D=9、S=20，所给预算充足；1200 长链与 16 层重复来源预算也核对正确。没有使用正式研究或锁定测试数据。
6. 固定 [run_checks.py](run_checks.py) 代替手拼 pytest 命令，自动使用新 RUN 内的 basetemp；保留失败 RUN 原名。preflight 必须先于产品文件落盘，状态先于编码；文档落盘后只需一次最终 docs 检查，不为自引用时间重复运行。

## 核对与交接边界

[planning_check.py](planning_check.py) 核对规划范围、冻结源码、文档链接／卫生、ready 状态、检查器语法和四阶段实际命令构造；pytest 调用在此只作模拟，不启动测试进程。原始结果保存在 [planning-check](planning-check/)；最终冻结清单在该 RUN 结束后生成，避免活动记录自引用哈希。

[T0010 交接](../../docs/handoffs/T0010-minimum-depth.md) ready，产品实现与新增测试仍为 **not_run**。Pi 执行后再由 Codex 按 A1–A7 验收。规范证明身份、唯一性、motif、完整 world 审计仍另拆；没有声称新的研究结果或训练成本收益。本轮不 commit/push。

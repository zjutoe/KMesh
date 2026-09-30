# T0019 规划核验（r1，2026-09-28）

当前状态：**accepted / round 3 / attempt 3**，2026-09-29 已核对同步；见 [第三轮接受记录](acceptance/README.md)。随后经授权提交为 `ffd1bdf` 并快进合入本地 master，合并后 32 项定向测试通过、未 push；见 [合并记录](integration/README.md)。后续为 [T0020](../../docs/handoffs/T0020-motif-split-catalogue.md)，尚未发布。以下保留各历史时点记录。

交接见 [T0019-motif-candidate-audit.md](../../docs/handoffs/T0019-motif-candidate-audit.md)，设计依据见 [D39](../../docs/decisions.md#d39正式保留目录冻结前的有限候选审计)。基线为 `e04706b2fa0541672c15a1ed5d6940784d9d43ae`，规划开始时主仓库干净。

本目录记录 **Codex 对设计前提的核验**。尚未实施 `kmesh.logic.motif_candidates`，没有生成完整 80 候选报告；没有正式 split 或研究数据。Pi 的实际实现／自检须在独立任务发布后进行。

[planning_probe.py](planning_probe.py) 只构造七个逐项写出的 witness：CC、II、CJ、JC、CJC、JJ、TTT。调用已验收的 verifier、计数、深度、整树键和 T0018 审计接口，确认：

- 七个 witness 均合法、规范证明数为 1，深度／步数符合手算。
- 七个完整键互异；CC 与 II 虽端点相同但结构不同。
- CJC 的完整支持子树包含 CJ，不包含 JC；本目录内其余命中与手算一致。

执行退出 0、stderr 空。准确命令、退出码与输出位于 [planning-r1/](planning-r1/)。运行使用 T0018 解释器、只读主仓库、显式主仓库 `PYTHONPATH`、隐藏 CUDA 和禁用 bytecode；这不是 T0019 专用环境预检。

80 个独立键、七个长度／深度 bucket、144 条总包含边和 64 条非自身边，是交接中给出推导的**待实测预期**，未作为本轮观测结果记录。后续任务不能以这些预期填充报告，必须从真实依赖调用计算。原规划日志不可覆盖，失败或后续修订另编号。

后续 r2 准备完成时任务为 **ready**。独立环境的 1050 项基线、七个规划 witness 和两模型连接预检通过；以上段落及 planning-r1 保留 r1 规划时点。准备结果和原生 Pi 启动入口见 [preparation-r2/README.md](preparation-r2/README.md)。

2026-09-28 第二轮状态为 **blocked**（round 2 / attempt 2），审查结论 `needs_changes`。32 项定向、1082 项全量及完整 80 候选目录已运行通过，但三项测试缺口仍待返工，触发连续相同问题停止规则；历史核验见 [blocked-r2/README.md](blocked-r2/README.md)。

2026-09-28 暂停诊断时为 **paused / round 3 / attempt 2**：原阻塞恢复后 Pi 已修改测试并自检，但新增派生 bytecode 缓存令重新提交的范围检查失败。没有第三轮 Codex 结论；详见 [paused-r3/README.md](paused-r3/README.md)。

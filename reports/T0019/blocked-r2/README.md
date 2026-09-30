# T0019 第二轮阻塞状态核验（2026-09-28）

控制器状态为 **blocked / feedback**，round 2 / attempt 2；最近审查结论为 **needs_changes**，尚未验收。SQLite 最后更新时间为 **2026-09-28 10:14:05 UTC**，原因是 `Two consecutive reviews retain the same issue set`。两轮均保留 T0019-R1／R2／R3，触发重复问题停止规则；不是超时，也未耗尽 manifest 的四轮上限。

本次 Codex 读取控制器 SQLite、两轮审查、规定检查原件及涉及的测试代码，核对当前工作树、提交快照、允许路径和检查证据哈希。当前快照为 `83a0b001ab1653e3b9494fece46666d903c804262a4ac79f942c08bc6f41b8fe`，与第二轮提交一致。没有重跑测试、改写实施文件或恢复控制器。机器可读核验结果与原件引用见 [summary.json](summary.json)。

## 已有结果

| 第二轮规定检查 | 实际结果 |
|---|---|
| focused | 32 passed in 15.53s，退出 0 |
| full | 1082 passed in 34.98s，退出 0；1050 基线 + 32 新测试，无 skip／xfail |
| catalogue | 退出 0；80 个候选、80 个独立完整键、7 个 bucket、144 条包含边，其中非自身边 64 条 |

命令、退出码、stdout／stderr 哈希与 manifest／原件一致；三项 stderr 均空。独立审查报告确认 80 个 witness 合法，未发现产品正确性缺陷，但三个测试仍不能拒绝对应错误实现。检查通过不能替代验收通过。

Pi 身份来自提交时扩展运行元数据：`bonsai/bonsai2-27b/xhigh`，不是 RPC 取证或后端权重证明。原始 state、会话与审查流留在仓外；本目录仅导出审查意见、必要检查结果和发布契约。

## 最小返工要求

以下沿用 [第二轮审查原件](round-2-review.md)，不改变 r2 接口、范围或 A1–A7：

1. **T0019-R1，测试约第 674 行：** 公共子进程 helper 只检查了 `types.py` 的路径。每个审计／成功 CLI／失败 CLI 子进程均须验证实际 `motif_candidates.py` 来源；`runpy` 路径须核对解析出的 origin 或执行命名空间路径。保留显式 src 插入、禁用导入 finder 及最终扫描。用外部产品 origin 反例验证各适用子进程会拒绝；维持产品导入和执行审计时的禁用导入守卫。
2. **T0019-R2，测试约第 731 行：** 污染测试的 `base` 也是产品返回值，可能共享嵌套容器。修改返回值之前保存独立深拷贝或序列化基线，之后将新报告与该不变基线比较。验证“顶层 dict 不同、嵌套状态共享”的错误实现会被拒绝。
3. **T0019-R3，测试约第 591 行：** 消息断言在传播后比较同一异常实例，无法发现 `exc.args` 被改写。对四个依赖绑定均在调用前保存 `str(exc)`，传播后与保存值比较；保留实例、cause、context 和停止调用断言。验证原实例但消息被修改的错误实现会被拒绝。

第二轮已有有效修复：禁用导入守卫、bytecode 前后快照、CLI／函数结果比较、支持的异常类型及 cause／context 检查。继续返工时保留这些修复，最后运行原 manifest 的三项检查并交独立 Codex 审查。

## 恢复边界与证据

当前 `codinator/interactive.py` 的 `resume()` 仅允许 `paused / feedback` 进入返工，`blocked / feedback` 会报 `Task requires a new contract or explicit investigation; automatic resume is unavailable`。本次通过源码核对该限制，没有试运行恢复或改写 SQLite。继续实施前须明确处理控制器的恢复入口，不能把反复 `/codex-resume` 当作可行步骤，也不能静默改状态或覆盖旧 attempt。

- [第一轮审查](round-1-review.md)、[第二轮审查](round-2-review.md)及 [第二轮 verdict](round-2-verdict.json)原样导出；所有失败证据仍在仓外。
- [发布时 r2 交接](published-handoff-r2.txt) SHA-256：`3622be65e75dec49d4820cbeb2d38e2a0ddc0df526034ad101d8706b5d42a61f`，已核对 intake 与当前任务工作树。
- 仓外原件：`/home/mye/.local/state/codinator/interactive/tasks/T0019-motif-candidate-audit/attempt-0002`。
- 任务工作树：`/home/mye/data/kmesh-worktrees/T0019-motif-candidate-audit`；本次仅同步主仓库状态文档，未回写冻结工作树。T0019 实现尚未合入主仓库，未 commit／push／merge。

## 后续：恢复入口已修复（2026-09-28）

用户随后要求修复 Codinator。修复已应用到 `/home/mye/src/llm/codinator`：相同 issue ID 不再提前停止返工，原四轮上限保留；旧版这一特定阻塞可显式恢复。90 项 Python、9 项 Pi 扩展测试及非作者审查通过。使用本任务 SQLite／attempt 私有副本演练，成功进入 `needs_changes / round 3 / attempt 2`，69 个历史证据文件不变；真实状态未修改，也未调用模型。

以上“不支持恢复”描述保留状态检查时点；更新后的入口可用。需退出旧原生 Pi／控制器，再在用户终端执行：

```bash
bash /home/mye/src/llm/KMesh/reports/T0019/launch-pi.sh --resume
```

该命令加载新控制器，核对冻结快照和证据后把原 review 交给 Pi 继续返工。无需改 manifest 或冻结任务文件。修复验证记录见 `/home/mye/src/llm/codinator/validation/rework-20260928/`；本目录原审查、检查输出及 summary.json 不回写。

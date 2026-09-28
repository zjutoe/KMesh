# T0018 验收同步（2026-09-28）

控制器于 **2026-09-28 06:18:00 UTC** 将 `T0018-heldout-motifs` 标为 **accepted**，round 2 / attempt 2，phase `done`。主会话已只读核对 SQLite、独立审查结论、检查原件和当前工作树，全部绑定同一提交快照；没有待处理问题。正式结论见 [review.md](review.md) 和 [verdict.json](verdict.json)，完整摘要见 [summary.json](summary.json)。

| 核验 | 实际结果 |
|---|---|
| 控制器规定定向检查 | 39 passed in 0.27s，退出 0 |
| 控制器规定全量检查 | 1050 passed in 19.15s，退出 0；1011 基线 + 39 新测试，无 skip／xfail |
| 独立审查定向复跑 | 39 passed in 0.26s，退出 0 |
| 独立审查错误实现守卫 | 10 个针对性错误实现均被行为断言拒绝 |
| 主会话终态定向复核 | 39 passed in 0.27s，退出 0；只读工作树、禁用 bytecode／pytest 缓存、隐藏 CUDA |
| 范围与冻结核对 | 相对发布快照仅两个允许文件；复核后工作树和控制器检查证据未变，源码无 `.pyc` |

控制器检查的准确命令、退出码及 stdout／stderr 位于 [controller-checks/](controller-checks/)；主会话本轮复核记录位于 [closeout/](closeout/)。独立审查的两次实际命令事件及其输出摘录位于 [reviewer-verification.json](reviewer-verification.json)，绑定原始审查 stdout 的 SHA-256。本轮未重复运行全量检查，已核验控制器全量原件，并复跑风险相关定向检查。

接受的 HEAD 为 `03bbce2a401097f8ce78a9a13a07457e8753e797`，提交快照 digest 为 `bcf5afa94762ffba858b4de591d70e43edefdb4da92a2a9dcaafa62c4c6fca4c`。以下实现仍在独立工作树 `/home/mye/data/kmesh-worktrees/T0018-heldout-motifs`，尚未提交或合并到主仓库。

| 接受文件 | SHA-256 |
|---|---|
| `src/kmesh/logic/heldout_motifs.py` | `5c785ef250b26daecb9b09606cfa67bd5ef71bf60c96ba565b0af85eaa48e91e` |
| `tests/test_heldout_motifs.py` | `a0c7ffc33f3090bfdfc920155e32b1fc8f0e63bfba17d4349c972ee520115339` |

发布时的 r3 交接逐字归档为 [published-handoff-r3.txt](published-handoff-r3.txt)，SHA-256 为 `4c5b918bcbe1568ba2fd6f9178f2e32717e70a8e4c18276eb64ab82d08e1a5ee`；[原 manifest](published-manifest.json) SHA-256 为 `35382226eb20a06d9293c6d15c752bafe5e02a121ce6f286976133bfaafdca89`。主仓库交接状态的同步不修改这些原件或已验收工作树。

首次提交曾因隔离子进程仅用 `python -I` 产生 bytecode 越过允许路径而暂停。失败现场、缓存及状态副本先保存在 `/home/mye/data/kmesh-T0018-recovery-cache-f37g9nlf`，随后只清理 14 个派生 `.pyc` 和 2 个空目录，源文件与测试未变；[清理结果](cache-recovery.json)留存。Pi 后续将该子进程改为显式 `-I -B`。此故障不等于正式首轮审查。

[正式首轮审查](review-round1.md)为 `needs_changes`：31 项定向／1042 项全量虽通过，重复项调用次数、异常身份与优先级、独立预算失败及晚失败停止、后部 list 条目提前校验四类测试缺口仍存在。第二轮仅补强测试，产品 hash 未变；新增 8 项，T0018-001–004 全部关闭。Pi 最终总结中的错误源码 hash 和“此前已 accepted”措辞由本页核验值及正式审查历史更正，原总结不回写。

实施身份来自原生 Pi 扩展运行元数据：`bonsai/bonsai2-27b/xhigh`；独立审查启动记录为 `gpt-6-astra/xhigh`，退出 0 且有 `turn.completed`。不将原生会话标为 RPC 取证，也不将客户端元数据当作后端权重证明。原始 state、完整会话和失败探针留在 `/home/mye/.local/state/codinator/interactive/tasks/T0018-heldout-motifs` 及关联仓外目录；本目录仅导出必要结果。包括审查中先失败后修正的边界 fixture 在内，旧尝试未覆盖或改记为成功。

验收仅覆盖**给定查询、参考证明目录和完整有根支持子树**的命中审计；正式 split、world 无泄漏、训练及局部更新成本尚无本任务证据。本次没有 commit／push／merge，也未启动下一项研究任务。

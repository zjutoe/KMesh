# T0018 提交与合并（2026-09-28）

用户在确认验收后明确要求“提交并合并到主仓库”。已将两个获准文件提交为 **`40aacbfe23e7f3e8a1d538ba87104fcfe8fa7795`**，并从 `T0018-heldout-motifs` 快进合入本地 `master`；原主仓库 HEAD 为 `03bbce2a401097f8ce78a9a13a07457e8753e797`。本目录随随后整理规划／验收文档的提交一起保存。未执行 push。

提交前已确认控制器 `accepted / done`、round 2 / attempt 2，任务工作树与接受快照 `bcf5afa94762ffba858b4de591d70e43edefdb4da92a2a9dcaafa62c4c6fca4c` 一致。源码／测试的 Git blob 与 [接受摘要](../acceptance/summary.json) 中的 SHA-256 一致，合并未改变其内容，也未覆盖主仓库已有文档。

合并后在只读沙箱运行 **39 项定向测试，全部通过（0.26 秒，退出 0）**。沿用任务解释器，以显式 `PYTHONPATH` 指向主仓库 `src`，并在同一测试进程中断言 `kmesh.__file__` 确实位于主仓库；禁用 bytecode／pytest 缓存并隐藏 CUDA。精确命令和输出见 [focused/](focused/)，环境与结果见 [verification.json](verification.json)。本轮未重复全量测试；实现与获准版本逐字一致，控制器原有 1050 项全量通过的证据继续保留。

原生 Pi 的实施来源和独立 Codex 的验收结论保留在实现提交说明及 [验收目录](../acceptance/README.md)。准备记录、契约归档、验收摘要和所有已导出原件未覆盖；原始控制器状态、会话和失败记录继续保存在仓外。

Git 提交会改变 HEAD／索引，因此提交后的整个工作树 digest 与验收时不同；[merge.json](merge.json)明确保存旧快照到实现提交的对应关系。原任务工作树中所有已接受文件内容保持不变，发布时的未提交规划材料仍原样保留。验收摘要中“未提交／未合并”的文字描述验收时点，本页记录后续授权操作。

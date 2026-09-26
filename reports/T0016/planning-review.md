# T0016 发布前设计核验

2026-09-26，Codex 主会话完成契约，非作者代理 `/root/design_t0012` 两次只读复核设计与最终交接。结论：接口、调用顺序、预算与五组验证无矛盾，可发布；指出 motif 必读链接笔误，已更正为 docs/motif_identity_v1.md。该代理没有编写产品／测试、运行检查；不把设计意见当作产品验收。

主会话另在新的独立工作区运行 [planning_probe.py](planning_probe.py)，只调用已验收 T0014/T0015/T0006，核对手算完整主例、实际存储重排、裁剪片段负例及32链528个Header，结果通过。新venv既有934项回归通过，stderr为空；命令、耗时和原始输出在 [planning-checks](planning-checks/) 中。这不是T0016实现通过的证据。

工作区 /home/mye/data/kmesh-worktrees/T0016-subtree-motifs，基线011fc81cd6c6396a1de8cd0179ef7f658aae0fa0。环境 Python3.13.9、kmesh0.1.0、pytest8.4.2，editable导入精确指向本worktree/src/kmesh/__init__.py。安装使用已有系统包、--no-index/--no-deps，无下载。

采用现有后台服务串行处理；发布前队列为空，无Pi进程，llama-server存在。服务已配置 http_proxy/https_proxy=http://localhost:8888；Pi子进程按控制器代码移除代理并直连。本任务发布清单只允许两个新文件，4轮／4小时／单阶段1小时；不授权提交、推送、合并。运行状态保存在 /home/mye/.local/state/codidator，发布后冻结此worktree直到终态。

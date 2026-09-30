# T0020 r3 已发布

[发布回执](receipt.json) 固定 intake、契约／manifest SHA-256、精确集成目标与运行预算。
控制器已启动首轮真实 Pi `bonsai/bonsai2-27b/xhigh`，首次观测为 implementing / round 1 / attempt 1，
见 [启动记录](started.json)。宿主用户服务 enabled / active / running，主进程738013；
Codex 工具 PID 命名空间中的 `process_alive=false` 不表示宿主任务已停止。

这是执行起点，不是实施完成、审查接受或合并结果。当前状态使用
`codinator status T0020-motif-split-catalogue` 查询。独立审查接受后由 Pi 创建提交并快进合并，
控制器核验同一提交后推进本地 master；不 push，也不自动开始下一研究任务。

发布后原任务工作树、冻结交接及既有 evidence 不回写。后台服务持有生命周期，
结束本次主界面对话不暂停任务。原始状态、认证和会话留在仓外控制器目录。

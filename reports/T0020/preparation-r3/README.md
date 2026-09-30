# T0020 r3：验收后的 Pi 提交与合并

用户明确更新了交付流程：独立 Codex review accepted 后，Pi + Bonsai 负责 Git commit 和 merge to master。
r3 在实际发布前加入该步骤，保存 [r2 原交接／manifest](prior-contract-r2/) 与 SHA-256。
原两文件范围、A1–A6、研究协议与预算不变；不 push、不自动开展下一任务。

- [最新 manifest](../task.json)：指定主仓库 `/home/mye/src/llm/KMesh`、master、基线 `ffd1bdf4276c4347de6964627863a1368d5ff857`。
- `planning_paths` 明确覆盖已有 AGENTS、研究计划、README、docs 和 T0018–T0020 报告；仅用于声明已有未提交材料，不进入产品提交，也不增加 Pi 实施权限。
- [Codinator 非作者审查](codinator-review.json)：accepted，记录修复的三个问题、独立回归和精确审阅 hash。
- [最终代码真实闭环](codinator-live-summary.json)：真实 Pi 实施、独立 Codex 接受、Pi 私有 clone 提交并合并，控制器把同一个 commit 推进独立测试主仓库；原工作树冻结和未提交规划保留通过。这不是 T0020 产品执行。
- [部署记录](codinator-deployment.json)：139项 Python、14项扩展测试通过；用户服务 enabled / active / running。部署以 `32c187e` 加文件 hash 标识的未提交修改为准，未 commit/push Codinator。
- T0020 环境与1082项基线沿用已核验的 [r2 准备](../preparation-r2/README.md)；本轮未改产品依赖，无须把旧基线重标为新运行。

合并发生在单独集成阶段：Pi 在私有 Git 副本创建带正文的单一提交并 ff-only merge；
控制器在沙箱中核对完整 tree、父提交和接受证据后推进同一提交到真实 master。
原任务工作树仍冻结。目标漂移、暂存／路径冲突或中断保留接受结论与旧 evidence，
显式恢复只继续集成。单独审查接受不算最终交付；全部阶段共用总14400秒。

实际发布的 intake、契约 hash、服务状态和执行起点在 `../publication/receipt.json` 留证；
该文件出现前不能仅凭本准备说明声称已 submit。

# T0020 规划与发布前置

交接：[T0020-motif-split-catalogue.md](../../docs/handoffs/T0020-motif-split-catalogue.md)；划分协议：[motif_split_v1](../../docs/motif_split_v1.md)。r2 已完成独立环境、1082项基线和真实模型预检，发布契约为 **ready**；产品尚未实施，具体发布状态以控制器为准。见 [准备记录](preparation-r2/README.md)。

r1 规划从 T0019 已接受的完整候选报告分析设计前提。[planning_probe.py](planning_probe.py) 为 Codex 的离线规划核验，读取 [原报告副本](../T0019/acceptance/catalogue.json)，不实现新产品或重新构造候选。[准确命令与退出状态](planning-r1/result.json)、[实测输出](planning-r1/stdout.json)保留。退出 0、stderr 空，输入哈希 `0e84e0ee386d046664c54c88b5ae798bc492cce101e666d6cbfc389481d9c5b4`。

[规划文档核验](planning-validation.json)已通过：完整字面分配及七桶与实测一致，57 个本地链接／锚点有效，T0019 原工作树与接受快照、检查证据及导出原件仍匹配，`git diff --check` 通过。该核验不包含新产品测试或模型调用。

观察到的图共有 16 个包含组，每组 5 个候选；整组分配后 train/dev/test 为40/20/20键、8/4/4组，七个深度／步数桶均按2:1:1配平，同集合边72/36/36，六个跨集合方向均为0。该证据只支持有限 witness 目录和完整有根支持子树口径，不能作为未来生成 world 或开放边界结构无泄漏的证明。

发布前置（r2 已完成环境／预检与 manifest，提交时核验冻结）：

1. 准备独立工作树，明确实际 HEAD 和已有规划改动；按 T0019 接受哈希带入其源码／测试并冻结为前置 intake。T0019 已按用户授权合入 master@ffd1bdf，新工作树直接继承接受文件。
2. 建立属于新工作树的解释器，核验 realpath、1082 项基线、只读检查边界及指定 Pi/Codex 可用性。
3. 发布前核验 Codinator 独立后台服务健康。2026-09-29 已启用并通过真实 Pi／Codex 探针，见 D42；T0020 尚未执行。Codex 主界面管理任务，Pi RPC 实施与独立 Codex 验收，T0018/T0019 原生任务不迁移。
4. 创建固定 manifest：两条精确允许路径、三项180秒检查、最多4轮、单次Pi/Codex各7200秒、总14400秒；记录冻结契约／基线 hash，再将交接升级 ready 并按已有授权明确 submit。

r2 已具备工作树与 manifest；产品／新测试／机器目录在发布前仍为 `not_run`。规划脚本与输出不能被 Pi 导入为实现或测试 oracle。

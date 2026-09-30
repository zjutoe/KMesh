# T0019 独立环境与发布准备（r2，2026-09-28）

任务已达到 **ready**，本轮没有发布或启动产品实施。沿用用户此前选择的原生 Pi 界面；[交接 r2](../../../docs/handoffs/T0019-motif-candidate-audit.md)、[D40](../../../docs/decisions.md#d40t0019-独立环境与原生-pi-发布准备)和 [manifest](../task.json)已对齐。原 r1 交接及规划材料保存在 [prior-contract-r1/](prior-contract-r1/)，原始 r1 核验日志保持不变。

## 启动

在真实交互终端运行：

```bash
bash /home/mye/src/llm/KMesh/reports/T0019/launch-pi.sh
```

[启动脚本](../launch-pi.sh)设置专用 Pi 配置、CPU／禁用缓存环境和 Codex 代理，然后运行 `codinator pi`。这条命令会发布 manifest 并进入原生 Pi 自动实施／独立审查闭环，无需另行 `submit/run`。当前仅准备好脚本，尚未执行。

退出后恢复同一任务：

```bash
bash /home/mye/src/llm/KMesh/reports/T0019/launch-pi.sh --resume
```

界面命令为 `/codex-status`、`/codex-pause`、`/codex-resume`。Pi 在所有工具结束后单独调用 `codex_submit_review`，以 Markdown 提交真实执行总结；控制器生成正式文件，独立 Codex 安排契约内返工。SQLite 为运行状态真值，不要求 Pi 编辑交接或 delivery 文件。

## 工作树与环境

- 分支／工作树：`T0019-motif-candidate-audit`／`/home/mye/data/kmesh-worktrees/T0019-motif-candidate-audit`。
- 基线 HEAD：`e04706b2fa0541672c15a1ed5d6940784d9d43ae`，含 T0018 的已验收实现；发布时同时冻结未提交规划／准备文件，不自动 commit。
- 解释器：该工作树 `.venv/bin/python`，Python 3.13.5，pytest 8.3.4、setuptools 72.1.0、wheel 0.45.1。离线 `venv --system-site-packages` 及无下载的 editable 安装均成功，包导入 realpath 已核对属于 T0019 工作树。
- Codinator 源码 HEAD：`15690b10ed1169fb8ba6749a6e1a4caa2f47d0b1`；Pi 0.87.1、Codex CLI 0.157.1。没有修改控制器。
- 专用 Pi 配置：`/home/mye/data/kmesh-T0019-preparation-cwn8wlo4/launch-pi`。从 T0018 已验证的 settings/models/auth 逐文件复制到新目录，保留本机 `http://127.0.0.1:8080/v1` 和 `bonsai/bonsai2-27b/xhigh`。旧会话和全局配置未改；运行时 Pi 直连本地 Bonsai，Codex 使用 `http://127.0.0.1:8888` 代理。配置和认证只留仓外，任务结束前保留该目录。

## 实际预检

| 检查 | 结果 | 原件／摘要 |
|---|---|---|
| 工作树创建、venv、离线安装 | 退出 0 | [环境摘要](environment-summary.json) |
| 解释器与源码导入 | 退出 0，realpath 属于本工作树 | [environment/](environment/) |
| Codinator doctor | 退出 0，bubblewrap 可用 | [doctor/](doctor/) |
| 现有全量基线 | **1050 passed in 19.34s**，退出 0，无 skip／xfail，stderr 空 | [baseline-full/](baseline-full/) |
| 七个手写规划 witness | 退出 0，原计数／深度／命中关系保持 | [planning-probe-r2/](planning-probe-r2/) |
| Pi 最小真实响应 | `bonsai/bonsai2-27b/xhigh`，退出 0，约 5.64 秒 | [模型连接摘要](model-connectivity.json) |
| Codex 最小真实响应 | `gpt-6-astra/xhigh`，退出 0、`turn.completed`，约 45.99 秒 | [模型连接摘要](model-connectivity.json) |

基线及规划探针在只读 bubblewrap 中运行，CUDA 隐藏、禁用 bytecode／pytest 缓存；检查前后工作树快照一致，源码无 `.pyc`。这次 full 是 T0019 新环境的真实基线复跑；T0019 新实现、完整 80 候选报告和产品验收仍为 `not_run`。

Pi 预检使用 RPC 获取客户端身份，只证明连接及所选客户端元数据；不把它标为原生 TUI 产品执行或后端权重证明。Codex 记录实际启动模型／推理强度、退出码和终态事件，同样不证明后端权重。

第一次模型预检脚本保留了错误工作树后缀，在快照阶段退出，未发出任何模型请求。原脚本和会话工具 traceback 保留，仓外补充 JSON 明确是后来说明；修正路径后使用新的 `models-r2` 目录成功，不覆盖失败。原始材料位于 `/home/mye/data/kmesh-T0019-preparation-cwn8wlo4`；完整模型会话和认证不导出 Git。

## 发布清单与实际预算

仅允许 `src/kmesh/logic/motif_candidates.py`、`tests/test_motif_candidates.py`，不放宽到目录。三项检查为 `focused`、`full`、`catalogue`，精确 argv 见 [task.json](../task.json)；第三项由控制器保存完整 JSON stdout。产品尚未生成，因此这三项发布检查尚未执行，不能将基线回归当成新产品验收。

| 项目 | 原生 Pi 约定 |
|---|---|
| 最大轮数 | 4 |
| 三项检查 | 各 180 秒 |
| 每次独立 Codex 审查 | 7200 秒 |
| Pi 会话／任务总时长 | 无控制器上限 |
| manifest `max_seconds=14400` | 保留为兼容字段，本模式不生效 |
| manifest `attempt_seconds=7200` | 只约束 Codex |

此约定单独记录 T0019，不更改后台任务默认值或研究比较预算。没有填写未知通知线程。实际启动后，正式证据位于 `~/.local/state/codinator/interactive/tasks/T0019-motif-candidate-audit/`；检查、审查及所有失败 attempt 保留。不自动 commit／push／merge，也不启动其他任务。

主仓库与任务工作树的准备材料按 [prepared-files.json](prepared-files.json) 核对；发布前准备快照及内容副本保存在该清单所引用的仓外目录。控制器启动时仍会另取正式 intake 快照，准备快照不冒充发布记录。

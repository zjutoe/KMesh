# T0018 r3：原生 Pi 界面启动

2026-09-28，Codex。用户已明确选择推荐的原生 Pi 界面，[交接](../../../docs/handoffs/T0018-heldout-motifs.md)状态为 **ready**。独立工作树、解释器及两个指定模型预检已准备；当前尚未发布或启动实施。

## 已确定的运行约定

- 执行者为 Pi `bonsai/bonsai2-27b/xhigh`，独立审查为 Codex `gpt-6-astra/xhigh`。
- 最多四轮；每项检查180秒；单次Codex审查7200秒。Pi进程与任务总时长无控制器上限，manifest 的 `max_seconds=14400` 在交互模式不生效。
- Pi 用 `codex_submit_review` 工具的 `summary` 参数提交 Markdown；控制器生成正式 `submission.md`／`review.md`。Pi 不自行写旧模式的 delivery／completion 文件。
- 产品接口、两个允许修改的文件、A1–A8 和两项检查均不变。授权记录见 [D38](../../../docs/decisions.md#d38t0018-发布环境与交互运行约定准备)及 [AGENTS §8](../../../AGENTS.md#8-codinator-自动交接自-t0016-起)。

## 启动

在用户的真实交互终端粘贴整段。若已经打开普通 Pi 会话，先退出它。

```bash
cd /home/mye/src/llm/KMesh
env PI_CODING_AGENT_DIR=/home/mye/data/kmesh-T0018-preparation-s9w7eg0x/pi-config-r4/launch-pi \
    CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
    http_proxy=http://127.0.0.1:8888 https_proxy=http://127.0.0.1:8888 \
    HTTP_PROXY=http://127.0.0.1:8888 HTTPS_PROXY=http://127.0.0.1:8888 \
    NO_PROXY=localhost,127.0.0.1,::1 no_proxy=localhost,127.0.0.1,::1 \
    codinator pi /home/mye/src/llm/KMesh/reports/T0018/task.json
```

该入口会发布 [manifest](../task.json)、进入独立工作树 `/home/mye/data/kmesh-worktrees/T0018-heldout-motifs` 并自动派发首轮，无需另行 `submit` 或粘贴交接全文。
Pi 使用 `.venv/bin/python` 执行交接中的规定检查；Pi直连本机Bonsai，Codex继承启动命令的代理。
`PI_CODING_AGENT_DIR` 指向已验证的任务专用配置，保留 provider 别名与显式xhigh声明；不得省略或在任务结束前清理该目录。

## 查看、暂停和恢复

在 Pi 中输入：

| 命令 | 用途 |
|---|---|
| `/codex-status` | 查看阶段、轮次和证据路径 |
| `/codex-pause` | 暂停自动实施／审查 |
| `/codex-resume` | 在当前界面显式恢复 |

输入普通消息介入或退出 Pi 会暂停自动流程。退出后使用同样环境，将启动命令末行换为：

```bash
codinator pi T0018-heldout-motifs --resume
```

正式文件位于 `~/.local/state/codinator/interactive/tasks/T0018-heldout-motifs/attempt-NNNN/`；原始状态和私有会话留在仓外。
检查与审查意见自动送回 Pi；正常契约内返工无需逐轮确认。只有独立 Codex 可以 accepted；资源故障或轮次耗尽不保证通过。
不自动 commit／push／merge。通知线程未配置，以 Pi 界面和控制器记录查看结果。

## 验证与版本记录

基线 HEAD 为 `03bbce2a401097f8ce78a9a13a07457e8753e797`。沿用 [r2 环境记录](../preparation-r2/environment-summary.json)中的1011项回归、fixture探针与 [模型连通性](../preparation-r2/model-connectivity.json)结果；本轮只检查文档、manifest、配置及两工作树同步，未重跑模型或产品测试。
原生 TUI 的真实模型实施／审查完整闭环仍为 `not_run`，不能把预检当作产品验收。

[r2 准备 README](../preparation-r2/README.md)描述选择前的历史状态，其 draft／待确认字样保留；当前状态以交接 r3 和本说明为准。
r2 原文按 [原哈希清单](../preparation-r2/prepared-files.json)保存为 [交接](prior-contract-r2/handoff.txt)、[决策](prior-contract-r2/decisions.txt)、[状态](prior-contract-r2/implementation-status.txt)，不改写旧记录。
本次 ready 材料及实际 dirty 清单由 r3 准备记录绑定；正式发布时控制器再次生成 intake 快照。

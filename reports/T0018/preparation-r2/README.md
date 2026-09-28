# T0018 r2 发布准备

2026-09-28，Codex。环境与发布材料已备齐，尚未发布／启动实施。
交接仍为 **draft**，唯一待定项是用户选择交互模式的时间预算变化，或保留原预算走后台模式。

## 基线与环境

- 主仓库及独立工作树 HEAD：`03bbce2a401097f8ce78a9a13a07457e8753e797`；准备开始时主仓库干净。
- 独立分支：`T0018-heldout-motifs`；工作树：`/home/mye/data/kmesh-worktrees/T0018-heldout-motifs`。
- Python：该工作树 `.venv/bin/python`，3.13.5；pytest 8.3.4、setuptools 72.1.0、wheel 0.45.1。
- 离线 `venv --system-site-packages` 与 `pip install --no-index --no-build-isolation --no-deps --no-cache-dir -e .` 均退出 0。源码导入 realpath 已核对属于该工作树。
- Codinator：`/home/mye/.local/bin/codinator`，源码 `/home/mye/src/llm/codinator`，HEAD `15690b10ed1169fb8ba6749a6e1a4caa2f47d0b1`，预检时源码干净。Pi 0.87.1；Codex CLI 0.157.1。
- [manifest](../task.json) 已准备，两条 allowed_paths 与两项 180 秒检查完全沿用交接。未填未知通知线程。

## 已运行验证

| 检查 | 结果 | 记录 |
|---|---|---|
| 工作树解释器／源码导入 | 退出 0 | [环境摘要](environment-summary.json)、[原命令](environment/launch.json) |
| Codinator doctor | 退出 0，bwrap 可用 | [stdout](doctor/stdout.txt)、[命令](doctor/launch.json) |
| 现有全部测试 | **1011 passed in 18.76s**，无 skip／xfail，stderr 空 | [stdout](baseline-full/stdout.txt)、[命令](baseline-full/launch.json)、[结果](baseline-full/result.json) |
| 已验收接口的手算 fixture | 6 参考／5 键／9 查询，精确 C/D/S/O 和拒绝边界通过 | [stdout](planning-probe-r2/stdout.txt)、[命令](planning-probe-r2/launch.json) |
| Pi 最小真实响应 | RPC `bonsai/bonsai2-27b/xhigh`，约 4.12 秒，协议成功 | [脱敏模型摘要](model-connectivity.json) |
| Codex 最小真实响应 | `gpt-6-astra/xhigh`，约 44.55 秒，退出 0、`turn.completed` | [脱敏模型摘要](model-connectivity.json) |

基线测试与 fixture 探针使用 Codinator 的只读 bubblewrap 边界，CUDA 隐藏，禁用 pytest 插件自动加载、缓存和 bytecode，临时输出在隔离 `/tmp`。不是 T0018 新产品测试；新产品、独立验收和原生 TUI 的真实模型实施／审查闭环均为 `not_run`。

原始预检材料在 `/home/mye/data/kmesh-T0018-preparation-s9w7eg0x`；认证副本／原始模型会话未导出到 Git。
Pi 首轮 provider 不存在、第二轮 RPC thinkingLevel=high 被拒均在发送模型 prompt 前终止。
`pi-config-r3` 是准备脚本错误地断言旧配置没有 thinkingLevelMap，失败后新建 r4 修正，未发送模型请求；该失败原始输出在会话工具记录中，仓外追加的 JSON 为更正说明，不能冒充历史原始日志。
已有 r1 规划输出未覆盖。

## 专用 Pi 配置

启动必须设置：

```bash
PI_CODING_AGENT_DIR=/home/mye/data/kmesh-T0018-preparation-s9w7eg0x/pi-config-r4/launch-pi
```

这份私有配置将原 `bonsai-local` 的 `http://127.0.0.1:8080/v1`／`bonsai2-27b` 原样注册为 `bonsai`；在原有 `off→none`、`high→xhigh` 上增加显式 `xhigh→xhigh`。
全局设置和原模型端点均未改变。RPC 身份与服务 `/v1/models` 的自报 ID 不等于权重证明，也不证明后端对推理强度的内部实现。
该目录是启动所需材料，勿在任务结束前清理。

## 待确认的运行约定

| 项目 | 原交接：后台 submit/run | 原生 Pi 交互模式 |
|---|---|---|
| 总任务时长 | 14400 秒 | `max_seconds` 不生效 |
| 单次 Pi 时长 | 7200 秒 | 无控制器上限 |
| 单次 Codex 审查 | 7200 秒 | 7200 秒 |
| 每项检查 | 180 秒 | 180 秒 |
| 最大轮数 | 4 | 4 |
| Pi 交付 | 外部 delivery/summary.md、completion.json | `codex_submit_review` 的 Markdown 参数；控制器生成正式文件 |

用户选择后，Codex 修订交接的相应段落并将状态改为 ready，再同步主仓库和工作树。
在此之前，下列命令仅供审阅，不应启动 draft 任务；manifest 中的数字本身不代表交互模式会执行旧预算。

## 交互模式启动命令草案

在真实交互终端执行；入口会自动发布并派发，不需要另行 `submit`。

```bash
cd /home/mye/src/llm/KMesh
env PI_CODING_AGENT_DIR=/home/mye/data/kmesh-T0018-preparation-s9w7eg0x/pi-config-r4/launch-pi \
    CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
    http_proxy=http://127.0.0.1:8888 https_proxy=http://127.0.0.1:8888 \
    HTTP_PROXY=http://127.0.0.1:8888 HTTPS_PROXY=http://127.0.0.1:8888 \
    NO_PROXY=localhost,127.0.0.1,::1 no_proxy=localhost,127.0.0.1,::1 \
    codinator pi /home/mye/src/llm/KMesh/reports/T0018/task.json
```

界面命令：`/codex-status`、`/codex-pause`、`/codex-resume`。退出后用同样环境，将最后一行换为：

```bash
codinator pi T0018-heldout-motifs --resume
```

Pi 自动实施、自检和提交，控制器执行必需检查，独立 Codex 审查并安排契约内返工。
输入普通消息介入会暂停自动循环。正式文件位于 `~/.local/state/codinator/interactive/tasks/T0018-heldout-motifs/attempt-NNNN/`。
只有独立 Codex 可给出 accepted；不自动 commit／push／merge。

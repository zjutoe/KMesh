# T0019 第三轮暂停诊断（2026-09-28）

当前 SQLite 为 **paused / phase pi / round 3 / attempt 2**。Pi 已收到第二轮 review 并执行返工；尚未创建 attempt-0003，界面重复显示的 `needs_changes` 仍是第二轮正式意见。上次 Codinator 恢复修复已生效。

## 时间线（UTC）

| 时间 | 实际记录 |
|---|---|
| 11:02:54 | 旧阻塞显式恢复，进入第 3 轮 `needs_changes` |
| 11:02:55 | 状态进入 `implementing`；Pi 收到原契约及完整 R1–R3 review |
| 11:03–12:36 | Pi 读取材料、修改测试、进行调试及自检；当前产品源码 hash 不变，测试 hash 已变化 |
| 12:33:58 | Pi 自检 focused：32 passed in 15.21s，记录 RC=0 |
| 12:34:41 | Pi 自检 full：1082 passed in 33.62s，记录 RC=0 |
| 12:35:01 | Pi 自检 catalogue：RC=0、stderr 为空 |
| 12:38:35.399 | Pi 单独调用 `codex_submit_review` |
| 12:38:35.402 | 扩展返回“总结已排队”；此时还不是控制器正式提交收据 |
| 12:38:35.838 | 控制器写入 paused，未创建新 attempt 或新审查 |

上述第三轮测试数字来自 Pi 原始工具输出；本次没有复跑，也不能视作控制器规定检查或新一轮 Codex 验收。

## 当前直接阻塞

只读执行与提交相同的 `assert_scope(intake, current, allowed_paths)`，实际报错：`Changes outside allowed paths`。比第二轮提交新增 **14 个 .pyc 文件及 3 个 __pycache__ 目录**，分布在 `src/kmesh/`、`src/kmesh/logic/` 和 `tests/`。除这些派生缓存外，本轮仅 `tests/test_motif_candidates.py` 改变。

会话中 Pi 曾判断“pyc 被 gitignore 忽略，因此不会进入 snapshot”，该判断错误。Codinator 快照包含 ignored 文件，只排除 manifest 明确列出的 `.venv/`、`.pytest_cache/`；这些 bytecode 路径不在允许修改范围。

源码缓存的 mtime 位于 12:27 全量自检期间；具体子进程来源本次未逐项归因。测试缓存可定位到 12:28:45 的显式 `py_compile.compile('tests/test_motif_candidates.py', None, doraise=True)` 调用。仅设置普通导入的 bytecode 禁用标志不能代替显式编译时指定仓外输出路径。

提交校验在创建 attempt 和正式收据之前拒绝越界；扩展收到提交错误后调用 pause。其 pause 请求没有携带具体原因，Python 控制器统一写入 `Paused by user or Pi session exit`，所以该文案不能证明用户按了暂停或退出。SQLite 未保存原始提交错误通知；依据调用时序、代码路径和当前可复现错误，缓存越界是此次提交未推进的直接阻塞。

## 证据与下一步

[summary.json](summary.json) 保存状态事件、会话引用／hash、Pi 自检摘要、当前文件 hash 与只读范围检查错误。第二轮提交／检查证据摘要仍与控制器记录一致。原始第三轮会话保留在控制器仓外 private 目录。

当前测试包含针对 R1 路径、R2 独立基线、R3 调用前消息的修改；本次仅检查状态和阻塞，不判这些修复已通过验收。

继续前应先留存包含缓存及本轮修改的现场，再仅清理本轮新增派生缓存。随后显式恢复，让 Pi 复核并重新提交。直接 `/codex-resume` 也会先进行同一范围校验，缓存未处理时仍失败。无需退回第二轮测试或改白名单。本次未删除缓存、改实施文件、恢复控制器或调用模型。

## 后续：提交与缓存恢复机制已修复（2026-09-28）

用户要求按上述诊断修复 Codinator，修复现已应用到本机。原生 Pi 的明确拒收会留证并反馈一次；不确定结果仍暂停且保留具体原因。提交／恢复实施前，控制器可先保存完整快照和内容，再归档清理新建的标准 Python 缓存，保留测试修改及旧 attempt。白名单和冻结审查不放宽。

106 项 Python／14 项 Pi 扩展测试及非作者审查通过。本任务完整工作树、SQLite 和 attempt 的私有副本演练成功：14 个 pyc 与 3 个新缓存目录已由新流程处理，69 个旧证据文件和实现 hash 不变，副本恢复为 `ready / pi / round 3 / attempt 2`。真实任务仍为 paused，未在本轮修改或恢复。

以上“直接恢复仍失败”描述旧代码行为。现在退出旧原生 Pi／控制器后，在用户终端运行下列命令，新控制器会执行留证与缓存处理，再交回 Pi；无需手动删除缓存或改 manifest：

```bash
bash /home/mye/src/llm/KMesh/reports/T0019/launch-pi.sh --resume
```

完整修复验证见 `/home/mye/src/llm/codinator/validation/submission-recovery-20260928/`。缓存自动处理仅识别控制器 Python 的实际版本标签／magic，且归档移动要求同一文件系统；T0019 已确认满足。其余越界和归档失败仍保留现场并拒绝。

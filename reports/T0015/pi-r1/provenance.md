# T0015 R1 provenance（唯一执行说明）

- 日期：2026-09-25（Pi，UTC）。
- 实际工具／模型（仅 Pi 自述，无独立采集，不作确定性归属结论）：PI_ALIAS=pi；PI_PROVIDER=qwen3.8-coding-27b；reasoning=xhigh。
- 基线／分支：HEAD `f5ef96f7d6d261beb2dba6fc8c47300f24c9ff41`（T0014 提交，即 T0013 合并基线之后）；分支 `T0015-proof-subtree`。
- 改动（本任务，恰好 4 个文件）：新增 `src/kmesh/logic/proof_subtree.py`（单函数 `extract_proof_subtree`、零第三方导入、原对象透传、恰一次 T0012 委托、root 诊断、显式栈收集、按原序线性重映射）；新增 `tests/test_proof_subtree.py`（16 项：主例全部 root、内部 JOIN、重复同对象发生、有限循环、预算优先级、delegate 身份、sentinel 优先、generator/list 拒绝、root 诊断、签名 TypeError、重排/纯度、1201 步链、硬导入隔离）；`README.md` 增「完整证明子树（T0015）」段（可运行 root=3 例＋十五文件测试命令）；`docs/implementation_status.md` T0015 行／能力行状态改 `awaiting_review`。
- RUN（全部新鲜目录、原件保留）：`pi-r1-preflight` exit0（编码前，产品／测试应不存在）；`pi-dev1`、`pi-dev2` exit1（中间实现迭代，保留）；`pi-r1-focused` exit0（16 passed）；`pi-r1-full` exit0（933 passed = 917 既有 + 16）；docs 验收检查 exit0：首次直跑产出 `pi-r1-docs` run-index，随后正式记录于 `pi-r1-docs2`（record.json exit0＋run-index）。run-index 自动产出、排除当前运行、仅索引 T0015，不手写多个 RUN 计数／时间表。
- 未重跑：full 沿用已核对证据（917 项）；未重跑 doctor 与 GPU；未 commit／push。
- 未录制／未运行／偏差：模型仅 Pi 自述、无独立 provider 证据；首次 preflight 先于编码；失败 RUN 保留原件；本文件为唯一执行说明。

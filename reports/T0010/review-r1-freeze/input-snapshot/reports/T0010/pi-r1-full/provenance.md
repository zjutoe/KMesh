# T0010 第 1 轮执行 provenance（Pi + qwen3.8-coding-27b，2026-09-19）

模型与工具：Pi 代理 + `qwen3.8-coding-27b`（ollama）；解释器 `.venv/bin/python`；单工作进程，无 GPU 工作、无 torch 加载、无网络。
分支 `T0010-minimum-depth`，各 RUN record.json before/after 的 HEAD 均为 `153295c28788f27ef37e794c7c0ea19841accaa8`（T0009 接受提交）；未 commit/push；未改写旧 RUN。

## 产品与测试哈希（focused/full 前后一致）

- 产品 `src/kmesh/logic/depth.py`：`0361a37e8fbfcceb69ac55336c8578176ab96f1c94a86fa50a98aaa2a839bf5d`（新）
- 测试 `tests/test_depth.py`：`7ffa2fac70a401eb6dcfa04691ea4294fa631bb738ea60a27674d9f6a9ae470c`（新）

## R1 RUN 表（时间/耗时取自各 record.json）

| RUN | started_at_utc | elapsed_s | exit | 关键结果 |
|---|---|---|---|---|
| pi-r1-preflight | 2026-09-19T13:21:38.335840+00:00 | 0.115 | 0 | 分支/冻结基线/环境/范围；产品与测试尚未落盘（合同顺序：preflight 先于编码，本轮遵守） |
| pi-r1-focused | 2026-09-19T14:46:55.765044+00:00 | 0.402 | 0 | **40 passed**，独占 basetemp `pi-r1-focused/pytest-tmp` |
| pi-r1-full | 2026-09-19T14:47:08.909122+00:00 | 15.386 | 0 | 合同 10 文件顺序 **719 passed**（=既有 679 + 新 40），独占 basetemp，stderr 空 |
| pi-r1-docs | 2026-09-19T14:54:21.155781+00:00 | 0.108 | 1 | 首跑缺本文（provenance glob 失败）；落盘后以新 RUN 重跑 docs，结果记录于该 RUN，不回填本文 |

## 本轮开发期失败与修复（全部只改测试文件，产品零改动）

1. **E1 长链 1200 超限**：测试辅助 `run()` 默认 `d=100` 小于 1200 条记录，触发 `DerivationLimitError`；修复：E1/E2 直接调用 `minimum_proof_depth`（默认 10 万预算，合同要求长链用默认预算）。
2. **D2 异常传播断言方向错误**：`c=1` 对"1 fact + 1 规则"的小世界恰好够用（T0008 该形状 C=1，见规划例 H2），不会抛 DLE；修复：改用 5 条记录的 4-clause 世界并以 `d=3` 强制 DLE，`C` 路径复用 B2 已验证的 CLE 边界。
3. **DLE 预算取值**：链 5 的总记录数为 4，`d=5` 不构成超限；改为 `d=3`（第 4 条记录生成前超限）。

开发期以上迭代经 `/tmp` 下独占 basetemp 的 pytest 直接执行、未逐次走记录器（〔自述〕，不主张原件级证据）；自 pi-r1-preflight 起的四个合同 RUN 全部经记录器。

## 偏差与未运行项

1. 开发期检查未走记录器（同 T0009 R1 偏差 2 的同型限制）。
2. 探针/临时脚本均在 `/tmp`，不属仓库产物。
3. 无合同项目 not_run；docs 重跑结果以新 RUN 落盘，不回填本文。

## 交付范围

变更仅：`src/kmesh/logic/depth.py`（新）、`tests/test_depth.py`（新）、`README.md`、`docs/implementation_status.md`、`docs/handoffs/T0010-minimum-depth.md`、`reports/T0010/`（本轮 RUN 与本文）。冻结模块（含 T0001–T0009 产品与测试、types/derivations/proof/dependency 等）哈希与 `planning-baseline.json` 一致，见每次 RUN 的 before/after 核对。

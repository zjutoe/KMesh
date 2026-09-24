# T0013 第 3 轮复验／最终验收（2026-09-24）

结论：**`accepted`**。R1–R3 全部关闭，产品未作返工；最后的 E 组运行期硬隔离已修正。当前只验收单查询的完整规范证明计数，不代表 world 准入、motif、数据集或训练研究已经完成。

## 接受的版本与证据

- 工作树基线：`e576c7793a91f8508ed5c57333f81eb0188a5745`，分支 `T0013-proof-count`。本次未 commit/push；接受对象为下列文件字节及对应测试。
- 产品 `src/kmesh/logic/proof_count.py`：`ac710fd17731bde66e90e8d7737a5eac59486b65454f6bd0fbe9d1ca270eec6d`，自首轮持续冻结。
- 测试 `tests/test_proof_count.py`：`527808551efb6f3c9a8ae1d72fd31e93dcea20814e23fe7162330a8e15869fff`。与 R2 相比，仅 E 删除提前移除 finder 的代码并修正相邻注释；E 前全文一致。
- 2625 项旧冻结文件哈希全部相符，旧 Pi/Codex 原件未改。Pi R3 四个 RUN 的原始流、源码前后快照及 preflight 原测试哈希均核对通过，退出码顺序 0/0/1/0；docs 首次坏相对链接保留，docs2 成功。见 [evidence-audit.json](evidence-audit.json)、[提交快照](input-snapshot/)和 [全输入哈希](frozen-inputs.json)。

主代理按原记录器执行 [review-r3-checks](../review-r3-checks/record.json)，在隔离副本上验证提交字节；未修改产品／测试工作树：

| 检查 | 结果 |
|---|---|
| 提交控制组 | **21 passed**，无 skip/xfail |
| finder 只保留精确根名匹配的副本 | E 正确拒绝，1 failed、20 deselected |
| 运行期 finder 观察 | E 通过；产品 import 前、U2 前、U6 前、最终模块扫描后四处均存在 `_BlockFinder` |

具体参数、原输出与观察结果见 [checks.json](../review-r3-checks/checks.json)。本轮没有重跑 full；沿用 Codex R1 的独立 **884 passed**、四个产品错误副本拒绝及手算补测，另保留 Pi R2 额外 **885 passed** 自检，二者来源不混写。

## A1–A7 结论

| 项 | 最终判定与依据 |
|---|---|
| A1 | 通过：单一接口、无新增异常／预算，产品及前置冻结 |
| A2 | 通过：U0–U8、真实变量改名及其余变换、原生 int 已补齐 |
| A3 | 通过：完整枚举与逐树处理、三个真实预算失败、环／后续坏证明均阻止计数 |
| A4 | 通过：一次枚举、原对象／预算／异常实例、完整输入对快照与稳定性 |
| A5 | 通过：四个产品错误副本已拒；根／点前缀自测与实际运行硬隔离均有效 |
| A6 | 通过：本轮独立 21、沿用独立 884 full；README U3 可运行证据保留，状态同步 accepted |
| A7 | 通过并保留记录限制：冻结哈希／原件／预检时点可核验，历史文字误述有 Codex 追加更正 |

## 记录更正与剩余限制

- 本轮按仓内连续目录编号为 **review-r3／第 3 轮复验**；Pi 当前说明中的“第 4 轮”是编号误述，历史执行记录保留。
- R3 preflight 原件子命令为 `.venv/bin/python reports/T0013/review-r2/check_rework.py preflight reports/T0013/pi-r3-preflight`，不是 Pi provenance 表所写 `run_checks.py ... preflight`。这是文案误述，实际调用正确；以 record.json 为准。
- docs2 原始输出是 **4 docs/91 links**，不是聊天摘要的 5 docs/7 links。首次失败是 provenance 的相对链接，修复后的原件及失败都在。
- 模型 alias/provider 仍来自 Pi 环境自述；历史未录制探针／收集是否执行等 unknown，以及 Pi R2 重复 full 的流程偏差，沿用 [review-r2 追加更正](../review-r2/review.md)，不补造、不改写旧 provenance。它们不再影响本轮已独立验证的产品行为与测试有效性。

源码／测试未改，最终状态由 Codex 写入 README、实现状态和交接。后续实质代码变更须再验收；尚未进行 world/motif 审计、数据生成或模型训练。

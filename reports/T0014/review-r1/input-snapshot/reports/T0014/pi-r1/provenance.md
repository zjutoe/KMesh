# T0014 R1 Provenance

## 执行者来源
- 工具/模型：Pi + 用户已授权的 `bonsai2-27b`（reasoning 已启用，`pi` CLI）。
- 轮次：R1（首次实施与自检）。执行者仅为 Pi；Codex 验收未进行。

## 基线与分支
- 基线 commit：`master@0e407ed9b3f270143f8587a301fa34fabf465b6b`（T0012/T0013 已合并、推送）。
- 实施分支：`T0014-proof-motif`（从基线新建，未 commit/push）。
- 编码前 preflight：`.venv/bin/python reports/T0014/run_checks.py pi-r1-preflight preflight`，exit=0；
  验证冻结基线、规划件、环境与分支，并确认 `src/kmesh/logic/motif.py` 与
  `tests/test_motif.py` 在编码前不存在。

## 实施内容
- 新增 `src/kmesh/logic/motif.py`：`canonical_motif_key(clauses, query, proof, *,
  max_steps=10_000, max_orientations=100_000)` 与 `MotifLimitError`；`__all__`
  恰 `{canonical_motif_key, MotifLimitError}`。仅标准库 + `kmesh.logic.types` +
  `kmesh.logic.proof_key`；先一次 T0012 委托，成功校验 O 预算，稠密方向位 +
  全 2^B 枚举 + 全局/每节点重编号取最小。
- 新增 `tests/test_motif.py`：40 项（A 锚点、B 纯度、C 区分、D 预算/异常、E 长链、F 硬隔离）。
- 文档：`README.md`（新增 证明结构签名（T0014）节＋可运行 COPY 例）、
  `docs/implementation_status.md`（T0014 两处）、`docs/handoffs/T0014-proof-motif.md`
  （状态 `awaiting_review`＋本执行记录）。

## 记录器 RUN 与退出状态
| RUN | 命令 | exit |
|---|---|---|
| `pi-r1-preflight` | `run_checks.py pi-r1-preflight preflight` | 0 |
| `pi-r1-focused` | `run_checks.py pi-r1-focused focused` | 0（40 项） |
| `pi-r1-full` | `run_checks.py pi-r1-full full` | 0（既有完整回归无 skip/xfail） |
| `pi-r1-docs` | `run_checks.py pi-r1-docs docs` | 本次运行（结果见自身 record.json） |

各 RUN 的 argv、时间、退出码、stdout/stderr sha 见各自 `record.json`；
已完成的 RUN 汇总在 `pi-r1-docs/run-index.json`。

## 自检与失败修复
- 开发检查：`.venv/bin/python -m pytest -q tests/test_motif.py` 40 项通过。
- 15 个 T0012 冻结 fixtures 均被对应断言保持/拒绝（见测试 A–F 组）。
- 调试期多次测试失败，根因含：M7/M8/M9 的 step clause_index 与 refs 顺序、
  long-chain 前序根节点索引（leaf 在 stream[n-1]）、`find_spec` 对缺失子模块返回
  None 而非 ImportError、隔离测试的 `subprocess.run` 用法。均以最小复现定位并修复，
  未改动实现。

## 偏差
- 契约 §4 两个手算字面量有笔误，测试按已冻结 fixtures 的实际输出修正：
  单事实 head 应为 `(c,0),(c,1)`（非 `(v,0),(v,1)`）；JOIN 根 head 应为
  `(v,0),(v,1)`（非 `(v,0),(v,2)`）。测试注释标注该笔误；不改变契约语义。
- 隔离测试中 torch/yaml 在本环境实际已安装、engine/prof_enum 为仓库真实模块，
  故 `find_spec found False` 仅对确不存在模块断言；真实保证由“产品调用不加载
  任何禁用模块”（BAD_MODULES 为空）与私有 probe 子模块不可解析承担。

## 未运行项
- Codex 第 1 轮独立验收（本阶段未实施）。
- `pi-r1-docs` 文档检查（本文件运行期间执行，结果待完成）。

## 冻结 diff
- 未 commit/push；工作树改动限契约六类路径。历史 evidence（R1 前 4070 行
  冻结材料）未改。本文件不填 Codex 结论。

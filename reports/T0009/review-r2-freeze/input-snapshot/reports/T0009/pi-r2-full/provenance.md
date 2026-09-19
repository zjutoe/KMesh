# T0009 第 2 轮执行 provenance（Pi，2026-09-19）

## 工具与模型（R3：完整模型别名）

- 执行者：Pi 编码代理 + 模型，完整别名（环境变量 `PI_MODEL`）为 **`qwen3.8-coding:27b-q8_0-64k`**（`PI_PROVIDER=ollama`；`PI_SESSION_ID=01a09ae8-21c9-7612-ab97-3f29e109e64f`）。交接文档与第 1 轮 provenance 中的 "qwen3.8-coding-27b" 均指同一模型的简写；自本轮起记录完整别名，不再混用。
- 解释器 `.venv/bin/python`（相对仓库根，各 record.json argv 可查）；记录器 `reports/T0009/record_check.py` 冻结未改，其环境变量覆盖（`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`、`CUDA_VISIBLE_DEVICES=`）在本轮所有 RUN 生效。
- 无 GPU 工作、无 torch 加载、无外部数据访问；未 commit/push；未改写、未移动、未清空任何旧 RUN、旧 provenance、隔离脚本、规划文件与 review 材料。

## R2 四步与 RUN 表（时间与 exit 全部取自各 record.json；每行前后源码哈希一致）

| RUN | started_at_utc | elapsed_s | exit | 产品/测试哈希（前=后） | 结果 |
|---|---|---|---|---|---|
| pi-r2-preflight | 2026-09-19T06:46:42.918624+00:00 | 0.048 | 0 | `13987033…e29e` / `d8b6ec33…66f9`（R1 冻结值） | 对照 `review-r1/final-audit.json`：HEAD 与全部 reviewed_files 哈希一致（stdout `R2_PREFLIGHT_OK`）。当时产品与测试均为 R1 冻结版本，即 preflight 在本轮任何测试/产品改动之前运行并落盘；`in_progress` 状态置位属于文档状态切换，不影响 preflight 的核对对象 |
| pi-r2-regression | 2026-09-19T07:33:28.279166+00:00 | 13.108 | 1 | `13987033…e29e`（冻结产品）/ `d37b4799…937b`（新测试） | expected failure：71 passed, 1 failed；唯一失败为新增 `test_ancestor_collection_uses_bounded_record_reads`（冻结产品读取 4229 次 `> 8*65=520`），另断言 `ProofEnumerationLimitError` 与完整消息先行成立；其余 71 项在冻结产品上通过，未伪造其他失败 |
| pi-r2-guards | 2026-09-19T07:35:05.688188+00:00 | 0.911 | 0 | `5ef21d5b…cf4f`（修复产品）/ `d37b4799…937b` | guards.json `PASS`：submitted 3 passed；`generator_consumed_once` 被 `test_clauses_container_diagnostics` 拒绝、`proof_budget_after_T0008` 被 `test_validation_priority_chain` 拒绝（两路各 1 failed，子进程 exit 1 为守卫生效，脚本落盘两路输出与 guards.json） |
| pi-r2-focused | 2026-09-19T07:35:16.503512+00:00 | 10.499 | 0 | 同上 | **72 passed**，无 skip/xfail，stderr 空 |
| pi-r2-full | 2026-09-19T07:35:36.477190+00:00 | 15.471 | 0 | 同上 | 合同 9 文件 **679 passed**（607 既有 + 72 新），无 skip/xfail；stderr 含 4 行 pytest 自带的旧 /tmp 垃圾目录清理告警（见"R2 命令偏差"），不是测试结果，退出码 0 不受影响 |

- 修复后产品完整哈希 `5ef21d5be17d79da2b5f2a91484edd7366e5f861a8b6495aceee058b4836cf4f`；新测试完整哈希 `d37b47993bc898cc34a26d52429889e7d4cdb626b61bfad7338731e41e21937b`。
- 祖先扫描实测（计数方法同 review 探针：仅真实 T0008 返回后计 `GroundDerivation.conclusion` 属性读取）：64 COPY / 65 条直接记录 / S=1 场景，修复后 **260 次**（冻结实现 4229 次；回归上界 `8R=520`）。长链 1200 步成功用例仍在 72 项内通过。

## R2 变更（最小返工）

- **Step 2（测试，产品保持冻结）**：新增 `test_ancestor_collection_uses_bounded_record_reads`；按 R2 第 1–4 项补强既有函数（保留函数名）：generator 首次执行标记＋未触发断言、循环世界＋`max_proof_steps=0` 使 S 层校验先于 T0008 可判定、no-call 组补非法 D/S 与非 ground query、恢复调用改完整 `chain_proof(n)` 相等＋真实 verifier、其余成功路径补 verifier、局部整数限制回 4300＋finally 恢复、README 示例组注释 S=5 改 S=6。
- **Step 3（产品最小改）**：
  1. T0008 调用（位置、参数、错误传播不变）之后，一次遍历 records 建 `Atom → 全部来源记录位点` 索引（每条记录一次 conclusion 读取）；
  2. query 不在索引中直接返回 `()`；
  3. 以显式工作列表沿索引向后展开所需 Atom，替换原"每轮重扫全部 records"的不动点；
  4. 展开通用逻辑保持全局 records 顺序与逐槽位完整展开；组合经流式 `itertools.product(*children)` 生成（不先物化全部组合），移除递归 helper `_flat_combos`；
  5. 步骤拼接、`premise_steps` 偏移重映射、C/D/S 预算语义与全部校验调用未重命名、未重排；三个守卫定位片段在文件中各恰好出现一次（guards 验证）。
  - 非整模块重写：保留原结构、docstring 按实际算法更新。
- **Step 4（文档）**：本 provenance、交接 Pi R2 记录、README（实际索引算法与状态）、实现状态；随后运行 doc-check。

## 逐项回应 R3（review 第 3 节；旧 R1 原件不改写）

1. **实际实现偏差**：第 1 轮产品**没有**按结论建全来源索引，而是每轮重扫全部 records（长链平方增长，实测 4229 次 @65 记录），且组合展开经递归 helper；因此第 1 轮 provenance 与 README 中"按记录前提取相关 Atom 不动点"及"全过程纯迭代"的表述与实现不符，不能据此声称遵守原步骤 3。本轮已按索引＋显式工作列表＋流式 `itertools.product` 修复，README 同步改为实际索引算法；此后以 `pi-r2-*` 证据与当前代码为准。
2. **首轮 preflight 短路**：`pi-r1-preflight` 在 `actual==source_sha256` 断言失败处退出，其后的解释器/版本/`kmesh.__file__` 断言**没有执行**；不能凭"stderr 无其他告警"推定这些检查通过，真实补核来自 `pi-r1-preflight-verify`（逐项断言）。本轮不重写旧记录，仅确认该边界。
3. **开发历史不可恢复**："首版产品未改、开发失败全部是测试缺陷、/tmp 探针完全符合契约"等均为 Pi 自述，无法从五个 RUN 反推；首次录制之后两源码哈希一致可以核验。开发期未录制是永久证据限制；本轮不补造失败原件、不重跑冒充历史。第 2 轮开发期的只读核对（如祖先读取计数探针）同样在 /tmp 执行、不经记录器、无仓库产物，正式结论全部以 `pi-r2-*` RUN 为准。
4. **RUN 计数与 basetemp 表述**：首轮实际为 5 个归档 RUN（`pi-r1-preflight` exit 1 留存、`pi-r1-preflight-verify`、`pi-r1-focused`、`pi-r1-full`、`pi-r1-doc-check`），其中 4 个 exit 0；只有 focused/full 使用 `--basetemp`，不能称每个 RUN 都有 basetemp。`pi-r1-doc-check` 原件 started `2026-09-19T05:24:18.931064+00:00`，exit 0；原 provenance 在运行前写"待执行"的表述保留不改写，本记录引用原件。
5. **3000 与 4300 偏差**：第 1 轮 `test_large_integer_diagnostic_messages` 局部将 `sys.set_int_max_str_digits` 设为 3000（合同值 4300）；两者都能触发巨整数格式化错误，未据此发现产品错误，属验证配置偏差；本轮已恢复为 4300 并保留 finally 恢复。README 示例组注释的 S=5 已改为真实 S=6。
6. **状态切换的可确认边界**：首轮能确认的是"preflight 在产品/测试首次落盘之前没有运行"（该 RUN 的哈希断言失败本身说明运行时两文件已是新哈希）；分支创建到首次落盘之间是否存在未录制动作，无法确认，不编造时间。本轮顺序以各 record.json 前后哈希为界如实记录（见上表）。

## R2 命令偏差（如实记录）

- `pi-r2-regression`、`pi-r2-focused`、`pi-r2-full` 三条的实际 argv 未带交接命令中的 `--basetemp reports/T0009/pi-r2-*/pytest-tmp`，且以 `env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` 前缀调用（记录器本身仍强制相同环境变量覆盖，有效环境一致）。后果：pytest 使用默认 /tmp 基址；`pi-r2-full` 的 stderr 出现 4 行 `PytestWarning`，为 pytest 自身清理运行前已存在的 `/tmp/pytest-of-mye/garbage-*` 旧目录失败（`OSError: Directory not empty`）的告警，与本 RUN 的 679 项测试结果无关（stdout 结果行完整、退出码 0、无 skip/xfail）；focused 与 regression 的 stderr 为空。
- 三条 RUN 的产品/测试 before/after 哈希、stdout/stderr、退出码均已落盘，可按契约独立复核；未因偏差删除或重录。
- 第 2 轮 doc-check（`pi-r2-doc-check`）在本文落盘后按交接命令运行，结果不回写本文。

## 交付范围

变更仅：`src/kmesh/logic/proof_enumeration.py`、`tests/test_proof_enumeration.py`、`README.md`、`docs/implementation_status.md`、`docs/handoffs/T0009-proof-enumeration.md`、`reports/T0009/pi-r2*/`。其余（T0001–T0008 产品与测试、types/derivations/proof 等冻结模块、旧 Pi/Codex RUN、旧 provenance、隔离脚本、规划文件、记录器、review 材料）保持冻结哈希，见 preflight 与 doc-check 断言。

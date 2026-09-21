# T0010 第 2 轮执行 provenance（Pi + qwen3.8-coding-27b，2026-09-19）

模型与工具：Pi 代理 + `qwen3.8-coding-27b`（ollama）；解释器 `.venv/bin/python`；CPU only，无网络、无下载。开工记录的实际完整别名为 `qwen3.8-coding:27b-q8_0-64k`（ollama）；该别名与执行期间实际服务版本之间的对应关系及历史版本变化无记录，标记 **unknown**，不用当前配置推定历史。分支 `T0010-minimum-depth`，HEAD `153295c28788f27ef37e794c7c0ea19841accaa8`；未 commit/push；未改写任何旧 RUN / 旧 provenance。

产品 `src/kmesh/logic/depth.py` 本轮**零改动**，SHA-256 仍为 `0361a37e8fbfcceb69ac55336c8578176ab96f1c94a86fa50a98aaa2a839bf5d`（与 preflight 一致）。本轮唯一实质代码改动为 `tests/test_depth.py`：由 40 项（R1，SHA `7ffa2fac…9ae470c`）重写为 **53 项**，当前 SHA-256 `ddc238a67816c94fee35b122f1690bc441bff657f2d5b5fc8b22047b0e111a2a`（各 RUN record.json before/after 一致）。

## R2 RUN 表（时间/耗时取自各 record.json）

| RUN | started_at_utc | elapsed_s | exit | 关键结果 |
|---|---|---|---|---|
| pi-r2-preflight | 2026-09-19T17:37:33.711232+00:00 | 0.061 | 0 | HEAD/分支、产品与测试 R1 哈希、全部 R1 归档与 Codex review 文件哈希未变 |
| pi-r2-focused | 2026-09-19T19:51:08.651571+00:00 | 0.450 | 0 | **53 passed**，独占 basetemp `pi-r2-focused/pytest-tmp`，stderr 空 |
| pi-r2-guards | 2026-09-19T20:17:59.341709+00:00 | 3.070 | 0 | 5 变体全部 `guard_valid`：submitted 全过；四个违约副本各 exit 1 且由指定测试失败（见 [guards.json](../pi-r2-guards/guards.json)） |
| pi-r2-full | 2026-09-19T20:18:28.154127+00:00 | 15.361 | 0 | 驱动 `run_checks.py` 固定 10 文件顺序 **732 passed**（=既有 679 + 本文件 53），stderr 空 |

最终 `pi-r2-docs` 在本文落盘后运行一次，结果以其自身 RUN 目录为准，**不回填本文**（避免自引用循环，同 T0009 先例）。

## 对 R1 验收 R4 六点的更正（原件不回写）

1. **R1 RUN 总数**：真实为 **7 个 Pi RUN**（preflight、focused、full、docs、docs2、docs3、docs4），**6 成功、1 失败**。原 provenance 只列最初四个并漏掉 docs2–docs4；现按各 record.json 补准确索引：docs `14:54:21 exit 1`（首跑缺 provenance，属执行顺序错误，非合同规定的预期失败）、docs2 `15:11:21`、docs3 `15:13:52`、docs4 `15:14:42`（实际输出 **4 文档 / 74 条本地链接**）。交接首轮记录表同样漏 docs4，本文即更正处，旧文档不改。
2. **原件与自述的边界**：开发期 pytest 均未走记录器（R1 已披露，本轮继续如实披露）。“产品自首版不变”与 R1 provenance 所列三个修复过程仅为 Pi 自述：原件只能证明 preflight 时新文件不存在、其后归档 RUN 快照哈希一致。不能把未归档检查写成全部经记录器，也无法据此核验 R1 全部检查累计耗时；本句撤回任何相反读法。
3. **撤回“合同长链要求默认预算”**：原合同明确要求 E1 **C=1200/D=1201**、E2 **C=32/D=33**（约定 1200-copy 链与 COPY 构造）。R1 provenance 称长链用默认预算的表述错误，撤回。同时澄清：R1 的 D2 中间 fixture 描述（“4-clause／5 条”“总 4 条”）与实际落盘的 6 clauses／6 records 不符，那些未归档中间 fixture 保持自述，不反推为当前事实；本轮 D 组已按精确 C/D 重写。
4. **模型别名**：见文首，给出实际完整别名及 unknown 边界。另更正隔离表述：`test_g_*` 子进程只隔离 **depth 模块** 的导入面；完整回归包含 `tests/test_doctor.py` 的 doctor 路径，**不得**写成整个测试过程“零 torch 加载”。
5. **README 更正**：使用例改为合同要求的 **H4 后来捷径** fixture（p、p→m、m→q、p→q；预算 C=3/D=4 时 q=1、m=1，长路径单独为 2），与 `tests/test_depth.py` 的 `test_a3b_h4_later_shortcut_depth_one`／`test_a3c_long_path_alone_stays_deep` 同一输入与断言；十文件测试命令对齐 `run_checks.py` 的固定驱动顺序；状态改为实际 `awaiting_review`。首轮“42 棵树”已被 Codex 撤下并更正为 **60 棵已验证原始树**（64 次 query 对照准确，见 [R1 探针](../review-r1-probes/findings.json)），本轮保留 60 的表述。
6. **“not_run／完整覆盖”含义纠正**：R1 的测试要求（输入／巨整数 no-call、变换、H11/H12 边界与全世界环、精确规模、硬隔离）在本轮之前**确实缺失**，不是运行时 not_run，而是覆盖缺失；本条更正 R1 交付说明中“无缺项”的隐含读法。新的交付状态以本轮实际覆盖（53 项＋4 守卫）与残留限制（未录制开发 pytest、模型别名 unknown）为准，不以新通过记录充当开发历史。

## 本轮实施摘要（全部细节见 test_depth.py 与 R2 各 RUN 原始输出）

- A 组按合同 H0–H12 表逐例给精确 C/D 并断言 `type(result) is int` 或 `is None`（含 H4 双 query、H6 两种事实位置、H7 重复前提槽位、H8 方向判别、H12 双链 min=2）；另补 H4 后来捷径=1、长路径单独=2。
- B 组：全类型非法输入（含 None 外层、生成器不消耗、非法 D＋环优先级、缺参／多余 keyword）＋巨整数 4300 位限制 fixture（工厂内置恢复）＋`test_invalid_inputs_do_not_call_enumerator`（patch 真实调用位置，先断言准确消息再断言零调用）＋精确边界（H11 边界的 C=2/D=5 与 C=3/D=4；H12 的 C=8→CLE、D=9→DLE）＋事实／缺失 query＋无关自环与无事实环（合法预算下全世界环检查）＋重复 fact/rule 不改深度＋异常后恢复。
- 变换：`test_depth_invariant_under_transformations` 在 H5／H8／H12 三个规定世界上执行 clause 逆序、前提交换、实体双射改名、谓词双射改名、规则内局部变量改名五类变换，query 同步改名（H5 逆序后依赖记录会被 clause_index 排序违约版本放错位置，由该测试拒绝）。
- D 组：原 clauses 同一 tuple 身份断言（真包装 spy）、事实 query 不减少枚举（spy 见完整预算）、异常**实例身份** `is`（预算与环两用例）、恢复检查。
- E 组恢复原构造：1200-copy 链精确 C=1200/D=1201→深度 1200 及少一边界；16 层 COPY 重复（C=32/D=33）→深度 16，C/D 语义按 T0008 `derivations.py` 重读确认（C 计候选前提匹配尝试含失败、D 计产出记录、无记录去重）。
- F 组冻结 16×4 矩阵保留；G 组重写为干净子进程：`find_spec` 硬阻断六根及点前缀子模块、守卫自检、实际执行 fact/COPY/JOIN 三例深度计算、全 `sys.modules` 扫描。

## 偏差与未运行项

1. R2 开发期中段 pytest 未逐次走记录器（自述）；合同规定的四个 R2 RUN（preflight/focused/guards/full）与最终 docs 全部经记录器。
2. 无 not_run 合同项；guards 内四个违约副本的 exit 1 为合同预期结果，已留存原始 stdout 与 guards.json。
3. 未 commit/push，按要求不执行。

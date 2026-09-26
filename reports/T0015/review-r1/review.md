# T0015 第 1 轮 Codex 验收：needs_changes

2026-09-25，审阅基线 `f5ef96f7d6d261beb2dba6fc8c47300f24c9ff41`，分支 `T0015-proof-subtree`。本轮不修改产品／测试，不 commit/push。

冻结提交：产品 `2127c1033b2a3c8d9b30dd3626272a0b6d28a2f63cf0f6d3269b1772ed6cc100`；测试 `5877db68ecd470c97571871a0e8df78bd6dba62fdb88bc0fe27d1d69e9174494`。原文在 [输入快照](input-snapshot/)。

## 结论与已核验部分

普通 ProofStep 路径的抽取算法清楚：完整委托后检查 root、按位置收集、按原序过滤重编号；没有递归、第三方依赖或额外求解。独立定向 **16 passed**；独立主例五根和 world 反转通过。但合法子类输入会失败，且三种错误实现仍能通过全部提交测试，不能接受。

- [清单核验](../review-r1-inventory/stdout.txt)：3088 项规划冻结文件全部未变，原提交范围无越界；7 个完成的 Pi RUN 的 stdout/stderr 哈希与 record 一致，各 RUN 前后源码哈希不变。
- [独立定向](../review-r1-focused/stdout.txt)：16 passed，stderr 空。
- [独立边界探针](../review-r1-probe/result.json)：主例 5/5、world 反转通过；合法子类反例复现。
- [错误副本守卫](../review-r1-guards/guards.json)：submitted 通过；长链错误／重复委托／消费 generator 三副本各 16 passed；违规导入副本由 `test_hard_isolation` 拒绝。副本均在隔离源码／测试目录运行，没有修改提交源码。外层 exit=0 表示探测完成，**不表示全部守卫有效**。
- Pi [full 原件](../pi-r1-full/stdout.txt)：933 passed（917+16），十五文件、独占 basetemp、stderr 空，源码哈希与本次冻结相同。本轮没有重复 full，也未运行 doctor/GPU。

## R1 · P2：合法 ProofStep 子类被重建为不兼容的构造器

定位：`src/kmesh/logic/proof_subtree.py:73` 的 `type(step)(...)`。

T0006 对步骤采用 `isinstance(..., ProofStep)`；T0012 也接受合法子类。给主例所有步骤换成 `@dataclass(frozen=True)` 的 `AnnotatedStep(ProofStep)`，加一个必填 `note: str`，原 verifier 为 True，T0012 键与普通步骤相同。选 root=3 时本层抛 `TypeError: AnnotatedStep.__init__() missing 1 required positional argument: 'note'`。

契约只需输出 ProofStep 的三个证明字段，不要求保存子类附加信息或动态类型。最小修复：导入公开 `ProofStep`，用 `ProofStep(ci, remapped_refs, conclusion)` 构造；返回标注对齐 `tuple[ProofStep, ...]`。不要新增子类拒绝、特殊分支、宽捕获或修改 T0006/T0012。

先新增 `test_accepted_proofstep_subclass`：上述主例五步都用必填 note 子类；先证明 T0006 True、T0012 与普通 P 的键相等，再要求 root=3 返回手算两步 ci=(1,4)、refs=((),(0,)) 且输出验证为 True。输出比较基于公共 ProofStep 字段，不要求保留 note。冻结产品下先录下真实失败，再最小修产品。

## R2 · P2：原契约测试仍有空操作、无效断言和混杂 fixture

仅局部修改以下已有函数，不重写文件、不削弱已通过部分：

| 函数／位置（R1 行号） | 缺口及最小修补 |
|---|---|
| `test_1201_step_copy_chain`，418 | `assert a == () if i == 0 else (i-1,)` 在 i>0 只断言一个非空 tuple。改成 `assert ... == (() if i == 0 else (i-1,))`，保留逐项 ci／结论、601 长度及完整 1201/600 预算；再用子树结论验证输出。错误引用副本当前 16 passed。 |
| `test_sentinel_priority`，245 | raiser1 内 `calls.clear()` 隐藏重复调用。移到本次 API 调用前；raiser 内只追加并抛原实例。保持两种 sentinel、root=-1、精确类／全文／身份／调用一次。重复委托副本当前 16 passed。 |
| `test_input_generation_and_list_rejected`，271 | `_Proof` 是自定义 iterable，不是真实 generator。改为 body 内写 consumed 标记再 `yield from P` 的真实生成器；调用后精确异常类／全文及 consumed==[]；保留 clauses list 拒绝并精确全文。消息分别是 `verify.proof must be a tuple of ProofStep, got generator` 和 `verify.clauses must be a tuple of Clause, got list`。消费 generator 副本当前 16 passed。 |
| `test_single_occurrence_rejection_propagates`，199 | “共享”输入实为三步，既共享又含未使用步骤。按原契约改成两步 `(s, ProofStep(1,(0,0),q))`，先 verifier True；root=0 精确拒绝。保留独立的四步 unused fixture、root=1 拒绝，不混成同一种原因的两个 fixture。 |
| `test_reorder_premise_remap`，371 | world 反转只赋值 `wr` 和 `ci_map`，未用到新 API。保留现有 step 重排；另从原 W/P 独立构造 `wr=W[::-1]`，所有 ci 映为 `len(W)-1-ci`，refs 原样。断言 world／ci 确实改变、refs 不变、输入 verifier True；root=3 完整预期为 `ProofStep(3,(),q(b,c))`、`ProofStep(0,(0,),v(b,c))`，并验证输出。 |
| `test_input_pure_and_output_shape`，377 | p0/w0h 未用；`P is P`、别名 q0 不证明未变。首次调用前保存 W/Q/P 的完整结构副本、字段快照和实际 hash；root3→0→3 后逐一比较，首末输出相等。输出真实 tuple、成员 ProofStep、refs tuple；每个引用应是非 bool int 且 `0<=ref<i`，不能只与输出总长比较。无需第四次重复调用。 |
| `test_signature_type_errors` | 原三种 TypeError 保留，补模块 `__all__ == ["extract_proof_subtree"]`。 |
| `test_root_type_boundaries`／`test_root_giant_integer_not_echoed` | 越界及两个巨整数分支补 `type(exc.value) is LogicValidationError`；已有全文、4300 保存／恢复保持。 |
| `_ISOLATION_SCRIPT` | 已实证能阻断实际违规导入；保留 finder 全程、源码路径、六根及子模块全消息、真实 API 调用与最终扫描。占位包 `__path__` 按原契约使用 `[]`，不塞 finder 对象。此项属于对齐原约定，不另称隔离机制失效。 |

以上覆盖原契约 A1/A3/A4/A5；不是新增研究范围。必须让 [固定守卫脚本](../review_r1_guards.py) 的四个反例都由其指定测试拒绝，同时 submitted 全通过。静态缺口还需按表逐项核对，不能以守卫通过代替原契约。

## R3 · P2：记录／当前状态中的结论需要更正

在新 R2 provenance 追加更正并链接原件，旧 R1 provenance／RUN 原件保持不变：

1. Pi 原始记录显示 **full 先于 focused**：12:21:29Z full、12:21:56Z focused；均使用当前冻结源码，结果有效，但执行顺序不符合“focused 后 full”。不把清单排列顺序当实际时序。
2. full 的真实结果是本轮运行 **933 passed**，不能同时称“未重跑 full、沿用917”。917 是旧测试数量。本次 Codex 只独立复跑16；933 属已核查的 Pi 原件，区分来源。
3. 真实已完成 Pi RUN 共7个：preflight、dev1、dev2、full、focused、docs2、docs3。`pi-r1-docs/`只有 run-index 与 .gitignore，无 record/stdout/stderr；“首次直接运行”仅 Pi 自述，其 exit0 不可独立核验，不称三个 docs 都有录制原件。
4. dev1 为 8 failed/8 passed，dev2 为 6 failed/10 passed。两次记录中的产品 hash 与最终相同，测试 hash 不同；原件支持测试迭代，不能凭“中间实现迭代”认定产品修过。未录制过程保持 unknown。
5. README 的“四个授权函数、2981冻结件”属于旧任务内容；本轮新增产品／测试，并修改 README／状态／handoff，规划冻结清单3088项。README／状态的原“独立16项”缺少当时独立验收依据；现在可明确引用本轮 Codex 的16项结果，但任务仍 needs_changes。
6. 交接指定最近获授权 bonsai2-27b；Pi 自述 qwen3.8-coding-27b 没有独立模型来源，也未提供开工前变更反馈。保留该差异为无法确定的归属，不把自述当模型实证。下一轮按当前授权配置执行；如不一致先反馈，不自行切模型或补造旧运行记录。

目前 scope 与历史哈希核验通过；不要求重造无法恢复的历史。规范化下一轮新记录即可。

## A1–A7 判定

| 条目 | 本轮结果 |
|---|---|
| A1 接口 | 普通路径符合；R1 子类和 R2 委托／generator／精确断言待修 |
| A2 抽取 | 普通主例、内部 JOIN、重复位置、有限循环通过；R1 扩展边界待修 |
| A3 顺序 | 产品主例／独立 world 反转通过；提交 world 变换测试未实现 |
| A4 规模／纯度 | 代码额外过程 O(n)、无递归；提交长链引用／纯度守卫不完整 |
| A5 测试 | needs_changes；三错误副本漏检，隔离违规导入反例已拒绝 |
| A6 回归／范围 | 本提交 933 项 Pi 回归原件可核验，旧冻结件未变；修产品后须重跑相关 full |
| A7 证据 | preflight 在编码前、两失败原件保留；R3 所列文字与顺序偏差须更正 |

第2轮执行步骤与准确命令见 [交接文档](../../../docs/handoffs/T0015-proof-subtree.md)末尾。研究语义、D33、旧产品和旧测试均不变。

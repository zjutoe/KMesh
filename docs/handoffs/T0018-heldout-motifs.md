# T0018：指定查询批次的保留结构命中审计

## 任务信息

- 任务编号／修订号：T0018 / r3，2026-09-28。r1 保留于 Git `03bbce2:docs/handoffs/T0018-heldout-motifs.md`；r2 补充环境与预检，原文按记录哈希归档于 [r2 交接](../../reports/T0018/readiness-r3/prior-contract-r2/handoff.txt)。r3 按用户明确选择冻结原生 Pi 交互交付／预算约定，产品接口和 A1–A8 不变。
- 状态：**accepted**（2026-09-28 06:18:00 UTC，round 2 / attempt 2）。独立审查关闭 T0018-001–004；控制器 39 项定向／1050 项全量通过。用户随后授权提交并合并，实现已提交为 `40aacbfe23e7f3e8a1d538ba87104fcfe8fa7795` 并快进合入本地 `master`，源码／测试与接受 hash 一致。见 [验收同步](../../reports/T0018/acceptance/README.md)及 [合并记录](../../reports/T0018/integration/README.md)。
- 本文为 r3 契约的终态同步视图，产品接口和验收条件未变；原发布契约逐字保留于 [r3 原件](../../reports/T0018/acceptance/published-handoff-r3.txt)，SHA-256 `4c5b918bcbe1568ba2fd6f9178f2e32717e70a8e4c18276eb64ab82d08e1a5ee`。下文准备阶段记录按其原日期理解，不改写历史或独立工作树中的冻结文档。
- 所属阶段与协议：M1 数据审计前置操作；研究计划 v0.1.3、E0 `e0_v2`、E1 `e1_v3`、`proof_identity_v1`、`proof_motif_v1` 均不变；工程决策 [D37](../decisions.md#d37指定查询批次与参考证明的结构命中审计)。本项不冻结正式数据准入／划分规则。
- 规划者／独立验收者：Codex + `gpt-6-astra`／`xhigh`；执行者：Pi + `bonsai2-27b`／`xhigh`。模型身份以实际运行元数据记录，不能用自述代替后端权重证明。
- 基线：r1 规划基线为 `8571d0646dfe6fd2f2ad91f839a011094dc20f49`；r2 准备及独立工作树 HEAD 为 `03bbce2a401097f8ce78a9a13a07457e8753e797`。两次准备开始时各自的 `git status --short` 均为空；当前基线已提交 r1 规划及控制器名称更正。
- 发布时未提交规划改动：`AGENTS.md`、本交接、`docs/decisions.md`、`docs/implementation_status.md`、`reports/T0018/task.json`、`reports/T0018/preparation-r2/`、`reports/T0018/readiness-r3/`。这些是 Codex 规划材料，Pi 不得编辑；最终清单和哈希由准备记录留存，实际发布时控制器再次整体快照。此处描述发布基线，不因后续授权提交改写历史。
- 独立分支／工作区：`T0018-heldout-motifs`／`/home/mye/data/kmesh-worktrees/T0018-heldout-motifs`，2026-09-28 已创建；`.venv` 为该工作树专用解释器。
- 前置验收：[T0014 单树 motif](T0014-proof-motif.md)和 [T0017 全部证明子树联集](T0017-query-motifs.md)；其间接依赖保持原契约。T0017 的 [接受摘要](../../reports/T0017/acceptance/summary.json)记录控制器 51 项定向／1011 项全量及独立 51 项通过。
- 必读：[AGENTS §8](../../AGENTS.md#8-codinator-自动交接自-t0016-起)、研究计划 §4.5／§5.2–5.4、[motif 规范](../motif_identity_v1.md)、上述两份交接、`src/kmesh/logic/motif.py`、`query_motifs.py`、`types.py`。

## 研究目标、已有证据与选题依据

最终问题是：LLM 训练中大多数更新能否限制在少量参数内，并在达到同等质量时降低**包括读取、路由、维护和必要全局更新在内的总成本**。当前先做 E0 读取／组合、E1a 无梯度内容更新和 E1b 局部参数学习；真正的 LLM 训练对照属于另立协议的 E4。

截至本基线，T0001–T0017 的成果是已验收的工程基础：环境诊断／模型结构配置、逻辑类型、两个独立闭包求解器、证明核验与完整枚举、最短深度、同世界证明身份／计数、跨世界 motif 及全部证明的完整子树联集。r1 研究回顾中的 1011 项回归来自 T0017 的控制器记录；r2 已在本任务新环境独立重跑 1011 项，证据单列于下文。小世界交叉检查和手算／错误实现守卫支持这些接口的正确性，不能当作神经模型的实验证据。

M0 仍未闭环，M1 尚无正式生成器、冻结保留目录、family 划分及完整数据审计；模型、训练、更新收益和成本实验均为 `not_run`。本项将已有结构原语接成一个能回答“哪些指定查询命中了哪些保留结构”的离线操作，为后续组合划分提供可用接口。

研究计划 §5.2 限制的是**训练查询的有效证明**。本项只检查调用者明确提交的查询，不扩大为 world 的全部可推导 ground atoms，也不把规则共存本身当作泄漏。查询集合是否完整覆盖实际监督数据，仍由未来数据流水线审计。

## 目标、范围与交付物

单一目标：给定一个有限无环世界、一批 ground 查询及一批合法参考证明，返回每个查询的全部证明中，哪些参考证明结构作为**完整有根支持子树**出现。

Pi 只允许新增／修改：

1. `src/kmesh/logic/heldout_motifs.py`
2. `tests/test_heldout_motifs.py`

不改前置产品／测试、包初始化、依赖、配置、交接或报告。本任务通过原生 Pi 界面的 `codex_submit_review` 工具提交 Markdown 执行总结，由控制器生成仓外 `submission.md`／`review.md` 及审查所需内部记录；Pi 不自行写 delivery 或 completion 文件。控制器 SQLite 为运行真值，终态后由主会话 Codex 同步本文。

本项不做正式 heldout 清单／split 配额、生成器、world 准入总开关、证明唯一性／深度汇总、持久 JSON 格式、CLI、模型或训练。也不实现任意裁剪片段／带开放边界的结构匹配。返回空命中只说明**本批查询、给定参考目录、完整子树口径**下未命中，不能宣称整个数据集无泄漏。

## 前提与假设

### 已验证事实

- 基线中的 `motif.py` SHA-256 为 `23d175e8865b3ace1d4ffd4094b67fcb18c8c36ae986f3b44b2e148fde80476f`。
- `query_motifs.py` SHA-256 为 `3feb1fb5801e5504fd9d79e6087bab06e159ec69f098ed3168aeb950e6e456f9`，`test_query_motifs.py` 为 `17c022f05acd7751b2e6677f8a1e698c99479a50c9b64d67baf9dfe6141cc59c`，与 T0017 接受摘要一致。
- r2 独立工作树 `.venv` 基于 `/opt/anaconda3/bin/python` 离线建立，Python 3.13.5、pytest 8.3.4、setuptools 72.1.0、wheel 0.45.1；通过 `--system-site-packages` 复用现有依赖，并执行 `--no-index --no-build-isolation --no-deps --no-cache-dir -e .`。`kmesh` 导入 realpath 已核对属于该工作树。主仓库仍无 `.venv`，历史 T0017 环境记录不改写。完整版本见 [环境记录](../../reports/T0018/preparation-r2/environment-summary.json)。
- Codex 已以已验收 T0014／T0017 核对本交接的六个参考证明、九个手算查询命中关系，以及 W_C 的 C/D/S/O 精确边界。见 [规划探针](../../reports/T0018/planning_probe.py)、[stdout](../../reports/T0018/planning-probe-r1.stdout)及 [stderr](../../reports/T0018/planning-probe-r1.stderr)。这只检验 fixture 与依赖接口一致性，不是 T0018 产品／测试实现，也不是独立证明依赖的完整性。

### 发布条件与访问边界

- r2 已通过 `codinator doctor`、工作树导入检查、只读沙箱内 1011 项基线回归及独立目录中的 fixture 探针。控制器入口为 `/home/mye/.local/bin/codinator`，源码 HEAD 为 `15690b10ed1169fb8ba6749a6e1a4caa2f47d0b1`。版本变化不改写旧证据；后续规定回归失败先调查。
- r2 已核验 Pi `bonsai/bonsai2-27b/xhigh` 的 RPC 身份和真实最小响应，以及 `gpt-6-astra/xhigh` 的 CLI 调用、退出 0 和 `turn.completed`。Pi 使用仓外 T0018 专用配置，启动时必须带上 r3 启动说明中的 `PI_CODING_AGENT_DIR`；全局配置未改。身份来源、失败尝试与限制见 [模型预检摘要](../../reports/T0018/preparation-r2/model-connectivity.json)。这不是 T0018 实施或验收，也不是后端权重证明；正式原生 Pi 会话记录其实际客户端元数据，不标作 RPC 运行。
- 已建立 [manifest](../../reports/T0018/task.json)：版本 1、上述 id／workspace／handoff、精确两条 allowed_paths、下文两项 checks、`max_rounds=4`、`max_seconds=14400`、`attempt_seconds=7200`、excludes 为 `.venv/` 和 `.pytest_cache/`。r3 准备时尚未发布，随后按用户选择进入原生 Pi 闭环并验收；[原发布 manifest](../../reports/T0018/acceptance/published-manifest.json)另存。未配置通知线程，避免沿用其他任务会话。Pi 不自行创建或修改 manifest。
- 数据仅为本文合成内存 fixture；seed 为 N/A（确定性）。不读正式或锁定数据，不导入旧 tests／reports 作 oracle，不访问网络、GPU或教师，不下载依赖／模型，不启动训练。
- 用户于2026-09-28明确选择原生 Pi 界面，按 AGENTS §8 的 T0018 例外执行：最多四轮，每个必需检查180秒，单次独立Codex审查7200秒；Pi进程及任务总时长无控制器上限。manifest 的 `max_seconds=14400` 仅保留格式兼容，在本模式不生效；`attempt_seconds=7200` 只限制Codex。CPU检查、CUDA隐藏，无研究GPU预算。资源／连接故障、越界、轮次耗尽或用户介入时保留现场并停止自动派发；按实际控制器状态记 paused／blocked，检查原因后显式 `/codex-resume` 或 `codinator pi T0018-heldout-motifs --resume`，不盲目重放不确定提交。

## 具体实施步骤

### 1. 核对发布快照

仅在用户按 r3 启动命令明确发布、控制器派发本轮后执行。核对控制器 intake 的 HEAD、dirty 清单、只读交接与 manifest；首次 attempt 确认两目标文件原本不存在，返工则使用控制器指定的上一轮快照。发现依赖 hash 或契约有影响任务的变化先反馈，不回滚他人文件。

预期结果：执行汇总可追溯到真实基线、解释器和控制器 attempt；无需修改本文状态。

### 2. 实现唯一公开接口和匹配语义

```python
def heldout_motif_hits(
    clauses, queries, references, *,
    max_fact_checks: int = 100_000,
    max_derivations: int = 100_000,
    max_proof_steps: int = 100_000,
    max_orientations: int = 100_000,
) -> tuple[frozenset[int], ...]:
    ...
```

`__all__ == ["heldout_motif_hits"]`。不新增公开类型、异常或辅助 API。

- `clauses` 是原世界，范围继承 T0017；本层不复制、转换或自行求解。
- `queries` 为非空 tuple，元素是 ground `Atom`，允许重复，输出与其位置一一对应。只接收一个世界，不将不同查询的命中合并为单个集合。
- `references` 为非空 tuple，每项严格有三个位置 `(reference_clauses, reference_query, reference_proof)`。内部对象由 T0014 验证；可以来自不同世界。参考证明只定义**该棵完整树**的结构，不枚举参考 query 的其他证明，也不把参考树的所有子树自动加入保留目录。
- 参考继承 T0014 对给定有限循环规则证明的接受范围，不另加世界 DAG 检查；目标世界仍严格继承 T0017 的关系 DAG 要求，两者不能互相放宽。
- 接受 tuple／Atom 的既有合法子类，使用 `isinstance`；不消费列表或生成器来转换输入。三元组只核对外层 tuple 和长度，不在此重写 clause／proof 校验。
- 参考条目的位置 `j` 只是这次输入目录的索引，不是持久 motif ID，也不提供给模型。不同参考证明若具有同一键，命中时仍返回全部对应索引。

定义参考键 `K_j = canonical_motif_key(*references[j])`，查询结构集 `U_i = query_subtree_motif_keys(clauses, queries[i])`，则：

```text
hits[i] = frozenset(j for j in range(len(references)) if K_j in U_i)
return tuple(hits)
```

这是数学结果约束，不要求照抄循环；可用“完整键 → 原位置集合”索引。比较完整 tuple 键，不比较摘要、节点数、深度、根 Header 或端点关系。不另写 motif 规范化／证明搜索，不跨调用缓存。

预期结果：返回真实 tuple，各项真实 frozenset，元素是真实非负 int；外层长度等于输入查询数，结果整体可 hash。

### 3. 固定校验、调用与失败顺序

1. 先校验 `queries` 外层／非空，再从左到右校验每个成员的 Atom 类型及 ground 性。
2. 再校验 `references` 外层／非空和每项三元组形状，**全部形状检查成功**后才调用依赖。此时不检查内部 proof，也不访问 `clauses` 内容。
3. 按 reference 原顺序，每项恰一次调用 T0014 `canonical_motif_key(ref_clauses, ref_query, ref_proof, max_steps=S, max_orientations=O)`，三个对象与 S/O 都原样传入。同一对象重复出现也逐项调用，不能先去重。目录全部成功后才检查目标 queries。
4. 按 queries 原顺序，每项恰一次调用 T0017 `query_subtree_motif_keys(clauses, query, max_fact_checks=C, max_derivations=D, max_proof_steps=S, max_orientations=O)`，所有对象／预算原样传入。重复 query 也照常调用；查询为事实、不可推出、前面已命中或已经覆盖全部参考索引，都不能跳过后续查询。
5. 所有参考与查询调用完整成功后才返回。依赖异常不捕获、重建、包装、修改消息或重试；立即停止，无部分结果和“未命中”的错误替代值。

本层不新增预算校验器：S/O 先由参考 T0014 检查，C/D 在首个目标 T0017 调用时检查；参考失败先于目标世界／C/D 的错误。局部输入错误先于全部依赖错误。不得为了复用前项结果改变这个顺序。

本层新增错误均为 `LogicValidationError`，全文固定；`TYPE` 仅取类型名，`i` 是十进制位置，不 repr 未验证对象：

| 条件 | 消息 |
|---|---|
| queries 非 tuple | `heldout_motifs.queries must be a tuple of ground Atom; got TYPE` |
| queries 为空 | `heldout_motifs.queries must be non-empty` |
| queries[i] 非 Atom | `heldout_motifs.queries[i] must be an Atom; got TYPE` |
| queries[i] 非 ground | `heldout_motifs.queries[i] must be a ground Atom` |
| references 非 tuple | `heldout_motifs.references must be a tuple of reference triples; got TYPE` |
| references 为空 | `heldout_motifs.references must be non-empty` |
| references[i] 非 tuple 或长度不为 3 | `heldout_motifs.references[i] must be a (clauses, query, proof) tuple` |

直接产品导入只允许标准库、`kmesh.logic.types` 的 Atom／LogicValidationError（Clause 可仅作注解）、`motif.canonical_motif_key`、`query_motifs.query_subtree_motif_keys`。两个调用点须模块级按名导入，便于在真实绑定处 spy；其已验收间接依赖正常保留。不直接调用 solver、verifier、enumerator、proof_count 或深度模块；不做 IO。

预算解释：C/D 每次目标调用各自约束全世界直接推导；S 对目标是相关证明累计生成步数，对每个参考是单棵给定树的长度上限；O 对参考树和每个目标子树分别限制方向枚举。四值不跨参考／查询扣减，不是整批总计算预算。重复世界求解是本版明确成本，不假称复用索引或线性复杂度；先完成正确组合，后续优化另验。

### 4. 建立手算语义测试

测试在本文件定义 fixture，不导入规划探针或前置测试。下列 a/b/c/m/n/o 是不同常量；大写缩写只用于文档。

`F_p(a,b)` 表示事实，`C(p,q)` 表示 `p(?x,?y)→q(?x,?y)`，`I(p,q)` 表示 `p(?x,?y)→q(?y,?x)`，`J(p,r,q)` 表示 `p(?x,?y),r(?y,?z)→q(?x,?z)`。世界和证明步骤严格按表中顺序；证明条目写作 `(clause_index, premise_steps, conclusion)`，构造为真实 `ProofStep`。

| 参考索引 | reference_clauses；query | 手写完整证明 |
|---|---|---|
| 0，F | `F_p(a,b)`；`p(a,b)` | `(0,(),p(a,b))` |
| 1，C | `F_p(a,b), C(p,q)`；`q(a,b)` | `(0,(),p(a,b)), (1,(0,),q(a,b))` |
| 2，I | `F_p(a,b), I(p,q)`；`q(b,a)` | `(0,(),p(a,b)), (1,(0,),q(b,a))` |
| 3，J | `F_p(a,b), F_r(b,c), J(p,r,q)`；`q(a,c)` | `(0,(),p(a,b)), (1,(),r(b,c)), (2,(0,1),q(a,c))` |
| 4，CJ | `F_f(m,n), F_g(n,o), C(f,h), J(h,g,k)`；`k(m,o)` | `(0,(),f(m,n)), (2,(0,),h(m,n)), (1,(),g(n,o)), (3,(1,2),k(m,o))` |
| 5，C 的改名副本 | `F_s(m,n), C(s,t)`；`t(m,n)` | `(0,(),s(m,n)), (1,(0,),t(m,n))` |

参考 1／5 同键，其余四个键互异。主样例都使用完整六条目录，默认四预算；期望为下表集合写法对应的真实 tuple of frozensets，不从待测函数或它的依赖生成 expected。

| ID | clauses；queries | 完整期望（按查询顺序） |
|---|---|---|
| H0 | 空世界；`(z(a,b),)` | `(∅,)` |
| H1 | W_A=`F_p(a,b), F_r(b,a), C(p,q), I(r,q)`；`(q(a,b), p(a,b), z(a,b), q(a,b))` | `({0,1,2,5}, {0}, ∅, {0,1,2,5})` |
| H2 | W_B=`F_p(a,b), F_r(b,c), C(p,u), J(u,r,v), C(v,t)`；`(t(a,c), v(a,c), u(a,b), p(a,b))` | `({0,1,4,5}, {0,1,4,5}, {0,1,5}, {0})` |
| H3 | W_C=`F_q(a,c), F_p(a,b), F_r(b,c), J(p,r,q)`；`(q(a,c), p(a,b))` | `({0,3}, {0})` |

- H1 的两条替代证明分别是 COPY／INV，只看第一棵会漏项；输出保留重复查询和等价参考的两个索引。
- H2 中深度 2 的 CJ 出现在 `t(a,c)` 深度 3 证明内部；裸 J **不命中**，因为其一个子支持包含 COPY，不能将该支持裁去并补成边界事实。
- 另用 H2 的 `p(a,b)`，目录只含原参考 4，期望 `(∅,)`：参考的内部事实不是自动保留项。仅原参考 3 配 H1 的 `q(a,b)`，也期望 `(∅,)`。
- H3 的查询本身虽有事实证明，另一条 JOIN 证明仍必须检查。此处含深度 0／1 的参考只作单元锚点，不是正式组合目录，也不改变主测试深度 2–3 的计划。
- 对 H1 做全世界＋查询同步关系／实体双射、world 逆序；对 H2 做局部变量双射、JOIN body 交换。每个变换须实际改变字段，命中索引不变；分别改变参考的关系／实体名称也不改对应结构命中。将参考目录逆序后，旧索引 j 精确变成 `5-j`。

### 5. 补齐边界、失败与隔离测试

- **委托：** 在本模块两个真实绑定处联合日志 spy，使用合法外层输入，核对先全部参考再全部查询、原内部对象 `is`、每项恰一次、重复项仍处理、默认预算及非默认 `11/13/17/19` 全部原样传入。fake 返回键仅用于委托测试，不替代 H0–H3 的真实语义。
- **局部校验：** 覆盖两外层的 list／生成器／空 tuple、queries 的坏成员／非 ground、references 的 list 条目／长度 2 或 4。生成器 body 标记不得被触发；列表和生成器不能被默默转 tuple。后部形状错误应在首次依赖前抛出。全文断言新增消息，并用叠加错误确认 queries → references → 依赖的顺序。签名缺参、额外位置参数、未知 keyword 为普通 TypeError。
- **真实预算与晚失败：** 使用 W_C、仅含原参考 0 的目录（新索引为 0）、queries=`(p(a,b), q(a,c), z(a,b))`。C/D/S/O=`2/4/6/2` 时完整结果 `({0},{0},∅)`；O=1 时第二个 query 的替代 JOIN 证明抛原 MotifLimitError，前面已命中也不能返回；S=5 时同处抛 ProofEnumerationLimitError。用透传 spy 确认第三 query 未调用，不替换真实依赖。实际测试 C=1、D=3 时保留 DerivationLimitError；只保留参考 4 且 S=3 时先报单参考 ProofLimitError，目标零调用。
- **异常身份：** 分别让第二个参考、第二个查询抛哨兵异常，确认后续项零调用；覆盖 LogicValidationError／ProofLimitError／MotifLimitError／DerivationLimitError／ProofEnumerationLimitError 中对应依赖支持的类。调用前保存期望类、消息、cause、context 和 suppress_context，调用后检查同一实例且各字段未改。不得用“当前异常消息与同一被修改对象的当前消息相等”代替期望快照（T0017 已出现过此测试缺口）。参考错误叠加 C=0，仍先报参考错误。
- **委托输入：** 用真实 API 检查非法原 clauses、循环世界、无证明查询及无效 C/D/S/O；与依赖原诊断比较，保留顺序，不重做所有前置输入矩阵。非正整数／bool 由既有依赖拒绝。本层不产生“审计失败但空命中”的成功结果。
- **纯度：** H1→H0→H1，调用前后比较全部原 clauses／queries／references 的独立结构快照及 hash，检查真实返回容器和 hash。不让一次调用污染下次，不修改参考的原 proof。
- **导入隔离：** 新 Python 子进程在 sys.path 首位插入当前测试所属仓库 src，核对产品 realpath；整个产品导入及一次 H1 真实调用期间禁止 `torch`、`yaml`、`kmesh.logic.engine`、`kmesh.logic.reference_engine` 根名及点前缀。finder 全程保留，末尾扫描 sys.modules；对根和临时 package 的 `_t0018_probe` 子模块各作真实 import 自检并断言拦截消息，清除临时占位。允许 T0014／T0017 必需的间接 proof／enumeration 依赖。隔离脚本不复用旧 tests／reports。

只验证本层新增契约与关键委托，不复制 T0014／T0017 的整个测试矩阵，不按测试条数验收。至少让测试能够拒绝：仅首查询、合并所有查询结果、等价参考只报一个索引、只整树或只首个证明、把参考所有子树都设为保留、命中后早停／异常改成空集、跳过后续失败等错误。

### 6. 运行自检并提交独立验收

按下文先定向后全量。开发检查从首次尝试起由 Pi 原始工具事件留证，每次使用新的 `/tmp` basetemp；失败也保留。控制器另独立录制必需检查和提交快照，旧 `record_check.py` 不适用于本自动任务。

自检完成且其他工具均已结束后，单独调用 `codex_submit_review`，不与其他工具同批调用；`summary` 参数为 Markdown，分列实际改动、命令／退出码、失败修复、未运行项、模型来源、范围偏差及证据路径，未运行填 `not_run`。提交后等待控制器冻结／检查及独立 Codex 正式意见；返工仅按原契约执行，下一轮重新提交。实现完成不自填 accepted，独立 Codex 依据冻结 diff、实际测试质量及控制器证据验收。不得自动 commit/push/merge。

## 验证方法

以下是 **T0018 实施后的规定命令**；r2 已准备独立解释器，manifest 已按 argv 数组录入。当前产品／测试尚未实施，因此两项 T0018 提交检查仍为 `not_run`。工作目录固定为 `/home/mye/data/kmesh-worktrees/T0018-heldout-motifs`：

```bash
env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/mye/data/kmesh-worktrees/T0018-heldout-motifs/.venv/bin/python -m pytest -q -p no:cacheprovider --basetemp /tmp/kmesh-T0018-focused tests/test_heldout_motifs.py
env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/mye/data/kmesh-worktrees/T0018-heldout-motifs/.venv/bin/python -m pytest -q -p no:cacheprovider --basetemp /tmp/kmesh-T0018-full tests
```

每项 180 秒；预期退出 0，无 skip／xfail。基线全量 1011 项，新测试 N 项时为 1011+N，若实际不同须核对收集和基线，不能凑数。控制器在只读工作树、每次独立 `/tmp` 中执行上述固定 basetemp；Pi 开发命令必须换新的临时目录，不能复用控制器路径删除旧材料。

r1 Codex 规划检查（2026-09-27，工作目录为主仓库，已运行、退出 0）：

```bash
env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /opt/anaconda3/bin/python reports/T0018/planning_probe.py > reports/T0018/planning-probe-r1.stdout 2> reports/T0018/planning-probe-r1.stderr
```

结果：6 个参考证明／5 个不同键、9 个手定查询命中关系、C/D/S/O=`2/4/6/2` 成功和 S=5／O=1 拒绝均符合设计，stderr 空。该文件为已留存 r1 原件，不可再次用上述重定向覆盖；后续检查另编号。r1 时完整回归、T0018 测试、Pi 实施和独立验收均 `not_run`；r2 新增的基线回归与探针另列，不回填为 r1 结果。

## 验收标准

- [x] A1：仅两个允许的产品／测试文件；接口、公开名、导入和只读材料边界符合发布契约。
- [x] A2：H0–H3 及仅 CJ／仅 J 目录的完整结果与手算一致；内部复合子树、替代证明、重复查询和重复参考索引均覆盖。
- [x] A3：参考只表示整棵合法证明；既不信任手填未验证键，也不把其子树自动纳入目录；重命名／前提交换不改变语义，目录重排正确改变索引。
- [x] A4：局部校验顺序与全文、所有依赖的原对象／预算／调用次数、先参考后目标均有有效测试；生成器未消费。
- [x] A5：真实预算边界、后部失败、异常身份及消息快照正确；全部成功才返回，无早停或部分成功。
- [x] A6：原输入纯度、真实输出类型、可 hash、跨调用稳定性和硬导入隔离通过；模型可见信息未增加。
- [x] A7：控制器两项检查通过，结果绑定正确快照；独立 Codex 审阅实现和行为测试，并针对实际风险核验能捕捉关键违约，不仅依据 Pi 报告验收。
- [x] A8：保留失败尝试与原发布契约；报告明确本项仅是给定查询／目录／完整子树口径的匹配，不能称作正式 split、world 无泄漏或局部更新研究结果。

## Pi 执行记录

发布前历史为 `not_run`：r1 完成研究回顾和交接设计，r2 完成环境准备，r3 根据用户选择确定原生 Pi 运行约定并标 ready；最小模型连通性探针不算 Pi 产品实施。

2026-09-28 终态同步：Pi 通过原生界面实施及 `codex_submit_review` 提交，客户端元数据为 `bonsai/bonsai2-27b/xhigh`，不是 RPC 运行或后端权重证明。基线 HEAD `03bbce2a401097f8ce78a9a13a07457e8753e797`；新增两个允许文件。首次提交遇 bytecode 越界，先保留失败现场、清理派生缓存，Pi 将隔离子进程改为 `-I -B`。正式首轮 31／1042 项通过但仍须补强测试；第二轮仅改测试，39／1050 项通过，两项规定检查均退出 0。准确命令／stdout／stderr、接受 hash、原件路径与更正见 [验收摘要](../../reports/T0018/acceptance/README.md)及 [机器可读记录](../../reports/T0018/acceptance/summary.json)。正式数据、训练和性能实验未运行；原始会话及全部失败证据留在仓外，未覆盖。

## Codex 验收记录

2026-09-27 规划记录：已核对仓库／验收摘要和依赖 hash，运行上述已有接口的 fixture 检查，退出 0。未实施新 API、未运行 T0018 测试、未验收产品。

文档检查：`git diff --check` 退出 0；本文 9 个本地链接目标存在，新交接／规划探针／输出文件的尾随空白与末尾换行检查通过。T0016／T0017 接受摘要列出的全部产品和测试 hash 与当前文件一致。新产品／测试文件确认尚不存在，未把历史回归结果记作本轮检查。

上述为 r1 规划记录，当时发布环境未满足，状态为 **draft**。实施后的 accepted／needs_changes／blocked 结论只由独立验收产生，并绑定实际快照及原发布契约 hash。

### r2 发布准备记录（2026-09-28，Codex；以下为选择前历史）

- 已完成工作树、离线 editable 安装、环境核验和 manifest。独立只读沙箱的基线全量检查退出 0：**1011 passed in 18.76s**，无 skip／xfail；r2 fixture 探针退出 0，保持 6 参考／5 不同键／9 查询和 S/O 拒绝边界。产物见 [准备目录](../../reports/T0018/preparation-r2/README.md)；不是 T0018 新实现测试。
- `codinator doctor` 通过；Pi 0.87.1、Codex CLI 0.157.1。Codex 最小探针通过（44.55 秒）；Pi 经专用 provider 别名和显式 xhigh 配置后通过（4.12 秒）。原 provider 缺失、客户端 high 不匹配以及准备脚本断言失败均保留，未把失败改记为成功。
- 专用配置复制已有 `bonsai-local` 的同一 `bonsai2-27b`／本机 8080 端点为 `bonsai`，并在现有 `off→none`／`high→xhigh` 映射上增加 `xhigh→xhigh`。不是更换模型；不改全局配置。客户端身份不等于服务端权重证明，原生 TUI 的真实模型实施／审查闭环本轮 `not_run`。
- **唯一待定项为运行预算／入口。** 当前交接的交付方式与单进程 7200 秒、总任务 14400 秒仍描述 `submit/run` 流程。原生 `codinator pi` 改为由 Pi 调用 `codex_submit_review` 提交 Markdown，控制器生成 `submission.md`／`review.md`，不要求 Pi 写 completion 文件；它不执行 `max_seconds`，`attempt_seconds` 只限制单次 Codex 审查，Pi 无控制器时间上限。不能把 manifest 中存在预算数字等同于已强制执行。
- 已向用户明确列出“采用交互模式并记录预算变化”与“保留原预算使用后台模式”两种选择；答复前不默许扩大预算，不发布。选择后由 Codex 对齐本文的交付／预算段及 AGENTS §8 适用说明，记录到 decisions，并改为 `ready`；不得交由 Pi 猜测。
- 当前 **draft** 仅保留上述待定项；产品／测试两个目标文件不存在，实施、独立验收、commit／push／merge 均未运行。

### r3 运行方式确定（2026-09-28，Codex）

- 用户明确答复：“运行方式用推荐的原生Pi界面”。此前已明确列出预算差异，因此按该选择记录本任务的交互交付及时间约定；不再要求重复确认。
- 当前状态改为 **ready**；产品接口、步骤2–5、A1–A8和两项检查不变，研究协议版本不变。r2 原交接、决策和状态文档按当时哈希归档，预检日志与失败材料不覆盖。
- 已对齐 AGENTS §8 的任务例外、本文及 [D38](../decisions.md#d38t0018-发布环境与交互运行约定准备)。启动入口为 `codinator pi`，不预先执行后台 `submit/run`，不启动后台服务接管本任务。
- 本轮只更新协议／发布材料及核验同步，沿用 r2 的1011项基线回归与模型预检，未把历史结果记作新测试。准确命令与状态见 [r3 启动说明](../../reports/T0018/readiness-r3/README.md)及准备快照；实施和产品独立验收仍为 `not_run`。

### r3 终态验收同步（2026-09-28，Codex）

- 控制器 SQLite 为 `accepted / done`，round 2 / attempt 2；[独立审查结论](../../reports/T0018/acceptance/review.md)无遗留问题。接受快照 `bcf5afa94762ffba858b4de591d70e43edefdb4da92a2a9dcaafa62c4c6fca4c`，当前独立工作树与之相同；仅两条允许路径有实现变化。A1–A8 按原条件勾选，未改契约。
- [首轮审查](../../reports/T0018/acceptance/review-round1.md)的 T0018-001–004 为测试缺口：重复调用、异常身份／优先级、预算独立失败／后续停止、后部 list 条目提前校验。Pi 仅补强测试后全部关闭，产品源码 hash 未变。
- 控制器定向 **39 passed in 0.27s**／全量 **1050 passed in 19.15s**，退出 0、无 skip／xfail。独立审查实际运行 39 项定向，并确认 10 个针对性错误实现被拒绝；启动模型 `gpt-6-astra/xhigh`，进程退出 0 且有 `turn.completed`。
- 主会话核对控制器状态、提交／检查证据 hash、正式 verdict 与实际差异，再在只读沙箱独立复跑 **39 passed in 0.27s**，退出 0；复核后工作树／原检查证据未变，源码无 `.pyc`。本轮未再跑 full，沿用已核验的控制器全量原件；命令与验证脚本见 [本轮复核记录](../../reports/T0018/acceptance/closeout/)。
- Pi 最终总结中畸形源码 hash 与“此前已接受”措辞不作为事实：正确 hash 见 [summary.json](../../reports/T0018/acceptance/summary.json)，首轮实际为 `needs_changes`，第二轮才 `accepted`。旧总结、缓存故障及探针失败原件保留，不回写成成功。
- 本次仅同步主仓库文档和必要验收摘要，独立工作树及其原发布契约不改；接受代码仍在独立工作树，未 commit／push／merge。验收仅针对给定查询／参考目录／完整有根支持子树口径，不证明正式数据划分或整体 world 无泄漏。

### 用户授权提交与合并（2026-09-28，Codex）

- 用户明确要求“提交并合并到主仓库”。提交前重新核对控制器 `accepted`、原接受快照及检查证据、两个目标文件 hash，均一致；任务分支只提交两个已验收实现／测试文件。
- 实现提交 `40aacbfe23e7f3e8a1d538ba87104fcfe8fa7795` 已从 `T0018-heldout-motifs` 快进合入本地 `master`。提交的 Git blob 与两份接受 SHA-256 完全一致，合并保留主仓库现有规划／验收文档；原任务工作树的文件内容未改，原始 state 和失败记录未动。
- Git HEAD／索引因授权提交发生变化，不再要求提交后的整个工作树 digest 等于提交前验收快照；原 digest 与实现提交的对应关系见 [合并记录](../../reports/T0018/integration/merge.json)。验收报告中的“未提交／未合并”为验收时点历史，本段记录后续状态。未执行 push。

后续依赖方向（未分配编号、未授权实施）：先冻结正式 motif 目录与匹配覆盖规则，再落实单世界准入和 family／split 审计、生成器及 M0 剩余检查；随后才进入模型 smoke 和 E0。是否将完整子树作为正式唯一匹配口径仍需单独研究决策，不能在本任务中悄悄缩窄计划的“子结构”含义。

2026-09-28 后续分解追加：用户要求分解下一项后，已安排 [T0019：深度 2–3 候选 motif 目录审计](T0019-motif-candidate-audit.md)。正式目录冻结之前，先对固定 80 个最小候选核验独立结构、规范唯一性、深度和包含关系；不预设候选族足以覆盖研究目标，不直接分配 train/dev/test。T0019 当前 draft，未发布；本任务原契约与验收结果不变。

2026-09-28 T0019 准备追加：独立环境、1050 项基线和模型预检已通过，T0019 已升为 ready / r2，发布清单和原生 Pi [启动说明](../../reports/T0019/preparation-r2/README.md)已就绪；尚未启动实施，上条 draft 记录保留为分解时点。

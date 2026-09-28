# T0018：指定查询批次的保留结构命中审计

## 任务信息

- 任务编号／修订号：T0018 / r1，2026-09-27。
- 状态：**draft**。实施契约已写定；独立工作树／解释器尚未准备，指定模型的运行可用性未核验。2026-09-28 控制器已统一名称并安装为 `codinator`，命令缺失已解除。完成下述发布前检查后，由 Codex 改为 `ready`；尚未 submit。
- 所属阶段与协议：M1 数据审计前置操作；研究计划 v0.1.3、E0 `e0_v2`、E1 `e1_v3`、`proof_identity_v1`、`proof_motif_v1` 均不变；工程决策 [D37](../decisions.md#d37指定查询批次与参考证明的结构命中审计)。本项不冻结正式数据准入／划分规则。
- 规划者／独立验收者：Codex + `gpt-6-astra`／`xhigh`；执行者：Pi + `bonsai2-27b`／`xhigh`。模型身份以实际运行元数据记录，不能用自述代替后端权重证明。
- 基线：`8571d0646dfe6fd2f2ad91f839a011094dc20f49`；规划开始时 `git status --short` 为空。该基线包含 T0017 接受实现，随后一提交仅调整 AGENTS 中的默认时间预算。
- 本轮未提交规划改动：本交接、`docs/decisions.md`、`docs/implementation_status.md`、`reports/T0018/`。这些是 Codex 规划材料，Pi 不得编辑；发布时重新记录实际 HEAD／完整 dirty 清单并整体快照，不悄悄沿用过时基线。
- 拟用独立分支／工作区：`T0018-heldout-motifs`／`/home/mye/data/kmesh-worktrees/T0018-heldout-motifs`，**尚未创建**。
- 前置验收：[T0014 单树 motif](T0014-proof-motif.md)和 [T0017 全部证明子树联集](T0017-query-motifs.md)；其间接依赖保持原契约。T0017 的 [接受摘要](../../reports/T0017/acceptance/summary.json)记录控制器 51 项定向／1011 项全量及独立 51 项通过。
- 必读：[AGENTS §8](../../AGENTS.md#8-codinator-自动交接自-t0016-起)、研究计划 §4.5／§5.2–5.4、[motif 规范](../motif_identity_v1.md)、上述两份交接、`src/kmesh/logic/motif.py`、`query_motifs.py`、`types.py`。

## 研究目标、已有证据与选题依据

最终问题是：LLM 训练中大多数更新能否限制在少量参数内，并在达到同等质量时降低**包括读取、路由、维护和必要全局更新在内的总成本**。当前先做 E0 读取／组合、E1a 无梯度内容更新和 E1b 局部参数学习；真正的 LLM 训练对照属于另立协议的 E4。

截至本基线，T0001–T0017 的成果是已验收的工程基础：环境诊断／模型结构配置、逻辑类型、两个独立闭包求解器、证明核验与完整枚举、最短深度、同世界证明身份／计数、跨世界 motif 及全部证明的完整子树联集。最近的 1011 项回归来自 T0017 的控制器记录，**不是本轮重新运行的结果**。小世界交叉检查和手算／错误实现守卫支持这些接口的正确性，不能当作神经模型的实验证据。

M0 仍未闭环，M1 尚无正式生成器、冻结保留目录、family 划分及完整数据审计；模型、训练、更新收益和成本实验均为 `not_run`。本项将已有结构原语接成一个能回答“哪些指定查询命中了哪些保留结构”的离线操作，为后续组合划分提供可用接口。

研究计划 §5.2 限制的是**训练查询的有效证明**。本项只检查调用者明确提交的查询，不扩大为 world 的全部可推导 ground atoms，也不把规则共存本身当作泄漏。查询集合是否完整覆盖实际监督数据，仍由未来数据流水线审计。

## 目标、范围与交付物

单一目标：给定一个有限无环世界、一批 ground 查询及一批合法参考证明，返回每个查询的全部证明中，哪些参考证明结构作为**完整有根支持子树**出现。

Pi 只允许新增／修改：

1. `src/kmesh/logic/heldout_motifs.py`
2. `tests/test_heldout_motifs.py`

不改前置产品／测试、包初始化、依赖、配置、交接或报告。自动任务中只向控制器指定的外部 `delivery/summary.md` 和 `completion.json` 写本轮交付；控制器状态为运行真值，终态后由主会话 Codex 同步本文。

本项不做正式 heldout 清单／split 配额、生成器、world 准入总开关、证明唯一性／深度汇总、持久 JSON 格式、CLI、模型或训练。也不实现任意裁剪片段／带开放边界的结构匹配。返回空命中只说明**本批查询、给定参考目录、完整子树口径**下未命中，不能宣称整个数据集无泄漏。

## 前提与假设

### 已验证事实

- 基线中的 `motif.py` SHA-256 为 `23d175e8865b3ace1d4ffd4094b67fcb18c8c36ae986f3b44b2e148fde80476f`。
- `query_motifs.py` SHA-256 为 `3feb1fb5801e5504fd9d79e6087bab06e159ec69f098ed3168aeb950e6e456f9`，`test_query_motifs.py` 为 `17c022f05acd7751b2e6677f8a1e698c99479a50c9b64d67baf9dfe6141cc59c`，与 T0017 接受摘要一致。
- 当前可用 `/opt/anaconda3/bin/python` 为 Python 3.13.5，pytest 8.3.4、setuptools 72.1.0、wheel 0.45.1。当前仓库无 `.venv`，历史 T0017 工作区和仓外控制器 state 在本环境不可见；不能把历史 Python 3.13.9／pytest 8.4.2 写成本次环境。
- Codex 已以已验收 T0014／T0017 核对本交接的六个参考证明、九个手算查询命中关系，以及 W_C 的 C/D/S/O 精确边界。见 [规划探针](../../reports/T0018/planning_probe.py)、[stdout](../../reports/T0018/planning-probe-r1.stdout)及 [stderr](../../reports/T0018/planning-probe-r1.stderr)。这只检验 fixture 与依赖接口一致性，不是 T0018 产品／测试实现，也不是独立证明依赖的完整性。

### 待满足条件与访问边界

- 发布前由 Codex 确认 `codinator` 可调用，在独立工作区离线准备 `.venv` 和当前源码的 editable 安装，核验 `kmesh` 导入 realpath 属于该工作区，记录 Python／pytest／依赖实际版本。2026-09-28 已确认控制器的安装入口为 `/home/mye/.local/bin/codinator`，源码位于 `/home/mye/src/llm/codinator`；本任务工作树和模型运行条件仍待准备。版本变化不改写旧证据；规定回归失败先调查。
- 同时核验 Pi 的 `bonsai2-27b` 和独立 Codex 的 `gpt-6-astra`／`xhigh` 可用，按 AGENTS §8 配置访问；不可用时保留 draft 并报告，不换模型或由规划方代写产品。
- Codex 在发布前建立 `reports/T0018/task.json`：版本 1、上述 id／workspace／handoff、精确两条 allowed_paths、下文两项 checks、`max_rounds=4`、`max_seconds=14400`、`attempt_seconds=7200`、excludes 为 `.venv/` 和 `.pytest_cache/`。通知线程仅填当时真实值，不能抄旧任务 ID。本轮尚无可执行 manifest，Pi 不自行创建或发布。
- 数据仅为本文合成内存 fixture；seed 为 N/A（确定性）。不读正式或锁定数据，不导入旧 tests／reports 作 oracle，不访问网络、GPU或教师，不下载依赖／模型，不启动训练。
- 单 Pi／Codex 进程 7200 秒，总任务 14400 秒含检查，最多四轮；每个必需检查 180 秒。CPU 执行、CUDA 隐藏，无 GPU 预算。预算不是完成保证；超时、基础设施问题或越界进入 blocked，保留原 attempt，由 Codex 明确处理后才 resume。

## 具体实施步骤

### 1. 核对发布快照

仅在 Codex 完成发布准备并明确分配后执行。核对控制器 intake 的 HEAD、dirty 清单、只读交接与 manifest；首次 attempt 确认两目标文件原本不存在，返工则使用控制器指定的上一轮快照。发现依赖 hash 或契约有影响任务的变化先反馈，不回滚他人文件。

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

外部 delivery 分列实际改动、命令／退出码、失败修复、未运行项、模型来源和范围偏差；未运行填 `not_run`。实现完成不自填 accepted，独立 Codex 依据冻结 diff、实际测试质量及控制器证据验收。不得自动 commit/push/merge。

## 验证方法

以下是**完成发布前准备后的规定命令**，当前独立解释器尚不存在，未在本轮执行。工作目录固定为 `/home/mye/data/kmesh-worktrees/T0018-heldout-motifs`；manifest 按 argv 数组录入同样参数：

```bash
env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/mye/data/kmesh-worktrees/T0018-heldout-motifs/.venv/bin/python -m pytest -q -p no:cacheprovider --basetemp /tmp/kmesh-T0018-focused tests/test_heldout_motifs.py
env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/mye/data/kmesh-worktrees/T0018-heldout-motifs/.venv/bin/python -m pytest -q -p no:cacheprovider --basetemp /tmp/kmesh-T0018-full tests
```

每项 180 秒；预期退出 0，无 skip／xfail。基线全量 1011 项，新测试 N 项时为 1011+N，若实际不同须核对收集和基线，不能凑数。控制器在只读工作树、每次独立 `/tmp` 中执行上述固定 basetemp；Pi 开发命令必须换新的临时目录，不能复用控制器路径删除旧材料。

本轮 Codex 规划检查（工作目录为主仓库，已运行、退出 0）：

```bash
env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /opt/anaconda3/bin/python reports/T0018/planning_probe.py > reports/T0018/planning-probe-r1.stdout 2> reports/T0018/planning-probe-r1.stderr
```

结果：6 个参考证明／5 个不同键、9 个手定查询命中关系、C/D/S/O=`2/4/6/2` 成功和 S=5／O=1 拒绝均符合设计，stderr 空。该文件为已留存 r1 原件，不可再次用上述重定向覆盖；后续检查另编号。完整回归、T0018 测试、Pi 实施和独立验收均 `not_run`。

## 验收标准

- [ ] A1：仅两个允许的产品／测试文件；接口、公开名、导入和只读材料边界符合发布契约。
- [ ] A2：H0–H3 及仅 CJ／仅 J 目录的完整结果与手算一致；内部复合子树、替代证明、重复查询和重复参考索引均覆盖。
- [ ] A3：参考只表示整棵合法证明；既不信任手填未验证键，也不把其子树自动纳入目录；重命名／前提交换不改变语义，目录重排正确改变索引。
- [ ] A4：局部校验顺序与全文、所有依赖的原对象／预算／调用次数、先参考后目标均有有效测试；生成器未消费。
- [ ] A5：真实预算边界、后部失败、异常身份及消息快照正确；全部成功才返回，无早停或部分成功。
- [ ] A6：原输入纯度、真实输出类型、可 hash、跨调用稳定性和硬导入隔离通过；模型可见信息未增加。
- [ ] A7：控制器两项检查通过，结果绑定正确快照；独立 Codex 审阅实现和行为测试，并针对实际风险核验能捕捉关键违约，不仅依据 Pi 报告验收。
- [ ] A8：保留失败尝试与原发布契约；报告明确本项仅是给定查询／目录／完整子树口径的匹配，不能称作正式 split、world 无泄漏或局部更新研究结果。

## Pi 执行记录

`not_run`：本轮只完成研究回顾和交接准备，尚未发布。发布后 Pi 仅写控制器指定的外部 delivery；本段由主会话 Codex 在终态后同步，保留实际执行者、基线、命令／退出码、产物 hash、偏差和未运行项。

## Codex 验收记录

2026-09-27 规划记录：已核对仓库／验收摘要和依赖 hash，运行上述已有接口的 fixture 检查，退出 0。未实施新 API、未运行 T0018 测试、未验收产品。

文档检查：`git diff --check` 退出 0；本文 9 个本地链接目标存在，新交接／规划探针／输出文件的尾随空白与末尾换行检查通过。T0016／T0017 接受摘要列出的全部产品和测试 hash 与当前文件一致。新产品／测试文件确认尚不存在，未把历史回归结果记作本轮检查。

当前状态仍为 **draft**：发布环境未满足；契约未留待 Pi 决定的研究选项。Codex 完成工作树／解释器／控制器／模型核验和 manifest 后再改 ready。实施后的 accepted／needs_changes／blocked 结论只由独立验收产生，并绑定实际快照及原发布契约 hash。

后续依赖方向（未分配编号、未授权实施）：先冻结正式 motif 目录与匹配覆盖规则，再落实单世界准入和 family／split 审计、生成器及 M0 剩余检查；随后才进入模型 smoke 和 E0。是否将完整子树作为正式唯一匹配口径仍需单独研究决策，不能在本任务中悄悄缩窄计划的“子结构”含义。

# KMesh

KMesh 是一个研究项目，探索能否通过小范围的学习和更新，让模型持续获得新能力，并降低大语言模型（LLM）的训练成本。

我们最终想验证的问题是：**LLM 训练中，大多数时候是否只需要更新一小部分参数，就能达到与全局更新相当的学习质量？**

参数可以粗略理解为模型内部可调整的数值，训练通过调整这些数值改变模型的行为。这里的“全局更新”允许调整整个模型的参数；“局部更新”只允许调整选定的小部分，其余部分保持不变。最终方案可以包含少量必要的全局更新，具体需要多少，由实验回答。

如果大多数学习确实能够局部完成，而且省下的计算超过了选择更新位置、读取知识和维护系统的开销，训练总成本就有望明显下降。**更新的参数少了多少，与训练实际便宜了多少，需要分别测量。**

当前从一个更小、便于检查的“知识网络”入手。设想把知识组织成一张张相互关联的卡片，每张卡片保存一条事实或规则；一个较小的计算核心负责寻找、读取和组合这些卡片。计划中把这样的知识单元称为 *patch*。

例如，卡片分别写着“甲是乙的父亲”“乙是丙的父亲”，以及“一个人的父亲的父亲是他的祖父”。模型需要组合这些信息，回答“甲是不是丙的祖父”。随后，我们可以修改其中一张卡片，观察相关答案是否随之改变，以及无关问题是否仍能答对。

这个例子包含几个逐步加深的问题：模型是否真的读了卡片？能否把熟悉的知识用于没见过的组合？知识变化后能否及时使用新内容？进一步，只训练少数卡片对应的参数，能否让模型更好地使用这些知识，并把收益推广到没有练习过的问题？

研究按以下路径推进。括号中的编号对应详细研究计划。

1. **先建立一个答案可信的小实验环境。**

   从简单的事实和规则生成问题，用两个独立的程序求解并核对答案。模型输入中不包含答案或证明过程，并检查训练与测试之间是否存在重复或泄漏。先确认程序正确、小模型确实能学会基本任务，再进行更复杂的比较。

2. **验证模型能否读取和组合知识（E0）。**

   让模型在这个小世界中回答问题，特别检查训练时没有见过的知识组合。改变关键卡片的内容，看答案是否按规则变化，以检验模型对外部知识的实际依赖。同时比较有无知识之间的连接、不同读取方式的效果，判断哪些机制有用。这一阶段会训练模型使用知识，尚未验证局部参数学习。

3. **验证知识变化后能否持续正确工作（E1a）。**

   固定已经训练好的模型，连续增加、替换或撤销知识卡片，不调整模型参数。检查新知识能否生效、新旧知识能否一起使用，以及仍然正确的旧知识是否被保留。旧事实被合理修订后，答案应跟随新事实变化，这种变化不能算作遗忘。

4. **验证少量局部参数的学习是否有额外价值（E1b）。**

   固定共享计算核心等部分，只训练指定知识卡片附带的一小组参数。比较“只改卡片内容”“改内容后再做局部学习”和“改内容后调整共享计算核心等模型参数”的结果，观察局部学习能否改善未练习过的问题，以及是否干扰其他知识。还要实际核查未获准更新的参数及其训练状态确实没有变化。

5. **根据基础实验的证据，设计真正的 LLM 训练对照（E4）。**

   前面各阶段得到可解释的结果后，再制定独立实验，比较每步全局更新与主要采用局部更新的训练方式。从头训练和在已有模型上继续训练分别研究；在其中一个阶段有效，结论也应限定在那个阶段。最终同时回答：多少训练步骤可以局部完成，每次需要更新多少参数，学习质量能否保持，以及达到同等质量实际节省多少总成本。

后续还有两条按需要开展的支线：从实例中形成可复用的新知识（E2），以及把知识分布在显存、内存和硬盘中，研究容量与速度的取舍（E3）。它们是否开展，取决于基础实验发现的瓶颈，不要求全部做完才能研究 E4。

前面的实验分别提供不同层次的证据。换一张卡片后答对问题，说明内容更新能够生效；局部训练后能答对更多未见问题，才支持局部学习的价值。即使这两点都成立，仍需实际的 LLM 训练对照，才能判断“大多数训练可以局部化”是否成立。

成本比较也要计入全过程：读取和处理知识、计算答案、学习更新、维护索引、搬运数据，以及偶尔需要的全局更新。我们关心的是达到相同质量所花的总时间和计算资源，并同时检查新能力与旧能力的表现。

项目优先获得可信证据，积极借鉴已有论文的方法。某种图结构没有收益、局部学习只在部分任务中有效，或者参数更新更少却没有节省总成本，都应如实记录。这些结果能帮助我们明确下一步该研究什么，也能说明当前假设的适用范围。

## 安装与诊断

仓库根目录下：

```bash
/opt/anaconda3/bin/python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install --no-index --no-build-isolation --no-deps -e '.[dev]'
```

目前实现了 `doctor` 诊断子命令（模块与控制台两种等价入口）与下文 `config validate-model` 校验命令：

```bash
.venv/bin/python -m kmesh.cli doctor --out reports/environment.json
.venv/bin/kmesh doctor --out reports/T0001/environment-console.json
```

报告为运行时采集的真实环境信息（Python、平台、依赖元数据、PyTorch CUDA 探测），三种状态：

- `ok`：torch 可用且探测到 CUDA 设备，退出码 0；
- `cpu_only`：torch 可用但本进程看不到 CUDA 设备，退出码 0，stdout 明确显示 `cpu_only`；
- `error`：依赖元数据缺失或 torch 导入/设备探测失败，报告仍会写出，退出码 1。

`doctor` 只读环境，不证明 GPU 能通过 forward/backward 或可稳定训练。配置校验（仅模型结构，不导入 torch）：

```bash
.venv/bin/python -m kmesh.cli config validate-model --config configs/model_e0.yaml
```

成功退出码 0，stdout 为单个 JSON：`schema_version`（整数 1）、`validation_scope`（字符串 `model_only`）、`model`（已校验的九字段字典）；校验失败退出码 1，stderr 给出源路径与原因；参数错误退出码 2。**只校验研究计划 §8.3 的 model 区块，不校验路由、训练、数据划分或设备可用性，也不表示完整 E0 配置符合协议、训练可以开始。**

逻辑内容类型（T0003）：`kmesh.logic.types` 提供不可变、可哈希的 `Atom(pred, args)` 与 `Clause(body, head)` 及构造时静态检查（二元 arity、ASCII 标识符词法、变量 `?` 前缀、0–2 前提、head 变量必须在 body 中出现）。这是后续求解器与数据构造共用的接口，**状态为已验收（`accepted`）**：R1 已关闭，Codex 独立完整回归 167 项及首轮 18 项边界探测全通过。尚无 CLI/文件加载，构造成功只验证句法与单 clause 变量作用域，不代表任何 world 通过完整 E0 数据审计。实现状态见 [docs/implementation_status.md](docs/implementation_status.md)。

参考闭包求解器（T0004）：`kmesh.logic.reference_engine` 提供 `reference_closure(clauses, *, max_rule_evaluations=100_000)`，用枚举变量绑定的前向链（全部输入 clause body+head 参数中常量的排序集合作常量域、逐规则局部变量作用域、同步不动点）计算直到一轮不新增的全部可推 ground `Atom`，返回只含 ground `Atom` 的不可变 `frozenset[Atom]`。预算异常 `ReferenceLimitError` 按“每个非空规则的候选绑定检查一次计一次”累计（事实不消耗，最终无新增轮的检查也计；预算恰好用完且已完成无新增轮时正常返回，不返回部分闭包）。包不导入 torch/PyYAML，`kmesh.logic` 包 `__init__.py` 保持零导入，参考版与未来主版不共享推理代码。最小使用例（纯标准库依赖）：

```python
from kmesh.logic.reference_engine import reference_closure
from kmesh.logic.types import Atom, Clause

world = (
    Clause((), Atom("r1", ("a", "b"))),
    Clause((), Atom("r2", ("b", "c"))),
    Clause((Atom("r1", ("?x", "?y")), Atom("r2", ("?y", "?z"))),
           Atom("r3", ("?x", "?z"))),
)

closure = reference_closure(world)
# frozenset({r1(a,b), r2(b,c), r3(a,c)})：初始事实与全部推导的 ground Atom
```

**状态：已验收（`accepted`），R1 已关闭。** Codex 第 2 轮独立原因守卫 7/7、完整回归 218 项通过。证明验证器在该任务验收时尚未实施（现由 T0006 覆盖）；生成器/关系 DAG world 审计仍未实施。双求解器一致性目前仅由 T0005 的 64 个固定 seed 小世界实测交叉验证，尚不构成研究结论。

索引闭包求解器（T0005，主求解路径）：`kmesh.logic.engine` 提供 `indexed_closure(clauses, *, max_fact_checks=100_000)`，以 tuple 形式的已校验 `Clause` 序列为输入（非法输入按 `indexed.*` 字段报 `LogicValidationError`，含非 bool 正整数预算检查），用谓词索引 + 前提拼接的同步不动点（D20：每轮索引取上一轮快照、按 body 顺序逐前提拼接、逐候选检查、整轮完成后再合并新增 head）计算全部可推 ground `Atom`，返回不可变 `frozenset[Atom]`；与参考实现不共享推理代码。预算异常 `IndexedLimitError` 按“每个准备用于匹配的候选 fact 计一次”累计（失配也计、空前提桶成本为 0、最终无新增轮的检查也计；恰好用完且完成无新增轮时正常返回，超限立即抛错且不返回部分闭包）。最小使用例（纯标准库依赖）：

```python
from kmesh.logic.engine import indexed_closure
from kmesh.logic.types import Atom, Clause

world = (
    Clause((), Atom("p", ("a", "a"))),
    Clause((Atom("p", ("?x", "?y")),), Atom("q", ("?x", "?y"))),
)

closure = indexed_closure(world)
# frozenset({p(a,a), q(a,a)})：初始事实与全部推导的 ground Atom
```

**状态：已验收（`accepted`，2026-09-16），R1–R3 已关闭。** Codex 第 2 轮独立完整回归 **337 项通过**（含 119 项索引测试与 64 个固定 seed 世界交叉验证），原流式探针通过；已改为逐候选嵌套匹配，补齐真 INTER 手算例，并核验失败先留存、修复后通过的证据链。首轮丢失历史及本轮记录补充见 [T0005 验收记录](docs/handoffs/T0005-indexed-closure.md)。更大 world 分布上的一致性与世界审计尚未实施；证明验证器在该任务验收时尚未实施（现由 T0006 覆盖，已验收），不能据此声称双求解器对所有输入等价或研究假设成立。

独立证明验证器（T0006，落实 D21）：`kmesh.logic.proof` 提供冻结 dataclass `ProofStep(clause_index, premise_steps, conclusion)`（字段约束统一抛 `LogicValidationError`，使用 `proof_step.`/`verify.` 字段路径与受控诊断输出，巨整数仅输出类型名）与 `verify_proof(clauses, query, proof, *, max_steps=10_000)`。逐步核验“每步 conclusion 是否由指定原始 clause 的 head 与已验证前提 conclusion 的局部绑定推导”（空 body 为事实引用、非空 body 从全新变量作用域绑定、常量必须相等、共享变量必须归一、引用严格向前），返回严格 `bool`；索引越界、self/forward 引用、伪造/篡改/不一致的证据均返回 False 不抛错；总步骤数（含事实、重复与合法无关步骤）超过预算立即抛 `ProofLimitError`（不得与 False 混淆，不返回部分结论）；空 proof 返回 False。包保持零导入，不依赖任何求解器。**True 只证明这份给定证据有效（不证明唯一、最短或无替代路径），False 只说明该证据无效，不得用于产生 query 的负标签**；证明与中间结论仅供离线审计，不进入模型输入或 forward/predict。最小使用例（研究计划 §4.2 主例）：

```python
from kmesh.logic.proof import ProofStep, verify_proof
from kmesh.logic.types import Atom, Clause

clauses = (
    Clause((), Atom("r1", ("a", "b"))),
    Clause((), Atom("r2", ("b", "c"))),
    Clause((Atom("r1", ("?x", "?y")), Atom("r2", ("?y", "?z"))),
           Atom("r3", ("?x", "?z"))),
    Clause((Atom("r3", ("?x", "?y")),),
           Atom("r4", ("?y", "?x"))),
)
proof = (
    ProofStep(0, (), Atom("r1", ("a", "b"))),
    ProofStep(1, (), Atom("r2", ("b", "c"))),
    ProofStep(2, (0, 1), Atom("r3", ("a", "c"))),
    ProofStep(3, (2,), Atom("r4", ("c", "a"))),
)
assert verify_proof(clauses, Atom("r4", ("c", "a")), proof) is True
```

**状态：已验收（`accepted`，2026-09-17），R1–R4 已关闭。** Codex 第 3 轮独立复跑 **101 项 proof 测试**，确认“引用不足”与“大正前提引用”测试能拒绝对应错误实现；Pi 的 **438 项完整回归**记录与源码哈希核对通过。产品源码始终冻结；历史留证限制见 [T0006 交接文档](docs/handoffs/T0006-proof-verifier.md)，复验详情见 [验收报告](reports/T0006/review-r3/review.md)。

关系依赖无环检查（T0007，落实 D25）：`kmesh.logic.dependency` 提供 `relation_topological_order(clauses)`，对一组已校验 `Clause` 检查“前提关系→头关系”离线依赖 DAG 是否无环，无环时返回确定性的关系名元组：顶点为出现过的全部头/体谓词（含无事实与无 head 的关系），边按 body 顺序逐体原子指向 head、重边去重，每次取当前零入度中最小的字符串序谓词（大小写保留）。clause 重排、前提互换、重复事实/规则结果不变；自环、两环、三环、不连通分量中的环、环带下游、仅体现在第二个前提的自环，以及无事实但 ground 规则成环（可达性不能替代 DAG 检查）均拒收；拒收时不返回部分顺序，错误消息固定为 `dependency.clauses: cyclic predicate dependency`（只含字段与原因，不点名谓词）。输入边界：外层必须为 `tuple`、逐项必须为 `Clause`，类型检查先于图工作，不消费迭代器，大整数诊断仅含类型名；函数幂等于同输入、不修改输入、无全局状态。它只是确定性约定，不是逻辑深度/研究层级，不得成为模型 token、嵌入、读取路由或额外特征，也不表示 E0 world 已通过完整审计；它与读图是不同图对象。最小使用例（研究计划 §4.1 主例）：

```python
from kmesh.logic.dependency import relation_topological_order
from kmesh.logic.types import Atom, Clause

def atom(pred, x, y):
    return Atom(pred, (x, y))

clauses = (
    Clause((), atom("r1", "a", "b")),
    Clause((), atom("r2", "c", "d")),
    Clause((atom("r1", "?x", "?y"), atom("r2", "?y", "?z")), atom("r3", "?x", "?z")),
    Clause((atom("r3", "?x", "?y"),), atom("r4", "?y", "?x")),
)
assert relation_topological_order(clauses) == ("r1", "r2", "r3", "r4")
```

**状态：已验收（`accepted`，2026-09-17），R1/R2 已关闭。** Codex 第 2 轮独立复跑 **44 项测试**，确认新 generator 断言能拒绝错误诊断；产品保持冻结，首轮 **482 项完整回归和 512 个小图核验**继续有效，本轮未重复全量运行。执行记录已更正，历史留证限制仍保留。详见 [T0007 交接文档](docs/handoffs/T0007-relation-dag.md)与 [验收报告](reports/T0007/review-r2/review.md)。
直接推导枚举（T0008，落实 D26）：`kmesh.logic.derivations` 提供 `GroundDerivation`（frozen 三元记录：`clause_index`、`premises`、`conclusion`）、`DerivationLimitError` 与 `enumerate_derivations(clauses, *, max_fact_checks=100_000, max_derivations=100_000)`。输入为已校验 `Clause` 元组且关系依赖 DAG 无环（内部调用 T0007 检查）；按确定性拓扑序→同组原 index→候选桶内 args 字典序单次迭代，事实按输入位置与顺序保留，规则在每个新就绪 head 谓词处对其**当前全部具体前提**做穷举匹配，每次成功应用产出一条记录（body 按序、绑定后具体 ground 前提元组），同一结论的不同来源全部保留，候选 Atom 按谓词桶去重，**不展开**上游完整证明组合。它不是完整证明树：不能用记录数判定 query 的完整证明数、唯一性或最短深度。计数契约：每次单原子匹配消耗 1 次 `max_fact_checks`；每条新记录消耗 1；预算恰好够完成枚举时仍正常返回，仅当还需再执行一次操作（一次匹配或一条记录）才超限、不返回部分结果、抛 `DerivationLimitError`（消息固定为 `enumerate.max_fact_checks exhausted before enumeration completed` 或 `enumerate.max_derivations exhausted before enumeration completed`），不表示否定或唯一。输入边界：外层必须为 `tuple`、逐项 `Clause`、预算必须为非 bool 正整数，错误消息固定且不回显大整数值；循环输入在匹配前拒收；函数幂等于同输入、不修改输入、无全局状态；不导入 torch/yaml/engine/reference_engine/proof，全部新信息仅供离线审计，不成为模型 token、嵌入、读取路由或额外特征。最小使用例：

```python
from kmesh.logic.derivations import enumerate_derivations
from kmesh.logic.types import Atom, Clause

def atom(pred, x, y):
    return Atom(pred, (x, y))

clauses = (
    Clause((), atom("r1", "a", "b")),
    Clause((), atom("r2", "b", "c")),
    Clause((atom("r1", "?x", "?y"), atom("r2", "?y", "?z")), atom("r3", "?x", "?z")),
)
derivations = enumerate_derivations(clauses)
assert tuple(d.conclusion.pred for d in derivations) == ("r1", "r2", "r3")
assert derivations[2].premises == (atom("r1", "a", "b"), atom("r2", "b", "c"))
```

**状态：已验收（`accepted`，2026-09-18，Codex 第 2 轮复验），R1–R4 已关闭。** 独立定向回归 **125 项通过**，新测试可拒绝两种已知错误实现；README 顺序收集 607 项无错误，隔离检查可发现禁用子模块。Pi 的 **607 项完整回归**原件与源码哈希已核对；产品冻结，首轮 128 个小世界的全部直接推导来源核验继续有效。历史留证限制保留，不代表已完成 M1 或 E0 world 完整审计。详见 [T0008 交接文档](docs/handoffs/T0008-ground-derivations.md)与 [验收报告](reports/T0008/review-r2/review.md)。

有限证明枚举（T0009）：`kmesh.logic.proof_enumeration` 提供 `ProofEnumerationLimitError`（`RuntimeError` 子类）与 `enumerate_proofs(clauses, query, *, max_fact_checks=100_000, max_derivations=100_000, max_proof_steps=100_000)`，返回单个 ground query 的全部完整证明树（`ProofStep` 的 tuple 套 tuple）。它只调 T0008 `enumerate_derivations` 一次；T0008 返回后按各记录 conclusion 建 Atom→全部来源记录位点的索引（每条记录一次 conclusion 读取），query 不在索引中直接返回 `()`，否则以显式工作列表沿索引向后展开所需 Atom（含中间结论与事实，不展开不相关 Atom，无每轮重扫），再按全局记录序逐槽位完整展开：每个完整组合经流式 `itertools.product` 生成（不先物化全部组合）并独立保留，上游全部替代来源、重复 clause、重复槽位均不合并，子证明按槽位后序拼接、右子树内部引用整体偏移重映射。入口按“容器→成员→query 类型→ground→三个预算”次序校验，消息固定、不回显未验证值的 repr/str，合法巨正整数预算接受。预算：C/D 沿用 T0008 全世界精确计数（本层不额外扣减），S 为全部相关 Atom 的已缓存证明长度之和（含中间结论与事实）；一个组合需 `1 + sum(len(child))`，先算长度并在复制任何步骤前检查累计额度；恰好用完成功，不足立即抛 `ProofEnumerationLimitError`（消息固定为 `proofs.max_proof_steps exhausted before enumeration completed`），不返回部分结果、不因已找到第二棵树而停。query 为不存在的 Atom 返回 `()`；T0008 超限原样传播，不转空结果。输出是**原始有序树**，不是规范证明：只完成单查询层面的完整枚举与预算消耗审计，规范唯一性、最短深度、motif 审计均未完成，不等同 M1 完成。最小使用例（与 `tests/test_proof_enumeration.py` 用同一输入和明确断言覆盖）：

```python
from kmesh.logic.proof_enumeration import enumerate_proofs
from kmesh.logic.types import Atom, Clause

def atom(pred, x, y):
    return Atom(pred, (x, y))

clauses = (
    Clause((), atom("p", "a", "b")),
    Clause((atom("p", "?x", "?y"),), atom("q", "?x", "?y")),
    Clause((atom("q", "?x", "?y"),), atom("r", "?y", "?x")),
)
proofs = enumerate_proofs(
    clauses,
    atom("r", "b", "a"),
    max_fact_checks=2,
    max_derivations=3,
    max_proof_steps=6,
)
assert len(proofs) == 1
assert tuple(s.conclusion.pred for s in proofs[0]) == ("p", "q", "r")
assert tuple(map(tuple, (s.premise_steps for s in proofs[0]))) == ((), (0,), (1,))
```

**状态：`awaiting_review`（2026-09-19，Pi 第 2 轮返工完成，待 Codex 第 2 轮复验）。** 第 1 轮 [Codex 验收](reports/T0009/review-r1/review.md) 判定 `needs_changes`（R1 祖先收集偏离、R2 测试守卫缺口、R3 证据表述）；本轮已恢复索引＋显式工作列表祖先收集与流式组合（长链祖先读取 4229→260）、补强测试（冻结产品失败已存 `pi-r2-regression`）、R3 逐项更正（[provenance](reports/T0009/pi-r2-full/provenance.md)）。独立九文件回归 **679 项通过**。规范唯一性／最短深度／motif 未实现。

运行测试：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q tests/test_engine.py tests/test_reference_engine.py tests/test_logic_types.py tests/test_proof.py tests/test_dependency.py tests/test_derivations.py tests/test_proof_enumeration.py tests/test_config.py tests/test_doctor.py
```

当前限制：T0001、T0002、T0003 覆盖最小包、环境诊断、模型结构配置校验与带静态校验的不可变逻辑类型（均已验收）；T0004 覆盖朴素参考闭包求解器（已验收）；T0005 覆盖索引主闭包求解器与 64 个固定 seed 小世界交叉验证（第 2 轮已验收，`accepted`）；T0006 覆盖独立给定证明验证器（第 3 轮已验收，`accepted`）；T0007 覆盖离线关系依赖无环检查（第 2 轮已验收，`accepted`）；T0008 覆盖无环世界的直接推导枚举（第 2 轮已验收，`accepted`）；T0009 的单查询原始有序证明树枚举第 2 轮返工已完成（`awaiting_review`，R1–R3 已处理，待 Codex 第 2 轮复验）；规范唯一性、最短深度、motif 审计、完整运行配置校验、数据、模型、训练与评估均未实现，M0 未完成。实现状态见 [docs/implementation_status.md](docs/implementation_status.md)。

截至 2026-09-16，项目处于 M0 实施阶段：研究计划和协作协议已建立；**T0001：最小 Python 包与环境诊断命令** 和 **T0002：模型结构配置的读取与校验** 均已通过 Codex 验收（`accepted`）。T0002 第 3 轮独立复跑 99 个测试、规定检查和原始异常反例通过；验收依据及历史证据限制见 [T0002 交接文档](docs/handoffs/T0002-model-config.md)。**T0003：逻辑原子与 clause 的不可变表示及静态校验**第 2 轮验收通过（`accepted`），R1 已关闭；独立完整回归 167 项及首轮 18 项边界探测全通过，见 [T0003 交接文档](docs/handoffs/T0003-logic-types.md)。**T0004：小世界朴素参考闭包求解器**第 2 轮验收通过（`accepted`），R1 关闭：独立原因守卫 7/7 有效、完整回归 218 项通过，见 [T0004 交接文档](docs/handoffs/T0004-reference-closure.md)。**T0005：独立索引闭包与小世界交叉验证**第 2 轮验收通过（`accepted`，2026-09-16）：独立完整回归 337 项与原流式探针通过，R1–R3 关闭，见 [T0005 交接文档](docs/handoffs/T0005-indexed-closure.md)。M0 尚未完成，也尚无研究实验结果，以上内容描述的目标与路径仍待验证。

实施采用小任务逐项推进：Codex + `gpt-6-astra`（`xhigh`）负责分解任务、编写交接文档和验收；Pi + `qwen3.8-coding-27b` 负责实现与自检。每项任务都有明确步骤、验证方法和验收标准，交接与执行记录统一保存在 `docs/handoffs/`。

进一步阅读：

- [完整研究计划](KMesh_Research_Plan_v0.1.md)：假设、实验设计、评价标准与参考论文；文档当前修订为 v0.1.1，保留原文件名。
- [项目工作协议](AGENTS.md)：职责分工、实施边界和验收流程。
- [任务交接目录](docs/handoffs/)：逐项实施的任务契约与记录。
- [首项任务 T0001](docs/handoffs/T0001-bootstrap-doctor.md)：建立可安装包和真实环境诊断入口。

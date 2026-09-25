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

**状态：`accepted`（2026-09-19，Codex 第 2 轮复验），R1–R3 已关闭。** 独占临时目录的独立九文件回归 **679 项通过**、stderr 空；两种已知错误实现均被加强后的测试拒绝。同一 S=1／65记录探针下，结论读取 **4,229→69**；260 是不同预算下完整展开的计数，不能直接对比。失败先留存链和接受哈希已核对，遗漏 basetemp／未归档检查等执行限制保留，见 [验收报告](reports/T0009/review-r2/review.md)。规范唯一性／motif 未实现；最短深度见下方 T0010。

单查询最短证明深度（T0010）：`kmesh.logic.depth` 提供 `minimum_proof_depth(clauses, query, *, max_fact_checks=100_000, max_derivations=100_000) -> int | None`，返回该 query 的最小证明树深度：事实为 0；规则为 1 + 最深前提（重复槽位自然覆盖）；同一结论多条来源记录取最小值。入口按“容器→成员（首个非法下标）→query 类型→ground→两个预算”次序校验（与 T0009 同口径：非 bool 正整数；消息固定且不回显未验证值）。它**只调 T0008 `enumerate_derivations` 一次**，传入原 clauses（同一 tuple，不重建）与原预算：query 是事实或不存在也不提前返回；T0008 的预算与依赖周期错误在该次调用内部原样传播，**永不转为 `None`**。T0008 完整返回后对记录做单趟前向：每条 fact 结论深度 0，每条 rule 结论深度 `1 + max(前提深度)`，同一结论只保留最小值；返回 `depths.get(query)`——无可推导记录时 `None`。**不展开任何证明树、不递归、不做证明树搜索、不用 T0006 重验证**；时间 O(R)、辅助空间 O(A)（R＝record 数，A＝distinct Atom 数），完整调用仍付 T0008 的匹配与存储成本。深度只是最小证明树深度，不等于步数、证明数、拓扑层级或 motif；仅作离线审计指标，不作为任何模型输入。最小使用例（与 `tests/test_depth.py` 同一输入和明确断言覆盖）：

```python
from kmesh.logic.depth import minimum_proof_depth
from kmesh.logic.types import Atom, Clause

def atom(pred, x, y):
    return Atom(pred, (x, y))

clauses = (
    Clause((), atom("p", "a", "b")),
    Clause((atom("p", "?x", "?y"),), atom("m", "?x", "?y")),
    Clause((atom("m", "?x", "?y"),), atom("q", "?x", "?y")),
    Clause((atom("p", "?x", "?y"),), atom("q", "?x", "?y")),
)
assert minimum_proof_depth(clauses, atom("q", "a", "b"),
                           max_fact_checks=3, max_derivations=4) == 1
assert minimum_proof_depth(clauses, atom("m", "a", "b"),
                           max_fact_checks=3, max_derivations=4) == 1

long_only = (
    Clause((), atom("p", "a", "b")),
    Clause((atom("p", "?x", "?y"),), atom("m", "?x", "?y")),
    Clause((atom("m", "?x", "?y"),), atom("q", "?x", "?y")),
)
assert minimum_proof_depth(long_only, atom("q", "a", "b"),
                           max_fact_checks=2, max_derivations=3) == 2
```

长路径 p→m→q 把 q 放到深度 2，但后来的捷径 p→q 让最小深度回到 1；只留长路径时保持 2。事实（直接给出的结论）深度为 0，完整枚举后仍推不出的 query 返回 `None`；预算不足或依赖成环时抛 T0008 的原有异常，不会变成 `None`。

**状态：`accepted`（2026-09-20，Codex 第 3 轮复验），R1–R4 全部关闭。** 产品保持冻结；独立定向回归 **53 项通过**，四个故意违约副本均被指定测试拒绝，确认异常身份、校验优先级和 H8 真实前提交换的守卫有效。本轮未重复全量回归，沿用已核对原件与哈希的 Pi 第 2 轮 **732 项通过**记录。64 次 query／60 棵证明对照继续有效；未录制检查等历史限制保留，见 [第 3 轮验收报告](reports/T0010/review-r3/review.md)。规范唯一性与 motif 未实现。

单条 clause 规范内容键（T0011，落实 D29）：`kmesh.logic.clause_key` 提供单一公开函数 `canonical_clause_key(clause) -> tuple`，返回全嵌套结构键 `("clause_key_v1", (head_pred, term0, term1), (body_atom_key, ...))`，其中 term 为 `("v", n)`（变量，首现编号）或 `("c", s)`（常量原拼写）；body 长度 0／1 只考察原顺序，长度 2 考察原序与逆序两个候选并取字典序最小值。只消除 clause 内变量改名与双前提顺序差异，**不**是证明键、世界级摘要或唯一性／motif 审计，不删除重复前提，不改变 `Clause` 结构性相等或 Python hash 语义；包零导入。最小使用例（与 `tests/test_clause_key.py` 相同输入）：

```python
from kmesh.logic.clause_key import canonical_clause_key
from kmesh.logic.types import Atom, Clause

def atom(pred, x, y):
    return Atom(pred, (x, y))

a = Clause((atom("p", "?x", "?y"),), atom("q", "?x", "?y"))
b = Clause((atom("p", "?u", "?v"),), atom("q", "?u", "?v"))
c = Clause((atom("p", "?x", "?y"),), atom("q", "?y", "?x"))

# 同内容、仅变量改名：键相等；仅 head 方向不同：键不等
assert canonical_clause_key(a) == canonical_clause_key(b)
assert canonical_clause_key(a) != canonical_clause_key(c)
assert canonical_clause_key(a) == (
    "clause_key_v1",
    ("q", ("v", 0), ("v", 1)),
    (("p", ("v", 0), ("v", 1)),),
)
```

**状态：`accepted`（2026-09-21，Codex 第 2 轮复验）**，R1–R4 关闭。独立定向 **63 项通过**，五种违约副本均被对应断言拒绝；补齐了实际改名／逆序、纯度与类型、完整诊断、根及子模块隔离守卫。产品保持冻结，本轮未重跑全量，沿用 Codex 第 1 轮 **771 项回归**与 **3571 次有限 oracle 检查**。记录更正与历史限制见 [T0011 交接文档](docs/handoffs/T0011-clause-key.md)及 [第 2 轮验收报告](reports/T0011/review-r2/review.md)。

> T0012 已由 Codex 第 5 轮验收通过（2026-09-23）；核验范围及保留限制见 [R5 报告](reports/T0012/review-r5/review.md)。

单棵证明的规范键（T0012，落实 D29/D30）：`kmesh.logic.proof_key` 提供单一公开函数 `canonical_proof_key(clauses, query, proof, *, max_steps=10000) -> tuple`，返回一个平坦前序键 `("proof_key_v1", (header, ...))`，每个 `header = (GroundKey, ClauseKey)`。`GroundKey` 是结论原子的三件 `(pred, const0, const1)`（常量字面，非 `("c", s)` 包装）；`ClauseKey` 的格式与 T0011 `canonical_clause_key` 一致（形式为 `("clause_key_v1", ...)`），由本产品内部编码、不调用 T0011。该键只针对一棵已提交、验证器通过、且每个非末节点被恰好引用一次（末节点 0 次）的“发生树”；不搜索、不判定唯一性、不是 motif 或世界级摘要。算法（仅调用 T0006 `verify_proof`）：

1. 一次调用 T0006 `verify_proof(clauses, query, proof, max_steps=max_steps)`；其 `LogicValidationError`／`ProofLimitError` 原样透传（本层不做预扫描、不改包装）；验证器返回 `False` 时抛 `LogicValidationError("proof_key.proof must be a valid proof of query")`。
2. 判单发生树：每个非末步骤 ref 次数恰为 1、末步骤 0；否则抛 `LogicValidationError("proof_key.proof must be a single occurrence tree")`，不静默去重。
3. 自底向上为每节点算 `ClauseKey`：0/1 前提取原序候选；2 前提比较 `fwd_key` 与 `rev_key`（head 后按 body 左到右编号），不同则取较小者并同步交换对应子树引用，相等时再用 `_compare_subtrees` 对两子树前序流做深比较打破平局；据此定 `children_order`（即“自底向上决定局部 joint 顺序，仅当两 slot 候选相等时比较子树顺序”）。
4. 自末节点（根）以显式栈前序遍历，把各 `(GroundKey, ClauseKey)` 依次入流；返回 `("proof_key_v1", 流)`。

仅消除结构同构子树置换、两前提 joint 顺序、ref 列表顺序与步编号差异；保留全部真实支持与重复发生，拒绝未引用步骤与共享 DAG；包零第三方导入（仅相对导入 `proof` 的验证器与异常类型；ClauseKey 内部编码，不依赖 T0011 包）。导入隔离检查（测试中用 `sys.meta_path` 禁止 `torch`、`yaml` 及所有非白名单 `kmesh.logic.*`）是测试护栏，用于保证本包运行时只依赖 `kmesh.logic.proof`，并非 `canonical_proof_key` 的运行时功能或自检。最小使用例（与 `tests/test_proof_key.py` 的 K1 相同输入）：

```python
from kmesh.logic.proof_key import canonical_proof_key
from kmesh.logic.types import Atom, Clause
from kmesh.logic.proof import ProofStep

# K1：一个事实 + 一条 COPY 规则推出第二个事实（两步发生树）
clauses = (
    Clause((), Atom("p", ("a", "b"))),
    Clause((Atom("p", ("?x", "?y")),), Atom("q", ("?x", "?y"))),
)
query = Atom("q", ("a", "b"))
proof = (
    ProofStep(0, (), Atom("p", ("a", "b"))),    # p(a,b)：事实
    ProofStep(1, (0,), Atom("q", ("a", "b"))),  # q(a,b)：由 p(a,b) 推出
)
k = canonical_proof_key(clauses, query, proof)
assert k == (
    "proof_key_v1",
    (
        (("q", "a", "b"),
         ("clause_key_v1", ("q", ("v", 0), ("v", 1)),
          (("p", ("v", 0), ("v", 1)),))),
        (("p", "a", "b"),
         ("clause_key_v1", ("p", ("c", "a"), ("c", "b")), ())),
    ),
)
```

**状态：`accepted`（2026-09-23，Codex 第 5 轮独立复验）。** 独立定向 **69 项通过**，13 个违约副本被相应断言拒绝；联合交换、重复 COPY 规则和谓词／常量大小写对照已核验。三组完整输入快照由 Codex 保留探针补证通过。产品保持冻结，本轮未重跑 full，沿用 Codex R1 的 840 项回归。缺失 preflight 等执行偏差、测试覆盖差异与历史证据限制保留，见 [R5 验收报告](reports/T0012/review-r5/review.md)及 [交接文档](docs/handoffs/T0012-proof-key.md)。

运行测试：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q tests/test_proof_key.py tests/test_clause_key.py tests/test_depth.py tests/test_proof_enumeration.py tests/test_derivations.py tests/test_dependency.py tests/test_proof.py tests/test_engine.py tests/test_reference_engine.py tests/test_logic_types.py tests/test_config.py tests/test_doctor.py
```

规范证明计数（T0013，落实 D31）：`kmesh.logic.proof_count` 提供单一公开函数 `count_canonical_proofs(clauses, query, *, max_fact_checks=100000, max_derivations=100000, max_proof_steps=100000) -> int`，是 T0009 原始树枚举与 T0012 单棵规范键的薄组合。固定行为：首操作恰好一次调用 T0009 `enumerate_proofs`（C/D/S 原样透传；C/D 交给 T0008 推导枚举，S 为全部生成子步骤的累计预算——耗尽在枚举时抛 `DerivationLimitError`／`ProofEnumerationLimitError`；预算超限是限流异常，不是“无证明”结果，也不返回部分计数；世界失败抛 T0009 的 `LogicValidationError`），其后按原返回顺序对每个原始树恰好一次调用 T0012 `canonical_proof_key(clauses, query, proof, max_steps=S)`（验证由 T0012 负责），以完整前序键的集合归并，返回集合长度（`type` 为 `int`）；空枚举在枚举成功后返回 0，且从不调用键。0 表示完整枚举后 query 不可推出；1 表示唯一规范证明（重复来源、α-等价树、对称槽的 AB/BA 排列归一）；大于 1 表示存在多条互不相同的支持。不搜索、不判定 motif、不是世界级摘要，也不新增预算、摘要类型、缓存或第二个唯一性 API。

**状态：`accepted`（2026-09-24，Codex 第 3 轮复验，R1–R3 关闭）。** 产品持续冻结；独立定向 21 项通过，根／子模块前缀自测有效，运行期观察确认 finder 在真实导入、U2/U6 及最终扫描后均保留。沿用 Codex 独立 884 项 full；Pi 额外自检 885 项单列为 Pi 证据，本轮未重跑 full。历史记录更正及模型自述来源限制保留。见 [最终验收报告](reports/T0013/review-r3/review.md)与 [交接文档](docs/handoffs/T0013-proof-count.md)。

U3 直接可运行例（两条相同 p 事实 ＋ COPY 规则 ＋ α-等价 COPY 规则；原始 4 棵证明树归一为 1 棵）：

```python
from kmesh.logic.proof_count import count_canonical_proofs
from kmesh.logic.types import Atom, Clause


def fact(pred, a, b):
    return Clause((), Atom(pred, (a, b)))


def a(pred, x, y):
    return Atom(pred, (x, y))


world = (
    fact("p", "a", "b"),
    fact("p", "a", "b"),
    Clause((a("p", "?x", "?y"),), a("q", "?x", "?y")),
    Clause((a("p", "?u", "?v"),), a("q", "?u", "?v")),
)
query = a("q", "a", "b")
print(count_canonical_proofs(world, query,
                            max_fact_checks=2, max_derivations=4,
                            max_proof_steps=10))  # 1
```

运行测试（十三文件）：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q tests/test_proof_count.py tests/test_proof_key.py tests/test_clause_key.py tests/test_depth.py tests/test_proof_enumeration.py tests/test_derivations.py tests/test_dependency.py tests/test_proof.py tests/test_engine.py tests/test_reference_engine.py tests/test_logic_types.py tests/test_config.py tests/test_doctor.py
```
## 证明结构签名（T0014）：单棵证明跨世界 motif 键

`kmesh.logic.motif` 提供单棵证明的有界参考 motif 键。对同一棵出现树的多份等价世界（关系／实体／局部变量改名），`canonical_motif_key(clauses, query, proof, *, max_steps=10_000, max_orientations=100_000)` 返回完整平坦 `proof_motif_v1` 前序键，只记录树形、参数位置、schema 常量／变量、重复槽位与跨子树共享，不记录具体关系／实体名。结构等价的不同支持可能具有同一 motif，但**不是**唯一性判据：两条同世界不同支持仍可同 motif（仍依赖 T0013 计数／唯一性审计）；跨世界 motif 仅用于离线审计，不进入模型输入白名单，也不表示 world 无泄漏、内部子结构匹配或 split 完成。

预算：`max_steps` 原样透传给 T0012（默认 10_000）；`max_orientations` 限制联合方向候选数（默认 100_000）。B 个二槽发生要求恰 2^B 候选（重复也计）；超限在编码前预检并抛 `MotifLimitError`，禁止部分键、剪枝或近似。本阶段为指数有界参考算法，预算不是固定墙钟保证；后续如优化须另验完整性。

当前状态为 **`accepted`**（2026-09-25，Codex 第4轮复验）。独立32项通过，四个违约副本均被对应断言拒绝；产品冻结，四函数修补及2981项旧材料未变已核验。本轮未重跑full，沿用已核对的Pi917项回归；历史留证和模型来源限制保留，记录误述由Codex追加更正。见 [最终验收报告](reports/T0014/review-r4/review.md)与 [交接文档](docs/handoffs/T0014-proof-motif.md)。

最小可运行例（单事实 ＋ COPY 得 `q(a,b)`）：

```python
from kmesh.logic.motif import canonical_motif_key
from kmesh.logic.types import Atom, Clause
from kmesh.logic.proof import ProofStep

clauses = (
    Clause((), Atom("p", ("a", "b"))),
    Clause((Atom("p", ("?x", "?y")),), Atom("q", ("?x", "?y"))),
)
query = Atom("q", ("a", "b"))
proof = (
    ProofStep(0, (), Atom("p", ("a", "b"))),
    ProofStep(1, (0,), Atom("q", ("a", "b"))),
)
k = canonical_motif_key(clauses, query, proof)
print(k)
assert k == ("proof_motif_v1", (
    ((0, 0, 1), (0, ("v", 0), ("v", 1)), ((1, ("v", 0), ("v", 1)),)),
    ((1, 0, 1), (1, ("c", 0), ("c", 1)), ()),
))
print("COPY motif key matches contract literal")
```

运行测试（T0014 及既有回归，十四文件）：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q tests/test_motif.py tests/test_proof_count.py tests/test_proof_key.py tests/test_clause_key.py tests/test_depth.py tests/test_proof_enumeration.py tests/test_derivations.py tests/test_dependency.py tests/test_proof.py tests/test_engine.py tests/test_reference_engine.py tests/test_logic_types.py tests/test_config.py tests/test_doctor.py
```

当前限制：T0001、T0002、T0003 覆盖最小包、环境诊断、模型结构配置校验与带静态校验的不可变逻辑类型（均已验收）；T0004 覆盖朴素参考闭包求解器（已验收）；T0005 覆盖索引主闭包求解器与 64 个固定 seed 小世界交叉验证（第 2 轮已验收，`accepted`）；T0006 覆盖独立给定证明验证器（第 3 轮已验收，`accepted`）；T0007 覆盖离线关系依赖无环检查（第 2 轮已验收，`accepted`）；T0008 覆盖无环世界的直接推导枚举（第 2 轮已验收，`accepted`）；T0009 的单查询原始有序证明树枚举已验收（`accepted`，第 2 轮关闭 R1–R3，执行限制保留）；T0010 的单查询最短证明深度已验收（`accepted`，第 3 轮关闭 R1–R4，历史留证限制保留）；T0011 的单条 clause 规范内容键已验收（`accepted`，第 2 轮关闭 R1–R4，独立 63 项及五个违约守卫通过）；T0012 的单棵证明规范键已验收（`accepted`，Codex R5 独立 69 项及 13 个违约守卫通过，三组输入纯度以独立探针补证，流程偏差与历史限制保留）；T0013 的单查询规范证明计数已验收（`accepted`，Codex 第 3 轮独立 21 项、前缀守卫及运行期硬隔离通过，历史记录限制保留）；T0014 的单棵证明跨世界 motif 键已通过 Codex 第4轮验收（`accepted`，独立32项及四个违约守卫通过，执行限制保留）；正式数据唯一性准入、world motif 审计、完整运行配置校验、数据、模型、训练与评估均未实现，M0 未完成。实现状态见 [docs/implementation_status.md](docs/implementation_status.md)。

截至 2026-09-24，项目处于 M0 实施阶段：研究计划和协作协议已建立；**T0001：最小 Python 包与环境诊断命令** 和 **T0002：模型结构配置的读取与校验** 均已通过 Codex 验收（`accepted`）。T0002 第 3 轮独立复跑 99 个测试、规定检查和原始异常反例通过；验收依据及历史证据限制见 [T0002 交接文档](docs/handoffs/T0002-model-config.md)。**T0003：逻辑原子与 clause 的不可变表示及静态校验**第 2 轮验收通过（`accepted`），R1 已关闭；独立完整回归 167 项及首轮 18 项边界探测全通过，见 [T0003 交接文档](docs/handoffs/T0003-logic-types.md)。**T0004：小世界朴素参考闭包求解器**第 2 轮验收通过（`accepted`），R1 关闭：独立原因守卫 7/7 有效、完整回归 218 项通过，见 [T0004 交接文档](docs/handoffs/T0004-reference-closure.md)。**T0005：独立索引闭包与小世界交叉验证**第 2 轮验收通过（`accepted`，2026-09-16）：独立完整回归 337 项与原流式探针通过，R1–R3 关闭，见 [T0005 交接文档](docs/handoffs/T0005-indexed-closure.md)。T0014 单树 motif 键已通过 Codex 第4轮验收（`accepted`，2026-09-25），具体证据与执行限制见上文。M0 尚未完成，也尚无研究实验结果，以上内容描述的目标与路径仍待验证。

实施采用小任务逐项推进：Codex + `gpt-6-astra`（`xhigh`）负责分解任务、编写交接文档和验收；Pi + `qwen3.8-coding-27b` 负责实现与自检。每项任务都有明确步骤、验证方法和验收标准，交接与执行记录统一保存在 `docs/handoffs/`。

进一步阅读：

- [完整研究计划](KMesh_Research_Plan_v0.1.md)：假设、实验设计、评价标准与参考论文；文档当前修订为 v0.1.3，保留原文件名。
- [项目工作协议](AGENTS.md)：职责分工、实施边界和验收流程。
- [任务交接目录](docs/handoffs/)：逐项实施的任务契约与记录。
- [首项任务 T0001](docs/handoffs/T0001-bootstrap-doctor.md)：建立可安装包和真实环境诊断入口。

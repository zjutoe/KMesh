# T0008：无环世界的直接推导枚举

## 任务信息

- 任务编号／修订号：T0008 / r1，2026-09-17。
- 状态：`awaiting_review`（2026-09-17，Pi + `qwen3.8-coding:27b-q8_0-64k` 完成实施与自检；分支 `T0008-ground-derivations` 自基线 `a944125` 建立，保留 Codex 交接改动；未 commit/push）。
- 所属阶段与协议：M1 / E0-D；研究计划 v0.1.2，E0 `e0_v2` §4.1–4.5、§5.2、§15.1；工程约定 D26。不改变数据划分、模型信息、训练目标或研究预算。
- 规划者／验收者：Codex + `gpt-6-astra`，`xhigh`。
- 执行者：Pi + `qwen3.8-coding-27b`；当前完整模型别名 `qwen3.8-coding:27b-q8_0-64k`（ollama），开工记录实际值，不自行换模型／配置。
- 基线：`a9441250626f087dc8dbc1f560b7fbe3fe92488b`，当前分支 `T0007-relation-dag`，已推送同名远端；规划起点工作树干净。**此基线不在当前 master 上；不得从 master 的旧版本开工。** 核对后从此基线建立 `T0008-ground-derivations` 并保留 Codex 交接改动。
- 前置：[T0003](T0003-logic-types.md) 内容类型、[T0007](T0007-relation-dag.md) DAG 检查已验收；T0004/T0005 求解器仅作测试端对照，T0006 verifier 留作后续完整证明核验。既有完整回归 482 项。
- 已有交接改动：Codex 新增本文、`reports/T0008/` 记录器／规划材料，追加 D26／T0007 后续关联，更新实现状态；不是 Pi 的产品交付。
- 必读：[AGENTS.md](../../AGENTS.md)、[研究计划 §4–5／15.1](../../KMesh_Research_Plan_v0.1.md)、[D18／D25／D26](../decisions.md)、[types.py](../../src/kmesh/logic/types.py)、[dependency.py](../../src/kmesh/logic/dependency.py)、本文及 [record_check.py](../../reports/T0008/record_check.py)。
- 规划审阅：[planning-review.md](../../reports/T0008/planning-review.md)；接口／例子／预算已独立核对，产品验收仍须在 Pi 交付后进行。

## 目标、范围与交付物

**单一目标：在关系依赖无环的 clauses 中，完整列出每个事实和每次成功规则应用的“原 clause 位置、具体前提、具体结论”。** 同一结论的不同来源都要保留，为之后检查替代证明提供基础。

一个直接推导不是一棵完整证明树。上游结论可能有多种证明，下游对它的一次引用仍只产生一条直接推导。**不得据本接口的记录数判定 query 的完整证明数、唯一性或最短深度。** 后续任务再展开／验证完整证明，并另做规范 signature、motif、family 和泄漏审计；本任务不宣称 M1 完成。

| 允许新增／修改 | 交付内容 |
|---|---|
| `src/kmesh/logic/derivations.py` | frozen `GroundDerivation`、`DerivationLimitError`、`enumerate_derivations` 及必要私有函数 |
| `tests/test_derivations.py` | 手算完整记录、匹配／预算边界、结构校验、64 个微型世界对照、导入隔离 |
| `README.md`、`docs/implementation_status.md` | 简短 API 用法、实际状态、上述限制及测试命令 |
| 本交接文档 | 头部状态与追加 Pi 执行记录；不改契约／验收标准／Codex 记录 |
| `reports/T0008/` 下新的 `pi-*` RUN／脚本目录 | 原始命令、两路输出、退出码、哈希，最终 full RUN 的 provenance |

记录器与 `.gitignore` 原样使用。冻结旧源码／测试、`logic/__init__.py`、AGENTS、研究计划、decisions、旧交接及历史报告。只新增一个产品模块，不重构共享匹配框架、不新增依赖、World 包装类、CLI 或持久化格式。无外部数据、模型、训练或 GPU 工作。

## 前提与假设

- [规划核对](../../reports/T0008/planning-baseline.json) 已确认 HEAD、T0007 接受哈希、Python 3.13.9、editable kmesh 0.1.0、pytest 8.4.2；新模块／测试尚不存在。`.venv/bin/python` 可用，使用 `python -m pytest`，不要假定存在 `.venv/bin/pytest`。
- 输入 Atom/Clause 均经正常构造，不处理绕过 frozen／构造器的伪造对象。沿用二元、0–2 前提、head 变量受 body 约束；不额外限定 COPY/INV/JOIN/INTER 模板。body-only 变量、常量、ground 规则、重复 clause 都合法。
- DAG 保证全部前提谓词先于结论谓词完成。具体前提元组确定本 clause 的全部 body 变量绑定，因此可在每个 head 谓词处一次性收集全部直接应用，无需同步不动点轮次。这个完备性前提须以手算记录和闭包对照核验。
- 只读仓库相关代码／文档和环境元数据；测试全部手工合成，没有锁定研究测试、外部数据、网络、依赖安装或 GPU。记录器固定 `CUDA_VISIBLE_DEVICES=""`，不是机器没有 GPU 的证据。
- 仅使用 CPU，每条检查命令墙钟上限 120 秒，总自检命令耗时预算 10 分钟。达到时限、旧文件哈希不符或契约冲突时保存证据并反馈，不扩预算或跳过用例。接口的两项计数预算只约束枚举工作／输出量，不是正式数据生成配额、proof 数上限或绝对内存／墙钟保证。
- 若 HEAD 仅新增本次交接文档提交，核对旧源码和契约未变后记录实际基线继续；其他相关变化先反馈，不回退他人工作。

## 具体实施步骤

### 1. 核对起点并落盘状态

先运行下方 preflight，核对 before 中两个新文件为 null，旧文件／记录器哈希与 planning-baseline 一致。记录实际模型、基线和分支，将本文与实现状态置 `in_progress` 后再编码。分小段写文件；中断后读已落盘内容，不整体重写已经完成的模块。

### 2. 定义直接推导的结构和输入边界

```python
@dataclass(frozen=True)
class GroundDerivation:
    clause_index: int
    premises: tuple[Atom, ...]
    conclusion: Atom

class DerivationLimitError(RuntimeError): ...

def enumerate_derivations(
    clauses: tuple[Clause, ...],
    *,
    max_fact_checks: int = 100_000,
    max_derivations: int = 100_000,
) -> tuple[GroundDerivation, ...]: ...
```

`clause_index` 是本次 clauses 的位置，不是稳定 patch ID；`premises` 按原 body 位置保存 ground Atom（不是 ProofStep 下标）。事实记录的 premises 为 `()`。不增添角色、模板、深度、rank 或 proof ID 字段。

GroundDerivation 构造按下表从上到下校验；只检查局部结构，不查看 clauses，不验证推导语义。大正 index 可合法构造。

| 字段／顺序 | 规则 | 完整错误消息（T 为实际类型名，i 为位置，n 为长度） |
|---|---|---|
| clause_index | `type(value) is int` 且 ≥0 | `derivation.clause_index must be a non-bool non-negative integer; got T` |
| premises 容器 | `isinstance(value, tuple)` | `derivation.premises must be a tuple of Atom; got T` |
| premises 长度 | 最多 2，先于成员检查 | `derivation.premises holds at most 2 atoms; got n` |
| 每个 premises[i] | 先 Atom 类型，再 is_ground | `derivation.premises[i] must be an Atom; got T` 或 `derivation.premises[i] must be a ground Atom` |
| conclusion | 先 Atom 类型，再 is_ground | `derivation.conclusion must be an Atom; got T` 或 `derivation.conclusion must be a ground Atom` |

所有这些错误用现有 `LogicValidationError`。冻结、结构相等和可 hash；premises 顺序／重复原子保留。漏参／额外关键字仍由 Python 抛 TypeError。

enumerate_derivations **依次**校验：clauses 是 tuple → 从左至右每项是 Clause → max_fact_checks → max_derivations → 调用已验收 `relation_topological_order(clauses)`。预算必须 `type(value) is int` 且 >0，不做转换，不限制合法大正整数。错误消息分别为：

```text
enumerate.clauses must be a tuple of Clause; got T
enumerate.clauses[i] must be a Clause; got T
enumerate.max_fact_checks must be a non-bool positive integer; got T
enumerate.max_derivations must be a non-bool positive integer; got T
```

DAG 的循环错误原样传播：`dependency.clauses: cyclic predicate dependency`；连同无事实、不连通和不能触发的循环都拒绝。非法参数先于 DAG 错误；通过所有校验后空输入才可返回 `()`。

类型诊断只用 `type(value).__name__`，不得格式化未验证值／容器，不宽泛捕获异常或修改整数转换上限。不消费非法外层 generator。

### 3. 按谓词拓扑顺序枚举全部直接应用

实现迭代的、索引化的扫描，不递归，不做全局常量域的笛卡尔积，不调用旧求解器来补答案。

1. 保留原 clause index，按 head 谓词分组；组内保持原输入顺序。依照 T0007 返回的关系拓扑序处理各组（body-only 谓词没有 clause 组）。
2. 对每个已完成谓词维护去重 ground Atom 桶，桶按 `atom.args` 的 Python tuple 字符串顺序排序；不按上游推导记录建立候选桶。当前 head 组完成后再定稿自己的桶，供后继使用。
3. 每条事实产生一条 `(index, (), head)` 记录；相同事实在不同位置出现也各保留一条。每条非空规则只扫描一次，按原 body 顺序匹配桶内原子。常量须相等、同一变量须在两参数／两前提内一致，变量字典只在本次规则匹配分支内共享。ground 前提匹配得到空字典也算成功。
4. 单前提：逐候选匹配；双前提：第一桶为外层，每次匹配第一前提成功后立即按序扫描第二桶。在第二前提成功时立即实例化 head 并追加记录，不先收集全部绑定表。同一 ground Atom 可以同时用于两个重复前提。
5. **每个成功的 `(clause_index, ordered ground premises)` 必须保留一次，即使 conclusion 已知也不跳过。** 多个 body-only 变量绑定可产生相同 conclusion；不同 clause 也可产生相同 conclusion。这里只对候选 Atom 去重，不合并推导来源、不按支持集或 motif 合并记录。
6. 返回恰为 tuple；记录顺序是 **T0007 的谓词拓扑序 → 同 head 的原 clause index → 上述候选嵌套顺序**。不对最终结果另做全局排序。同一输入重复运行结果完全相同；输入 clauses 重排会改变 index／顺序，不要求原 tuple 逐位不变。

产品依赖只允许标准库、`kmesh.logic.types` 与 `kmesh.logic.dependency`。不导入／调用 engine、reference_engine、proof、torch、yaml；不修改旧模块来共用私有方法。无文件 I/O、随机性、全局可变缓存或输入修改。索引／匹配细节可用少量私有函数，不建立新框架。

**完整性含义：** 在 DAG 输入下，返回中 conclusion 的集合应恰为完整闭包；每个前提在更早已完成谓词的结论集合中。它保存全部直接来源，尚未组合每个前提的替代证明。

### 4. 实现可核对的预算与失败语义

- `max_fact_checks`：每准备把一个候选 Atom 与当前前提／当前绑定匹配时，先检查剩余额度，再扣 1。失败匹配也计数；第二桶因不同第一候选反复扫描，每次都计数。空桶不产生候选；双前提第二桶为空时仍须按上述次序扫描第一桶，不能提前短路改变计数。事实、建索引／排序、实例化 head 不消耗本预算。
- `max_derivations`：每追加一条记录（含事实、重复 clause 记录、同 conclusion 的替代来源）前检查额度，再消耗 1。它数的是输出记录，不是不同结论数。
- 两项都是整次调用累计。恰好用完并完成枚举应正常返回；只有还需下一次操作才超限。无需最后“无新增轮”。先前输出额度用完但后续仅有失败匹配时，仍可成功完成。
- 成功匹配后立即检查输出额度；匹配预算检查发生在该次匹配之前。若不同限制可能先触发，严格遵循实际扫描操作顺序，不预估数量或预先合并预算。
- 超限抛 DerivationLimitError，消息固定为 `enumerate.max_fact_checks exhausted before enumeration completed` 或 `enumerate.max_derivations exhausted before enumeration completed`。不返回部分记录／False、不吞异常、不标记唯一／不可推出；局部输出全部随异常丢弃。失败后再次正常调用不受污染。

### 5. 编写有区分力的测试

以下简写 `p(a,b)` 表示 Atom，`x/y/z` 在对象中写 `?x/?y/?z`，`k` 是常量。`D(i, (前提…), 结论)` 表示 GroundDerivation。**所有正例按完整记录比对，不只检查 conclusion 集合或长度。** 预期不得由被测枚举器或其私有函数生成。

#### 手算主例与预算

| 例 | 按输入顺序的 clauses | 完整预期要点 | 检查数 C／记录数 D |
|---|---|---|---|
| E0 | 空 | `()` | 0 / 0 |
| E1 | `z(c,d)`、`p(a,b)`、重复 `p(a,b)` | `D(1,(),p(a,b)), D(2,(),p(a,b)), D(0,(),z(c,d))` | 0 / 3 |
| E2 | `r1(a,b)`、`r2(b,c)`、`r1(x,y),r2(y,z)→r3(x,z)`、`r3(x,y)→r4(y,x)` | 两事实，`D(2,(r1(a,b),r2(b,c)),r3(a,c))`，`D(3,(r3(a,c),),r4(c,a))` | 3 / 4 |
| E3 | `p(a,b)`、`p(a,c)`、`p(x,y)→q(x,k)`、`q(x,k)→r(x,k)` | 两事实，两条 index=2 的 q(a,k)（前提不同），一条 index=3 的 r(a,k) | 3 / 5 |
| E4 | `p(a,b)`、`p(c,d)`、`q(a,b)`、`q(b,a)`、`q(c,e)`、`p(x,y),q(x,y)→r(x,y)` | 五事实，只新增 `D(5,(p(a,b),q(a,b)),r(a,b))` | 8 / 6 |
| E5 | `p(a,b)`、`p(c,c)`、`p(x,x)→r(x,x)` | 两事实，只新增 `D(2,(p(c,c),),r(c,c))` | 2 / 3 |
| E6 | `p(a,b)`、`p(x,y),p(x,y)→q(x,y)` | 一事实，`D(1,(p(a,b),p(a,b)),q(a,b))` | 2 / 2 |
| E7 | `p(a,b)`、`p(a,b)→q(c,d)` | 一事实和一个完全 ground 的应用，不能误把空 binding 当失败 | 1 / 2 |
| E8 | `p(a,b)`、`p(c,d)→q(c,d)` | 只有事实；检查失败但仍计 1 | 1 / 1 |
| E9 | `p(a,b)`、`p(c,d)`、`p(x,y),q(x,y)→r(x,y)` | 只有两事实；第二桶为空仍扫描两个 p | 2 / 2 |
| E10 | `q(a,b)`、`p(x,y),q(x,y)→r(x,y)` | 只有 q 事实；第一桶为空不扫描第二桶 | 0 / 1 |

每行都验证精确输出。C>0 的行用预算 C 正常结束，C>1 时再用 C−1 抛匹配超限；C=0 用合法最小预算 1。D>0 的行用输出额度 D 正常结束，D>1 时用 D−1 抛输出超限；E0 用两个 1。测一项不足时另一项给足，不互相遮蔽；0 预算另测输入错误。E8 特别用 `max_derivations=1` 证明已满额但没有新输出时仍可成功。

再覆盖以下不同机制（可以组合相关 fixture，不必追求固定测试数）：

- **全部替代来源与事实并存：** `(p(a,b), q(a,b), p(x,y)→q(x,y), 重复同条规则, q(x,y)→r(x,y))`。返回两个事实、两条 index=2/3 的 q 推导、一条 index=4 的 r 推导，共 5 条、C=3。不能跳过已知 head，也不能让重复来源扩大下游候选桶。facts 与规则在同 head 组的原 index 顺序必须保留，再把 q 事实移到规则之后验证此顺序。
- **上游替代不在本层展开：** E3 中 r 只有一条直接记录，却有两种上游完整证明；把 r 的规则改为 `q(x,k),q(x,k)→r(x,k)`，仍只有一条 `(q(a,k),q(a,k))` 记录（总 C=4）。不可因为只见一条 r 记录就输出“唯一”。
- **匹配完整性：** JOIN 同 head 来自不同中间实体（`p(a,b),p(a,c),q(b,d),q(c,d)` → r(a,d)），保留两条不同前提配对，拒绝共享变量冲突的交叉配对。另有第一候选绑定失败、第二候选成功的例，确认失败不污染绑定；不同 clause 复用 `?x` 不串绑定；方向 INV、head 常量和两个互不共享变量的前提都要覆盖。
- **双前提空绑定：** `(p(a,b),q(c,d),[p(a,b),q(c,d)]→r(e,f))`，两次匹配都得到空字典但必须产生第三条记录；完整返回两事实及 `D(2,(p(a,b),q(c,d)),r(e,f))`，C=2／D=3。与 E7 分别覆盖双／单前提路径。
- **即时追加／预算先后：** 上述 JOIN 四事实 + 一规则，给 `max_fact_checks=2,max_derivations=4`，第一对在第 2 次匹配成功后必须报输出超限，不能先扫描后续候选报匹配超限。相同输入 `max_fact_checks=1,max_derivations=4` 则先报匹配超限。断言两种完整原因。
- **候选桶排序：** 两条 p 事实输入顺序 p(c,d)、p(a,b)，后接 COPY 到 q；事实记录保持输入顺序，q 记录按 p(a,b)、p(c,d) 顺序。新就绪 b 在孤立 z 前的顺序沿用 T0007，不重新实现拓扑策略。
- **长链／纯度：** p0000(a,b) 事实加 1199 条 COPY 到 p1199；返回 1200 条手算记录（indices 与节点序对应），C=1199；不改递归上限、不写耗时阈值。输入前后相等、重复调用完全相同，先预算失败／循环失败后成功不会残留状态。返回类型恰为 tuple，记录 frozen/hash/equality，前提顺序和 clause_index 影响结构相等。
- **DAG 拒绝：** 自环、无事实 p→q→p、一个合法分量加断开循环；均断言原 dependency 完整循环消息。成功后又加入无法触发的 ground 循环也必须拒绝，不能因当前闭包无变化而忽略。
- **输入和优先级：** 上述两个 API 的每条校验分支都有合法对照与单点变异；每例断言完整目标原因与路径。外层 list/generator 不转换，generator 不消费；tuple 成员 Atom/None 非 Clause；预算 0、−1、bool、float、None；GroundDerivation 非 int／负 index、premises 非 tuple／3 个成员／非 Atom／含变量、非 Atom／非 ground conclusion。多错仅用于专门优先级例：三前提含坏成员先报长度；cycle+坏成员先报成员；cycle+坏预算先报预算；两个预算均坏先报 max_fact_checks。
- **大整数边界：** fixture 固定 `sys.set_int_max_str_digits(4300)`、finally 恢复，用工厂＋短 ids。`10**5000` 用作合法 index／两个正预算应接受；负巨整数作 index／预算、正巨整数作 clauses／tuple 成员／premises 成员／conclusion 应抛目标 LogicValidationError 而不是格式化 ValueError。只检查 type 名称，不 repr 参数值。无需造无穷多类型组合。

#### 64 个微型世界的独立对照

不用随机生成器，也不调用被测函数生成预期。按 mask=0…63，六个 bit 分别决定以下 clause 是否存在，顺序固定：四事实 `p(a,b),p(a,c),q(b,d),q(c,d)`，COPY `p(x,y)→s(x,y)`，JOIN `p(x,y),q(y,z)→r(x,z)`。每个世界用足够预算枚举，验证：

1. conclusion frozenset 同时等于现有 reference_closure 和 indexed_closure 的完整返回；只在测试端导入两求解器。
2. 直接记录还要等于**独立手算预期**：存在的每个 fact 各一条；COPY 存在时，对存在的两条 p 各一条 s；JOIN 存在且第 0、2 bit 同时存在时有经 b 的 r(a,d)，第 1、3 bit 同时存在时有经 c 的 r(a,d)，无其他配对。由保留 clauses 的实际位置映射 index，使用 `Counter(actual) == Counter(expected)` 比较全部记录及其出现次数，不能仅比较 set 而漏掉重复输出；输出顺序由主例单测，不使用被测排序来构造预期。

这可抓住“闭包对了但丢掉替代来源”的错误，不能将闭包一致当全部推导已穷尽的唯一证据。六位集合都是无环；不把循环世界交给本接口后要求和旧求解器同接受范围。

#### 新进程导入隔离

干净 Python 子进程中，用 finder 阻断 `torch`、`yaml`、`kmesh.logic.engine`、`kmesh.logic.reference_engine`、`kmesh.logic.proof`（精确根名或根名加点前缀），先各直接 import 并断言 ImportError 以自检守卫。再导入新模块，构造 ground 记录并运行 E2／空输入／超限路径；扫描全部 sys.modules 确认禁用根及子模块均未加载。允许 types/dependency；`logic/__init__.py` 保持零导入。不要用会污染其他测试的全局 autouse 隔离。

### 6. 留存检查并交回

从首次开发检查起都用原记录器，包括临时探针／README 示例／文档检查。命令写错、收集失败、测试 fixture 错误也是一次尝试；失败先留存，再最小修复换新 RUN。成功 RUN 同样不可覆盖，不能删除／清空／移动旧目录来重录；不要先在 `/tmp` 裸跑再只归档最终成功。

README 加一个短例及“直接应用不是完整证明”的限制，测试命令补新文件。最终 full RUN 添加 provenance：实际工具／完整模型、HEAD、源码测试哈希、RUN argv／退出码／原始路径、未运行项、偏差；时间取 record.json，命令耗时与实施时段分开写。无需重复机器 doctor，不把记录器隐藏 CUDA 解释为硬件变化。

最后一次文档编辑后用一个新 RUN 检查 `git diff --check`、新文本换行／尾随空白、新本地链接、授权路径、旧源码哈希和忽略 scratch。无需固定测试总数、git status 行数或不断回填本次检查时间的自引用清单。不要复制历史 evidence 再做大型冻结框架；原记录器已经保存源码与原始输出。

本文 Pi 区追加真实记录，本文／实现状态／README 本项状态置 `awaiting_review` 并冻结相关 diff。Codex 验收前不启动后续证明任务、不自动 commit/push。

## 验证方法

工作目录 `/home/mye/src/llm/KMesh`。记录器创建全新 RUN，固定插件隔离、CUDA 隐藏和 120 秒时限，保存 19 项源码／测试／记录器的前后哈希。**RUN 不预建；不向尚不存在的 RUN 重定向。** preflight 在实施前；focused 成功后才跑 full，不串接 doctor。

```bash
.venv/bin/python reports/T0008/record_check.py pi-r1-preflight -- .venv/bin/python -c 'import sys, kmesh; from importlib.metadata import version; print(sys.executable); print(sys.version); print(kmesh.__file__); print({n: version(n) for n in ("kmesh", "pytest")})'
.venv/bin/python reports/T0008/record_check.py pi-r1-focused -- .venv/bin/python -m pytest -q tests/test_derivations.py --basetemp reports/T0008/pi-r1-focused/pytest-tmp
.venv/bin/python reports/T0008/record_check.py pi-r1-full -- .venv/bin/python -m pytest -q tests/test_derivations.py tests/test_dependency.py tests/test_proof.py tests/test_engine.py tests/test_reference_engine.py tests/test_logic_types.py tests/test_config.py tests/test_doctor.py --basetemp reports/T0008/pi-r1-full/pytest-tmp
.venv/bin/python reports/T0008/record_check.py pi-r1-diff-check -- git diff --check
```

其他检查亦通过记录器，例如 `pi-r1-doc-check -- .venv/bin/python reports/T0008/pi-r1-scripts/check_docs.py`。失败换未使用编号并同步 basetemp；原始失败目录保留。所有新测试及原 482 项通过，无 skip/xfail；非零退出、超时 124、启动错误 127 均不是通过。不调用旧任务记录器或旧固定哈希审计脚本。

## 验收标准

- [ ] A1：GroundDerivation 的三个字段、结构校验／顺序、不可变性和错误边界符合契约；enumerate 参数错误先于 DAG；大整数诊断安全。
- [ ] A2：无环输入完整保存每个 clause 位置的全部 ground 直接应用；事实／规则／不同绑定的替代来源不丢失，下游候选 Atom 去重，不展开 proof 组合。
- [ ] A3：匹配共享变量／常量／重复前提／ground／body-only 变量正确；按 topo→index→候选顺序一次迭代，长链和纯度通过；不支持的循环明确拒绝。
- [ ] A4：两类预算的逐操作计数、精确边界、先后顺序及异常符合契约，不返回部分结果，不把超限当否定／唯一。
- [ ] A5：完整手算记录、能拒绝错误实现的反例和 64 世界独立预期通过；与两闭包求解器一致；原 482 项回归通过且不改弱旧测试。
- [ ] A6：产品只依赖标准库／types／dependency；禁用导入守卫有效，所有新信息仅供离线审计，不扩展模型输入／预测路径。
- [ ] A7：授权范围、基线、实际模型、命令／失败链／输出／退出码和哈希可核对；历史不覆盖，文档准确区分直接推导、完整证明和未完成研究工作。

## Pi 执行记录

第 1 轮（2026-09-17，Pi + `qwen3.8-coding:27b-q8_0-64k`，ollama）：分支 `T0008-ground-derivations` 自 `a9441250626f087dc8dbc1f560b7fbe3fe92488b` 建立，开工时工作树仅含 Codex 交接改动。

**偏差与说明：**
1. 契约命令中的相对解释器路径 `.venv/bin/python` 在本环境 shell=False 下无法解析（裸 `python` 解析到 `/opt/anaconda3/bin/python`，无 `kmesh`）；全程改用同一文件的绝对路径 `/home/mye/src/llm/KMesh/.venv/bin/python`，pytest 均以 `python -m pytest` 启动，解释器版本不变（3.13.9，editable kmesh 0.1.0，pytest 8.4.2）。
2. E0/D 预算契约：C/D 的“−1 边界”在预算 <2 时无合法更小正整数（0/负数为输入错误非耗尽）；相应主例（E8 C=1、D 总量 ≤1）只验最小合法预算，C≥2/D≥2 的主例均验证了 −1 边界；E0 按契约用两个 1。
3. 微世界 64 例的预期记录组顺序由 `relation_topological_order`（T0007 确定性 Kahn）推导，不硬编码 copy/join 先后。

**开发失败链（失败先保存，未覆盖）：** `pi-r1-focused-dev1`（原始合同名下首次失败运行：测试收集错误，`rule()` helper 多传参数；已按“失败先保存”重命名为 dev1，合同名重录成功）、`pi-r1-preflight-dev1/dev2/dev3` 与 `pi-r1-preflight-verify-dev1`（预检解释器/脚本修正）；`pi-r1-focused-dev2`（135 过/31 败/2 错：测试侧 helper 与 `pytest.raises` 误用）、`pi-r1-focused-dev3`（集合误用）、`pi-r1-focused-dev4`（141/25/2：错误消息与 E0/E7 边界修正）、`pi-r1-focused-dev5`（154/12/0：bucket 传播与拓扑序修正）、`pi-r1-focused-dev6`（165/1：隔离脚本预算算错）、`pi-r1-focused-dev7`（166/0/0：dev 链终态）。产品侧唯一真实缺陷为成功应用未将新结论入候选桶导致 JOIN 链截断（dev4→dev5 修复）。

**合同 RUN（绝对解释器偏差见上；basetemp 按契约；exit 0）：**

| RUN | 命令 | 结果 |
|---|---|---|
| `reports/T0008/pi-r1-preflight` | `record_check.py pi-r1-preflight -- <绝对解释器> -c '<版本探测>'` | exit 0，解释器/版本/包路径正确 |
| `reports/T0008/pi-r1-focused` | `record_check.py pi-r1-focused -- <绝对解释器> -m pytest -q tests/test_derivations.py --basetemp reports/T0008/pi-r1-focused/pytest-tmp` | **122 passed**（无 skip/xfail） |
| `reports/T0008/pi-r1-full` | `record_check.py pi-r1-full -- <绝对解释器> -m pytest -q tests/test_derivations.py tests/test_dependency.py tests/test_proof.py tests/test_engine.py tests/test_reference_engine.py tests/test_logic_types.py tests/test_config.py tests/test_doctor.py --basetemp reports/T0008/pi-r1-full/pytest-tmp` | **604 passed** = 122 新 + 482 原，无 skip/xfail |
| `reports/T0008/pi-r1-diff-check` | `record_check.py pi-r1-diff-check -- git diff --check` | exit 0，无空白问题 |
| `reports/T0008/pi-r1-doc-check` | `record_check.py pi-r1-doc-check -- <绝对解释器> reports/T0008/pi-r1-scripts/check_docs.py` | 本地链接/末尾换行/行尾空白 |

每 RUN 目录含 `command.json`、`run.env`（退出码与环境）、`stdout.txt`/`stderr.txt` 与前后 19 项哈希；`record_check.py` 本身哈希 `ab6ff5a2…07d1`（原样使用）。

**关键文件 sha256（本轮结束、文档定稿后）：**
- `src/kmesh/logic/derivations.py`：`32634248f401865d068b13758e133037a7a9bc3dcfa409526bc7df86a9aaf29b`
- `tests/test_derivations.py`：`694c255ad5251ac1813b07ec335787b96a14e33b020a6aaaf865ac081c338fc0`
- 冻结核对（与 T0001–T0007 接受值一致，未改）：`dependency.py` `4b01df6f…`、`test_dependency.py` `722869ef…`、`types.py` `b8468612…`、`proof.py` `008bdd36…`、`engine.py` `21c4694f…`、`reference_engine.py` `54ff628a…`、`logic/__init__.py` `649c92a6…`（记录器前后哈希一致）。

**其他事实：** 1200 条长链、64 微世界×2 求解器对照、预算精确边界、导入隔离子进程检查均在 `tests/test_derivations.py` 内并通过；无外部数据/网络/模型/GPU；总自检耗时远低于 10 分钟预算；无 `not_run` 项；未 commit/push，提交与推远端未获授权故不做。完整哈希与命令环境见 `reports/T0008/pi-r1-full/provenance.md`。

## Codex 验收记录

尚未验收产品。规划核对不等于实施验收；此区由 Codex 在收到 Pi 交付后填写 A1–A7、独立复验结果、具体返工或剩余限制及接受哈希。

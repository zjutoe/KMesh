# T0004：小世界朴素参考闭包求解器

## 任务信息

- 任务编号／修订号：T0004 / r1，2026-09-15。
- 状态：`accepted`；Codex 第 2 轮复验通过，R1 关闭，A1–A7 全部通过。独立原因守卫 7/7、完整回归 218 项通过；接受版本见第 2 轮验收记录与文件哈希。
- 所属阶段：M1 可信数据的参考求解路径；M0 仍未完成，本任务不开始正式数据生成或模型实验。
- 研究依据：[研究计划](../../KMesh_Research_Plan_v0.1.md) v0.1.1、E0 `e0_v2`，§4.1、§4.5、§13.2、§14.2、§15.1；工程约定见 [D19](../decisions.md#d19参考闭包的求解与预算约定)。
- 规划者／验收者：Codex + `gpt-6-astra`，`xhigh`。
- 执行者：Pi + `qwen3.8-coding-27b`；上轮实际别名为 `qwen3.8-coding:27b-q8_0-64k`（ollama）。记录本轮完整模型别名，不自行换模型或更改 Pi/Ollama 配置。
- 基线：`e53e2bd0ec4cf3347c5b6103ab8061d71666150b`，`master`，规划开始时工作树干净。Codex 随交接新增本文、T0004 记录器/规划证据，更新 decisions、implementation_status，并纠正 T0003 当前版本说明；这些是已知未提交交接改动。
- 前置：[T0003](T0003-logic-types.md) `accepted`，实现提交 `6a81224eead0df659a4ba0e83cc391d7307550f5`；逻辑包、types.py、test_logic_types.py 的当前/提交哈希均与 [最终验收清单](../../reports/T0003/review-r2/final-audit.json)一致。T0001/T0002 也已验收，旧测试合计 167 项通过是历史验收结果，不冒称本次重新运行。
- 必读：[AGENTS.md](../../AGENTS.md)、本文、上述研究章节、[types.py](../../src/kmesh/logic/types.py)、[旧逻辑测试](../../tests/test_logic_types.py)、[记录器](../../reports/T0004/record_check.py)。无需读取完整旧日志或其他项目。

## 目标、范围与交付物

单一目标：对一组已合法构造的 Clause，用**枚举变量绑定的朴素 forward chaining**计算全部可推出的 ground Atom，直到闭包不再增加。结果供后续主求解器核对，当前只有第一条求解路径，不能宣称标签已经双重验证。

| 允许新增／修改 | 本任务内容 |
|---|---|
| `src/kmesh/logic/reference_engine.py` | 一个公开闭包函数、一个预算异常及必要私有函数；仅标准库和已有逻辑类型 |
| `tests/test_reference_engine.py` | 手算闭包、语义不变性、输入/预算边界和导入隔离测试 |
| `README.md`、`docs/implementation_status.md` | 当前已实施/待验收状态、最小 Python 使用例与准确限制 |
| 本交接文档 | 头部状态、追加 Pi 执行记录；不改契约或填写 Codex 结论 |
| `reports/T0004/` 下全新 `pi-*` RUN 目录 | 原始命令、stdout/stderr、退出状态、哈希与简短 provenance |

Codex 提供的 `reports/T0004/record_check.py`、`.gitignore` 和 `planning-*` 材料保持原样。`docs/decisions.md` 由 Codex 维护。现有 `logic/__init__.py`、`types.py`、其他产品及全部旧测试不改；不清理上轮的非阻塞格式问题。

不实现主索引求解器、通用匹配/统一算法公共库、World/Patch/Proof/ClosureResult 类、证明或深度记录、verifier、文件解析、CLI、生成器、DAG/模板/family 审计、模型和训练。不添加依赖/安装/网络访问，不读研究数据，不自动 commit/push。计划 §13.2 的 RuleEngine/World 是后续接口展望；本任务只提供可被后续适配的纯函数，不创建空框架。

## 前提与假设

- 已验证环境：`.venv/bin/python` 为 Python 3.13.9，editable `kmesh 0.1.0` 指向本仓库 `src/kmesh/__init__.py`，pytest 8.4.2；本任务两个产品/测试目标文件尚不存在。实施前用下方命令再次保存实际起点。
- 可用接口：Atom/Clause 不可变且可哈希；Atom 有 `variables` 和 `is_ground`；所有 head 变量在该 clause 的 body 出现，事实 ground。正常构造的这些对象可直接信任，不重复检查内部词法，也不处理绕过冻结机制伪造的实例。
- 本求解器处理有限、正向、无函数的 Horn 子句，包括静态类型能表示的重复前提/规则、常量规则和循环。**这不放宽 E0 生成世界的关系 DAG 约束**；循环只是求解器终止性测试，生成器审计仍未实现。
- 仅读本仓库相关代码、任务证据与环境元数据。全部 fixture 手工合成，数据版本、采样 seed、checkpoint=N/A；不做随机世界生成，不接触锁定测试或外部数据。
- CPU 自检，单个记录器命令最多 120 秒，总自检预算 10 分钟；函数自身另有明确的候选绑定检查上限。超过上限/超时、依赖或基线不符时保存证据并反馈，不提高预算掩盖问题或无界重试。
- Pi 可从上述基线保留交接改动建立 `T0004-reference-closure` 分支。若 HEAD 仅新增本交接的提交，核对 diff 和 T0003 接受哈希、记录实际提交后继续；涉及产品/契约变化则先反馈。不得覆盖已有改动。

## 具体实施步骤

### 1. 保存起点，确认边界

先运行 preflight，核对基线与 T0003 清单，再置 `in_progress`。只新建本轮模块和测试；新模块从 `kmesh.logic.types` 导入 Atom、Clause、LogicValidationError，包 `__init__.py` 保持零导入。

中断恢复时先核对已落盘内容，分小段写实现/测试并检查；保留已完成代码，避免重新整文件生成导致已验证内容丢失。已出现的失败先用新 RUN 留存，再作局部修复。

可检查结果：实际起点有记录，未改旧产品和测试，也未提前填写实现通过。

### 2. 固定公开接口和错误边界

```python
class ReferenceLimitError(RuntimeError):
    """The reference solver cannot finish within its evaluation budget."""

def reference_closure(
    clauses: tuple[Clause, ...],
    *,
    max_rule_evaluations: int = 100_000,
) -> frozenset[Atom]: ...
```

- `clauses` 必须为 tuple，成员为 Clause；不接受 list/set/dict/generator，不转换输入。空 tuple 合法。重复 Clause 合法且保留在规则扫描中；输出按集合去重。
- `max_rule_evaluations` 必须为非 bool 的正整数；不得 int()/float() 强转。先验证容器、成员和预算，再进入任何空输入快返/推理，空世界也不能忽略非法预算。
- 非法输入抛已有 `LogicValidationError`。消息含 `reference.clauses`、`reference.clauses[i]` 或 `reference.max_rule_evaluations` 及目标原因（tuple / Clause / 非 bool 正整数）；全文不固定。类型/值错误只报字段、预期、实际类型或长度，**不要 repr 未验证对象/整个容器**。例如 `10**5000` 及 `-(10**5000)` 不得令错误报告逸出普通 ValueError。
- 超预算抛 `ReferenceLimitError`，消息含 `reference.max_rule_evaluations` 和超限原因；不得返回空集合/部分闭包、静默跳过规则或改为 warning。调用方漏参、多余参数仍由 Python 抛普通 TypeError。不新增泛型错误包装或宽泛 `except Exception`。
- 返回值只含 ground Atom，是不可变 frozenset；包含初始事实及全部推导事实，不包含规则、标签、证明、深度或模板名。不修改输入，不存跨调用/跨 clause 的绑定状态。

可检查结果：接口唯一、返回/异常可直接区分，非法输入不会被当作“无结论”。

### 3. 实现枚举绑定与同步不动点

定义并按以下次序实现，必要的替换函数保持模块私有：

1. 从**全部输入 clause 的 body 和 head 参数**收集常量集合 `D`，排序得到枚举序列。变量名和谓词不属于实体域；不只收集事实中的常量，不自动加虚拟实体，不接受额外 query/domain 参数。
2. 初始集合 `F0` 为所有空 body clause 的 head；其余 clause 按输入顺序保存为规则。为每条规则单独收集所有不同变量 `V_r`（body/head 的并集），排序；body-only 变量也必须参与绑定，重复变量只计一次。
3. 每轮固定上一轮集合 `F_t`，本轮新增内容单独收集。对每条非空规则，用 `itertools.product(D, repeat=len(V_r))` 枚举**所有**候选绑定 `theta`；同名变量只在本条规则/该绑定中使用。替换 body/head 中的变量，常量与参数方向不变。
4. 只有全部 ground body Atom 都属于 `F_t`，才将 ground head 加入下一轮集合。两个前提是逻辑合取，同一个事实可以满足重复前提；不能把两个前提当作要消耗的两份资源，也不能分别选不一致的变量绑定。不能依靠事实的集合迭代顺序传播本轮新结果。
5. `F_(t+1) = F_t ∪ {本轮推导的 heads}`；一轮无新增时返回 `frozenset(F_t)`，否则继续。不按模板写捷径，不做索引 join、谓词索引、缓存替换结果或 semi-naive 增量推理，不调用未来主求解器。

`D` 在开始时一次确定。规则可以把只在 head 出现的常量带入推导，但不会产生输入中不存在的新常量。有限谓词集合 `P` 与 `D` 的 ground atom 上限为 `|P| * |D|²`，每个非终止轮至少新增一个 Atom；因此在预算允许时能到达最小闭包。闭包有界不等于运算便宜，仍须按下面规则计预算。

**累计预算精确定义：** 每准备检查一个非空规则的候选绑定，先确认还剩预算，再扣 1；检查前提为真/假都计，重复规则分别计，最后一轮“无新增”的检查也计。跨轮累计，不按规则/轮次重置；空 body 初始事实不消耗预算。不要求公开计数，但测试必须能区分这些行为。

- 恰好用完预算且已完成无新增轮，正常返回；只有要进行第 `max_rule_evaluations + 1` 次检查时才抛异常。超限后不得返回此前已得到的 facts。
- 零变量的非空规则有且仅有一个空绑定（包括实体域为空时）；有变量但 `D` 为空时没有候选绑定。空输入与仅事实输入不消耗预算。正预算 `1` 对它们有效。
- 除“没有非空规则”外，不以当前事实为空、规则已产出过 head 等条件提前结束或跳过候选；严格按本轮候选及不动点检查，保证上述计数有一致含义。
- 该上限约束实际候选检查次数，不是秒数或完整内存上限；测试输入始终是小型人工世界。将来批量生成使用索引主版，本参考实现不承担正式规模性能目标。

**独立性：** 参考版与未来主版只共享内容类型和静态校验；推理的匹配、绑定、规则应用、不动点逻辑各自实现。不得为两条路径预建共用求解辅助库。当前手算验证通过不能替代后续随机小世界双求解器闭包一致性与独立 proof verifier。

可检查结果：参考逻辑能逐行审阅，域完整、绑定作用域局部、同步多轮推导和预算行为明确。

### 4. 分组编写有独立预期值的测试

所有新测试放在 `tests/test_reference_engine.py`；可以有仅用于构造 Atom/Clause 的短帮助函数，不用另一个闭包实现或被测私有函数生成预期答案。不规定用例数量，以下行为全部覆盖即可。

**手算主例（与计划 §4.2 同义）：**

```python
world = (
    Clause((), Atom("r1", ("a", "b"))),
    Clause((), Atom("r2", ("b", "c"))),
    Clause((Atom("r1", ("?x", "?y")), Atom("r2", ("?y", "?z"))),
           Atom("r3", ("?x", "?z"))),
    Clause((Atom("r3", ("?x", "?y")),), Atom("r4", ("?y", "?x"))),
)
expected = frozenset({
    Atom("r1", ("a", "b")), Atom("r2", ("b", "c")),
    Atom("r3", ("a", "c")), Atom("r4", ("c", "a")),
})
```

必须比较完整集合相等，不能只检查一个正 query。另将最后规则的 head 改为 `r4(?x,?y)`，完整闭包的最后一项变为 `r4(a,c)`，`r4(c,a)` 不再可推。缺少 `r2(b,c)` 时，闭包只含 `r1(a,b)`。这些只是人工逻辑检查，不生成反事实数据集或声称已完成反事实审计。

| 测试组 | 具体输入与独立预期 |
|---|---|
| 空世界/事实 | 空 tuple → 空 frozenset；重复 `p(a,b)` fact → 仅一个 `p(a,b)`；不产生 `p(b,a)` |
| COPY/INV/INTER | 用 `p(a,b)`、`q(a,b)`、`q(b,a)` 三事实和 COPY、INV、INTER 三规则，逐个写出三个派生 head 的完整集合；INTER 只接受同一对参数的交集，不能接受错误谓词/反向绑定 |
| 重复变量 | facts `p(a,a)`、`p(a,b)`；`[p(?x,?x)] -> same(?x,?x)` 只增加 `same(a,a)` |
| 常量与域 | fact `seed(a,a)`；`[seed(?x,?x)] -> tag(?x,k)`；`[tag(?x,?y)] -> out(?y,?x)`；完整闭包恰为 `seed(a,a), tag(a,k), out(k,a)`，覆盖不在 facts 中的常量 `k` |
| 不连通变量 | facts `p(a,a), q(b,b)`；`[p(?x,?x),q(?y,?y)] -> r(?x,?y)` 仅增加 `r(a,b)`；确保枚举笛卡尔绑定而不是要求前提必须共享变量 |
| ground/重复前提 | ground body → ground head 的规则有/无前提时分别触发/不触发；`[p(?x,?y),p(?x,?y)] -> twice(?x,?y)` 可由单一 `p(a,b)` 满足；body 有变量、head 为 ground 的规则也正确 |
| 无事实/循环 | 纯变量 COPY 无常量事实 → 空；仅带常量的 ground 规则无初始事实 → 空；`p↔q` 循环无种子 → 空，有 `p(a,b)` 种子 → 恰有 `p(a,b),q(a,b)`，正常终止。循环 fixture 不作合法 E0 world |
| 局部作用域 | facts `p(a,b),q(c,d)`；两条独立 COPY 都使用 `?x/?y`，分别推出 `u(a,b),v(c,d)`；先求解此世界再求解空世界，后者仍为空 |

还需三组边界检查：

1. **集合语义/输入不变：** 主例规则重排（含反向放置）、JOIN 前提交换、同一规则变量一致改名后，闭包均与手算集合相同；重复规则不改变闭包（用充足预算）。结果全部 ground、类型恰为 frozenset；调用前后输入结构/顺序未变。将完整闭包作为额外 facts 与原规则再求解，结果仍相同；不测试证明深度/顺序。
2. **输入/异常/预算：** 非 tuple 容器、非 Clause 成员、非法预算 `True/False/0/-1/1.5/"2"/None`，逐条只破坏一个条件，并断言专用异常、目标路径与原因。额外用工厂+短参数 ids 测试 `clauses=10**5000`、`clauses=(10**5000,)`、`max_rule_evaluations=-(10**5000)`，避免 pytest 生成 ID 时先格式化大整数；如测试固定整数转换上限，用 fixture 在 finally 恢复。空世界非法预算也须拒绝。

   精确预算例：`p(a,a)` fact 加 `[p(?x,?x)] -> q(?x,?x)`，上限 `2` 返回 `{p(a,a),q(a,a)}`，上限 `1` 抛 ReferenceLimitError（最终无新增轮也要检查）。该 COPY 规则重复两次后，上限 `4` 成功、`3` 超限。另用不成立的 `[q(?x,?x)] -> r(?x,?x)` 加在原单 COPY 后：上限 `6` 成功返回 `{p(a,a),q(a,a),r(a,a)}`，`5` 超限，覆盖首轮前提不成立也计数。最后用 `[p(?x,?x)] -> q(?x,k)` 替代单 COPY：实体域 `{a,k}`，上限 `4` 成功、`3` 超限，覆盖所有候选绑定（包括失败绑定）的计数。所有预期须独立手写，低预算只断言失败、不接受部分闭包；仅事实/空世界上限 `1` 成功。用足够预算重复失败后的调用，结果不受上次影响。
3. **导入隔离：** 在新 Python 子进程中，导入前通过 finder 阻止 torch/yaml（包括子模块）；导入 `reference_engine` 后执行一个事实加 COPY，核对输出并断言二者未进入 sys.modules。检查仅标准库/内容类型依赖，包本身不自动导入求解器。不修改环境或安装依赖。

先检查测试 imports/fixtures，再运行定向检查和完整回归。测试不能为凑数量复制实现，也不能只核对返回集合长度。源码异常边界与实际推导同样需要验证。

### 5. 记录、同步状态并交回

README 补可执行 Python 使用例和“参考版已实施、awaiting_review；主版交叉验证/证明/world 审计尚未实施”；更新测试命令覆盖新文件。implementation_status 与本文状态同步；旧任务保持 accepted，M0/M1 不写完成。修正 README 中“目前只实现 doctor”这类与既有配置命令不符的当前说明即可，不重写研究目标。

Pi 区追加实际工具/完整模型、基线、文件、每条命令/退出码、失败/修复目录、偏差与 not_run。full RUN 完成后追加简短 provenance；原始失败和输出保留，无法核验的自述明确标注。完成后置 `awaiting_review`，冻结相关 diff，交 Codex 复验，不自动 commit/push。

## 验证方法

工作目录 `/home/mye/src/llm/KMesh`。Codex 已提供记录器，不需要从文档提取脚本或重写驱动。它先建全新 RUN 目录，保存命令、HEAD/status、前后源码哈希、stdout/stderr（含空文件）、退出码与时点；固定 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`、`CUDA_VISIBLE_DEVICES=""`、120 秒超时。已有目录会拒绝且不执行命令。每次失败/重跑更换 RUN 和对应 basetemp，不预先创建 RUN 或向不存在的目录重定向输出。

实施前：

```bash
.venv/bin/python reports/T0004/record_check.py pi-r1-preflight -- .venv/bin/python -c 'import sys, kmesh; from importlib.metadata import version; print(sys.executable); print(sys.version); print(kmesh.__file__); print({n: version(n) for n in ("kmesh", "pytest")})'
```

期望退出 0，版本/路径匹配；新模块与新测试哈希 null 是实施起点，不是完成。核对已有三个逻辑文件哈希与 T0003 接受清单。

定向检查：

```bash
.venv/bin/python reports/T0004/record_check.py pi-r1-focused -- .venv/bin/python -m pytest -q tests/test_reference_engine.py --basetemp reports/T0004/pi-r1-focused/pytest-tmp
```

期望最终退出 0，新增测试全部通过，无 skip/xfail。失败原样保存后局部修复，下次使用 `pi-r2-focused`，同时更换 basetemp。

完整回归（定向成功后）：

```bash
.venv/bin/python reports/T0004/record_check.py pi-r1-full -- .venv/bin/python -m pytest -q tests/test_reference_engine.py tests/test_logic_types.py tests/test_config.py tests/test_doctor.py --basetemp reports/T0004/pi-r1-full/pytest-tmp
```

期望新增测试及原 167 项全通过，无 skip/xfail。超时 124、启动失败 127 或其他非零均须记录，不得写 PASS。旧测试文件保持原样，失败不能靠删除/放宽旧断言处理。

最后运行 `git diff --check`，检查新文本末尾换行/尾随空白、本地链接和无被跟踪的 pytest-tmp。哈希由记录器收集，不重复复制源码与历史报告。所有 `reports/T0001/`、`T0002/`、`T0003/` 及本任务已存在 RUN/规划证据保持不变。

## 验收标准

- [x] A1：仅新增参考求解器/异常与对应测试；接口、严格输入检查、immutable ground 返回和错误字段按契约实现。
- [x] A2：域覆盖全部输入常量，规则内变量一致且相互隔离；空/单/双前提、重复变量/前提、常量、ground 规则的完整手算闭包一致。
- [x] A3：多轮同步推导、正反方向、缺前提、空/循环世界正确；语义等价重排/改名不改变闭包，输入与跨调用状态不受污染。
- [x] A4：实际候选检查累计限额正确，包含失败绑定、重复规则和终止轮；恰好完成可返回，超限明确失败且无部分结果。巨整数错误诊断不逸出。
- [x] A5：仅使用独立枚举参考算法，不混入主版共享推理/模型输入；导入隔离和全部新增测试通过，原 167 项原样回归。
- [x] A6：范围/模型/资源限制遵守，原始命令、输出、退出码及前后源码哈希可核验；失败、修复与历史均保留。
- [x] A7：README/状态/交接准确；仅参考路径完成，未声称双求解器一致、完整数据/证明审计、M0/M1 或研究命题已验证。

Codex 按冻结 diff、测试预期值与独立关键复跑决定 accepted/needs_changes，不仅凭 Pi “测试通过”摘要。后续候选任务是独立索引求解器及小世界闭包交叉验证，另行拆分；proof verifier/数据生成仍为后续工作。

## Pi 执行记录

以下保留 Pi 各轮执行记录；后续返工在本节追加，不覆盖契约或旧失败证据。

### 轮次 r1，2026-09-15（UTC）

- 轮次、日期、实际工具／完整模型：r1，2026-09-15；Pi + `qwen3.8-coding:27b`（ollama 运行时别名 `qwen3.8-coding:27b-q8_0-64k`，`PI_REASONING_LEVEL=off`）。状态流转：`ready` → 开始实施（未单独落盘 `in_progress` 状态行，直接按本文契约执行，现置 `awaiting_review`）。
- 实际基线与改动文件：分支 `T0004-reference-closure`（自 `master@e53e2bd0ec4cf3347c5b6103ab8061d71666150b` 创建，携带基线已知的未提交交接改动，未覆盖）。新增：`src/kmesh/logic/reference_engine.py`、`tests/test_reference_engine.py`、`reports/T0004/pi-r1-{preflight,focused,full}/` 与 `reports/T0004/pi-r1-full/provenance.md`、README/implementation_status/本文状态更新。未修改任何旧产品、旧测试、`types.py`、`logic/__init__.py`、`record_check.py`、`.gitignore`、`planning-*`。
- 命令、退出状态、结果、日志与版本/hash：
  1. `git status --short`；`git rev-parse HEAD`（`e53e2bd…`）；分支创建前逐一核对 T0003 已验收哈希（reference 文件组 3 项 SHA-256 与 `reports/T0003/review-r2/final-audit.json` 一致）。
  2. `git switch -c T0004-reference-closure`：exit 0。
  3. `.venv/bin/python reports/T0004/record_check.py pi-r1-preflight -- .venv/bin/python -c 'import sys, kmesh; from importlib.metadata import version; print(sys.executable); print(sys.version); print(kmesh.__file__); print({n: version(n) for n in ("kmesh", "pytest")})'`：exit 0；Python 3.13.9、kmesh 0.1.0（editable→本仓库）、pytest 8.4.2；证据 `reports/T0004/pi-r1-preflight/`。
  4. `.venv/bin/python reports/T0004/record_check.py pi-r1-focused -- .venv/bin/python -m pytest -q tests/test_reference_engine.py --basetemp reports/T0004/pi-r1-focused/pytest-tmp`：exit 0，`51 passed`。
  5. `.venv/bin/python reports/T0004/record_check.py pi-r1-full -- .venv/bin/python -m pytest -q tests/test_reference_engine.py tests/test_logic_types.py tests/test_config.py tests/test_doctor.py --basetemp reports/T0004/pi-r1-full/pytest-tmp`：exit 0，`218 passed in 3.68s`（新增 51 + 旧 167 全部回归），无 skip/xfail。
  6. `git diff --check`：exit 0；无新增未跟踪 pytest-tmp（均位于 `reports/T0004/pi-r1-*/pytest-tmp`）。
  7. 实现/测试文件 SHA-256（记录于 `reports/T0004/pi-r1-full/record.json`）：`reference_engine.py` `54ff628a…b64327`（全文 `54ff628abeb37dbe66410d87e5522af727db62e345cfa151281c14b64327a147`）；`test_reference_engine.py` 全文 `9c2292f87855904ac1f65edd99c47a9ef6363f0765b4ce5cd80bcbc2a6269b14`。
  8. 非正式 dev 自检：`/tmp/smoke_t0004.py`（主例、COPY/INV/INTER、常量域、语义不变性、预算 a–d、错误消息无 repr、导入隔离），全部断言通过后留在 /tmp（不入仓、不作为证据）。
- not_run、偏差、失败、阻塞及最小复现：正式记录命令无 not_run 项、无非零。偏差两处：(a) 实现/测试完成后才发现 Codex 已将本文重写为新结构（契约与预算例不变），已按新版文档核对并更新状态；(b) 开发期冒烟误将“COPY 规则重复两次”构造成 3 个规则实例导致预算 case b 假超限，定位为测试脚本自身构造错误，契约预算推导（2 个实例）下 limit 4 成功/3 超限；修正后正式测试按 2 实例编写并通过，实现未因此改动。阻塞：无。
- 提交验收的 diff／产物范围与状态：未跟踪新增：`src/kmesh/logic/reference_engine.py`、`tests/test_reference_engine.py`、`docs/handoffs/T0004-reference-closure.md`（含本轮记录）、`reports/T0004/pi-r1-*` 证据目录；已修改：`README.md`、`docs/implementation_status.md`、本文。冻结待验收，diff 止于 2026-09-15 本记录时点；未 commit/push。

### 轮次 r2（R1 返工），2026-09-15（UTC）

- 轮次、日期、实际工具／完整模型：r2，2026-09-15；Pi + `qwen3.8-coding:27b`（ollama 运行时别名 `qwen3.8-coding:27b-q8_0-64k`，`PI_REASONING_LEVEL=off`）。状态流转：开始即置 `in_progress`（本文件与实现状态均先落盘），完成四步契约后回置 `awaiting_review`。
- 实际基线与改动文件：分支 `T0004-reference-closure`（自 `master@e53e2bd0ec4cf3347c5b6103ab8061d71666150b`，Codex 第 1 轮冻结清单之上继续）。改动：`tests/test_reference_engine.py`（仅预算用例 `expect` 改为完整原因字符串元组、巨整数参数表新增 `expect` 列与 `assert expect in message`）、`reports/T0004/pi-r2-{reason-guards,focused,full}/`（新证据）、`reports/T0004/pi-r2-full/provenance.md`、`README.md`/`docs/implementation_status.md`/本文状态同步。产品源码冻结未改（`reference_engine.py` SHA-256 返工前后均为 `54ff628abeb37dbe66410d87e5522af727db62e345cfa151281c14b64327a147`，与 `reports/T0004/review-r1/final-audit.json` 一致）；未改契约、预算、接口、旧测试或 Codex 检查脚本；`review-r1*` Codex 证据目录保持原样。
- 命令、退出状态、结果、日志与版本/hash：
  1. 冻结核对：`sha256sum src/kmesh/logic/reference_engine.py tests/test_reference_engine.py` 与 `reports/T0004/review-r1/final-audit.json` 冻结值逐项一致；`git branch --show-current` = `T0004-reference-closure`。
  2. 状态置 `in_progress`（本文件头部与 `docs/implementation_status.md` 同步落盘后才开始改测试）。
  3. 测试修复（仅 `tests/test_reference_engine.py`）：预算参表 `(0, ("positive",)), (-1, ("positive",)), (1.5, ("float",)), ("2", ("str",))`（bool 两行与 `None` 行原样，循环断言 `for fragment in expect: assert fragment in message` 不变）；巨整数参表改为 `("build", "field", "expect")` 三列（`tuple` / `Clause` / `positive`），工厂 lambda、短 ids、`pinned_int_str_limit` fixture（finally 恢复整数转换上限）保留；两个测试函数名与 `field` 参数名未变；测试总数保持 51。
  4. 非正式 dev 自检（不入仓）：`check_reason_guards.py` dev 运行 `7/7` exit 0；定向 51 passed。
  5. `.venv/bin/python reports/T0004/record_check.py pi-r2-reason-guards -- .venv/bin/python reports/T0004/review-r1/check_reason_guards.py`：exit 0；`SUMMARY: 7/7 diagnostic reason guards effective`；证据 `reports/T0004/pi-r2-reason-guards/`。
  6. `.venv/bin/python reports/T0004/record_check.py pi-r2-focused -- .venv/bin/python -m pytest -q tests/test_reference_engine.py --basetemp reports/T0004/pi-r2-focused/pytest-tmp`：exit 0；`51 passed in 0.11s`；证据 `reports/T0004/pi-r2-focused/`。
  7. `.venv/bin/python reports/T0004/record_check.py pi-r2-full -- .venv/bin/python -m pytest -q tests/test_reference_engine.py tests/test_logic_types.py tests/test_config.py tests/test_doctor.py --basetemp reports/T0004/pi-r2-full/pytest-tmp`：exit 0；`218 passed in 3.63s`（新增 51 + 旧 167），无 skip/xfail；证据 `reports/T0004/pi-r2-full/` 及新增 `provenance.md`（记录各记录命令 `elapsed_s` 与完整实施时段，并引用 Codex 第 1 轮证据澄清）。
  8. `git diff --check`：exit 0。
  9. 返工后 SHA-256：`tests/test_reference_engine.py` `2434c17e929a9af13281041a9f92ac97e1f03eef98fb3c31a2b3347d1e213090`；其余文件以各 `record.json` 为准。
- not_run、偏差、失败、阻塞及最小复现：无 not_run、无非零、无阻塞。偏差：无（本轮按第 5 节 R1 四步契约执行，`in_progress` 先行落盘）。
- 提交验收的 diff／产物范围与状态：本轮仅测试断言补强、三个新 RUN 与 provenance、三处状态文档同步；产品源码与全部历史 RUN/Codex 证据未动。冻结待复验，未 commit/push。

## Codex 验收记录

产品验收按轮次记录如下；规划就绪检查不等同产品验收。

### 交接就绪检查，2026-09-15

- Codex + `gpt-6-astra`，`xhigh` 完成拆分。`/root/review_data_design` 提供只读设计建议；主代理据此固定逐轮枚举、同步闭包与累计候选检查预算，没有编写产品实现或测试。
- 未参与该草案设计的 `/root/review_t0001_code` 独立只读审阅契约、D19 和记录器，确认手算闭包、`2/1`、`4/3`、`6/5` 预算例及常量域例正确，接口/独立性/文件范围/命令无阻塞。审阅记录见 [planning-review.md](../../reports/T0004/planning-review.md)；该代理未运行产品测试。
- 主代理核对 T0003 提交 blob/工作树/接受哈希一致，旧产品、测试与 T0001–T0003 历史报告无改动，见 [planning-baseline-checks.json](../../reports/T0004/planning-baseline-checks.json)。记录器环境探针成功、非零退出/两路日志原样留存、拒绝重用且旧文件哈希不变，见 [planning-recorder-checks.json](../../reports/T0004/planning-recorder-checks.json)；超时/启动失败逻辑沿用旧记录器，本轮没有重复动态测试。
- 文档链接、Python 示例/记录器语法、三条命令的 RUN/basetemp 及空白检查通过，最终文件索引见 [planning-final-check.json](../../reports/T0004/planning-final-check.json)。结论：**交接 `ready`**；A1–A7 产品验收均 `not_run`，没有研究实验结果，不自动 commit/push。

### 第 1 轮实施验收，2026-09-15

- 验收者：Codex + `gpt-6-astra`，`xhigh`；实现/测试作者为 Pi + Qwen。`/root/review_t0001_code` 作非产品作者的只读审阅，并复核根代理反例，同意仅 R1 测试返工；该代理没有运行产品测试或修改文件。
- 冻结范围：`T0004-reference-closure`，HEAD `e53e2bd0ec4cf3347c5b6103ab8061d71666150b` 加未提交改动；37 项文件哈希见 [frozen-inputs.json](../../reports/T0004/review-r1/frozen-inputs.json)，提交审阅时的产品、测试、交接与文档差异见 [reviewed-diff.patch](../../reports/T0004/review-r1/reviewed-diff.patch)。`reference_engine.py` SHA-256 为 `54ff628abeb37dbe66410d87e5522af727db62e345cfa151281c14b64327a147`；测试为 `9c2292f87855904ac1f65edd99c47a9ef6363f0765b4ce5cd80bcbc2a6269b14`。这两个哈希是审阅版本，尚不是 accepted 结论。
- 独立完整回归：原记录器 RUN `review-r1-full`，按原四文件命令运行，退出 0，**218 passed**、无 skip/xfail；见 [stdout.txt](../../reports/T0004/review-r1-full/stdout.txt)和 [record.json](../../reports/T0004/review-r1-full/record.json)。运行前后源码哈希与冻结值一致。
- 补充核验：[boundary_probe.py](../../reports/T0004/review-r1/boundary_probe.py)，RUN `review-r1-boundaries`，退出 0；无事实 ground 规则仍计预算、零变量规则、仅 body 出现的常量域、body-only 变量预算、多个 JOIN 成功绑定及不一致绑定反例 **6 组通过**。同次探针另复现四条逐字符原因断言的假通过；退出 0 表示按预期复现，不表示这些测试有效。原始结果见 [stdout.txt](../../reports/T0004/review-r1-boundaries/stdout.txt)。未实现第二个求解器或随机世界生成。
- 原因断言专门检查：[check_reason_guards.py](../../reports/T0004/review-r1/check_reason_guards.py)读取测试自身的实际参数化数据，仅在内存替换测试调用目标，传入带正确字段路径但缺少完整原因的错误消息；RUN `review-r1-reason-guards` **退出 1，0/7 个 guard 有效**，见 [stdout.txt](../../reports/T0004/review-r1-reason-guards/stdout.txt)。这是 R1 修复前失败证据，不是当前求解器报错内容错误。
- 证据审计见 [evidence-audit.json](../../reports/T0004/review-r1/evidence-audit.json)：Pi 三个规定 RUN 与独立三个 RUN 的输出哈希/退出码/前后源码哈希匹配；13 项非状态规划文件、旧产品/测试与 T0001–T0003 历史未改。当前交接仅还原头部状态与 Pi 区，即逐字恢复规划最终哈希，契约正文未变。
- 非阻塞记录澄清：①规划在 08:37:41 UTC 已 ready，Pi preflight 为 09:13:02；没有证据支持 Pi 所述“实施中 Codex 重写契约”，该句保留为其自述，不作已核验事实。②开发脚本两次预算失败、修正为两个规则实例及 `SMOKE OK/exit=0` 已从该项目 Pi 会话找回，见 [session-evidence.json](../../reports/T0004/review-r1/session-evidence.json)；这是工具合并输出，不是规范 RUN 的两路日志，下轮仍须一开始用记录器保存失败。初次写入产品源码的内容哈希与冻结值一致，支持本次脚本修正未改变最终产品的说明。③未落盘 `in_progress` 已披露，返工时先同步状态。④preflight 至 full 结束约 45 分 38 秒，三个记录命令耗时总和约 4.37 秒；provenance 的“执行 <1 分钟”只能按记录命令耗时理解，不能作完整实施耗时。⑤实际源码没有单独的“空 domain 早退”分支，空 product 无候选后按正常不动点检查返回。⑥Pi 记录中的简写源码哈希首尾拼接有误，以同条完整哈希和 record.json 为准。
- 模型来源：上述会话在本任务时段的 28 条 assistant 元数据均为 `provider=ollama`、`model=qwen3.8-coding:27b-q8_0-64k`、`api=openai-completions`；只核对日志元数据，不声称独立核验权重。
- 结论：**A1–A4/A6/A7 通过（证据留存方式的限制如上），A5 因 R1 暂不通过；状态 `needs_changes`**。求解器在已核验范围内未发现缺陷，本轮只要求测试修正。最终索引见 [final-audit.json](../../reports/T0004/review-r1/final-audit.json)。Codex 没有修改产品或测试，没有 commit/push；参考版之外的主求解器/证明/world 审计和研究命题仍未验证。

#### R1（P2）：错误原因断言逐字符匹配，遗漏完整原因仍会通过

定位：首轮 `tests/test_reference_engine.py:373–377` 的 `expect` 部分为字符串，389–390 行的 `for fragment in expect` 因而逐字符执行 `in message`。消息 `reference.max_rule_evaluations: invalid type or size` 不含完整的 `positive`、`float` 或 `str`，却能让 0、-1、1.5、"2" 四条测试全部通过。三个巨整数用例在 414–416 行仅断言异常类型与字段，也没有检查原契约要求的目标原因。7 个假通过均已由专门检查保存。

Pi 仅按以下四步返工；原接口、算法、预算与验收标准不变：

1. 核对上述冻结源码/测试哈希与原分支，保留 Codex 新增证据，先将头部/实现状态置 `in_progress`。**产品源码保持冻结不改**；允许改 `tests/test_reference_engine.py`、本任务状态/追加 Pi 记录、README/implementation_status 当前说明，以及全新 `pi-*` RUN。不修改旧测试或 Codex 检查脚本。
2. 把预算测试的每个 `expect` 都写成字符串元组（例如 `("positive",)`、`("float",)`、`("str",)`），按完整片段检查，保留现有 bool/路径/异常断言。巨整数参数表补目标原因：非 tuple 输入为 `tuple`、非法成员为 `Clause`、负预算为 `positive`；保留工厂、短 ids 和整数转换上限的 finally 恢复。保持这两个测试函数名和 `field` 参数名，检查脚本从真实参数化数据读取新增原因参数。无需增加冗余测试数量，也不删除或放宽旧断言。
3. 上面的 `review-r1-reason-guards` 已保留修复前失败，不必重复同一失败。修复后依次用以下全新 RUN 验证；检查脚本预期 **7/7 有效、退出 0**，定向/完整回归全部通过、无 skip/xfail。再失败须保留输出，更换 RUN 与 basetemp 后重试，不覆盖旧目录。

   ```bash
   .venv/bin/python reports/T0004/record_check.py pi-r2-reason-guards -- .venv/bin/python reports/T0004/review-r1/check_reason_guards.py
   .venv/bin/python reports/T0004/record_check.py pi-r2-focused -- .venv/bin/python -m pytest -q tests/test_reference_engine.py --basetemp reports/T0004/pi-r2-focused/pytest-tmp
   .venv/bin/python reports/T0004/record_check.py pi-r2-full -- .venv/bin/python -m pytest -q tests/test_reference_engine.py tests/test_logic_types.py tests/test_config.py tests/test_doctor.py --basetemp reports/T0004/pi-r2-full/pytest-tmp
   ```

4. 在新 full 目录追加 provenance，分别记录检查命令耗时与完整实施时段；引用第 1 轮 Codex 的证据澄清，不改旧 provenance/Pi 自述/历史 RUN。同步 README/状态与本文 `awaiting_review`，追加第 2 轮 Pi 记录后交回复验，未 commit/push。


### 第 2 轮实施验收，2026-09-15

- 验收者：Codex + `gpt-6-astra`，`xhigh`；Pi 为测试修正作者。原非产品作者审阅者 `/root/review_t0001_code` 只读复核两处参数表及完整原因断言，同意关闭 R1；未由其重复跑测试。
- 接受版本：`T0004-reference-closure`，基线 `e53e2bd0ec4cf3347c5b6103ab8061d71666150b` 加本轮工作树；`reference_engine.py` SHA-256 为 `54ff628abeb37dbe66410d87e5522af727db62e345cfa151281c14b64327a147`（产品未改），`test_reference_engine.py` 为 `2434c17e929a9af13281041a9f92ac97e1f03eef98fb3c31a2b3347d1e213090`。基线本身不包含 T0004，实现提交须以这两个 blob 哈希关联。
- 差异核验：从首轮新文件 patch 恢复测试全文，哈希匹配首轮冻结值，再与本轮比较；仅预算参数的五个字符串变为元组，以及巨整数三行新增目标原因及断言。工厂、短 ids、fixture 恢复、原字段断言和其他测试未变，详见 [reviewed-test-diff.patch](../../reports/T0004/review-r2/reviewed-test-diff.patch)与 [frozen-inputs.json](../../reports/T0004/review-r2/frozen-inputs.json)。Pi 记录“None 行原样”有一处笔误，实际也正确改成 `("NoneType",)`，不影响验收。
- 独立复跑：原封不动使用首轮 `check_reason_guards.py`，新 RUN `review-r2-reason-guards` 退出 0，**7/7 有效**，见 [stdout.txt](../../reports/T0004/review-r2-reason-guards/stdout.txt)。新 RUN `review-r2-full` 按原四文件命令运行，退出 0，**218 passed**、无 skip/xfail，见 [stdout.txt](../../reports/T0004/review-r2-full/stdout.txt)。源码未改，首轮六组求解器边界结论沿用，没有重复无关探针。
- Pi 三个 r2 RUN 的退出码、两路输出哈希与前后源码哈希均匹配，旧规划/Pi/Codex 历史保持不变，证据索引见 [final-audit.json](../../reports/T0004/review-r2/final-audit.json)。新 provenance 分开记录命令耗时与实施窗口，并保留第 1 轮证据限制；其窗口起点采用验收记录时刻，是近似时段，不作为实际模型运行计时。
- 结论：**R1 关闭，A1–A7 全部通过，T0004 `accepted`**。Codex 只维护验收文档/证据，没有修改产品/测试。用户本轮已授权通过后提交、合并并推送；具体提交关联与下游任务将在后续交接中记录。主索引求解器、双求解器随机世界一致性、proof/world 审计及研究命题仍未验证。

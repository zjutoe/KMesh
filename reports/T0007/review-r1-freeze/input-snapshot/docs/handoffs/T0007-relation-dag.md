# T0007：关系依赖无环检查

## 任务信息

- 任务编号／修订号：T0007 / r1，2026-09-17。
- 状态：`awaiting_review`（2026-09-17，Pi + Qwen 第 1 轮实施完成；基线 `master@74a96f3`）。
- 所属阶段与协议：M1 / E0-D；研究计划 v0.1.2、E0 `e0_v2` §4.1、§4.4、§5.2。落实已有“关系依赖无环”约束，不改变研究协议。
- 规划者／验收者：Codex + `gpt-6-astra`，`xhigh`。
- 执行者：Pi + `qwen3.8-coding-27b`；沿用实际完整模型别名 `qwen3.8-coding:27b-q8_0-64k`（ollama），记录实际值，不自行换模型／配置。
- 基线：`master@74a96f3735831d16a14dedffbaa6e0654f8b7658`；规划起点工作树干净。本地 `origin/master` 同指此提交，未另行 fetch。T0006 实现提交为 `df0ee6732ede7b484bd2cf729143fae7c4e79c1c`，已合并至本基线。
- 前置：[T0003](T0003-logic-types.md) 的 Atom/Clause 已验收；[T0006](T0006-proof-verifier.md) 已验收，使后续生成的证明可独立核验。本函数只依赖 T0003 内容类型，不调用证明验证器或两条求解器。原有回归共 438 项。
- 已有交接改动：Codex 新增本文、`reports/T0007/` 记录器和规划证据，追加 D25／T0006 后续关联，更新实现状态。保留这些改动；本任务产品和测试尚不存在。
- 必读：[AGENTS.md](../../AGENTS.md)、[研究计划 §4–5](../../KMesh_Research_Plan_v0.1.md)、[D18／D25](../decisions.md)、[types.py](../../src/kmesh/logic/types.py)、本文及 [record_check.py](../../reports/T0007/record_check.py)。

## 目标、范围与交付物

**单一目标：检查输入 clauses 的“前提关系 → 结论关系”依赖是否无环；无环时返回确定的关系拓扑顺序，有环时明确拒绝。** 它是后续有限证明枚举的输入检查，不证明世界已通过全部 E0 审计。

| 允许新增／修改 | 交付内容 |
|---|---|
| `src/kmesh/logic/dependency.py` | 一个公开函数 `relation_topological_order`，必要时少量私有帮助函数 |
| `tests/test_dependency.py` | 手算顺序／循环反例、输入边界、不变性及导入隔离 |
| `README.md`、`docs/implementation_status.md` | 最小使用说明、测试命令、实际状态与限制 |
| 本交接文档 | 头部状态及追加 Pi 执行记录；不改契约／Codex 验收结论 |
| `reports/T0007/` 下新的 `pi-*` RUN | 原始命令／两路输出／退出码／哈希，full RUN 的 provenance；需要额外检查脚本时放在新 `pi-*-scripts/` 目录 |

记录器和 `.gitignore` 原样使用；不改旧产品／测试、`logic/__init__.py`、AGENTS、研究计划、decisions、旧交接或历史报告。不新增依赖。

不实现证明生成／枚举、最短深度、唯一性、motif、world 生成器／综合审计、JSON／CLI、模型或训练。不构建计划 §6 的 patch 相似图，不做图指导更新；本任务的关系依赖图与模型读取图是不同对象。不新增 World/Graph 包装类。

## 前提与假设

- 已验证基础：T0003 合法对象不可变、二元、0–2 前提、head 变量受 body 约束；T0004–T0006 的求解／验证允许有限循环实例，**不改这些旧接口的接受范围**。仅未来 E0 数据入口使用本函数施加无环约束。
- 输入只假定是正常构造的 Atom/Clause，不处理绕过构造器或 frozen 的伪造实例。DAG 检查不重复词法校验，不新增模板／实体域／数量约束。
- 环境沿用 `.venv/bin/python`、Python 3.13.9、editable kmesh 0.1.0、pytest 8.4.2。只读仓库相关代码／文档和环境元数据；测试全为手工合成，无外部数据、锁定研究测试或 checkpoint。
- 无网络、GPU、安装需求。单检查 CPU 120 秒、总自检 10 分钟；超时／基线不符保存证据并反馈，不扩大预算或跳过用例。
- 纯图扫描不进行推理、搜索或实体笛卡尔积；复杂度应为 O(C + B + (V + E) log V) 或更好（C 子句数，B 前提出现数，V 不同关系数，E 去重依赖边数）。不添加可配置搜索预算或世界大小上限。
- 核对后可保留交接改动建立分支 `T0007-relation-dag`。若 HEAD 只新增此次交接文档提交，核对产品和契约相同后记录实际基线继续；其他相关变化先反馈，不回退他人工作。

## 具体实施步骤

### 1. 核对起点，先落盘状态

运行下方 preflight。记录器的 before 中新模块／测试应为 null；旧产品／测试哈希应与 [planning-baseline.json](../../reports/T0007/planning-baseline.json) 一致。将本文和实现状态置 `in_progress` 后开始编码。

本轮只创建上表两个代码文件；分小段写入。中断后先读落盘内容，继续最小修改，不重新生成整个已完成文件。可检查结果：基线、实际工具／完整模型、起点与状态有记录。

### 2. 实现明确的入口和返回契约

```python
def relation_topological_order(clauses: tuple[Clause, ...]) -> tuple[str, ...]: ...
```

- `clauses` 必须是 tuple（沿用 `isinstance` 约定），每个成员必须是 Clause；先检查全部成员类型，再建图／判环。不转换 list/generator，不遍历非法外层对象的内容。空 tuple 合法，返回恰为 `()`。
- 使用现有 `LogicValidationError`，不另建异常类。外层错误消息含 `dependency.clauses` 与完整原因 `must be a tuple of Clause`；成员错误含 `dependency.clauses[i]` 与 `must be a Clause`；有环消息含 `dependency.clauses` 与 `cyclic predicate dependency`。类型诊断仅附 `type(value).__name__`，不得 repr 未验证对象或容器。漏参／额外参数仍为普通 Python TypeError。
- 参数错误必须先于图错误。例如有效自环 clause 后跟非法成员，应报该成员路径，不能先报循环。
- 成功时返回恰为 tuple，包含全部出现过的谓词名，每个恰好一次。输入对象／顺序不变；无模块级可变状态、随机性、文件 I/O 或缓存。
- 失败抛异常，不返回 False、None、空 tuple 或已处理部分顺序。不宽泛捕获异常，不静默丢弃规则。

可检查结果：空图、合法 DAG、输入错误和循环明确区分，超大整数非法输入不会因格式化逸出 ValueError。

### 3. 构建关系依赖并迭代排序

**图定义不可自行更改：**

1. 顶点是全部 clause 的 head/body `Atom.pred` 去重集合。事实的 head 也是顶点；只出现在 body 的关系也必须保留。
2. 对每个非空 body 中的每个原子加入有向边 `body_atom.pred -> clause.head.pred`。不分析实体、参数方向、变量是否能统一或事实是否可达；不从闭包、query 或 ProofStep 建图。
3. 边按谓词对去重。重复事实、重复 clause、同谓词的两个前提、不同规则产生的同一边都允许，不增加该边的入度。**重复数据检查留给以后，本函数不替代它。**
4. 自环即循环；两点／多点环、断开的循环分量、无事实的循环、当前 ground 条件不能触发的循环全部拒绝。即使闭包为空也不能放行。
5. 用迭代 Kahn 算法：计算去重边的入度；零入度顶点放入最小堆；每次取当前零入度集合中字典序最小的谓词，删去其出边，新的零入度节点立即入堆。比较按 Python 字符串自然顺序，保留大小写。
6. 输出数量不等于顶点数时抛上述循环错误。无需返回具体环、残余节点或路径；不要把 Kahn 残余节点都称为“环上的节点”。禁止递归 DFS，以免长链触发 Python 递归上限。

排序只是确定性约定，不是逻辑深度或研究层级。重命名会改变独立节点之间的字典序，不要求任意改名后输出顺序逐位对应。关系拓扑顺序／rank 只能留在离线审计，不能成为模型 token、embedding、读取路由或额外特征。

依赖仅限标准库和 `kmesh.logic.types`；不导入／调用 engine、reference_engine、proof、torch、yaml。`logic/__init__.py` 保持原来的零导入。

### 4. 用能区分错误实现的 fixture 验证

所有原子均为二元；下表 `x/y/z` 实际对象中写为 `?x/?y/?z`，`a/b/c` 是常量。预期手算，不通过被测帮助函数或求解器生成。

| 场景 | clauses 要点 | 完整预期顺序 |
|---|---|---|
| 空输入 | 无 | `()` |
| 仅事实，含重复 | `z(a,b)`、`p(a,b)`、重复 p | `("p", "z")` |
| 没有事实，body-only 节点 | `p(x,y) -> q(x,y)` | `("p", "q")` |
| 计划主例 | r1/r2 facts；JOIN 到 r3；INV 到 r4 | `("r1", "r2", "r3", "r4")` |
| 依赖方向优先于名称 | ground `z(a,b) -> a(c,c)` | `("z", "a")` |
| 新就绪节点立即参与选最小 | a/z facts；`a(x,y) -> b(x,y)` | `("a", "b", "z")`，不能为 FIFO 的 a/z/b |
| 两前提都要建边 | `z(x,y), p(y,z) -> a(x,z)` | `("p", "z", "a")`；实际变量写 `?z`，谓词 z 与变量不同 |
| 相同谓词边只计一次 | `p(x,y),p(y,z) -> q(x,z)`，规则重复一次，再有 `p(x,y)->q(x,y)` | `("p", "q")` |
| 大小写保持 | A/a/z 三个事实 | `("A", "a", "z")` |

其他必须覆盖的用例（无需凑固定测试数量）：

- **循环：** 单规则 `p(x,y)->p(x,y)`；无事实 p→q→p；三点 p→q→r→p；无环 a→b 与断开 q↔r 共存；环带下游 q→z。每例独立构造，断言 LogicValidationError＋字段路径＋完整循环原因，不能仅断言“抛了某个错误”。
- **只看第二前提才发现的自环：** `p(x,y),q(x,y)->q(x,y)`，若忽略第二前提会错误接受。相应无环对照把 head 改 r 后应返回 `("p", "q", "r")`。
- **不能用可达性替代 DAG：** ground 规则 `p(a,a)->q(b,b)`、`q(c,c)->p(d,d)`，不含事实；即使它们无法启动推导也必须拒绝。不运行闭包来设定预期。
- **变换和纯度：** 同一 DAG 重排 clauses、交换双前提顺序、重复规则／事实，输出相同；输入前后相等且顺序保留。先调用循环失败，再调用合法输入，结果不受污染。实体／变量一致改名不改变输出；谓词双射改名只检查手算的新顺序及原有边约束，不错误要求原序列逐位映射。
- **长链：** 手工构造 `p0000 -> p0001 -> ... -> p1199`（1199 条 COPY，每个 Atom 的 args 均为 `("?x", "?y")`），无事实。预期恰为 `tuple(f"p{i:04d}" for i in range(1200))`。不改递归上限、不设置耗时断言；本例只检查迭代实现和完整节点覆盖，不作性能结论。
- **输入边界：** list/dict/set/generator、None、int 外层；tuple 中非 Clause（Atom、None、list、bool、int）。每例仅违反目标规则，断言目标字段＋完整原因；generator 不应被消耗。有效循环 clause 后加非法成员需优先报成员路径。正常漏参／额外关键字断言 TypeError。
- **巨整数诊断：** 固定转换上限 4300 的局部 fixture，finally 恢复；`10**5000` 分别作为外层输入与 tuple 成员，必须报 LogicValidationError 和目标路径／完整类型原因。工厂与短 ids 避免 pytest 在收集阶段格式化整数。不需要为所有普通类型再各造一份巨整数组合。
- **新子进程隔离：** 导入新模块前用 finder 阻断 torch、yaml、`kmesh.logic.engine`、`kmesh.logic.reference_engine`、`kmesh.logic.proof`，根名精确匹配或以“根名＋点”开头。先对五个根各做一次直接 import 的 ImportError 自检，再导入 dependency，实际验证空输入和 a→b／孤立 z 的顺序；扫描全部 sys.modules 名称确认禁入根及子模块均未加载。隔离集中在新进程，不增加污染全量测试的 autouse fixture。

可检查结果：边方向、第二前提、去重入度、动态就绪顺序和全图循环都有能识别对应错误实现的用例；不靠一个无关错误提前返回“通过”。

### 5. 保存证据并交回

从首次开发检查起使用原记录器，包括临时探针、README 例、文档／链接检查；不先在 `/tmp` 裸跑再只归档成功结果。失败先保存，再最小修复并换新 RUN，成功 RUN 也不覆盖。

README 增加一个短 Python 使用例与本任务状态，测试命令补新文件；明确 DAG 不等于完整 world 审计，且不是模型读取图。full RUN 新增 `provenance.md`：实际工具／完整模型、基线、RUN 命令／退出码／路径、耗时与实施时段分列、偏差与 not_run。由 record.json 引用时间，避免为了回填本轮检查时间而反复检查同一批文件。

检查 `git diff --check`、新文本换行／尾随空白、新 provenance 和文档的本地链接、pytest-tmp 未跟踪。检查报告中固定哈希只指向不可变源码／测试；不要对自身或仍在回填的文档作循环冻结。最后一次文档编辑完成后只需一个新的卫生活动 RUN。

本文 Pi 区追加实际执行记录；将本文、README 对应状态与实现状态置 `awaiting_review`，冻结相关 diff，交 Codex 按 A1–A7 验收。不自动 commit/push，不启动后续任务。

## 验证方法

工作目录 `/home/mye/src/llm/KMesh`。记录器先创建独占 RUN，固定插件隔离／CUDA 隐藏和 120 秒上限，记录 HEAD/status、17 项源码／测试／记录器前后哈希、argv、两路输出、退出码。RUN 不预建，不向尚不存在的目录重定向。

按步骤分别运行（preflight 在任何实施前；focused 通过后才 full）：

```bash
.venv/bin/python reports/T0007/record_check.py pi-r1-preflight -- .venv/bin/python -c 'import sys, kmesh; from importlib.metadata import version; print(sys.executable); print(sys.version); print(kmesh.__file__); print({n: version(n) for n in ("kmesh", "pytest")})'
.venv/bin/python reports/T0007/record_check.py pi-r1-focused -- .venv/bin/python -m pytest -q tests/test_dependency.py --basetemp reports/T0007/pi-r1-focused/pytest-tmp
.venv/bin/python reports/T0007/record_check.py pi-r1-full -- .venv/bin/python -m pytest -q tests/test_dependency.py tests/test_proof.py tests/test_engine.py tests/test_reference_engine.py tests/test_logic_types.py tests/test_config.py tests/test_doctor.py --basetemp reports/T0007/pi-r1-full/pytest-tmp
.venv/bin/python reports/T0007/record_check.py pi-r1-diff-check -- git diff --check
```

其他检查同样走记录器，例如 `pi-r1-doc-check -- .venv/bin/python reports/T0007/pi-r1-scripts/check_docs.py`。无须另写包含固定测试哈希／精确 git status 行数的庞大检查框架；直接核对授权路径、旧源码哈希及新链接即可。

失败换未用编号（如 `pi-r2-focused`）并同步 basetemp，原始失败目录保留。最终新增测试与旧 438 项均通过、无 skip/xfail；timeout=124、launch error=127 或任意非零均不是 PASS。不得调用旧任务的记录器／会固定旧测试哈希的历史检查脚本。

## 验收标准

- [ ] A1：API、tuple／Clause 输入检查及优先级、诊断、大整数、空图与返回类型符合契约；只改授权范围。
- [ ] A2：全部 head/body 谓词入图，边方向正确、两前提均参与，重复边不重复计入度，不依赖可达性或闭包。
- [ ] A3：自环、各种循环及断开分量全部拒绝；失败不返回部分顺序，不把通过 DAG 当完整 world 合法。
- [ ] A4：按每一步当前就绪集的字典序稳定选择；重排／重复不变，1200 节点链通过，无递归／全局状态或输入修改。
- [ ] A5：手算正反例有区分力；错误断言检查完整原因；旧 438 项回归通过、无 skip/xfail，不改弱旧测试。
- [ ] A6：仅标准库／内容类型依赖，子进程隔离有效；拓扑顺序只用于离线审计，无新模型特征、求解调用、数据或训练。
- [ ] A7：基线、实际模型、原始命令／输出／退出码／哈希和所有尝试记录准确，新 RUN 独占，历史不覆盖；文档与状态符合实际。

## Pi 执行记录

每轮追加：日期／实际工具与完整模型、基线／文件、RUN 命令／退出状态／证据路径、检查耗时／实施时段、失败／偏差／not_run、提交验收范围。不要填写 Codex 验收结论。

### R1，2026-09-17（UTC）

- 执行：pi harness + `qwen3.8-max-preview`（实际 `qwen3.8-coding:27b-q8_0-64k`，ollama）；分支 `T0007-relation-dag`（自 `master@74a96f3` 创建）；基线与交接声明一致（工作树仅含 Codex 计划改动）。
- 变更文件（仅两处，均在授权范围内）：
  - 新增 `src/kmesh/logic/dependency.py`（sha256 `4b01df6f08e243c649f0459a23e6e8a68f946fc0eec41814f889e65cd972ca3f`）：单一公开函数 `relation_topological_order`，Kahn + 最小堆字典序选择，仅 import 标准库 `heapq` 与内容类型 `Clause, LogicValidationError`；三条错误消息固定为契约格式；无递归、无全局状态、无缓存、无文件/网络访问。
  - 新增 `tests/test_dependency.py`（sha256 `a4e428e9d1acc99a7dc3e01e725e7b3da8d009c8f1c39eeac957b8dd57d7e09c`）：**44 项**——手算顺序表 9 例（含“新就绪即参与”反 FIFO、大小写 `A<a<z`、重边去重）、循环 8 例（自环、两环、三环、断开分量、环带下游、第二前提自环、ground 规则循环、以及第二前提换 head 的非环对照）、变换/纯度 7 例（重排/前提互换/重复/输入不变/失败不污染/实体变量改名/谓词双射改名+1200 节点链）、输入边界 15 例（外层 6 类型、生成器不消费、成员 5 类型、成员错误优先于循环、缺失参数/意外关键字 TypeError）、大整数 2 例（4300 限制下 outer/member，消息只含类型名）、隔离 2 例（干净子进程 5 个禁用根守卫自检+契约运行+`sys.modules` 泄漏扫描；`logic/__init__.py` 零导入）。
  - `README.md`：T0006 段后新增 T0007（D25）说明与最小使用例，测试命令列表加入 `tests/test_dependency.py`。
- RUN（均在 `reports/T0007/`，详细时间/哈希/环境见 [pi-r1-full/provenance.md](../../reports/T0007/pi-r1-full/provenance.md)）：
  - `pi-r1-preflight`：exit 0；新两文件 before 为 null，已追踪 14 项与规划基线一致。
  - `pi-r1-focused`：`pytest tests/test_dependency.py -q`，exit 0，**44 passed**（0.356s）。
  - `pi-r1-full-dev1`：exit **1**；482 项全部通过，doctor 失败原因是命令误写 `python -m kmesh doctor`（包内无 `__main__.py`，正确入口为 `python -m kmesh.cli doctor`）。按“失败先留存”改名保留，未覆盖。
  - `pi-r1-full`：`pytest tests -q && python -m kmesh.cli doctor --out reports/T0007/pi-r1-full-doctor.json`，exit 0，**482 passed**（基线 438 + 新增 44，无 skip/xfail）；doctor 本次进程内读数 `cpu_only`（随后同命令连跑 3 次均 `status=ok`，差异为共享 GPU 探测瞬时抖动，非产品变化）。
  - `pi-r1-diff-check`：`git diff --check`，exit 0。
  - `pi-r1-diff-check-r2`：文档（README／status／本记录/provenance）编辑完成后补录，`bash -c "git diff --check && pytest tests/test_dependency.py -q"`，exit 0（2026-09-17 05:10:09.152551→05:10:09.516065 UTC，44 passed）；本行时间在本 RUN 之后补写，handoff 不在记录器文件集内，不改变该 RUN 的被检结果。
- 偏差：除上述 doctor 入口误写外无契约偏差；实施阶段一次通过，无产品级失败；not_run 项：Codex 验收项 A1–A7 由 Codex 复核。

## Codex 验收记录

产品 A1–A7 全部 `not_run`。交接就绪核查与后续产品验收分别记录；本轮不代写产品或产品测试。

### 交接就绪核查，2026-09-17

- Codex + `gpt-6-astra`（xhigh）规划；非作者 `/root/review_t0001_code` 独立只读审阅无阻塞，见 [planning-review.md](../../reports/T0007/planning-review.md)。函数粒度、输入优先级、手算用例及研究边界均明确，可交 Pi 实施。
- [规划基线](../../reports/T0007/planning-baseline.json)记录起点干净与 `master@74a96f3`；T0006 实现提交、合并基线及工作树的 proof 产品／测试均与接受哈希一致。除三份授权文档外，827 个已跟踪文件未变；没有创建本任务产品／测试。
- [preflight](../../reports/T0007/planning-preflight/)退出 0，确认 Python 3.13.9、editable kmesh 0.1.0、pytest 8.4.2；17 项前后快照一致，新文件为 null。记录器只沿用旧行为并替换任务前缀、增加两项哈希目标，`.gitignore` 沿用。
- [契约检查](../../reports/T0007/planning-checks/checks.json)通过：四条命令／RUN／basetemp 配对、Python 接口代码块语法、本地链接和空白正确；通过小图顶点排列穷举独立核对表内九个顺序与七个循环例。它只验证交接给出的预期，不是实现或产品测试结果。
- 最终文档／状态与冻结记录见 [planning-final-check](../../reports/T0007/planning-final-check/)。结论：交接 `ready`；产品 A1–A7 仍全部 `not_run`，未启动 Pi、未编写 dependency 实现／产品测试、未 commit/push。

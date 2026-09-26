# T0015：抽取一棵证明中的完整有根子树

## 任务信息

- 任务编号／修订号：T0015 / r2（2026-09-25：明确合法 ProofStep 子类输出采用公共三字段；其余接口／研究语义不变，追加第1轮验收与最小返工）。
- 状态：`awaiting_review`（Pi R2 返工完成，待 Codex 第2轮复验）
- 阶段／版本：M1审计基础；研究计划v0.1.3、E0 `e0_v2`、E1 `e1_v3`；`proof_identity_v1`、`proof_motif_v1`不变，落实D33。
- 规划／验收：Codex + `gpt-6-astra`，xhigh。
- 实施／自检：Pi + 用户最近授权的 `bonsai2-27b`。若当前配置不一致，开工前反馈；不根据旧provenance猜测模型。记录实际alias/provider/reasoning及来源，无原件的来源标自述。
- 基线：`f5ef96f7d6d261beb2dba6fc8c47300f24c9ff41`，开始规划时工作树干净，当前分支`T0014-proof-motif`；T0014已验收并提交。前置源文件hash在本任务规划记录核对。规划文档与`reports/T0015/`是需保留的未提交改动。
- 实施分支：从该基线建立`T0015-proof-subtree`，保留Codex规划改动；仅含本次规划的后续提交可作为开工HEAD，仍须通过冻结／范围检查。不自动commit/push。
- 前置：T0003逻辑类型、T0006 ProofStep/verifier、T0012单棵出现树键已验收；T0014给后续方向提供已验收motif键，但不是本函数依赖。
- 必读：[AGENTS](../../AGENTS.md)、研究计划§5.2、[proof_identity_v1 §3](../proof_identity_v1.md)、`src/kmesh/logic/proof.py`、`src/kmesh/logic/proof_key.py`及本文。无需重读全部历史返工。

## 目标、范围与交付物

单一目标：选中输入证明的某一步，抽出该结论和它实际依赖的**全部**支持步骤，重新编号前提引用，返回仍能被独立verifier验证的完整子证明。

新增`src/kmesh/logic/proof_subtree.py`和`tests/test_proof_subtree.py`；仅允许修改README本任务段、`docs/implementation_status.md`本任务行／能力行、本文件状态／执行记录，新增`reports/T0015/pi-*`。产品依赖、已有测试、规划件、记录器和driver/checker、旧任务及本任务已有RUN均冻结。

不实现motif枚举／匹配、任意裁剪或边界变量语义、证明搜索、world准入、split manifest、CLI、训练或GPU。不接入模型输入。完整子树只是后续泄漏审计的一个原语，不能单凭它声称训练中没有保留结构。

## 前提与假设

- 已验证：T0014接受hash与提交一致；T0003/T0006/T0012源文件与前次接受记录一致。Python、pytest、editable路径以 [规划基线](../../reports/T0015/planning-baseline.json)为准，不重建环境、不安装依赖。
- 已验证的手算主例见 [规划fixture检查](../../reports/T0015/planning-examples/result.json)；这些只验证旧T0006/T0012接受输入与预期子证明，**不是新函数已通过**。
- 待验证：新函数正确收集每个发生、保持顺序并重映射索引；这由本任务测试和Codex复验决定，不预写通过。
- 数据仅为手造小fixture及1201步链；不访问正式数据／锁定测试。CPU单RUN最多120秒；超时保留原件并反馈，不放宽预算或删断言。
- 张量形状、seed、训练资源：N/A，本任务无随机生成或神经计算。

## 具体实施步骤

### 1. 开工核对并先留preflight

核对分支／基线和已有规划改动，创建实施分支。本文件和实现状态T0015先置`in_progress`，**编码前**运行下方preflight。新产品／新测试应不存在。失败先反馈，不删除文件或回切源码伪造时序。

### 2. 实现一个接口

```python
def extract_proof_subtree(
    clauses, query, proof, root_step, *, max_steps=10_000
) -> tuple[ProofStep, ...]: ...

__all__ = ["extract_proof_subtree"]
```

按顺序执行：

1. 首业务操作恰一次调用本模块导入的`canonical_proof_key(clauses, query, proof, max_steps=max_steps)`，三对象／预算原样透传，不预扫描／复制／消费输入。其结果仅用于确认**整个输入**是合法出现树，键不作为返回值；所有底层异常原实例传播。不能在root为叶子时跳过完整检查。允许T0012接受的有限循环证明，不追加DAG限制。
2. 成功后检查`type(root_step) is int and root_step >= 0`。否则抛`LogicValidationError`，全文为`proof_subtree.root_step must be a non-bool non-negative integer, got TYPE`，TYPE仅为实际类型名。
3. 若`root_step >= len(proof)`，抛`LogicValidationError("proof_subtree.root_step must be less than the proof length")`。不回显该值，不引入新异常。缺参／多余位置／未知keyword保留Python TypeError。
4. 用显式栈沿选中步骤的`premise_steps`向其支持步骤遍历，以**原步骤位置**收集成员。一个发生一条输出；相等ProofStep甚至同一个对象在两个位置的两次发生不能合并。只收集被选根实际引用的分支，不枚举替代证明。
5. 按原`proof`顺序做一次线性过滤，构造旧位置→新位置映射；不能用DFS遍历次序输出，也不需要`sorted(selected)`。各输出ProofStep保留原`clause_index`、ground结论、前提槽位顺序，只把每个ref改为对应新位置。返回真实tuple。可复用不可变对象，不要求新对象或`is`身份。

输出最后一步结论为`proof[root_step].conclusion`；验证输出时query用该结论，clauses仍用原world。选中最后一步时结果结构等于原proof；选事实得到单步骤。输出无需是T0009固定后序，继承输入的合法拓扑存储顺序。

max_steps始终约束完整输入长度，而不是输出长度。无新增预算，额外抽取过程O(n)时间／空间，n为输入步骤数；复杂度不含T0012自身成本。首调用计算了完整key，这是明确的复用成本，不声称只处理局部步骤。

允许标准库、`kmesh.logic.types`、`kmesh.logic.proof`的ProofStep及`kmesh.logic.proof_key`。产品不调用verify_proof，不导入motif、求解器／枚举器、torch或yaml，不IO／递归／缓存，`logic/__init__.py`不改。

### 3. 集中测试：主例与固定边界

主例按原存储顺序定义（`a`是Atom的简写，不是实体变量）：

```python
def a(pred, x, y):
    return Atom(pred, (x, y))

world = (
    Clause((a("u", "?x", "?y"), a("v", "?y", "?z")), a("w", "?x", "?z")),
    Clause((), a("q", "b", "c")),
    Clause((a("p", "?x", "?y"),), a("u", "?x", "?y")),
    Clause((), a("p", "a", "b")),
    Clause((a("q", "?x", "?y"),), a("v", "?x", "?y")),
)
query = a("w", "a", "c")
proof = (
    ProofStep(3, (), a("p", "a", "b")),
    ProofStep(1, (), a("q", "b", "c")),
    ProofStep(2, (0,), a("u", "a", "b")),
    ProofStep(4, (1,), a("v", "b", "c")),
    ProofStep(0, (2, 3), query),
)
```

**A. 完整输出锚点与发生语义。** 每例先断言原proof经T0006为True，输出逐项完整相等并经T0006验证；expected不能调用目标函数生成。

| 场景 | 完整预期／要求 |
|---|---|
| 主例root=0/1 | 分别单个原事实，保留ci=3/1，refs=() |
| 主例root=2 | 原步骤0、2，ci=(3,2)，refs=((),(0,))，结论p(a,b)、u(a,b) |
| 主例root=3 | 原步骤1、3，ci=(1,4)，refs=((),(0,))；旧ref=1必须变为0 |
| 主例root=4 | 完整等于原proof；保持两分支交错顺序，不能重排为DFS后序 |
| 内部JOIN | 在主例world末尾加COPY w(x,y)→z(x,y)，proof末尾加ci=5/refs=(4,)/z(a,c)，query=z(a,c)；选root=4仍完整返回原五步交错proof，防止仅末根特殊处理 |
| 重复发生 | world为p(a,b)事实及p(x,y),p(x,y)→q(x,y)；`s=ProofStep(0,(),p(a,b))`，proof=(s,s,ProofStep(1,(0,1),q(a,b)))。选root=2保留三步／refs(0,1)，root=0/1各为一条。不是按值或id去重 |
| 有限循环 | p事实、p→q、q→p的合法三步证明，选中间root=1得到前两步；不新增世界无环拒绝 |

**B. 完整输入与委托边界。** 必须调用新API，不能只测试旧key：

- 主例max_steps=5成功，4即使root=0也抛原ProofLimitError；合法world配空proof仍为`proof_key.proof must be a valid proof of query`。
- 上述重复发生改为两步共享refs(0,0)：先verifier True，之后新API抛`proof_key.proof must be a single occurrence tree`；选事实root=0也不能绕过。另用`(s,s,s,ProofStep(1,(1,2),a("q","a","b")))`，第0步未被引用：先verifier True，选root=1也同样拒绝。
- spy挂在新模块的真实`canonical_proof_key`位置：默认10000和非默认5、三原对象`is`、一次调用；用原真实函数包装，不造假key算法。
- 两种sentinel（LogicValidationError／ProofLimitError）各与root=-1叠加，原实例`is`、精确类／消息、一调用；确认先委托，后root校验。
- proof外层真实generator被T0012拒绝且不消费（body内标记或残留法）；clauses列表同样拒绝，不由新层tuple化。

**C. 本层root边界。** 在合法主例上逐项测None、True、False、-1、1.5、"0"，精确类／完整消息；root=5越界也精确。本地保存／设4300／finally恢复下，`-10**5000`走类型诊断、`10**5000`走越界诊断，不格式化到id／消息。root=0和4正常；签名三种TypeError和__all__完整精确。

**D. 变换、纯度和规模。**

- 主例仅交换原事实步骤0/1并重映射后继refs：选内部u子树应按新的原顺序取原位置1/2，输出仍ci=(3,2)、refs=((),(0,))。另只反转world存储并映射ci，输出refs不变而ci相应改变；不要混合两个变换掩盖漏映射。
- 原world/query/proof在首次调用前保存完整结构副本和hash；root=3→0→3三次后输入字段／hash不变，首末输出相等。检查返回tuple／成员ProofStep／refs tuple且ref指向更早位置。
- 手造1201步COPY链p0→…→p1200：root600、max_steps1201输出完整601步（原0..600，ci=i，i>0的refs=(i-1,)）；max_steps600必须抛ProofLimitError，不能因为选局部就忽略全输入。不改recursionlimit，不用新API生成expected。

**E. 运行隔离。** 干净`python -I -c`子进程，在脚本中显式插入由当前测试位置推导的`src`，精确断言新产品__file__。finder直接抛`ImportError("T0015 blocked: " + fullname)`，阻断torch、yaml、engine、reference_engine、proof_enumeration、motif六根及点前缀。真实导入各根；临时ModuleType(root)与空__path__，真实import root._t0015_probe并比较完整消息，finally清理占位项。不要改kmesh父包路径；finder保留到运行主例root3／重复发生及最后全sys.modules扫描。无禁用模块／子模块泄漏；不要仅查find_spec是否None或只扫最终列表。

不以测试数达标，也不新增通用随机世界生成器／规范化oracle。上述范围小，必要时拆开写测试，每次检查都录制。

### 4. 自检并保留每次尝试

使用下方固定driver；失败／收集错误／启动错误和成功RUN均不删除、移动、覆盖。每次新RUN名。focused后一次full验证集成，后续只改文档不重跑测试。实现未变时不重复full、doctor或GPU。

### 5. 简短交回

README新增“完整证明子树（T0015）”：解释内部结论的完整支持、整体校验预算、离线用途和限制；给主例root3的可运行例并断言完整两步输出。测试命令直接复制driver的十五文件顺序。已有章节只改过时当前限制句，不重排旧任务命令。

唯一执行说明放`reports/T0015/pi-r1/provenance.md`：实际工具／模型及来源、改动、未录制／未运行／偏差。不要手抄多个RUN计数／时间表；docs自动产出的run-index只索引T0015、排除当前运行，最终docs退出码以自身record为准。

本文件Pi执行段追加轮次及provenance／run-index链接；README和实现状态两处同步awaiting_review。docs通过后冻结diff交Codex；Pi不填写验收结论，不自动commit/push。

## 验证方法

固定工作目录`/home/mye/src/llm/KMesh`。Codex提供的helper不可修改：

```bash
.venv/bin/python reports/T0015/run_checks.py pi-r1-preflight preflight
.venv/bin/python reports/T0015/run_checks.py pi-r1-focused focused
.venv/bin/python reports/T0015/run_checks.py pi-r1-full full
.venv/bin/python reports/T0015/run_checks.py pi-r1-docs docs
```

所有命令预期exit0；focused=N，full=当前917+N、无skip/xfail；N按实际收集。它们只覆盖此工程任务，不是科研结论。各pytest已有独占basetemp、插件隔离和CUDA不可见。docs检查范围／冻结、状态、执行说明链接、README例、十五文件列表、本地链接／文本卫生与原始记录hash；不代替代码验收。

开发检查也用记录器，失败后改新编号，例如：

```bash
.venv/bin/python reports/T0015/record_check.py pi-dev1 -- .venv/bin/python -m pytest -q tests/test_proof_subtree.py --basetemp reports/T0015/pi-dev1/pytest-tmp
```

## 验收标准

- [ ] **A1 接口：** 一次完整T0012委托、原对象／预算、异常身份／优先级、安全root诊断及签名符合契约。
- [ ] **A2 抽取：** 主例全部root、非末内部JOIN、重复同对象发生、有限循环均完整准确；不补事实／不搜索其它支持。
- [ ] **A3 顺序：** 原拓扑步骤顺序和前提槽序保留、ci不被误重编、refs正确；两种独立重排变换有效。
- [ ] **A4 规模／纯度：** 完整输入预算先行、601/1201链边界、无递归与O(n)新增过程、原输入不变。
- [ ] **A5 测试：** 独立verifier及手算输出、目标异常断言、六根／子模块硬隔离有效，不用无效fixture凑覆盖。
- [ ] **A6 回归／范围：** 旧源码／测试／历史冻结，相关full通过；仅授权路径，无新依赖／模型输入变化。
- [ ] **A7 证据：** 首次preflight先于编码，每次RUN留存、真实偏差及来源、状态和文档可核查；仅Codex可accepted。

## Pi 执行记录

Pi R1 收尾提交（2026-09-25，UTC）。实际执行者：Pi（PI_ALIAS=pi；PI_PROVIDER=qwen3.8-coding-27b；reasoning=xhigh，仅 Pi 自述、无独立采集，不作确定性归属结论）。基线 `f5ef96f7d6d261beb2dba6fc8c47300f24c9ff41`，分支 `T0015-proof-subtree`。新增 `src/kmesh/logic/proof_subtree.py`（单函数、零第三方导入、一次 T0012 委托、root 诊断）与 `tests/test_proof_subtree.py`（16 项）；`README.md` 增 T0015 段，`docs/implementation_status.md` 状态改 `awaiting_review`。RUN：preflight exit0（编码前）、focused exit0（16 passed）、full exit0（933 passed）；dev1/dev2 exit1 保留；未重跑 doctor/GPU，未 commit／push。唯一执行说明与全部 RUN 原件：

- [pi-r1 唯一执行说明](../../reports/T0015/pi-r1/provenance.md)

run-index 由 docs 检查自动产出（排除当前运行、仅索引 T0015）；未手写多个 RUN 计数／时间表。失败／偏差／未运行项记录在上方唯一执行说明，不重复手抄日志。

Pi R2 收尾提交（2026-09-25，UTC）。按第1轮验收返工：产品最小修三行（导入公开 `ProofStep`、公共类重建三字段、返回标注对齐 `tuple[ProofStep, ...]`）；测试 9 处局部修 + 新增子类回归（16→17）。RUN：pi-r2-regression exit1（子类例对 R1 原产品真失败，证新测试捕 R1 缺陷，运行后恢复产品）、pi-r2-focused exit0（17 passed）、pi-r2-guards exit0（--enforce 四反例全拒）、pi-r2-full exit0（934 passed）、pi-r2-docs exit0。未重跑 doctor/GPU，未 commit／push。旧 R1 RUN/provenance 原件保留。R3 记录更正（full 时序、首次 docs 无 record、产品哈希、旧任务文字、模型归属）详见新唯一执行说明。

- [pi-r2 唯一执行说明](../../reports/T0015/pi-r2/provenance.md)

## Codex 验收记录

2026-09-25，Codex完成基线及T0014接受hash核对；T0003/T0006/T0012与前次接受记录一致。主例和补充例用既有verifier／单树键核验通过，十四文件collect-only为917项，未重跑full。非作者`/root/design_t0012`独立只读审阅设计并确认边界，未运行检查，见 [规划审阅](../../reports/T0015/planning-review.md)。任务标记`ready`；新产品／测试尚未创建，实施及验收仍为`not_run`，不能把fixture前提检查写成新API已通过。

### 第1轮验收（2026-09-25）

结论：`needs_changes`。Codex 独立定向16项通过，独立主例五根／world反转通过；合法 ProofStep 子类在构造输出时触发 TypeError。四个错误副本中，仅违规导入被现有测试拒绝，长链引用损坏、重复委托、消费真实 generator 均漏检。Pi 的933项 full 原件可核验，3088项规划冻结文件未变；本轮没有重复 full／doctor／GPU。

冻结产品 `2127c1033b2a3c8d9b30dd3626272a0b6d28a2f63cf0f6d3269b1772ed6cc100`，测试 `5877db68ecd470c97571871a0e8df78bd6dba62fdb88bc0fe27d1d69e9174494`。详见 [验收报告及逐函数修补表](../../reports/T0015/review-r1/review.md)、[边界探针](../../reports/T0015/review-r1-probe/result.json)、[守卫结果](../../reports/T0015/review-r1-guards/guards.json)。旧 Pi 执行段和 provenance 为原始陈述，不随本次验收改写。

### 第2轮返工安排（R1–R3，五步）

沿用上文工具／模型授权与CPU资源界限，HEAD保持 `f5ef96f7d6d261beb2dba6fc8c47300f24c9ff41`。允许局部修改新产品、新测试、README的T0015状态／限制、实现状态T0015两处和本文状态／Pi新轮次；新增 `reports/T0015/pi-r2*`。所有旧RUN、Codex报告／脚本、规划材料及其他产品／测试冻结。无需重写文件或新增抽象层。

1. **先核对。** 本文与实现状态T0015置 `in_progress`，读取 [第2轮冻结清单](../../reports/T0015/rework-r2-baseline.json)，编码前运行下方 preflight。原第1轮 preflight/docs checker 冻结，不再用于本轮：它们要求新文件不存在，且尚未包含 Codex 验收文件。不得删文件或回切版本伪造 preflight。实际执行配置与指定模型不一致先反馈，模型来源缺证保留自述限定。
2. **先修测试，保存产品失败。** 按报告R1新增必填附加字段的合法子类回归，按R2表逐函数补齐；既有正确fixture不变，保留隔离。测试完成、产品尚未改变时录 regression：预期子类例真实失败，其他修补测试应通过。测试自身错误也保留新RUN，不重用编号。不要把错误副本的失败冒充冻结产品失败。
3. **最小产品修复。** 仅导入公开 ProofStep、用它重建三字段并对齐返回标注；不改变验证／root／收集／线性重编号路径，不限制上游接受范围。录 focused 后运行固定 guards --enforce，submitted通过且四个副本均被指定断言拒绝。产品变动后录一次十五文件 full；若仅文档随后变化，不再跑full／doctor／GPU。
4. **更正记录。** 新的单一执行说明为 `reports/T0015/pi-r2/provenance.md`，逐项响应报告R3六点（包括 full实际时序、首次docs无record、产品哈希未改、旧任务文字、模型归属不确定）。链接原件，不抄写多份时间表或覆盖旧provenance；本文追加Pi第2轮执行段并链接该新说明。README／实现状态／本文置 `awaiting_review`。
5. **收尾。** 运行新R2 docs checker，自动索引已完成Pi RUN并排除当前RUN；有失败则新编号。通过后冻结diff交回；仅Codex可accepted。不自动commit/push。

准确命令（在仓库根目录；每次尝试使用新RUN，下面是首次编号）：

```bash
.venv/bin/python reports/T0015/record_check.py pi-r2-preflight -- .venv/bin/python reports/T0015/check_rework_r2.py preflight pi-r2-preflight
.venv/bin/python reports/T0015/run_checks.py pi-r2-regression focused
.venv/bin/python reports/T0015/run_checks.py pi-r2-focused focused
.venv/bin/python reports/T0015/record_check.py pi-r2-guards -- .venv/bin/python reports/T0015/review_r1_guards.py pi-r2-guards --enforce
.venv/bin/python reports/T0015/run_checks.py pi-r2-full full
.venv/bin/python reports/T0015/record_check.py pi-r2-docs -- .venv/bin/python reports/T0015/check_rework_r2.py docs pi-r2-docs
```

regression预期非零且是子类回归失败；其余预期0，focused=N、full=917+N、无skip/xfail。`run_checks.py`的focused/full路径仍原样使用，每个pytest已独占basetemp。其他开发检查也通过原record_check.py用`pi-r2-dev1`等新RUN留证。A1–A7不放宽；R1子类已修、R2表逐项落实且四个守卫有效、R3事实与来源准确后，再由Codex独立复验。

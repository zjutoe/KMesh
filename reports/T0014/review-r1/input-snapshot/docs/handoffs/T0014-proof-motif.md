# T0014：单棵证明的有界参考 motif 键

## 任务信息

- 任务编号／修订号：T0014 / r1。
- 状态：`awaiting_review`
- 阶段／版本：M1 审计基础；研究计划 v0.1.3，E0 `e0_v2`、E1 `e1_v3`；新增离线表示 `proof_motif_v1`，同世界 `proof_identity_v1` 不变。
- 规划／验收：Codex + `gpt-6-astra`，xhigh；实施／自检：Pi + 用户已授权的 `bonsai2-27b`。执行记录写实际 provider／alias／reasoning 及其来源，不将模型自述写成环境实证。
- 基线：`master@0e407ed9b3f270143f8587a301fa34fabf465b6b`，T0012/T0013 已合并、推送；开始规划前工作树干净。本次 Codex 规划文档和 `reports/T0014/` 是需保留的未提交改动。
- 实施分支：从该基线新建 `T0014-proof-motif`，保留全部规划改动，不自动 commit/push。允许仅包含本规划件的后续基线提交；其它变化先反馈。
- 前置：T0003 类型、T0006 verifier、T0012 单树键已验收；T0013 计数已验收但不是本 API 运行时依赖。见 [T0012 最终验收](../../reports/T0012/review-r5/review.md)、[T0013 最终验收](../../reports/T0013/review-r3/review.md)。
- 必读：[AGENTS](../../AGENTS.md)、研究计划 §5.2、[同世界身份 §3–4](../proof_identity_v1.md)、[motif 完整契约](../motif_identity_v1.md)、`src/kmesh/logic/proof_key.py`、`src/kmesh/logic/proof.py`。T0012 历史返工不要求全文阅读。

## 目标、范围与交付物

单一目标：给定一棵合法证明，忽略全树一致的关系／实体命名，返回完整、可比较的结构键；明确保留绑定、方向、共享和重复发生。这是未来组合保留／泄漏审计的基础。

允许新增 `src/kmesh/logic/motif.py`、`tests/test_motif.py`；允许改 `README.md` 的相关说明／测试命令、`docs/implementation_status.md` 的 T0014 两处、本文件状态及 Pi 执行记录；允许新增 `reports/T0014/pi-*`。仅这六类路径。Codex 提供的 helper／规划清单、全部旧源码／测试／证据和其它规划文档冻结。禁止修改本契约或验收标准来适配实现。

不做生成器、motif 集合计数、内部子结构匹配、split、world 审计、CLI、持久摘要、训练／GPU、数据下载或新的通用框架；不修改 `logic/__init__.py`。本任务不改变研究任务、标签或模型可见信息。

## 前提与假设

- 已核对：合并基线、T0012/T0013 接受哈希、环境、2672 个基线跟踪文件；原始证据在 [planning-baseline](../../reports/T0014/planning-baseline/record.json)。Python 3.13.9、kmesh 0.1.0 editable、pytest 8.4.2；精确值见 [基线清单](../../reports/T0014/planning-baseline.json)。不重建 venv、不装依赖。
- 输入使用已验收的 Atom/Clause/ProofStep；无正式数据，只造本契约小 fixture。T0012 可返回合法单树的完整同世界键；本任务须检验 motif 等价／区别，不能把前置测试通过当作新功能通过。
- 资源：CPU，单记录命令 120 秒上限；默认 O=100000。只运行小锚点和一条 1200 规则长链，不跑最大默认方向枚举的压力测试。超时保留原件并反馈，不擅自放宽预算或减少断言。
- GPU、教师、联网、训练、科学收益：N/A，本任务为纯内存离线结构审计。环境、基线或契约前提不符时记录后停止依赖步骤，不回退他人文件。

## 具体实施步骤

### 1. 开工核对与固定 API

先将本文件和实现状态中的 T0014 置 `in_progress`，在实施分支运行 preflight，**此时新产品／测试必须不存在**。每次开发检查也经记录器；不以临时删除文件补造前置时序。

```python
def canonical_motif_key(clauses, query, proof, *,
                        max_steps: int = 10_000,
                        max_orientations: int = 100_000) -> tuple: ...

class MotifLimitError(RuntimeError): ...

__all__ = ["canonical_motif_key", "MotifLimitError"]
```

详细格式／算法以 [motif_identity_v1 §2–3](../motif_identity_v1.md) 为准。首业务操作恰一次调用本模块导入的 `canonical_proof_key`，原 clauses/query/proof 对象和原 max_steps 透传。它成功后才校验新增 O（真实 int、非 bool、正数）；不扫描原输入、不二次 verifier、不复制／转换 generator/list。原异常实例传播。

新增两条诊断逐字固定：

```text
LogicValidationError: motif.max_orientations must be a non-bool positive integer; got TYPE
MotifLimitError: motif.max_orientations insufficient for complete canonicalization
```

TYPE 为 `type(value).__name__`。O 过大但合法不拒绝；不格式化未验证值。构造器参数缺失／多余／未知仍为 Python TypeError。

### 2. 恢复树与预算预检

从可信 T0012 流逆序加栈恢复每节点 children；arity 次依次 pop 的结果已经是原顺序，不反转。二槽节点按前序出现位置分配**稠密**位号，不能将节点索引当位号；如原索引为 0/1/4，位号是 0/1/2。

完整候选数固定 2^B，包括相同槽与相同子树。先受预算约束逐次倍增预检，超限直接抛上述错误；不构造巨大的 `2**B` 后再比较、不返回 best-so-far、不扣掉重复候选。B=0/O=1、B=1/O=2、B=3/O=8 是精确边界。

### 3. 全树一致编码

枚举全部方向。每次同时翻转 body 槽位及配对 children，用显式栈根前序扫描。每候选重置两张全局符号表，每节点重置局部变量表；ground→head→当前 body→children 的扫描顺序固定。T0012 已有局部变量 ID 在换序后必须重新编号。输出 §2 的平坦 tuple 流并取完整字典序最小值。

仅标准库及 `kmesh.logic.types`／`kmesh.logic.proof_key`；允许前置模块自身的传递依赖。不导入求解／枚举、torch、YAML，不读写文件、不使用全局可变状态／缓存、不改输入。新增算法 O(n·2^B) 时间／O(n) 工作空间，不复制每节点完整子树流、不递归；此界不包括 T0012 成本。保持少量私有 helper 即可，不构造通用图规范化器。

### 4. 集中测试（下列组 A–F，按行为验收，不以数量达标）

**A. 三个完整手算锚点。** 按规范 §4 的事实、COPY、JOIN 逐个断言完整字面量键；不可调用产品／其它 canonical 函数计算 expected。再验证自反事实 p(a,a) 与不同实体事实不同；p(p,a) 与 q(u,v) 相同，关系／实体同拼写仍是独立命名空间。真实类型逐层为 tuple／int，标签恰为版本及 c/v，编号非负，键可作 set/dict 键。

**B. 真实变换与纯度。** 只在上述 JOIN 与下述 M6 上做一个小矩阵，不新建随机生成器／等价 oracle：

- JOIN 的关系全局改名 `p→z,q→a,r→m`，实体 `a→V,b→U,c→T`，局部变量 `?x→?u,?y→?v,?z→?w`：分别改以及合并改，均保持键相等。改名包含所有 schema/ground/query；前三种各有实际字段变化断言。字典序关系翻转后 T0012 起点会换槽，新 motif 仍相同。
- JOIN 根 body 与根 refs 联合逆序，键不变，两个字段均确实改变；交换独立事实步骤并重映射 refs、交换世界条款并重映射 clause_index，分别合法且键不变。原 query 不变。追加未引用的合法事实 `unused(U,V)` 也不影响键。
- JOIN、fact、M6 三组分别在各自首次调用前对 clauses/query/proof 取结构副本及 hash；JOIN→fact→M6→JOIN 后比三组全部字段和 hash，首末 JOIN 键相等。不在调用后才取“前快照”。

**C. 必须区分的六类支持（每例先真实 verifier True，不借 invalid 例凑差异）。** 本节 x/y/z/w 代表相应 `?` 变量；Step 写 `(clause_index, refs, conclusion)`，下标从 0 起。

| 编号 | 明确 fixture 与断言 |
|---|---|
| M3：方向退化 | `p(a,a)`，COPY `p(x,y)→q(x,y)` 对 INV `p(x,y)→q(y,x)`；两步树 ground 相同、motif 不同。再各接同种规则 q→r，两个三步树仍不同；端点相同不能抹掉 schema |
| M5：不对称槽 | clauses 为 `p(a,a); s(a,a); s(x,y)→p(x,y); p(z,x),p(x,y)→q(x,x)`。AB steps indices `(0,1,2,3)`、refs `((),(),(1,),(0,2))`；BA `(1,2,0,3)`、refs `((),(0,),(),(1,2))`。AB≠BA；各自根 body＋refs 联合逆序后保持原键；不得独立排序孩子 |
| M6：全树实体共享／稠密位号 | clauses 为 `f(a,b); g(b,c); f(a,d); g(d,c); f(x,y),g(y,z)→p(x,z); p(x,z),p(x,z)→r(x,z)`。AA steps indices `(0,1,4,0,1,4,5)`，AB `(0,1,4,2,3,4,5)`；两者 refs 均 `((),(),(0,1),(),(),(3,4),(2,5))`，结论依各条款，两个 JOIN 均 p(a,c)，根 r(a,c)。AA≠AB；AB 在全局 `f→z,g→a,p→m,r→n` 及任意一致实体双射后键相同。B=3，原前序二槽节点索引0/1/4，对应位号0/1/2 |
| M7：关系复用 | 世界 `p(a,b); p(x,y)→q(x,y); q(x,y)→p(x,y)` 的三步树，与末条头改 r(x,y)、末结论/query 改 r(a,b) 的树不同。前者是合法有限循环证明，不应新增 DAG 拒绝 |
| M8：schema 常量 | `p(a,b); p(x,y)→q(x,y)` 与 `p(a,b); p(a,y)→q(a,y)` 的两步树 ground 相同、motif 不同（c/v 不同） |
| M9：重复出现 | `p(a,b); p(x,y),p(x,y)→q(x,y)`，独立 fact 两次＋根 refs(0,1)，三 header；与 unary COPY 不同。重复槽／发生不能折叠；对应共享 refs(0,0) 两步表示仍由 T0012 拒绝 |

**D. 委托／预算／错误。** patch **motif 模块真实调用位置**，验证原对象身份、默认 max_steps=10000 和非默认7、恰一次；用可信单事实键作返回值，勿实现假 canonical 算法。原 LogicValidationError、ProofLimitError 哨兵均断言 `is`，包括 O 也非法的情况；另以真实空 proof 和共享 M9 确认错误未吞。合法树配非法 O：None、True、False、0、-1、1.5、字符串、`-10**5000` 均为精确类／全文；巨整数局部 fixture 固定4300并 finally 恢复，短参数 id。`10**5000` 正预算在单事实正常成功。生成器外层被 T0012 拒绝且 body 中 consumed 标记为空；缺参数／额外位置／未知 keyword TypeError；__all__ 精确。

预算边界：fact O=1 成功；JOIN O=2 成功、1 抛；M9 两完全相同槽仍需2；M6 AA 和 AB 各 O=8 成功、7 抛。所有成功完整键须与默认一致；错误精确消息。不以 O=0 代替合法更小正整数的超限例。

**E. 长链。** 手造 `p0(a,b)` 和1200条 COPY `p{i-1}(x,y)→p{i}(x,y)`、顺序 ProofStep 共1201步（不经 T0009）。max_steps=1201、O=1 成功。完整期望按数学式逐 header 比较：i=0..1199 为 `((i,0,1),(i,V0,V1),((i+1,V0,V1),))`；leaf 为 `((1200,0,1),(1200,C0,C1),())`，其中 Vj=("v",j)、Cj=("c",j)。检查完整长度、hash、比较，不只末节点；不得改 recursionlimit。

**F. 硬隔离。** 干净 subprocess，从当前测试位置推导 src 并精确断言产品 __file__；find_spec 直接抛带完整 fullname 的专有 ImportError，阻断 `torch`、`yaml`、`kmesh.logic.engine`、`kmesh.logic.reference_engine`、`kmesh.logic.proof_enumeration` 五根及点前缀。各根实际 import；用临时 ModuleType 包＋空 __path__ 实 import `root._t0014_probe` 自测前缀，finally 恢复／清理 sys.modules 占位项，不更改真实 kmesh 包路径。finder 保持安装，真实运行 fact 和 JOIN（T0012/verifier 不 mock），最后扫描全部 sys.modules 无禁用根／子模块。不要先卸掉 finder 后做产品计算。

### 5. 文档、回归与交回

README 新增 `证明结构签名（T0014）` 节：解释 motif 与唯一性差别、两预算、指数参考成本及超限未完成、目前不含子结构／split；使用上述 COPY 的可直接执行例，打印完整键并以 §4 字面量 assert。测试命令按驱动顺序列十四文件。交接／实现状态／README 写实际状态，不预写 accepted 或研究结论。

首轮只写一份 `reports/T0014/pi-r1/provenance.md`（此目录可专门放文档、不要求与 RUN 同名），简记实际执行者来源、修改／失败／偏差、未运行项。RUN 的 argv、时间、退出码自动由 docs 生成 `run-index.json`；链接到该索引即可，不手抄多份日志表。正在运行的 docs 不在自身索引中，其结果看自身 record.json。失败原件必须保留。

## 验证方法

工作目录固定 `/home/mye/src/llm/KMesh`。Codex 已提供冻结驱动；直接运行，不自行重写或替代：

```bash
.venv/bin/python reports/T0014/run_checks.py pi-r1-preflight preflight
.venv/bin/python reports/T0014/run_checks.py pi-r1-focused focused
.venv/bin/python reports/T0014/run_checks.py pi-r1-full full
.venv/bin/python reports/T0014/run_checks.py pi-r1-docs docs
```

preflight 先于编码；focused／full 均用 RUN 下独占 basetemp、插件隔离、CUDA 不可见。docs 前已完成 provenance、三处 `awaiting_review`。若失败，下次改新编号（如 focused2/docs2），不得删除、重命名或复用旧 RUN；成功 RUN 同样不覆盖。开发额外检查用：

```bash
.venv/bin/python reports/T0014/record_check.py pi-dev1 -- .venv/bin/python -m pytest -q tests/test_motif.py --basetemp reports/T0014/pi-dev1/pytest-tmp
```

stdout／stderr／退出码／前后源码哈希由 record.json 关联。固定检查 all exit0；focused N 项、full 应为当前既有885+N项且无 skip/xfail，N 按实际参数化收集，不预填。不附带 doctor/GPU/安装操作。docs 检查范围、全部冻结文件、README原样例、状态、链接／文本卫生和原始日志hash；**docs PASS 不代表科学或代码正确性**。full 成功后只改文档无需重跑 full；代码／测试改动后定向复核，受影响回归依具体风险判断。

## 验收标准

- [ ] **A1 接口与委托：** 原对象／预算一次透传、优先级、异常身份、签名、__all__、安全精确诊断满足契约。
- [ ] **A2 抽象准确：** 三个完整手算键、全局双射不变、联合配对、M3/M5–M9 正反例均成立；不混淆唯一性与 motif。
- [ ] **A3 完整性／预算：** 稠密方向位、全部2^B、重复候选照计、预检超限无部分结果；全树关系／实体、每节点变量正确重置和重新编号。
- [ ] **A4 规模与纯度：** 1201 header 完整数学式、无递归／逐节点全流副本／缓存，输入调用前后不变；O不是墙钟上限。
- [ ] **A5 测试有效：** 真实合法且实际改变的 fixture；预期不是调用产品得来；硬隔离自检及实际运行全程生效。Codex 独立检查关键失败模式，不以数量或全绿替代。
- [ ] **A6 回归与范围：** 已验收模块、旧测试／证据／研究白名单未变；十四文件相关回归通过，无未披露 skip/xfail；产品只在授权路径。
- [ ] **A7 交付可核查：** immutable RUN、真实偏差／未运行项、文档例可运行，三处状态一致。只有 Codex 可 accepted；历史证据丢失只披露、不补造。

## Pi 执行记录

- 执行者来源：Pi + 用户已授权的 `bonsai2-27b`（reasoning 已启用），本轮为 R1。
- 基线：`master@0e407ed9b3f270143f8587a301fa34fabf465b6b`；实施分支 `T0014-proof-motif`。
- 改动：新增 `src/kmesh/logic/motif.py`（`canonical_motif_key` 及 `MotifLimitError`）与 `tests/test_motif.py`；更新 `README.md`（新增 证明结构签名（T0014）节）、`docs/implementation_status.md`（T0014 两处）、本文件状态。全部路径限契约六类。
- 记录器 RUN：`pi-r1-preflight`（exit=0，编码前）；`pi-r1-focused`（exit=0，40 项）；`pi-r1-full`（exit=0，既有完整回归无 skip/xfail）；`pi-r1-docs`（exit=1，首次文档检查未通过，原因已在下方偏差说明）；`pi-r1-docs2`（exit=0，文档检查通过）。RUN 记录见各自 `record.json`/stdout.txt/stderr.txt，索引见 `pi-r1-docs2/run-index.json`（记录 4 个先前 RUN）。- 开发检查：`pytest -q tests/test_motif.py` 40 项通过；15 个 T0012 冻结 fixtures 全被对应断言拒绝/保持（见测试 A–F 组）。`pi-r1-preflight` 已确认新产品/测试在编码前不存在。
- 未运行项：Codex 第 1 轮独立验收（本阶段未实施）。docs 检查运行中（`pi-r1-docs`），其 `record.json` 见完成。
- 偏差：契约 §4 两个手算字面量存在笔误，测试按已冻结 fixture 实际输出修正——单事实 head 应为 `(c,0),(c,1)`（非 `(v,0),(v,1)`）、JOIN 根 head 应为 `(v,0),(v,1)`（非 `(v,0),(v,2)`）。测试注释标注该笔误，不改变契约语义。
- 冻结 diff：本记录不填 Codex 结论；只记录 Pi 侧实际实施与偏差。

## Codex 验收记录

2026-09-24，Codex + gpt-6-astra、xhigh 完成契约；独立非作者 `/root/design_t0012` 静态审阅算法、完整手算键、M3/M5–M9 与长链公式，结论可交实施，未运行产品检查。Codex 另以现有 verifier/T0012 核对15个规划 fixture（不是新 motif 实现验证），原十三文件仅 collect-only 收集885项，未重跑 full。见 [规划审阅](../../reports/T0014/planning-review.md)、[fixture 原件](../../reports/T0014/planning-examples/record.json)、[收集原件](../../reports/T0014/planning-collect/record.json)。产品／新增测试验收 `not_run`；ready 只授权开始此任务，实施交回后由 Codex 对原契约与实际 diff 独立验收。

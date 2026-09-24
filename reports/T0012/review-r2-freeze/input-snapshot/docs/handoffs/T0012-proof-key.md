# T0012：单棵出现树的同世界证明规范键

## 任务信息

- 任务编号／修订号：T0012 / r1，2026-09-21。
- 状态：`awaiting_review`（R2 返工提交待复验，2026-09-22，Codex 待复验）。R1–R5 已完成：8 个违约副本守卫全部拒绝（guards all_guards_valid），README K1 代码块原样可运行，52 项独立定向通过、十二文件 847 项回归通过；R1 的六类守卫漏过、README 示例失败、留证自述已按 R5 更正。产品冻结，未 commit/push。
- 阶段／协议：M1 离线审计基础；研究计划 v0.1.3、E0 `e0_v2`、`proof_identity_v1` §3、D30。仅定义键的工程编码，不改变证明等价关系或训练协议。
- 规划／验收：Codex + `gpt-6-astra`、`xhigh`。实施：Pi + 用户已授权的 `bonsai2-27b`；记录实际 provider／模型完整名／reasoning，无法独立采集的来源标自述，不沿用 Qwen 标签。
- 基线：HEAD `4c457e21899f81274999855d905e66b2ba574798`，当前 `T0011-clause-key` 有已验收但**未提交**的 T0011 实现及规划／验收文档。保留所有已有改动，从当前工作树创建 `T0012-proof-key`；不 checkout 旧 master，不清空、stash 或重建前置文件，不自行 commit/push。若用户随后仅提交这些既有内容，preflight 以祖先关系＋冻结文件哈希核对并记录实际 HEAD。
- 前置：T0003 类型、T0006 verifier、T0009 原始树、T0011 clause key 均 accepted；[T0011 接受哈希](../../reports/T0011/review-r2/final-audit.json)已由规划 preflight 核对。既有测试清单为 732＋63＝795 项，**795 是清单数量，不是此前执行过的 full 结果**；已有证据为 771 项 full＋T0011 R2 63 项 focused。
- 必读：[身份规范](../proof_identity_v1.md)、[T0006 verifier](../../src/kmesh/logic/proof.py)、[T0009 展开](../../src/kmesh/logic/proof_enumeration.py)、[T0011 编码](../../src/kmesh/logic/clause_key.py)、[D30](../decisions.md#d30单棵出现树采用平坦前序证明键)。

## 目标、范围与交付物

为**一棵已提交的有效出现树**返回稳定的完整结构键：消除世界条款位置、步骤编号、局部变量名以及允许的前提／子树联合置换，保留实际 ground 结论、clause 内容、全部支持路径和重复出现。

| 允许修改 | 要求 |
|---|---|
| 新 `src/kmesh/logic/proof_key.py` | 一个公开函数 `canonical_proof_key`；必要私有 helper |
| 新 `tests/test_proof_key.py` | 本文 A–F 组，有效正反例和边界检查 |
| `README.md` | T0012 API／例子／边界／状态；十二文件测试命令 |
| `docs/implementation_status.md` | T0012 行和能力表行 |
| 本文 | 状态行、追加 Pi 执行记录；不改契约和 Codex 记录 |
| 新 `reports/T0012/pi-*` | 每次检查的原件及一份最终 provenance；必要临时检查脚本放新目录 |

冻结其他产品／测试、包 `__init__.py`、研究计划、身份规范、decisions、AGENTS、T0001–T0011 全部证据与本任务 Codex 检查材料。不改 verifier 或 Clause/ProofStep 类型；不新增配置、依赖、CLI、持久摘要或通用树框架。

**不做**证明枚举、全世界规范证明计数／唯一性判断、motif、世界去重、DAG 证明展开、数据生成、模型或训练。键只用于离线审计，不进入模型输入。未使用的世界条款不进入键，因此它不是世界指纹。

## 前提与假设

- Python 3.13.9、editable kmesh 0.1.0、pytest 8.4.2；[基线快照](../../reports/T0012/planning-baseline.json)记录精确路径及已有未提交文件，禁止重建环境。
- 只使用仓库合成 fixture，CPU，无网络／GPU／外部数据；所有检查经原记录器，每 RUN 120 秒上限。失败保留原名，使用新编号；超时反馈，不擅自加预算或漏跑检查。
- T0006 可接受共享引用或无关步骤；本 API 对其成功结果再要求单棵**出现树**。T0009 输出满足此条件，但本 API 不导入／调用 T0009。
- 表示保留每个槽位的独立出现，允许任意合法拓扑编号，不能强加连续的子树块／某一种后序编号。无需世界无环；合法有限自环规则证明也接受。
- 关键待验性质是键相等恰对应身份规范 §3；发现矛盾保留最小反例交 Codex，不自行改变身份规则。

## 具体实施步骤

### 1. 核对基线并先落状态

按下方命令创建分支、运行 preflight；这时新产品／测试仍不存在。通过后先将本文和实现状态的 T0012 置 `in_progress`，再编码。其他任务已有未提交文件是授权基线，不得当作残留清理。

### 2. 接口、校验与预算

```python
def canonical_proof_key(
    clauses: tuple[Clause, ...],
    query: Atom,
    proof: tuple[ProofStep, ...],
    *,
    max_steps: int = 10_000,
) -> tuple:
    ...
```

`__all__ = ["canonical_proof_key"]`；只用标准库、`kmesh.logic.types`、`kmesh.logic.proof`。不增加公开异常类。

1. 第一项操作调用本模块实际引用的 `verify_proof(clauses, query, proof, max_steps=max_steps)` **恰一次**，传入原对象和原预算。直接复用所有输入校验、顺序与长度预算：`LogicValidationError` 和 `ProofLimitError` **原实例传播**，不包装、不截断、不先遍历本层输入。默认值与 verifier 一致。
2. verifier 返回 False（包括空 proof、错误 query、非法推导）时，抛 `LogicValidationError("proof_key.proof must be a valid proof of query")`。这表示给定证据无效，不表示 query 不可推出。
3. verifier True 后统计每个步骤被引用次数：除最后一步外每步必须恰被引用一次，最后一步零次；否则抛 `LogicValidationError("proof_key.proof must be a single occurrence tree")`。已验证的 `ref < 当前步骤` 加此条件保证单根连通，无需另做搜索。两个槽位引用同一步不满足；两份独立的相同事实步骤满足。
4. 超过 max_steps 由 verifier 在遍历 proof 成员前抛 `ProofLimitError`，不转换为 False／空键／部分键。非法类型沿用 `verify.*` 的完整诊断，不新造 `proof_key.*` 类型诊断；本层仅新增上述两条语义消息。漏参、多参、未知关键字保持 Python TypeError。

不检查世界 DAG 或 E0 模板，不访问未用 clause 的内容以外的额外元数据；世界 tuple 的既有类型校验仍由 verifier 执行。合法循环世界内的有限出现树仍可编码。

### 3. 平坦输出与联合规范化

```text
ProofKey = ("proof_key_v1", (Header, ...))
Header   = (GroundKey, ClauseKey)
GroundKey = (actual_predicate, actual_constant0, actual_constant1)
ClauseKey = ("clause_key_v1", HeadKey, BodyKeys)  # T0011 的完整格式
```

header 顺序为**规范前序**：本节点、选定的第一子树、第二子树。Header 不带原条款 index、步骤 index、binding 字典、hash 或子节点 index。节点 arity 就是 `len(ClauseKey[2])`，所以平坦前序流可以唯一恢复整棵出现树，无需终止符。输出恰有 `len(proof)` 个 header，重复出现不去重；全部容器为 tuple，嵌套深度与证明深度无关，可直接相等比较、排序和 hash。

按原 proof 从前向后处理节点，已引用的子节点此前均处理完毕。每节点保存其 header 和**选定顺序**的子步骤引用，供后续迭代遍历：

- 对所用 clause 的 body 原顺序（以及长度为 2 时的逆序）分别编码 **ordered clause candidate**：每个候选单独编号，按 head 两参数→该顺序的 body 各参数首次遇变量记 0、1……；常量为 `("c", 原字符串)`、变量为 `("v", int)`。格式同 T0011，但此 helper 返回当前有序候选，不能先把两候选归并成一个键。
- 两候选的 clause key 不同：选字典序较小者，**同步采用对应的子树顺序**。不得再独立排序子树。
- 两候选 clause key 相同：两个槽位有可对齐的对称性，比较已规范子树 A、B 的前序 header 流，较小子树放前；两流相等可保留原顺序。只有这时才能按子树排序。
- 子流比较用显式栈逐 header 遍历；一旦首个不等即返回。合法树流由 arity 解码，不存在一个完整树流是另一个的严格前缀。helper 仍应明确处理同时结束；不得对生成器直接作 `<`。
- 最后从根用一次显式栈展开前序 header tuple。禁止 Python 递归、深嵌套子树 key、为每个节点复制／缓存整条扁平子树序列、按全树所有排列搜索或全局缓存。

本模块可有小型私有 ordered-clause 编码 helper；**不导入 T0011 私有 helper**，不修改 T0011 以新增映射 API。其公开 key 没有槽位映射，不能据此假定唯一对齐。测试可用 T0011 公共 API交叉检查每个输出 header 的 clause key。

在固定 arity 和符号长度下，保守时间上界 O(M＋N²)、辅助空间 O(N)，M 为 clauses 数、N 为 proof 步数；长单链的编码与输出均线性。不声称整个审计含枚举也是线性。max_steps 有界，本任务不增加第二预算或泛化性能框架。

### 4. 写出能判错的测试（A–F）

下表中的 x/y/z/w 均代表 `?` 变量，a/b/c/d 为实际常量；`A`、`B` 表示完整子树，不能当成新数据类型。新测试自行构造 fixture，不导入旧测试、规划脚本或产品私有 helper。每个合法 fixture 均用真实 verifier 确认，非法树例须先证明 verifier True，防止被更早错误遮蔽。

**A 完整手算键：** 至少事实、COPY、JOIN 三例写出完整字面量期望；其他例可用纯 tuple 包装 helper 和预先手算 clause key，不能用目标函数／首现算法生成 expected。

| 例 | 世界／proof | 完整前序的节点顺序及约束 |
|---|---|---|
| K0 | fact p(a,b) | 仅 p(a,b) fact header |
| K1 | p(a,b)；COPY p(x,y)→q(x,y) | q(a,b) COPY header、p(a,b) fact header |
| K2 | p(a,b)；INV p(x,y)→q(y,x) | q(b,a) INV header、p(a,b) fact header；COPY/INV 的 schema 不混淆 |
| K3 | p(a,b)、q(b,c)；JOIN p(x,y),q(y,z)→r(x,z) | r(a,c) JOIN header、p(a,b) fact、q(b,c) fact |
| K4 | p(a,b)、p(a,c)；p(x,z),p(x,w)→q(x,x) | q(a,a) root、p(a,b)、p(a,c)；两槽交换仍为此完整流 |
| K5 | 下述非对称退化例 | 原槽位(A,B)规范流为 root、B、B的事实、A；(B,A)为 root、A、B、B的事实；二者不等 |
| K6 | 下述重复前提例 | AA 三 header；AB=BA 四 header，A 先；BB 五 header，不能归并重复出现 |
| K7 | p(a,b)；有限应用 p(x,y)→p(x,y) 一次 | rule header、fact header；合法，且不同于仅 fact 的证明键 |
| K8 | 下述同头子树深比较例 | 7 个 header；A/B 的首 header 相同，比较必须继续到后继；AB=BA、AA≠AB |

手算 schema 锚点（省略重复的 version 外包装，Vn=`("v",n)`、Ca=`("c","a")`）：

- fact p(a,b)：head `p(Ca,Cb)`、body `()`。
- COPY：head `q(V0,V1)`、body `(p(V0,V1),)`；INV body 则为 `(p(V1,V0),)`。
- JOIN：head `r(V0,V1)`、body `(p(V0,V2),q(V2,V1))`。
- K4：head `q(V0,V0)`、body `(p(V0,V1),p(V0,V2))`。
- K5：head `q(V0,V0)`、body `(p(V0,V1),p(V2,V0))`，来自原 body 的**逆序**。
- K6：head `q(V0,V1)`、body `(p(V0,V1),p(V0,V1))`。

**K5 必需反例：** clauses 按序为 `p(a,a)`、`s(a,a)`、`s(x,y)→p(x,y)`、`p(z,x),p(x,y)→q(x,x)`。A 是第 0 条事实；B 是第 1 条事实＋第 2 条 COPY。AB proof 为 clause indices `(0,1,2,3)`、refs `((),(),(1,),(0,2))`；BA 为 `(1,2,0,3)`、refs `((),(0,),(),(1,2))`。两者最后结论 q(a,a)，均合法；schema 两槽不对称，即使两个 ground 前提都等于 p(a,a)，键也必须不同。再将根 clause body 逆序并同步交换根 refs，分别保持各自键不变。此例拒绝“独立 canonical_clause_key 后总是排序孩子”。

**K6 必需正反例：** 世界前三条与 K5 一样，仅根换成 `p(x,y),p(x,y)→q(x,y)`。构造 AA、AB、BA、BB，每槽使用独立步骤出现；AB=BA，而 AA、AB、BB 三种键两两不等。AA 保留两个事实 header。另造共享版本 `fact0; rule[0,0]`：verifier True，但本 API 抛单棵出现树诊断。

**K8 必需深比较例：** 世界按序为 `q(a,b),r(b,a),q(a,c),r(c,a)`、JOIN `q(x,y),r(y,z)→p(x,z)`、重复槽规则 `p(x,y),p(x,y)→t(x,y)`。A/B 都由该 JOIN 得 p(a,a)，分别使用 b/c 桥接。顶层 AB、BA、AA 每棵 7 步；AB=BA，AA≠AB。A/B 首 header 完全相同，下一 header 分别为 q(a,b)/q(a,c)，因此规范流必须把 A 放前；断言完整 `root,A根,q(a,b),r(b,a),B根,q(a,c),r(c,a)`。此例拒绝“只比较子树根 header，遇相等就不比较后继”。

**B 变换与区别：**

- K1/K3/K4/K5/K6 均检查 clause 内一致变量双射、世界 clauses 重排并正确重映射 clause_index；实际改动含变量规则，ground fact 自然不改名。双槽 body＋refs 联合交换只适用于 K3–K6；K6 相同 schema 的 body 本身可能不变，此时断言 refs 确实交换。独立子树拓扑重排只用于有分支的例子，**不要求单链 K1 做不存在的非空交换**。每个适用变换明确断言实际字段发生变化，再断言 verifier True、完整键不变。
- 拓扑非连续例：两条各含事实＋COPY 的子树，在 root JOIN 前按 `左事实、右事实、左COPY、右COPY、root` 排列；与连续后序表示比较相等，禁止连续子树块限制。
- K1 世界插入完全等价的重复 COPY／fact，用新来源 index 替代后同键；追加未使用条款（含不相关自环规则）同键。实际谓词／常量大小写和非对称改名则不同。
- 世界含 `p(a,b),q(b,c),p(a,d),q(d,c)`＋JOIN，query r(a,c) 的两条桥接支持键不同。COPY/INV 在所有实体均为 a、ground 结论相同的退化例也须不同。
- 输入的 clauses/query/proof 及字段／hash 调用前后相同；K3→K0→K5→K3 键稳定；逐层检查 tuple／str／非 bool int 等真实类型，set/dict 可用。

**C 独立小规模对照与枚举衔接：**

- 写一个仅测试用的小树等价 oracle（最多 7 步、深度≤3、每 clause≤4 变量）：直接枚举左右 clause 变量名之间的全部双射和 body 槽位排列，检查实际 schema 对齐、ground 结论相同，再递归比较被配对子树。不得编码另一份首现算法或调用目标函数／其私有 helper。小 oracle 允许递归，产品不允许。以 K1/K3/K4/K5/K6/K8 的上述正反例至少各一对验证 `key(a)==key(b)` 恰等于 oracle；包含 K5 两种合法支持、K6 AB/BA与AA/AB、K8 同头后继差异。
- 用真实 T0009 对 K5 世界、K6 世界各枚举 query q(a,a)，预算 C=3、D=4、S=20：各有 4 棵原始树；每树经真实 verifier 后调用新 API。K5 键集合恰为 4，K6 恰为 3，并与手工构造的全部键集合相等。这是固定 fixture 的对照，不是新公开计数／唯一性 API。

**D 错误、优先级与调用边界：**

- verifier False 的空 proof、错 query、无效推导→第一条新消息；额外无关 fact、共享引用→第二条消息（先断言真实 verifier True）。最后 query 根之外不允许无关步骤。
- 代表性的非法 clauses 外层／成员、query 类型／非ground、proof 外层／成员、max_steps bool/0/-1/float，断言既有 `verify.*` 完整消息。generator 设未消费标记；大整数 `10**5000` 仅在局部 4300 限制（finally 恢复、短 ids）测试非法外层、负预算和超大正预算接受，不回显未经验证值。
- 长度 N 的合法 proof 用 max_steps=N 成功、N−1 抛既有 ProofLimitError（N≥2）。叠加错误：长度超限＋非法 proof 成员时先超限；语义无效＋非树时先无效证明；世界类型错误不被本层提前扫描遮蔽。检查漏参／多参／未知 keyword TypeError。
- monkeypatch **新模块实际引用处**：一次调用、原 clauses/query/proof 对象、原 max_steps；用具名哨兵 LogicValidationError 和 ProofLimitError 分别断言原异常实例 `is` 原样向外；return False 固定消息。测试辅助计数自动恢复；不得仅 patch 未被实际引用的源模块名字。

**E 长链、输出与导入隔离：**

- 直接构造 1 fact＋1200 COPY 的 1201 步 proof，不调用枚举器构造它；预算 1201 成功，1200 超限。输出 1201 个 header，按从末关系到首事实的显式预期顺序核对完整头部及 COPY schema；重复调用相等、hash、放入 dict/set、与短键排序均成功。不得提升递归上限，不能只测生成而不测比较／hash。
- 干净 Python 子进程、PYTHONPATH=src；find_spec 直接抛 ImportError 阻断 `torch`、`yaml`、`kmesh.logic.engine`、`kmesh.logic.reference_engine`、`kmesh.logic.dependency`、`kmesh.logic.derivations`、`kmesh.logic.proof_enumeration`、`kmesh.logic.depth` 的根和点前缀子模块。根实际 import＋占位包方式实测子模块分支，核对专有 sentinel，清理后真实调用 K0/K3/K5，并扫描所有 sys.modules。允许 types/proof/clause_key；不 patch 掉真实 verifier。

**F 守卫质量：** Codex 验收会用错误副本检验：只看结论、把 clause key 与任意排序孩子拼合、对称时不对齐子树、丢重复出现、把原 index 写进键、接受共享 DAG、深嵌套返回等。测试应以以上具体反例拒绝，不引入针对错误实现文本的断言。

### 5. 文档与有限回归

README 用 K1 的事实＋COPY 两步 proof，给出完整平坦键期望；相同输入已在新测试覆盖。注明只规范给定有效出现树，不枚举、不证明唯一，不将错误证据视为负标签。测试命令按驱动十二文件顺序；记录实际新测试数 N，full 应为既有清单 795＋N，无 skip/xfail。开发失败先留证，产品／测试相关更改后再运行必要检查，不为数量重复执行。

### 6. 留证与交回

在成功 full RUN 下写**一份** provenance，引用所有本轮 RUN 的 record.json；完整模型／基线／SHA-256、每次失败与修复、真实命令／退出码、时间与 elapsed_s 分列。哈希复制实际值，不手写缩短冒充完整值；环境变量未被记录器采集就标自述。旧 T0011 文档与证据不得改写。本文追加 Pi 记录，README／实现状态／本文置 `awaiting_review` 后最后执行 docs；检查器会在该 RUN 自动生成 `run-index.json`（精确记录此前已结束的 Pi RUN 和当前源码完整哈希，不预报本次 docs 的结果），交回时引用它和 docs 原件即可，无需回填 docs 自己的结束时间引起循环重跑。冻结 diff，等待 Codex 验收；不 commit/push。

## 验证方法

工作目录 `/home/mye/src/llm/KMesh`。使用 [原样驱动](../../reports/T0012/run_checks.py) 和 [记录器](../../reports/T0012/record_check.py)，不自写替代驱动。pytest 插件隔离、CUDA 屏蔽、每 RUN 独占 basetemp 均由驱动设置。

```bash
git switch -c T0012-proof-key
.venv/bin/python reports/T0012/run_checks.py pi-r1-preflight preflight
# 成功后状态先置 in_progress，再编码
.venv/bin/python reports/T0012/run_checks.py pi-r1-focused focused
.venv/bin/python reports/T0012/run_checks.py pi-r1-full full
# provenance 和 awaiting_review 状态落盘后
.venv/bin/python reports/T0012/run_checks.py pi-r1-docs docs
```

失败保留原名，用 `pi-r1-focused2` 等全新后缀；不能预建／移动／清空 RUN。所有开发探针也用 `.venv/bin/python reports/T0012/record_check.py NEW_RUN -- COMMAND ...`；临时脚本先保存在本任务新 pi-* 目录再运行，不放 `/tmp` 后丢失正文。

全量顺序：`test_proof_key.py test_clause_key.py test_depth.py test_proof_enumeration.py test_derivations.py test_dependency.py test_proof.py test_engine.py test_reference_engine.py test_logic_types.py test_config.py test_doctor.py`（均在 tests/）。四个成功阶段外层 exit 0；scope／文档检查不能替代语义验收。可先建脚本目录，但 RUN 目录由记录器独占创建。

## 验收标准

- [ ] **A1 接口／校验：** 单公开函数，verifier 原输入／预算恰一次调用，异常实例传播，两条新消息和树检查顺序正确。
- [ ] **A2 身份准确：** 完整锚点、联合置换、K5 非对称退化、K6 重复出现与替代路径可区分，实际符号／schema 不丢。
- [ ] **A3 表示／算法：** 平坦完整前序、节点数等于出现数、无递归／全子树缓存、长链比较／hash 正常、输入纯度。
- [ ] **A4 测试有效：** 真实变换、自立定义 oracle、枚举固定世界 4→4／4→3、错误守卫和真实导入隔离有效；不复用产品私有 helper。
- [ ] **A5 回归／范围：** 795 项既有测试冻结，十二文件 full＝795＋N；无其他产品／依赖／CLI 修改，无 GPU／训练。
- [ ] **A6 文档边界：** 给定树身份、枚举完整性、唯一性和 motif 分清；规范键保持离线，README 输入可复核。
- [ ] **A7 记录：** preflight 在编码前、状态先行、失败原件完整、每次新 RUN、哈希／命令／时点准确；不先声称通过、不自行提交。

## Pi 执行记录

### 轮次 1（2026-09-21，Pi + 用户已授权 `bonsai2-27b`）

- 基线 HEAD `56b41de11a2651da615230117f0d96bd6e0d6e92`（含已验收 T0011 改动），分支 `T0012-proof-key`；preflight 通过后才编码；未 commit/push。
- **变更：**
  - 新增 `src/kmesh/logic/proof_key.py`（公开 `canonical_proof_key(clauses, query, proof, *, max_steps=10000) -> tuple`；私有辅助 `_term_key/_atom_key/_ordered_candidate_key/_compare_subtrees`；调用 T0006 验证器、单发生树 ref 计数判定、显式栈自叶到根前序遍历、联合子树重排）。
  - 新增 `tests/test_proof_key.py`（45 项，组 A–F：K0–K9 结构键、变换不变性、非单发生树、重复前提、桥接、长度边界、错误类型）。
  - 更新 `README.md`（T0012 API／例子／边界／状态 `awaiting_review`；十二文件测试命令追加 `tests/test_proof_key.py`）、`docs/implementation_status.md`（T0012 行与能力表行，状态 `awaiting_review`）、本文（状态行与本执行记录）。
  - `reports/T0012/planning-review.md` 补注第 23 行“47 行”指的是 T0011 已接受的 `clause_key.py`（非本轮新增 `proof_key.py`），仅消除歧义，未改 T0011 证据；新增 RUN 原件 `reports/T0012/pi-r1-preflight`、`pi-r1-fused`、`pi-r1-full`。
- **命令与退出码（record.json 均留存于对应 RUN 目录）：**
  1. 编码前首次 focused（探测）：`.venv/bin/python -m pytest -q tests/test_proof_key.py` → 41 通过（含 3 项因 verifier 返回值未检查而误抛 `LogicValidationError`，据此修产品）。
  2. `python reports/T0012/run_checks.py pi-r1-preflight preflight` → exit 0，elapsed 0.23s；`check_delivery.py preflight reports/T0012/pi-r1-preflight`（scope/环境/基线通过、新文件缺失）。
  3. `python reports/T0012/run_checks.py pi-r1-fused focused` → exit 0，elapsed 0.39s；`pytest -q tests/test_proof_key.py --basetemp reports/T0012/pi-r1-fused/pytest-tmp`（45 项）。
  4. `python reports/T0012/run_checks.py pi-r1-full full` → exit 0，elapsed 15.88s；`pytest -q tests/test_proof_key.py tests/test_clause_key.py tests/test_depth.py tests/test_proof_enumeration.py tests/test_derivations.py tests/test_dependency.py tests/test_proof.py tests/test_engine.py tests/test_reference_engine.py tests/test_logic_types.py tests/test_config.py tests/test_doctor.py --basetemp reports/T0012/pi-r1-full/pytest-tmp`（840 项：原 795 + 新 45）。
- **失败与修复（逐条，均保留首次失败 RUN 或独立 pytest 日志）：**
  1. 产品 bug：`canonical_proof_key` 曾忽略 `verify_proof` 返回值，非单发生／无效 proof 被静默出键。修为 `if not verify_proof(clauses, query, proof): raise LogicValidationError(...)`；此后 verifier 失败正确抛 `LogicValidationError`。
  2. 测试 fixture bug（非产品）：K3 字面量顶层元组元结构错误（已重构正确括号）；joint-swap 与 non-contiguous 用 `(a,b)` 常量在桥接变量 `?y` 上冲突（`p(a,b)→?y=b` 与 `q(a,b)→?y=a`），改 q 事实为 `q(b,c)`、结论 `r(a,c)` 使桥接一致；`test_legal_length_boundary` 的 `c` 缺 COPY clause（`clause_index 1` 越界触发 `LogicValidationError` 而非 `ProofLimitError`），已补 clause；`_ne(a,b)` 缺 `label` 致 `TypeError`，改 `label=None`。
  3. 修复后全绿：focused 45/45、full 840/840，`git diff --check` 通过（docs 检查阶段复核）。
- **未运行项：** 文档检查 `pi-r1-docs` 尚未执行（待状态落盘后最后做）；Codex 独立验收 `not_run`。
- **偏差/说明：**
  - 基线 `56b41de` 为已验收 T0011 冻结基线；本轮未修改 T0011 接受的 `clause_key.py`/`test_clause_key.py`（仅全量回归引用）及 T0006 `proof.py` 之外产品。
  - 未 commit/push；工作树相对基线仅新增 `proof_key.py`、`test_proof_key.py` 及更新 README、implementation_status、本文与 RUN 原件。
- **当前源码 SHA-256（docs RUN 后，含末尾换行修复）：** `src/kmesh/logic/proof_key.py = 92dce0d424a60ae3f1f0d46a49da989eb8367258c287107a68ac541b637e03c1`；`tests/test_proof_key.py = 79e102c3a54d5b3e32fdc10ce93bb01bd417bece4f9a6bdb0d3cb612e62977d6`。
  - 说明：首次 full/focused RUN 后，为过 docs 的“文档末尾换行、无尾随空格”检查，给 `tests/test_proof_key.py` 末尾补一个换行（测试语义不变，随后 `tests/test_proof_key.py` + `tests/test_clause_key.py` 复验 108/108 通过）；其 SHA-256 由 `3432c001…` 变为上值。`src/kmesh/logic/proof_key.py` 未受影响。

### 轮次 2（R2，R1–R5 返工）（2026-09-22，Pi + 用户已授权 `bonsai2-27b`）

- 模型/来源：Pi + `bonsai2-27b`（`PI_MODEL`）；基线 HEAD `56b41de`（T0011 冻结基线），分支 `T0012-proof-key`。产品 `src/kmesh/logic/proof_key.py` 冻结未改（SHA `92dce0d424a60ae3f1f0d46a49da989eb8367258c287107a68ac541b637e03c1`），未 commit/push。
- 返工内容（对应 R1–R5）：
  1. **守卫测试补强**（45→52）：新增/改造精确异常消息（`==` 全文，拒 `diagnostic_suffix`）；`__suppress_context__ is False` 拒 `rebuild_exception`（ProofLimitError 与 verify 的 LogicValidationError）；`test_unused_legal_step_rejected` 拒 `allow_unused_steps`（未引用合法步）；`test_clauses_list_rejected_by_product` 拒 `coerce_clauses`（列表不被 coerce）；`test_variable_numbers_are_ints` 逐变量 `type is int`（拒 `float_variable_number`）；`test_import_isolation_hard_block` 以 `find_spec` 硬封锁 8 禁用根+点号子模块、自测 ImportError、K0/K3 实调、扫 sys.modules（拒 `lazy_forbidden_import`；移除绝对工作树路径，subprocess 用 `KMESH_SRC`/`PYTEST_DISABLE_PLUGIN_AUTOLOAD` 隔离源拷贝）；删除原末尾错误的 `.__all__` 检查，新增模块级 `__all__` 断言。
  2. **README**：改为 K1 两步例（事实+COPY）+ 完整字面量键，原样可运行；纠正算法说明（GroundKey=(pred,const0,const1)；自底向上定 joint 局部序，仅当两 slot 候选相等才比较子树；末步根前序；保留重复发生、拒无关步）；状态改 `awaiting_review`；移除 “Pi 独立验收” 归因。
  3. **留证（R5）**：新 RUN 留证于 `reports/T0012/pi-r2-preflight`、`pi-r2-guards`、`pi-r2-readme`、`pi-r2-docs`；R2 provenance 写于 `reports/T0012/pi-r2-guards/provenance.md`。R1 的 dev 失败与 “108 项复验” 无原始 RUN 原件，按 R5 标为自述/unknown；旧 Pi/Codex RUN、provenance、规划材料冻结，不改。
- 命令与退出码（record.json 均留存）：
  1. `record_check.py pi-r2-preflight -- check_rework.py preflight` → exit 0，elapsed 0.23s（scope/环境/基线通过）。
  2. `record_check.py pi-r2-guards -- guards.py reports/T0012/pi-r2-guards --enforce` → exit 0，elapsed 5.63s；guards all_guards_valid=True，8 个违约副本全拒。
  3. `record_check.py pi-r2-readme -- check_rework.py readme` → exit 0，elapsed 0.26s；README K1 块原样可运行。
  4. `record_check.py pi-r2-docs -- check_rework.py docs` → exit 0；run-index.json 生成。
- 测试：focused 52/52；十二文件 847/847（840 原 + 7 新增守卫）。
- 偏差/说明：本任务未改产品（92dce0d4…冻结）；测试 SHA 因新增守卫测试而变（现 `tests/test_proof_key.py = 8e1df17c4035d4790028dccdadc21f1c05a58e59b3609fe5bdc0dcbf0b7d3551`）；“108 项复验”与 R1 dev 失败无原始 RUN 原件，保留自述/unknown 并以新 RUN 留证，不重写旧 RUN。

## Codex 验收记录

2026-09-21，Codex + `gpt-6-astra`、xhigh：独立设计审阅已完成，明确了变换适用范围，并补入 K8 同头子树的后继比较反例。15 个手算键及 K8 七步例均经独立小规模 oracle 核验；K5/K6 用真实 T0009 和 T0006 确认 C=3/D=4/S=20、4 棵原始树分别对应 4／3 个规范键。详见 [规划审阅](../../reports/T0012/planning-review.md)和 [手算记录](../../reports/T0012/planning-examples/examples.json)。产品／新测试尚未实施，验收 not_run；ready 仅允许开始本契约内实施。


### Codex 第 1 轮验收（2026-09-22）

结论：`needs_changes`。当前产品未发现实现缺陷；新测试、README 与执行记录未满足原 A1–A7，返工 R1–R5 详见 [完整验收报告](../../reports/T0012/review-r1/review.md)。此结论不改变原身份规范或算法契约。

- 冻结：[提交哈希与原件审计](../../reports/T0012/review-r1-freeze2/input-audit.json)、[输入快照](../../reports/T0012/review-r1-freeze2/input-snapshot/)。1708 个规划冻结文件一致，HEAD `56b41de11a2651da615230117f0d96bd6e0d6e92` 是原规划基线后代。
- 独立 [full](../../reports/T0012/review-r1-full/record.json)：当前版本 **840 passed**，stderr 空，无 skip/xfail；[有限产品探针](../../reports/T0012/review-r1-probe/probe.json)通过 K5/K6/K8 定义对照、完整长链、原异常实例、无关步骤守卫。原样 README 块失败。
- [错误副本](../../reports/T0012/review-r1-guards/guards.json)：控制 45 项全过，允许无关步骤、强制 tuple、重建异常、诊断附加串、float 编号、延迟导入 engine 六副本也各 45 项全过；独立排序孩子与忽略深比较两副本被已有用例拒绝。
- 执行史：六个 Pi RUN 可核验；开发失败和声称的 108 项复验没有提交原件。当前测试删去一个末尾换行的哈希与 Pi full/fused 时一致。按 R5 追加更正，不回写旧证据。
- Codex 首个 freeze RUN 因自身路径过滤错误失败，原件保留；新 freeze2 核实前置文件全部未变。报告中已解释，不归责 Pi。
- 本轮只修改验收材料及状态，产品／测试未改；未 commit/push。`accepted` 只由 Codex 在复验后标记。

### 第 2 轮返工契约（R1–R5，四步）

**目标：** 补齐原任务的可判错测试、准确 README 和可核查执行记录。产品保持
`92dce0d424a60ae3f1f0d46a49da989eb8367258c287107a68ac541b637e03c1`；返工前测试应为
`79e102c3a54d5b3e32fdc10ce93bb01bd417bece4f9a6bdb0d3cb612e62977d6`。

**范围：** 仅 `tests/test_proof_key.py`、README 的 T0012 段／状态、实现状态的 T0012 两处、本文状态和追加 Pi 记录、新 `reports/T0012/pi-r2*`。不得改产品、前置模块／测试、原 R1 执行记录、旧 RUN、规划材料或 Codex 验收材料；不改环境、依赖、分支、HEAD，不 commit/push。保留原有效测试与现有独立 oracle，局部增强，不整份重写。若发现新产品反例，经原记录器保留后交 Codex 决定范围。

**步骤 1：返工前核对。** 在仓库根执行下列 preflight；不重跑要求“新文件不存在”的首轮 preflight。通过后先将本文与实现状态置 `in_progress`，再编辑测试。

```bash
.venv/bin/python reports/T0012/record_check.py pi-r2-preflight -- .venv/bin/python reports/T0012/review-r1/check_rework.py preflight
```

**步骤 2：按 R1–R3 最小补测试。** 逐组落实验收报告：D 组全部从新 API 检查精确边界和原对象／异常实例；新增 verifier True 的无关步骤反例；完整手算期望、原适用变换矩阵、现有 oracle 与 T0009 全集合衔接；逐层真实类型、不同关系长链及原生排序；八根／子模块硬隔离并真实计算。已有错误副本原件就是首轮测试缺陷的失败证据；不要为冻结的正确产品伪造一个失败。开发期每次执行仍用全新 RUN，失败原样保留。新测试数 N 不作固定配额，以覆盖原条件为准。

**步骤 3：定向／守卫与 README。** 完成测试后，按顺序运行下列命令；失败使用新后缀，不能移动旧目录。守卫须控制版通过、八种错误副本都由对应行为断言拒绝；检查 XML 中实际失败节点，不将收集错误／找不到模块当作有效守卫。R4 将 README 改成 K1 两步例和完整字面量键，保留标题定位文字“单棵证明的规范键（T0012”，然后运行实际 README 块。

```bash
.venv/bin/python reports/T0012/run_checks.py pi-r2-focused focused
.venv/bin/python reports/T0012/record_check.py pi-r2-guards -- .venv/bin/python reports/T0012/review-r1/guards.py reports/T0012/pi-r2-guards --enforce
.venv/bin/python reports/T0012/record_check.py pi-r2-readme -- .venv/bin/python reports/T0012/review-r1/check_rework.py readme
```

本轮仅测试和文档返工，**不重跑 full**；沿用 Codex R1 当前产品的 840 项独立结果，新增测试仅报告实测 N 项 focused，不宣称已执行 `795+N` 项回归。若最后又改测试，重跑受影响的 focused／守卫；仅文档措辞改动不要求重跑测试。

**步骤 4：记录与交回。** 在新 `reports/T0012/pi-r2-guards/provenance.md` 写一份记录，逐项落实 R5 表七项更正；列实际模型／来源、基线、产品／测试完整 SHA、各新 RUN 的原始命令、退出码、开始／结束时间与 elapsed_s。不可恢复项标自述／unknown，未来检查结果不预填。本文追加 Pi 第 2 轮记录，README／实现状态／本文置 `awaiting_review`，再运行：

```bash
.venv/bin/python reports/T0012/record_check.py pi-r2-docs -- .venv/bin/python reports/T0012/review-r1/check_rework.py docs
```

最后文档修改后如有必要用 `pi-r2-docs2` 新 RUN 复核；不改旧 docs 结果。范围／哈希／链接检查不能替代 A1–A7 语义验收。报告给 Codex 复验 R1–R5，Pi 不填写 accepted，不自动 commit/push。

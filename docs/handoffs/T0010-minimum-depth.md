# T0010：单查询的最短证明深度

## 任务信息

- 任务编号／修订号：T0010 / r1，2026-09-19。
- 状态：`accepted`（2026-09-20，Codex 第 3 轮复验通过，R1–R4 全部关闭；接受哈希与历史限制见文末）。
- 所属阶段／协议：M1 / E0-D；研究计划 v0.1.2、E0 `e0_v2` §4.3–4.5／§15.1；工程约定 D28。不改研究协议或深度分组配额。
- 规划者／验收者：Codex + `gpt-6-astra`，`xhigh`；执行者：Pi + `qwen3.8-coding-27b`。开工记录实际完整别名（此前 `qwen3.8-coding:27b-q8_0-64k`，ollama），不自行换模型。
- 基线：`153295c28788f27ef37e794c7c0ea19841accaa8`，已提交并推送 `origin/T0009-proof-enumeration`，规划起点工作树干净。**master 仍落后，须从本基线新建 `T0010-minimum-depth`，保留 Codex 本次规划改动。** 若只多出本次规划提交，核对冻结文件后记录实际 HEAD 继续；其他相关变化先反馈，不回退。
- 前置：[T0003](T0003-logic-types.md) 内容类型、[T0008](T0008-ground-derivations.md) 直接推导、[T0009](T0009-proof-enumeration.md) 原始证明树、[T0006](T0006-proof-verifier.md) 独立 verifier 均已验收。后两项只用于测试对照。既有 **679 项**独立回归来自 [T0009 第 2 轮](../../reports/T0009/review-r2/)，本轮规划不重跑。
- Codex 已有改动：本文、`reports/T0010/` 规划／检查材料、D28、T0009 当前提交绑定及后续关联、实现状态；不记为 Pi 产品实现。
- 规划审阅：[planning-review.md](../../reports/T0010/planning-review.md)。`reports/T0010/planning-files.json` 冻结本次规划材料、decisions 和 T0009 关联文档；清单自身不作自引用哈希，也禁止 Pi 修改。README、实现状态、本文的授权状态／记录更新不列入冻结清单。
- 必读：[AGENTS](../../AGENTS.md)、[研究计划 §4.3](../../KMesh_Research_Plan_v0.1.md)、[D26–D28](../decisions.md)、[derivations.py](../../src/kmesh/logic/derivations.py)、[types.py](../../src/kmesh/logic/types.py)、本文。测试对照另读 [proof.py](../../src/kmesh/logic/proof.py) 和 [proof_enumeration.py](../../src/kmesh/logic/proof_enumeration.py)。

## 目标、范围与交付物

**单一目标：给定无环世界和 ground query，返回它最少需要的推理层数；完整检查后仍无法推出时返回 `None`。** 用于以后按计划的深度 1–3／压力深度 4–5 分组。事实为 0；不限制输入深度，不在本任务生成或分桶数据。

| 允许 Pi 修改的路径 | 交付 |
|---|---|
| `src/kmesh/logic/depth.py`（新增） | 唯一公开函数 `minimum_proof_depth`，必要私有辅助函数 |
| `tests/test_depth.py`（新增） | 手算深度／预算、接口边界、证明对照、长链、隔离 |
| `README.md`、`docs/implementation_status.md` | 简短 API、可执行使用例、完整测试命令及真实状态／限制 |
| 本文 | 仅头部状态及追加 Pi 执行记录，不改契约或 Codex 记录 |
| `reports/T0010/` 下全新 `pi-*` 目录 | 每次检查原始记录、必要脚本、成功 full RUN 中的 provenance |

冻结其他源码／测试、`logic/__init__.py`、研究计划、AGENTS、decisions、旧任务及所有历史证据；Codex 本次规划文件和检查器也冻结。**不实现**证明身份／规范化、唯一性、motif／family／world 审计、生成器、深度分桶、批量查询 API、CLI、模型或训练。无需新数据类型、新异常、新依赖、新预算或返回证明见证。

## 前提与假设

- [planning-baseline.json](../../reports/T0010/planning-baseline.json) 已核对已接受 T0009 源码／测试哈希、Python 3.13.9、editable kmesh 0.1.0、pytest 8.4.2；新模块和测试尚不存在。使用 `.venv/bin/python -m pytest`，不假设有 `.venv/bin/pytest`。
- 内容对象由正常构造器创建；不处理绕过 frozen 的伪造对象。沿用一般二元、0–2 前提、head 变量在 body 绑定的 Horn 语义，不只接受四个生成模板。
- T0008 的完整记录按关系依赖排序；某条记录的每个 ground 前提，其全部来源已处理。独立前提的证明可自由组合，因而 `min(所有组合的 max 深度) = max(各前提的 min 深度)`。这是本任务递推成立的依据，不能把“第一条来源”当最短来源。
- `None` 只表示此有限世界完整枚举后的不可推出；异常／超限不能变成 `None`。反事实负例的评估深度桶仍由其配对正例给出，本 API 不推定负例桶。深度仅用于离线审计，不进入模型 token、embedding、路由、forward/predict。
- 测试仅用 CPU 和仓内手造数据，无网络、下载、外部／锁定研究数据或训练。记录器隐藏 CUDA，不把 cpu_only 写成机器无 GPU。
- 每个记录命令墙钟上限 120 秒，自检命令累计预算 10 分钟。超时／超预算或契约冲突留证反馈，不静默删例、降标准、扩预算。这里的执行预算不构成训练成本结论。

## 具体实施步骤

### 1. 先核对起点，再开始编码

按“验证方法”建分支并运行 preflight：新文件须不存在、旧文件及检查器哈希一致。成功后**先把本文和实现状态中的 T0010 改为 `in_progress`**，再实施。中断后读已落盘内容，从小段继续；不要整文件重写。

### 2. 固定公开接口与校验顺序

```python
def minimum_proof_depth(
    clauses: tuple[Clause, ...],
    query: Atom,
    *,
    max_fact_checks: int = 100_000,
    max_derivations: int = 100_000,
) -> int | None: ...
```

`__all__ = ["minimum_proof_depth"]`。产品只从标准库、`kmesh.logic.types`、`kmesh.logic.derivations.enumerate_derivations` 导入。建议按名导入该函数，让调用契约测试 patch `kmesh.logic.depth.enumerate_derivations` 这个真实调用位置。不得导入／调用 proof、proof_enumeration、两条 closure solver、torch、yaml；不重写匹配／绑定逻辑、无 I/O、无全局可变缓存。

入口严格依下表校验，抛已有 `LogicValidationError`。外层 tuple、Clause、Atom 用 `isinstance`；预算须 `type(value) is int and value > 0`。`T` 为 `type(value).__name__`，不打印未校验值的 repr／str。

| 顺序 | 非法条件 | 完整诊断 |
|---|---|---|
| 1 | clauses 不是 tuple | `depth.clauses must be a tuple of Clause; got T` |
| 2 | 从左起首个成员不是 Clause | `depth.clauses[i] must be a Clause; got T` |
| 3 | query 不是 Atom | `depth.query must be an Atom; got T` |
| 4 | query 含变量 | `depth.query must be a ground Atom` |
| 5 | max_fact_checks 不满足非 bool 正整数 | `depth.max_fact_checks must be a non-bool positive integer; got T` |
| 6 | max_derivations 不满足非 bool 正整数 | `depth.max_derivations must be a non-bool positive integer; got T` |

非 tuple 的生成器不消费一次；合法超大正整数预算接受，无额外最大值。缺必填参数／多余关键字仍由 Python 抛普通 `TypeError`。

全部本层校验完成后，**恰好调用一次** T0008，传入原 clauses 和两项原值预算。它的环检查及 `LogicValidationError`／`DerivationLimitError` 原样传播。包括 query 为事实、不存在、世界有无关分量时，都必须先成功完成全世界枚举；不能提前返回已知 0、已有深度或 `None`，不能只枚举 query 相关世界。

### 3. 单遍迭代计算最短深度

对 T0008 返回的记录按原顺序扫描，维护 **完整 ground Atom → 最小整数深度** 的局部字典：

1. 零前提记录的候选深度为 0。
2. 非空前提记录的候选深度为 `1 + max(此前已完成的各前提最小深度)`。依赖 DAG 保证这些键存在；用正常字典读取，不为缺前提编造默认 0、重试或吞错。
3. 若结论尚不存在，存候选；否则只保留新旧较小值。不能用真假值区分已有 0 与缺失，不能只保留第一条／最后一条来源。
4. 扫描完整个记录序列后返回 query 的深度；未出现返回 `None`。有结果须 `type(result) is int`，包括 0，不能返回 `False`。

不排序／重新枚举记录，不迭代到不动点，不递归，不展开完整证明树，不按证明步数或拓扑位置估深度。输入不变，多次调用结果一致；前一调用或异常不能污染后一调用。

新增 DP 时间为 O(R)、辅助空间 O(A)，R 是直接记录数，A 是其中不同 ground Atom 数。**完整 API 仍承担 T0008 的匹配时间及 R 条记录存储**，不能声称总流程线性或只用 O(A) 总空间。不设墙钟性能门槛；本项用算法审阅和下列结构用例检查。

### 4. 按具体例子写测试

下表中 `Fp` 表示事实 `p(a,b)`；`p→q` 是 `p(?x,?y)→q(?x,?y)`；`(p,q)→r` 两前提参数均为 `(?x,?y)`；方括号内是**输入 clause 顺序**。预算 C/D 是 T0008 全世界实际消耗，不是本层深度。调用时传 `max(1,C)`／`max(1,D)`。

| 例 | 输入与 query | 期望深度 | C / D |
|---|---|---|---|
| H0 | `[]`，`q(a,b)` | `None` | 0 / 0 |
| H1 | `[Fp]`，分别问 `p(a,b)`／`p(b,a)` | 0／`None` | 0 / 1 |
| H2 | `[Fp,p→q]`，`q(a,b)` | 1 | 1 / 2 |
| H3 | `[Fp,Ft,p→u,u→v,t→w,(v,w)→z]`，`z(a,b)` | 3；两前提深度 2、1，不能取 sum 或 min | 5 / 6 |
| H4 | `[Fp,p→m,m→q,p→q]`，`q(a,b)` | 1；原始证明深度依次 2、1 | 3 / 4 |
| H5 | H4 末尾加 `q→z`，`z(a,b)` | 2；后来捷径也影响下游 | 4 / 5 |
| H6 | `[Fp,p→q,Fq]` 与 `[Fp,Fq,p→q]`，均问 `q(a,b)` | 两者都是整数 0 | 1 / 3 |
| H7 | `[Fp,(p,p)→q]`，`q(a,b)` | 1；重复槽位不累加深度 | 2 / 2 |
| H8 | `[p(a,b),p(b,c),p(?x,?y)∧p(?y,?z)→r(?x,?z)]`；`r(a,c)`／`r(c,a)` | 1／`None` | 6 / 3 |
| H9 | `[q(a,b),p(c,d),p→q]`，分别问 `q(a,b)`／`q(c,d)` | 0／1；不能仅用谓词作键 | 1 / 3 |
| H10 | `[p→q]`，`q(a,b)` | `None` | 0 / 0 |
| H11 | `[Fq,Fp,p→u,u→v,v→z]`，分别问 `q(a,b)`／`missing(a,b)` | 0／`None`，仍耗完整世界预算 | 3 / 5 |
| H12 | `[Fa,Fb,Fc,Fd,a→m,m→n,n→z,(a,b)→u,(c,d)→v,(u,v)→z]`，`z(a,b)` | 2；长度 4／深度 3 的链和长度 7／深度 2 的树并存 | 9 / 10 |

18 个 query fixture 及 C/D 已用既有模块核对，见 [手写规划例](../../reports/T0010/planning_examples.py) 和 [运行结果](../../reports/T0010/planning-examples/)。**Pi 在新测试中独立写出输入及期望，不 import 规划脚本或旧测试来共享 fixture／答案。** 对 `None` 用 `is None`；成功整数除相等外检查准确类型。

新测试至少覆盖以下七组，参数化可用但不能只断言“某异常”：

- **A，手算语义与预算：** 上述全部例子。H3/H4/H11/H12 分别检查 C、D 刚好够完成和少 1 时的已有异常类型／完整消息；另一预算保持足够。H11 对存在／不存在 query 都检查超限，防早退。成本 0/1 无合法更小正预算，不伪造 0 为“超限测试”。另给事实 query＋无关自环、缺失 query＋无关自环、无事实循环，均应原样抛 `dependency.clauses: cyclic predicate dependency`。
- **B，不变性与调用独立：** 在 H5/H8/H12 上分别做 clause 逆序、两前提交换、实体与谓词分别双射改名（query 同改）、逐条规则变量局部改名；结果相等。添加重复 fact／rule 不改深度；预算使用默认充足值，不假设交换前提后的 C 不变。调用前后保存 clauses 相等／hash；先超限或非法调用再合法调用仍返回正确结果。
- **C，入口诊断：** 非 tuple 的 list／None／有消费标记的 generator，tuple 中非法成员，query 类型及非ground，两个预算各含 bool／0／负数／float／str／None。构造其他参数为合法值，每例比较完整诊断。至少检查“坏成员先于 query”“非ground query先于预算”“C先于D”“非法D先于世界环”的优先级；普通 Python TypeError 仍正常。用调用哨兵证明非法输入未调 T0008，并在真调用位置 patch，不能只看最终异常。
- **D，大整数安全：** `10**5000` 通过工厂／函数体生成，短参数 ids；fixture 把 Python int→str 上限局部固定为 4300，finally 恢复。大正整数作为 clauses／成员／query 均只报相应字段与 `got int`；负巨整数作每个预算均按契约拒绝；两预算同时为巨正整数时 H2 正常得 1。不对巨整数作 repr／字符串 ID。
- **E，调用边界：** patch 产品实际调用的 T0008 名称，用真实包装确认成功／空结果各调用一次、clauses 为原对象、两预算不变；用抛既有异常实例的哨兵确认两类异常身份 `is` 和消息均原样传播。不得把模拟返回错误顺序的记录当合法前置；本任务不负责重检 T0008 内部契约。
- **F，已验收证明对照：** 使用下文固定 16 个小世界×4 query。真实 `enumerate_proofs` 得到所有原始树，每条真实 `verify_proof` 必须 True，再按步骤引用在独立列表计算树高，取最小；空 tuple 期望 None。新 API 与此相等。不要拿 `len(proof)-1` 或旧 API 返回数当高度。对照与产品共享 T0008，仅是不同深度计算路径，不能称完全独立的推导完整性证明；手算 A 组必须保留。
- **G，规模与隔离：** 事实 `p0(a,b)`＋1200 个依次 COPY，C=1200/D=1201，期望 1200，不改递归上限。另构造 16 层、每层同一 COPY clause 重复两次（1 fact＋32 rules），C=32/D=33，期望 16；不展开其 65,536 棵原始树。干净子进程用 meta_path finder 在 `find_spec` 拒绝六根及点前缀子模块：`torch`、`yaml`、`kmesh.logic.engine`、`kmesh.logic.reference_engine`、`kmesh.logic.proof`、`kmesh.logic.proof_enumeration`；逐根 import 自检确实抛 ImportError，然后 import 新模块并构造 fact／COPY／JOIN 成功，扫描 sys.modules 无禁用模块。父进程测试使用 verifier 的合法导入不能污染此干净子进程；`logic/__init__.py` 保持零导入。

F 组精确构造（确定性遍历 `mask in range(16)`，不用随机 seed）：基础 clauses 依次为 `p(a,b)`、`q(b,c)`、`p(?x,?y)∧q(?y,?z)→r(?x,?z)`。按 bit 从小到大追加：bit0 再加一个 `p(a,b)`；bit1 加事实 `r(a,c)`；bit2 加 `p(?x,?y)→s(?x,?y)` 及 `s(?x,?y)→r(?x,?y)`；bit3 加 `r(?x,?y)→t(?y,?x)`。各世界查询固定为 `r(a,c)`、`r(a,b)`、`t(c,a)`、`t(a,a)`；两路径都用 C=1000/D=100，T0009 另用 S=100000。必须覆盖这 64 个比较，不把超限／异常当 None；这些小世界不是正式研究数据。

### 5. 自检与最小文档更新

首次开发检查起一律走记录器，失败用新 RUN 留存后再修改。focused 成功后只需一次 full 成功；产品或测试随后有实质改动才重跑相关项。README 提供 H4 小例 `minimum_proof_depth(...)=1`，且新测试明确覆盖同一输入；更新测试命令为下列十文件顺序。说明 0、None、超限与“独立给定证明验证／完整证明枚举／规范唯一性”的边界，保留未完成事项。

### 6. 写完记录后交回

在成功 full RUN 内写 `provenance.md`：完整模型别名、实际 HEAD／分支、变更及源码哈希、所有尝试和修复、每个 RUN 真实命令／退出码／耗时、当前结论与永久历史限制。时间取 record.json，elapsed_s 和起止时段分别命名。没有原件只写自述／unknown，不补造。

本文追加 Pi 记录并与实现状态置 `awaiting_review`，再跑最后 docs 检查。**不为回填 docs 自身结束时间反复改写 provenance**；可在交接引用最终 RUN 路径，记录器保存真实时间。冻结 diff 等待 Codex；不 commit/push、不自动进入后续任务。

## 验证方法

工作目录 `/home/mye/src/llm/KMesh`。先建分支，不移动任何既有 RUN：

```bash
git switch -c T0010-minimum-depth
.venv/bin/python reports/T0010/run_checks.py pi-r1-preflight preflight
```

此时新模块／测试必须尚未写入；如时序出错如实留存并反馈，不能删文件假造初始状态。preflight 成功后落盘 `in_progress` 再编码。

本次提供 [run_checks.py](../../reports/T0010/run_checks.py) 固定入口；它调用原样沿用的 [record_check.py](../../reports/T0010/record_check.py)，**自动给 pytest 添加 `--basetemp reports/T0010/RUN/pytest-tmp`**。不要改写命令或手工拼环境前缀，不串接 doctor。

```bash
.venv/bin/python reports/T0010/run_checks.py pi-r1-focused focused
.venv/bin/python reports/T0010/run_checks.py pi-r1-full full
.venv/bin/python reports/T0010/run_checks.py pi-r1-doc-check docs
```

- focused 仅跑 `tests/test_depth.py`；full 精确顺序为 `test_depth.py`、`test_proof_enumeration.py`、`test_derivations.py`、`test_dependency.py`、`test_proof.py`、`test_engine.py`、`test_reference_engine.py`、`test_logic_types.py`、`test_config.py`、`test_doctor.py`（均在 tests/）。预期全过、无 skip/xfail，full 为 **679＋新增测试数**；不要预先编造最终总数。
- preflight 核对分支／环境／冻结哈希／范围／新文件未生成；docs 调用 [check_delivery.py](../../reports/T0010/check_delivery.py) 检查范围、冻结文件、文档链接、文本卫生、awaiting_review，不替代产品验收。
- 四个最终检查都须 exit 0。每次尝试是新目录；例如首 focused 失败原件保留，下次用 `pi-r1-focused-dev2`，成功记录直接可交付，不为凑原名移动／覆盖。记录中写真实成功 RUN 名。
- 开发定向 pytest 也可用上述 focused 入口配新 RUN；任意额外探针必须用 `.venv/bin/python reports/T0010/record_check.py NEW_RUN -- COMMAND ...`。直接 pytest 时自己提供与该 RUN 对应的独占 basetemp。不要预建 RUN 目录、用它承接外层 shell 重定向或嵌套引号复杂的 `-c`；必要脚本先放全新 `pi-*-scripts/`。
- 记录器每次保存 argv、前后源码 hash／HEAD／分支／工作树、环境覆盖、stdout／stderr 原文与 hash、退出码、超时及 elapsed_s。不得删、清空、移动或覆盖失败／成功 RUN；`pytest-tmp/` 是唯一任务级 scratch 忽略项。尚未发生的检查写 not_run，不据此声明通过。

## 验收标准

- [ ] **A1 接口／输入：** 公开导出、默认值、返回类型及诊断／优先级完全一致；生成器不消费，大整数安全，非法输入无下游调用。
- [ ] **A2 最短深度：** H0–H12 所有 query 结果正确，fact=0、不可达=None，较晚捷径、两前提最大值、不同 ground 参数、短步骤与浅层数区别都有有效断言。
- [ ] **A3 完整性／预算：** T0008 只调一次、预算和异常不变；事实／不存在 query 仍受全世界环和预算约束；精确／少一边界有效，无部分结果。
- [ ] **A4 算法／规模：** 单遍迭代的 Atom 深度 DP，无递归／完整证明展开／反复全扫／全局状态；1200 长链和 16 层重复来源通过，复杂度措辞限定新增 DP。
- [ ] **A5 测试可信：** 手算独立期望、不变性、64 次真实证明对照及 verifier、隔离自检可核查；对照共享 T0008 的限制明确，测试不被更早失败遮蔽或只有字段没有原因。
- [ ] **A6 回归／范围：** 十文件完整回归通过，旧 679 项不改；仅授权路径，既有源码／历史报告／规划文件冻结；无额外依赖、模型输入或训练操作。
- [ ] **A7 交付证据：** 原始尝试不覆盖，前置检查先于编码，独占 basetemp，状态／README／provenance真实一致；未归档历史只作明确限制，不补造。研究计划中的完整数据审计仍未完成。

## Pi 执行记录

### 第 1 轮（2026-09-19，Pi 代理 + `qwen3.8-coding-27b`，ollama）

- 分支 `T0010-minimum-depth`，基线 HEAD `153295c28788f27ef37e794c7c0ea19841accaa8`；未 commit/push；未改写旧 RUN。
- 实际改动（仅允许交付物）：新增 `src/kmesh/logic/depth.py`（SHA-256 `0361a37e…39bf5d`）、新增 `tests/test_depth.py`（`7ffa2fac…9ae470c`，**40 项**）；更新 `README.md`（T0010 节＋十文件测试命令＋当前限制）、`docs/implementation_status.md`、本文头部状态。
- 合同 RUN（均经 `record_check.py`，各自独占 basetemp／证据目录）：

| RUN | exit | 关键结果 |
|---|---|---|
| [pi-r1-preflight](../../reports/T0010/pi-r1-preflight/) | 0 | 分支／冻结基线／环境／范围；新文件未生成（产品编写前） |
| [pi-r1-focused](../../reports/T0010/pi-r1-focused/) | 0 | **40 passed**（`tests/test_depth.py`） |
| [pi-r1-full](../../reports/T0010/pi-r1-full/) | 0 | **719 passed**（既有 679 ＋ 新 40），stderr 空 |
| [pi-r1-docs](../../reports/T0010/pi-r1-docs/) | 1 | 首跑缺 provenance（预期内），失败先留存 |
| [pi-r1-docs2](../../reports/T0010/pi-r1-docs2/) | 0 | 范围／冻结文件／4 文档 72 本地链接／文本卫生／awaiting_review 全部通过 |
| [pi-r1-docs3](../../reports/T0010/pi-r1-docs3/) | 0 | 本表补记 docs3 行前的最终重跑，全部通过 |

- 失败与修复（开发期）：见 [pi-r1-full/provenance.md](../../reports/T0010/pi-r1-full/provenance.md)（预算默认值不足、周期断言方向、DLE 预算取值三处理解错误，均只改测试文件，产品零改动）。
- 偏差／unknown／not_run：开发期 pytest 迭代直接以 `/tmp` 独占 basetemp 执行、未逐次走记录器（不主张原件级证据）；无合同项目 not_run。
- 交回状态：`awaiting_review`，请 Codex 按 A1–A7 验收；Provenance 见 [reports/T0010/pi-r1-full/provenance.md](../../reports/T0010/pi-r1-full/provenance.md)。

### 第 2 轮（2026-09-19，Pi 代理 + `qwen3.8-coding-27b`，ollama；开工别名 `qwen3.8-coding:27b-q8_0-64k`）

- 实际改动（仅允许交付物）：重写 `tests/test_depth.py`（R1 `7ffa2fac…9ae470c` 40 项 → 当前 `ddc238a6…111a2a` **53 项**）；更新 `README.md`（H4 后来捷径=1 使用例、十文件命令对齐驱动顺序、状态）、`docs/implementation_status.md`、本文头部状态；新增 `reports/T0010/pi-r2-*` RUN 与 [pi-r2-full/provenance.md](../../reports/T0010/pi-r2-full/provenance.md)。产品 `src/kmesh/logic/depth.py` 零改动（SHA-256 仍 `0361a37e…39bf5d`）。
- 按 R1 验收逐项补全：H0–H12 精确 C/D 与 `type(result) is int`／`None`；H11（C=2→CLE、D=4→DLE，双 query）与 H12（C=8→CLE、D=9→DLE）边界；`test_invalid_inputs_do_not_call_enumerator`（patch 真实调用位置、精确消息、零调用）；`test_large_integer_diagnostics`（4300 位限制 fixture 含恢复、短 ids 工厂）；异常实例身份 `is` 与原 clauses 同一 tuple 身份；非法 D＋环约定优先级；缺参／多余 keyword 的 TypeError；事实／缺失 query＋无关自环与无事实环用合法预算证明全世界环检查；重复 fact/rule 不改深度；异常后恢复；H5/H8/H12 五类变换（clause 逆序、前提交换、实体／谓词双射改名、规则内变量改名，query 同步改名）；E1 恢复 1200-copy 链 C=1200/D=1201（深度 1200）及少一边界，E2 改为 16 层 COPY 重复 C=32/D=33（深度 16，C/D 语义按 T0008 重读确认）；G 组重写为干净子进程 `find_spec` 硬阻断六根及点前缀、守卫自检、实际执行 fact/COPY/JOIN、全 `sys.modules` 扫描；F 组冻结 16×4 矩阵保留。开发期发现 E2 的 C/D 预算初读有误（误以为 T0008 记录去重），重读 `derivations.py` 后确认无记录去重，C=32/D=33 成立，未改契约。
- 自检（全部经记录器，墙钟上限 120s，累计远在 10 分钟预算内）：

| RUN | 命令 | 退出 | 结果 |
|---|---|---|---|
| pi-r2-preflight | `record_check.py pi-r2-preflight -- check_rework.py preflight` | 0 | 基线/产品/测试/旧证据与 review 文件哈希未变 |
| pi-r2-focused | `run_checks.py pi-r2-focused focused` | 0 | **53 passed**（0.29s），stderr 空 |
| pi-r2-guards | `record_check.py pi-r2-guards -- rework_guards.py reports/T0010/pi-r2-guards` | 0 | 5 变体 `guard_valid`：submitted 全过；`unchecked_integer_format`→`test_large_integer_diagnostics`、`invalid_input_calls_enumerator`→`test_invalid_inputs_do_not_call_enumerator`、`records_sorted_by_clause_position`→`test_depth_invariant_under_transformations`、`lazy_solver_import`→`test_g_depth_import_pulls_no_forbidden_modules` 各自失败 |
| pi-r2-full | `run_checks.py pi-r2-full full` | 0 | **732 passed**（679 既有＋53 新），stderr 空 |

- 偏差与限制：R2 开发期中段 pytest 未逐次走记录器（自述，同 R1 披露口径）；探针/临时脚本均在 `/tmp`；未 commit/push；最终 `pi-r2-docs` 在本文落盘后运行一次，其结果不回填本表（避免自引用，同 T0009 先例）。
- 交回状态：`awaiting_review`，请 Codex 按原 A1–A7 与 R1–R4 六点复验；Provenance 见 [reports/T0010/pi-r2-full/provenance.md](../../reports/T0010/pi-r2-full/provenance.md)。

## Codex 验收记录

规划核对见 `reports/T0010/planning-review.md`；已收到首轮产品，实际验收如下。

后续：先独立冻结规范证明身份及共享变量／前提交换／改名的正反例，再拆规范化实现与唯一性／motif 审计；完整 world 审计与正式生成继续在其后。T0010 不替这些步骤定义研究等价关系，不将 T0009 原始树数量当规范证明数。

### Codex 第 1 轮验收，2026-09-19

- **结论：needs_changes，R1–R4 待修。** Codex + `gpt-6-astra`，`xhigh`，非 Pi 作者；`/root/review_t0009_design` 只读复核原契约与测试，未改实现。
- [输入快照](../../reports/T0010/review-r1-freeze/audit.json)：HEAD `153295c28788f27ef37e794c7c0ea19841accaa8`，产品 SHA-256 `0361a37e8fbfcceb69ac55336c8578176ab96f1c94a86fa50a98aaa2a839bf5d`，测试 `7ffa2fac70a401eb6dcfa04691ea4294fa631bb738ea60a27674d9f6a9ae470c`。旧源码与规划哈希未变；7 个 Pi RUN 原件／哈希核对通过，未录制开发史仍不可核验。
- [独立十文件回归](../../reports/T0010/review-r1-full/) exit 0：**719 passed in 14.96s**，stderr 空，无 skip/xfail。[独立契约探针](../../reports/T0010/review-r1-probes/findings.json) 的手算／变换／巨整数／异常身份／实际导入隔离通过，未发现当前产品逻辑反例。
- [四种故意错误实现](../../reports/T0010/review-r1-mutations/findings.json) 却全部各自 **40 passed**：未校验先格式化、非法输入仍调用枚举、按 clause index 错序扫描、运行时导入 solver。真实提交源码与测试未改，故不接受当前回归保障。
- R1 输入／巨整数／调用边界，R2 变换／预算／规模，R3 硬隔离，R4 README 与记录更正；完整定位、验证及最小修复见 [review.md](../../reports/T0010/review-r1/review.md)。原 F 组64次对照有效，实际60棵树；README 的42已在当前状态撤下，旧快照保留。
- 任务未 accepted，未 commit/push。

### 第 1 轮返工要求：四步完成 R1–R4

本轮**产品 depth.py 冻结，不要求重写实现**。只允许修改 `tests/test_depth.py`、README、实现状态、本文状态／追加 Pi 记录，及全新 `reports/T0010/pi-r2*` 目录。旧 Pi/Codex RUN、旧 provenance、原规划和记录器、其余源码／测试全部冻结。如果补测试发现产品反例，先留存最小复现并反馈，由 Codex 判断后续范围。

1. **核对基线再开始。** 下列新 preflight 核对 HEAD、首轮产品／测试哈希、旧证据及 Codex review 文件。成功后把本文／实现状态置 `in_progress`，才编辑测试。不得复用原 preflight（它专供新文件不存在的阶段）。
2. **按原契约补测试（R1–R3）。** 依 review 逐项补全，保留有效手算／F组／生成器断言。为四个守卫固定测试函数名：`test_large_integer_diagnostics`、`test_invalid_inputs_do_not_call_enumerator`、`test_depth_invariant_under_transformations`、原 `test_g_depth_import_pulls_no_forbidden_modules`；可参数化。其余新测试名称自定。巨整数 fixture 恢复全局限制，隔离在干净子进程阻断六根及子模块、守卫自检并调用 fact/COPY/JOIN；恢复精确预算和约定 COPY。原产品预期通过这些正确契约用例，**不要求或伪造产品先失败**；开发测试写错也必须在新 RUN 留存后修改。
3. **验证新断言确实拒绝已知错误。** 先 focused，再下面给定 guards（当前产品的完整新测试须通过，四个副本各由指定测试失败），最后一次 full。guard 脚本不修改仓内产品／测试；变体副本在忽略的 RUN/pytest-tmp，原始结果与 guards.json 留存。不能改守卫脚本让外层通过，不能为凑40项删掉原有效测试。新增数以实际收集为准；full=679＋新测试文件当前项数。
4. **R4 更正与交回。** 按 review R4 的六点在新 full RUN 写 provenance（准确模型／时间／结果／更正／原件与自述边界）；README 使用原H4捷径=1，命令对齐十文件驱动，实际状态一致。旧provenance不回写。置 `awaiting_review` 后只跑一次最终 docs（失败则新RUN，不覆盖），不为回填其时间反复改写。冻结 diff 交回复验；不commit/push。

工作目录不变。以下 RUN 均未使用；失败保留原目录，再用新后缀，basetemp 自动跟随 focused/full 的 RUN。

```bash
.venv/bin/python reports/T0010/record_check.py pi-r2-preflight -- .venv/bin/python reports/T0010/review-r1/check_rework.py preflight
```

编辑完成后依序：

```bash
.venv/bin/python reports/T0010/run_checks.py pi-r2-focused focused
.venv/bin/python reports/T0010/record_check.py pi-r2-guards -- .venv/bin/python reports/T0010/review-r1/rework_guards.py reports/T0010/pi-r2-guards
.venv/bin/python reports/T0010/run_checks.py pi-r2-full full
```

以上外层均预期 exit 0；guards 内四个错误副本 exit 1 且由指定断言失败是预期，产品分支不能失败。每次开发检查也走新记录器 RUN，原十分钟自检命令累计预算沿用。

完成全部文档后：

```bash
.venv/bin/python reports/T0010/record_check.py pi-r2-docs -- .venv/bin/python reports/T0010/review-r1/check_rework.py docs
```

原 docs 检查器不包含本轮新增 Codex review 文件，故 R2 仅用 [check_rework.py](../../reports/T0010/review-r1/check_rework.py)。它核对最终review清单／历史／产品冻结以及新测试和文档的范围／链接／状态；不能替代实质验收。最终由 Codex 复核 R1–R4。

### Codex 第 2 轮验收，2026-09-20

- **结论：needs_changes；R3／R4 关闭，R1／R2 剩三处小修。** Codex + `gpt-6-astra`，`xhigh`，非 Pi 作者；`/root/review_t0009_design` 只读复核得出相同残留清单。
- 产品继续冻结为 `0361a37e8fbfcceb69ac55336c8578176ab96f1c94a86fa50a98aaa2a839bf5d`，本轮测试为 `ddc238a67816c94fee35b122f1690bc441bff657f2d5b5fc8b22047b0e111a2a`。HEAD 未变；[输入冻结](../../reports/T0010/review-r2-freeze/audit.json)核对115项旧材料／Pi原件，首轮review与规划不变。
- [独立守卫复跑](../../reports/T0010/review-r2-guards/guards.json)：当前53项通过、旧四个违约副本各被指定测试拒绝。Pi的732项全回归原件／哈希、stderr空已核对，本轮没有重跑旧679项。
- [补充探针](../../reports/T0010/review-r2-probes/findings.json)：只重建 LogicValidationError、交换 C/D 校验顺序、把 ground 检查移到预算之后，这三种违约副本仍各自53项全过；H8交换helper实际返回未改变的世界。当前产品未改，尚未发现产品逻辑反例。
- R3真实运行时隔离已完成；R4文档和历史归属更正成立，仍保留两轮未录制开发检查及模型历史映射unknown的限制。规模例的ground COPY特例满足本项规模目标，不另作返工理由。详见 [第2轮review](../../reports/T0010/review-r2/review.md)。未commit/push。

### 第 2 轮返工要求：仅三处最小修补

只允许改 `tests/test_depth.py` 中 `test_d2b_exception_instance_identity`、`test_c4_validation_priority`、`_swap_twin_premises`、`test_depth_invariant_under_transformations` 四个函数；另允许 README／实现状态／本文的当前状态与新增记录、全新 `reports/T0010/pi-r3*`。**产品、其余测试、原规划、全部旧RUN／provenance／Codex证据冻结。不整文件重写，不重开已关闭事项。**

1. **新preflight后落盘状态。** 核对当前产品／R2测试哈希、HEAD和全部历史，成功后本文与实现状态置 `in_progress`。
2. **按review的精确输入修补。** 异常哨兵改成 `LogicValidationError(DCE)`，断言对应异常类、`is`及完整DCE消息；恢复“非ground query＋c=0,d=-1”和“ground query＋c=0,d=-1”两种叠加错误（完整期望分别为ground错误、C预算错误，保留零调用断言）；交换helper只检查 `len(body)==2`，去掉args相等限制，并在变换测试显式断言H8末条body已经逆序且确实改变。保留全部其他断言与函数名，通常仍为53项。正确产品预期通过，不伪造产品失败。
3. **只跑给定新guards。** 它先跑当前完整定向套件；然后在隔离副本对三个产品违约版本及一个交换helper空操作版本，仅运行受影响的三个测试。原提交exit0，四副本exit1且由指定断言失败，外层exit0；原始输出全部保存。**无需额外focused、旧guards或全量732项**，不重复无关检查。若发现真实产品缺陷先留证反馈。
4. **记录后交回。** 新guard RUN内写provenance（全部尝试／修复、实际模型、哈希、真实命令时间、历史限制），更新README与两处状态并置 `awaiting_review`，再一次最终docs；旧记录不回写。不commit/push。

精确命令（工作目录不变，RUN均新；失败保留后换新编号，guard路径同步）：

```bash
.venv/bin/python reports/T0010/record_check.py pi-r3-preflight -- .venv/bin/python reports/T0010/review-r2/check_rework.py preflight
.venv/bin/python reports/T0010/record_check.py pi-r3-guards -- .venv/bin/python reports/T0010/review-r2/rework_guards.py reports/T0010/pi-r3-guards
.venv/bin/python reports/T0010/record_check.py pi-r3-docs -- .venv/bin/python reports/T0010/review-r2/check_rework.py docs
```

三条外层预期exit0。记录器与新脚本冻结；开发尝试同样用新RUN，不裸跑pytest、不覆盖失败。docs只在最终文档写好后执行，不为回填其时间再次修改。Codex下一轮只复核上述三处及相应证据。

---

### Pi 第 3 轮（R3）执行记录（2026-09-20）

实际工具／模型：Pi + `qwen3.8-coding-27b`；commit `153295c28788f27ef37e794c7c0ea19841accaa8`，分支 `T0010-minimum-depth`；产品冻结 `0361a37e…39bf5d`（三个 RUN 前／后均核）。

**修改文件：** 仅 `tests/test_depth.py`（四个指定函数）＋README／实现状态／本文状态与记录＋新 `reports/T0010/pi-r3*`。

**三处修补：**

1. `test_d2b_exception_instance_identity`：哨兵 `RuntimeError("sentinel-cycle")`→`LogicValidationError(DCE)`；`pytest.raises(RuntimeError)`→`pytest.raises(LogicValidationError)`；保留 `e1.value is cycle_error` 并新增 `assert str(e1.value) == DCE`；DerivationLimitError 分支未动。
2. `test_c4_validation_priority`：在既有 `assert calls == []`（保留）前新增两 case——`(fact("p"),)`＋非 ground query＋`c=0, d=-1` → `depth.query must be a ground Atom`；同世界 ground query＋`c=0, d=-1` → `depth.max_fact_checks must be a non-bool positive integer; got int`（C 先于 D）。
3. `_swap_twin_premises`：删除 `body[0].args == body[1].args` 限制（helper 名保留，只检查 `len(body) == 2`）；`test_depth_invariant_under_transformations` 在 H8 检查前显式断言交换后末条 body `== (旧 body[1], 旧 body[0])` 且 `!= 旧 body`。

**自检尝试与修复（诚实记录）：** 编辑阶段两次自身失误（H8 自检首稿写成无意义自引用断言；C4 编辑首稿误删其后的 `@pytest.fixture def capped_int_str_limit():` 定义行），均在任何录制 RUN 前发现并修正，`py_compile` 复核后才开始录制命令；开发自检 `pi-r3-dev1` 一次性通过（53 passed in 0.30s），无失败 RUN。

**R3 检查链（全部录制，失败若有以新后缀另存）：**

| RUN | 开始（UTC） | 命令 | 结果 |
|---|---|---|---|
| `pi-r3-preflight` | 2026-09-20T03:04:50.803572+00:00 | `record_check.py pi-r3-preflight -- review-r2/check_rework.py preflight` | exit 0（R2 测试 `ddc238a6…111a2a`、冻结规划哈希、HEAD 核对通过） |
| `pi-r3-dev1`（开发自检） | 2026-09-20T03:29:19.303843+00:00 | `run_checks.py pi-r3-dev1 focused`（basetemp `reports/T0010/pi-r3-dev1/pytest-tmp`） | exit 0，**53 passed in 0.30s** |
| `pi-r3-guards` | 2026-09-20T03:29:47.347869+00:00 | `record_check.py pi-r3-guards -- review-r2/rework_guards.py reports/T0010/pi-r3-guards` | exit 0 |
| `pi-r3-docs` | （本记录后） | `record_check.py pi-r3-docs -- review-r2/check_rework.py docs` | exit 0（一次性通过，见 docs 输出） |

守护结果（`pi-r3-guards/guards.json` 原件）：`submitted`（完整 53 项对照）exit 0；`reconstruct_logic_error`／`budget_d_before_c`／`ground_check_after_budgets`／`swap_helper_noop` 均 exit 1，且分别由 `test_d2b_exception_instance_identity`／`test_c4_validation_priority`／`test_c4_validation_priority`／`test_depth_invariant_under_transformations` 失败，四者 `guard_valid: true`；未伪造任何产品失败。

**新 R3 测试 SHA-256：** `648d815a986634ef53adfc85015bd6b8571e71fa1b134b7eb290b6d68da2ae01`（53 项，与 R2 同为 A：14、B：15、C：12、D：6、E：2、F：2、G：1）。

**产物：** `reports/T0010/pi-r3-preflight/`、`reports/T0010/pi-r3-dev1/`、`reports/T0010/pi-r3-guards/`（含 `guards.json`、各变体 argv／stdout／stderr、`pytest-tmp`、本记录 provenance 见 `reports/T0010/pi-r3-guards/provenance.md`）。

**偏差与阻塞：** 无阻塞；未 commit／push；按 R3 说明未跑额外 focused／旧 guards／全量 732；旧记录未回写。

### Codex 第 3 轮验收，2026-09-20

- **结论：accepted；R1–R4 全部关闭。** Codex + `gpt-6-astra`（`xhigh`）作为非 Pi 作者复核，三处剩余缺口均已补齐，未修改产品或测试。完整 A1–A7 判定及限制见 [第 3 轮验收报告](../../reports/T0010/review-r3/review.md)。
- 接受产品 SHA-256 `0361a37e8fbfcceb69ac55336c8578176ab96f1c94a86fa50a98aaa2a839bf5d`，测试 `648d815a986634ef53adfc85015bd6b8571e71fa1b134b7eb290b6d68da2ae01`。HEAD 仍为 `153295c28788f27ef37e794c7c0ea19841accaa8`，本结论对应未提交工作树；未 commit／push。
- [冻结核对](../../reports/T0010/review-r3-freeze/audit.json)：188 项旧材料哈希一致，产品／规划／既有源码未变，R2→R3 测试差异严格限于四个指定函数。[独立守卫](../../reports/T0010/review-r3-guards/guards.json)原提交 **53 passed in 0.32s**，四个违约副本各被指定测试拒绝，外层 exit 0、stderr 空。
- A1／A3 的真实异常身份和两种优先级守卫、A5 的 H8 实际交换通过；A2／A4 的手算、规模及证明对照继续有效。A6 沿用已核对原件／哈希的 Pi R2 **732 项完整回归**，本轮未重复 full；不将该历史结果写成 R3 独立全量复跑。
- A7 追加澄清：最终 Pi R3 有 **4 个 RUN**；`pi-r3-dev1` 是额外 focused，故“未跑额外 focused”有误。Pi 自述的录制前 `py_compile` 无归档原件，“全部开发检查已录制”不能确认；两次编辑失误过程仅作自述。组别计数 52 项之外另有变换测试 1 项，共 53。模型／用户确认及历史留证限制仍保留；这些澄清不改写旧 provenance，不再触发仅文字返工。
- 当前状态与 README／实现状态同步为 accepted。仅接受离线最短证明深度接口；规范证明身份／唯一性、motif、完整 world 审计及训练仍未完成。

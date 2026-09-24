# T0013：单查询的规范证明计数

## 任务信息

- 任务编号／修订号：T0013 / r1，2026-09-23。
- 状态：`accepted`（2026-09-24，Codex 第 3 轮复验，R1–R3 关闭）。
- 阶段／协议：M1 离线审计基础；研究计划 v0.1.3、E0 `e0_v2`、`proof_identity_v1`、D31。证明等价关系与数据准入规则不变。
- 规划／验收：Codex + `gpt-6-astra`、`xhigh`。实施：Pi，provider=bonsai、model=bonsai2-27b（pi 运行环境报告：PI_PROVIDER=bonsai、PI_MODEL=bonsai2-27b；用户已授权）。未被工具采集的环境不得写成独立核验。
- 基线：`e576c7793a91f8508ed5c57333f81eb0188a5745`，当前分支 `T0012-proof-key`，已推送且规划开始时工作树干净。本次规划文件为允许保留的未提交改动；Pi 从当前工作树创建 `T0013-proof-count`，不切回旧 master、不清空或 stash 规划材料，不自行 commit/push。
- 前置：T0009 完整原始树枚举、T0012 单树规范键均已验收；后者 [R5 审计](../../reports/T0012/review-r5/final-audit.json)所接受产品／测试已与基线 commit 核对。当前产品／历史文件由 [规划冻结清单](../../reports/T0013/planning-files.json)保护。
- 必读：[研究计划](../../KMesh_Research_Plan_v0.1.md) §4.5、§5.2；[身份规范](../proof_identity_v1.md) §3；[D31](../decisions.md#d31完整枚举后的规范证明计数)；`src/kmesh/logic/proof_enumeration.py`、`proof_key.py` 的公开契约。只需参考前置公开 API，不重读或重写旧任务的全部返工史。

## 目标、范围与交付物

**单一目标：** 一个函数精确计算给定 ground query 的同世界规范证明数。0 表示完整审计后不可推出，1 表示唯一规范证明，大于 1 表示多条不同支持证明；资源超限或验证失败均抛异常，不是上述任何一个计数。

| 允许改动 | 交付 |
|---|---|
| 新 `src/kmesh/logic/proof_count.py` | 单一公开函数；`__all__ = ["count_canonical_proofs"]` |
| 新 `tests/test_proof_count.py` | 下方 A–E 的小型组合测试 |
| `README.md` | T0013 API、U3 可运行例、十三文件测试命令、状态与限制 |
| `docs/implementation_status.md` | T0013 行及能力表行 |
| 本交接文档 | 状态与追加 Pi 执行记录，原契约／验收区不改 |
| 新 `reports/T0013/pi-*` | 原始 RUN、必要检查脚本和一份 provenance |

其他源码／测试、`logic/__init__.py`、规划检查器、身份规范、decisions、研究计划及旧证据全部冻结。**不做** motif、世界指纹、重复条款准入、split、数据生成、CLI、模型／训练；不增加摘要类型、新预算、新异常、缓存或第二个布尔唯一性 API。

## 前提与假设

- T0009 仅接受关系依赖无环的世界，完整返回所有有序原始出现树，失败没有部分返回；T0012 对每棵树执行真实验证并判单发生树，再生成规范键。T0012 单树允许有限循环证明，不改变本组合 API 从 T0009 继承的世界无环限制。
- 原始树可能只因重复 clause 或对称前提排列而不同，不能直接用原始树数量判唯一。计数为 1 也不意味着正式数据允许重复 clause，或 motif／world 审计已完成。
- Python 3.13.9、editable kmesh 0.1.0、pytest 8.4.2；准确环境见 [基线](../../reports/T0013/planning-baseline.json)。无需安装依赖、GPU、网络或外部数据。
- 规划已用既有 API 核对 U0–U8、U6 三个预算边界及两个无关环反例；[原件](../../reports/T0013/planning-examples/examples.json)。这些是 fixture 校验，不是新产品已经实现。
- 运行限于短 CPU 检查，记录器每 RUN 超时 120 秒。S 不是时间上限；不以超长链或大规模随机世界做本次组合测试。若发现既有 API 违约，保存反例交 Codex，不修改前置模块或自行解释为 0。

## 具体实施步骤

### 1. 先预检，再编辑

仓库根 `/home/mye/src/llm/KMesh`，先执行“验证方法”的分支／preflight 命令。成功后将本文与实现状态的 T0013 置 `in_progress`，再创建产品／测试。预检是必需项；若误先编辑，保留现状并报告，不删除新文件或恢复旧字节来制造编码前记录。

### 2. 只组合两个已验收 API

```python
def count_canonical_proofs(
    clauses: tuple[Clause, ...],
    query: Atom,
    *,
    max_fact_checks: int = 100_000,
    max_derivations: int = 100_000,
    max_proof_steps: int = 100_000,
) -> int:
    ...
```

固定行为顺序：

1. 函数首个业务操作是恰一次调用 `enumerate_proofs(clauses, query, max_fact_checks=max_fact_checks, max_derivations=max_derivations, max_proof_steps=max_proof_steps)`；输入对象和预算原样透传。本层不复制／转换输入、不预扫描、不另写校验或提前判断 fact／absent query。
2. 等完整枚举成功返回后，按原返回顺序，对**每个**原 proof 恰一次调用 `canonical_proof_key(clauses, query, proof, max_steps=max_proof_steps)`。重复原始树／重复键也不跳过此调用；保留原对象，不重排或重建证明。
3. 用完整 tuple 键的集合归并，完成全部树后返回集合长度，`type(result) is int`。不返回键、原始数量或 0/1/2 截断值；不在第一棵或第二个不同键后提前返回。

空枚举返回 0 且不调用 key；**仍须先成功完成枚举**。所有来自两调用点的异常均原实例向外传播，不吞掉、重建、包装或转成计数。校验次序、诊断和 C/D/S 语义完全沿用 T0009 的 `proofs.*`／下游错误；本层不新增 `count.*` 错误串。不另调用 verifier：T0012 已负责逐树验证。

S 是 T0009 **累计生成**的所有相关子证明步数预算，不是单棵长度或只计最终输出。任何返回树长度都不超过 S，所以将同一个 S 传给 T0012 是足够且一致的；不能遗漏关键字而引入默认 10000 的隐藏上限。

实现保持纯函数，仅依赖标准库、T0009、T0012（类型注解可导入 types）；不写 IO、全局状态、递归、求解器或新的规范化逻辑。整个调用仍支付枚举及逐树验证／规范化成本；不声称总运行时间线性或由 S 保证固定时长。

### 3. 写组合边界测试 A–E

自行构造以下小 fixture，不导入旧测试或规划脚本，不复制 T0012 的 oracle／长链／全变换套件。表中的 x/y/z/u/v 均为带 `?` 的变量。

**A：固定计数锚点。** C/D/S 依次为三个预算。每例对新 API 断言手算整数及 `type(result) is int`；原始数量可额外调用真实 T0009 核对，但不能拿 `len(set(canonical_proof_key(...)))` 给新 API 生成主 expected。

| 例 | 世界与 query | C/D/S | 原始树数 | 规范数 |
|---|---|---|---:|---:|
| U0 | 空世界，query p(a,b) | 1/1/1 | 0 | 0 |
| U1 | fact p(a,b)，query 同 fact | 1/1/1 | 1 | 1 |
| U2 | 两份相同 fact p(a,b)，query 同 fact | 1/2/2 | 2 | 1 |
| U3 | 两份 fact p(a,b)，COPY p(x,y)→q(x,y) 和 alpha 等价 p(u,v)→q(u,v)；query q(a,b) | 2/4/10 | 4 | 1 |
| U4 | fact p(a,a)，COPY p(x,y)→q(x,y)，INV p(x,y)→q(y,x)；query q(a,a) | 2/3/5 | 2 | 2 |
| U5 | 下述非对称世界，query q(a,a) | 3/4/20 | 4 | 4 |
| U6 | 下述对称重复槽世界，query q(a,a) | 3/4/20 | 4 | 3 |
| U7 | p(a,b),p(a,d),q(b,c),q(d,c)，JOIN p(x,y),q(y,z)→r(x,z)；query r(a,c) | 6/6/10 | 2 | 2 |
| U8 | fact p(a,b)，COPY p(x,y)→q(x,y)，query missing(a,b) | 1/2/1 | 0 | 0 |

U5/U6 世界前三条均为 `p(a,a)`、`s(a,a)`、`s(x,y)→p(x,y)`。U5 根为 `p(z,x),p(x,y)→q(x,x)`，两个槽不对称，AA/AB/BA/BB 四种支持不合并。U6 根为 `p(x,y),p(x,y)→q(x,y)`，AB/BA 合并而 AA/AB/BB 三种保留。重复发生不是删除重复槽位。

U7 再各自施加一次局部变量双射、clauses 逆序、JOIN body 逆序，query 不变；明确 world 确有改变，分别仍计数 2。这里由枚举器重新生成 proof，不手动重映射旧 proof。U7 的完整 `(clauses, query)` 在首次调用前 deepcopy 并取 hash，执行 U7→U0→U7 后比较完整输入与 hash、首末结果，避免把调用后的两次 hash 当作前后比较。

**B：真实失败与最小入口冒烟。**

- U6 将 C/D/S 分别减 1，其余维持表值：C=2、D=3 分别抛 `DerivationLimitError`，S=19 抛 `ProofEnumerationLimitError`；消息依次为 `enumerate.max_fact_checks exhausted before enumeration completed`、`enumerate.max_derivations exhausted before enumeration completed`、`proofs.max_proof_steps exhausted before enumeration completed`。
- 世界 `p(a,b)` 加无关自环 `r(x,y)→r(x,y)`，query 分别取 p(a,b) 与 missing(a,b)，都抛 `LogicValidationError("dependency.clauses: cyclic predicate dependency")`，不能返回 1／0。
- 新 API 代表性输入：clauses 为 list、带消费标记的 generator、非 ground query、S=True；其余参数合法。精确断言 `LogicValidationError` 和 T0009 消息：`proofs.clauses must be a tuple of Clause; got list`／`... got generator`（完整展开，含分号）、`proofs.query must be a ground Atom`、`proofs.max_proof_steps must be a non-bool positive integer; got bool`。生成器体内才写标记，拒绝后断言未消费。其余底层边界沿用旧测试，不再复制巨整数矩阵。

**C：组合调用契约。** patch **proof_count 模块实际引用处**的两个函数。

- 枚举 spy 记录先后事件、恰一次、clauses/query 的 `is`、三预算精确值；检查默认预算，以及显式 C=11、D=13、S=20001。返回 `(p0,p1,p0)` 三个 proof 引用，key spy 依序给出两个不同键（A/B/A）；要求调用三次、每个 proof 原对象、原 clauses/query、`max_steps=S`，结果 2。该 spy 只查组合调用，不代替 A 的真实计数。
- 枚举返回 `()` 时结果为整数 0，key 零调用。用超 10000 的 S spy 检查透传即可，不实际枚举万步长链。
- 模块 `__all__` 精确；缺参、额外位置参数或未知 keyword 保持普通 Python TypeError，不新增兼容入口。

**D：异常原实例与后续树不能漏检。**

- 枚举点分别抛具名 `LogicValidationError`、`DerivationLimitError`、`ProofEnumerationLimitError()` sentinel，断言 `exc.value is sentinel` 且 key 零调用。至少一次用原对象不支持预扫描的输入来确认没有本层预处理遮蔽 sentinel。
- key 点在第一棵成功后，对后续 proof 抛具名 `LogicValidationError` 或 `ProofLimitError` sentinel；要求原实例传播，不能跳过、返部分数或重建异常。断言实际已到达后续调用。
- 再仅替换枚举器，返回同一合法 fact proof 两次，随后一个结论与 query 不符的 ProofStep tuple；保留真实 T0012。整个调用必须抛 `proof_key.proof must be a valid proof of query`，不能因前两棵同键而提前返回 1。

**E：运行隔离。** 一个干净 Python 子进程，明确当前 src 路径，安装 finder 拒绝 `torch`、`yaml`、`kmesh.logic.engine`、`kmesh.logic.reference_engine` 的精确根与点前缀子模块。根实际 import 自测专有 ImportError 消息；用占位包实际 import 子模块 probe 并清理。随后真实计算 U2=1、U6=3，确认产品 `__file__` 是当前 src，扫描 sys.modules 禁用根及前缀均不存在。允许 T0009→derivations/dependency/types 和 T0012→proof 的必要依赖；不要错禁它们。

### 4. 文档、自检与交回

README 新段标题保留定位文字“规范证明计数（T0013”；用 **U3** 可直接运行例，写清原始 4 树经归并计 1；说明异常不是 0、只审计同世界证明数，键／证明仍是离线审计信息。记录实际新测试数 N，十三文件 full 应为已收集的 864＋N；不将收集结果称为已运行回归。

所有执行从第一次开发检查起经原记录器，使用全新 RUN；失败保留原名，不移动／删除／覆盖。普通只读查看文件无需包装。最终只写一份 `pi-r1-full/provenance.md`（若 full 重试则用实际成功目录），列事实、偏差、模型来源和 RUN 链接；不用反复手抄每条时间／哈希，docs 自动生成 run-index 并原样执行该 U3 代码块。没有原件写自述或 unknown，不恢复旧字节来补故事。

本文追加 Pi 记录，README／本文／实现状态置 `awaiting_review` 后跑 docs。docs 的 record.json 自身就是其最终时间与退出码，不回填 provenance 引发循环。冻结 diff 交 Codex；accepted 只由 Codex 标记。

## 验证方法

```bash
git switch -c T0013-proof-count
.venv/bin/python reports/T0013/run_checks.py pi-r1-preflight preflight
# 通过后置 in_progress，再创建产品／测试
.venv/bin/python reports/T0013/run_checks.py pi-r1-focused focused
.venv/bin/python reports/T0013/run_checks.py pi-r1-full full
# 一份 provenance、Pi 记录及 awaiting_review 状态落盘后
.venv/bin/python reports/T0013/run_checks.py pi-r1-docs docs
```

失败保留，下一次用 `pi-r1-focused2` 等新名；不得重建原 RUN。开发检查的准确入口为 `.venv/bin/python reports/T0013/record_check.py NEW_RUN -- COMMAND ...`。临时脚本放新 `reports/T0013/pi-*`，不放其他任务或 Codex review 目录。驱动负责插件隔离、CPU 环境及独占 basetemp。若不改测试／产品，不重复已通过检查；不运行 doctor、GPU 探测或无关任务。

## 验收标准

- [x] **A1 范围／接口：** 只有约定 count API，无新异常／预算／摘要；前置文件、规划和历史材料不变。
- [x] **A2 精确计数：** U0–U8 的手算整数、U5=4/U6=3、重复来源归并、两桥接支持及实际变换全部成立。
- [x] **A3 完整性／失败：** 枚举完成才计数、每树经过 T0012；三个真实预算失败、无关环、后续错误 proof 均阻止返回计数。
- [x] **A4 委托／纯度：** 一次枚举、原对象与预算、逐树有序调用、原异常实例；U7 输入完整前后快照与重复调用稳定。
- [x] **A5 隔离／测试有效：** 正确运行依赖与禁用根／子模块隔离；raw 数量冒充规范数、截断到 2、遗漏 key 预算、吞掉后续失败等错误能被上述目标断言拒绝。Codex 以有限错误副本核验，不要求 Pi 新造通用 mutation 框架。
- [x] **A6 回归／文档：** focused 与十三文件 full 无 skip/xfail；README U3 例可运行，实际语义与当前研究边界准确。
- [x] **A7 证据：** preflight 在创建新文件前；每次执行独立 RUN，失败原件不覆盖；原样驱动、一个 provenance、自动索引和实际模型来源准确，无未授权改动／commit／push。

## Pi 执行记录

第 1 轮（2026-09-23）：实施完成，状态 `awaiting_review`。未填写任何 Codex 结论。

- 实际工具／模型：Pi；provider=bonsai、model=bonsai2-27b（pi 运行环境报告：PI_PROVIDER=bonsai、PI_MODEL=bonsai2-27b）。
- 基线与分支：自当前工作树创建分支 `T0013-proof-count`（HEAD `e576c7793a91f8508ed5c57333f81eb0188a5745`）；规划文件未 stash；未 commit/push。
- 修改：新 `src/kmesh/logic/proof_count.py`（薄组合 API）；新 `tests/test_proof_count.py`（20 项，A–E）；`README.md` 新增 T0013 节（U3 可运行例、状态、十三文件测试命令）；`docs/implementation_status.md` T0013 行与能力表行；本文件状态与执行记录。`docs/decisions.md` 等冻结文件未改（D31 已覆盖本 API，未产生新决策）。
- 预检：新分支后、创建新文件前执行 [pi-r1](../../reports/T0013/pi-r1/record.json)（`python reports/T0013/run_checks.py pi-r1 preflight`，exit=0：frozen 基线、环境、scope、新产品/测试不存在）。基线收集 864 项（`python -m pytest tests --collect-only -q --no-headers`；交接文本中 `--tb=0` 形式在当前 pytest 8.4.2 无效，用等价收集命令）。
- 实现：A1 单一公开函数、`__all__ = ["count_canonical_proofs"]`；A2–A5 固定行为顺序（T0009 枚举恰好一次、预算原样透传；每棵原始树 T0012 恰好一次并透传 `max_steps=S`；完整 tuple 键集合长度返回 `int`；空枚举 0 且不调键）；A3–A6 不新增异常／摘要／缓存，S 同传 T0012（无默认 10000）；A4 文档。
- RUN [pi-r1-focused](../../reports/T0013/pi-r1-focused/record.json)：exit=0，新测试 20 项通过。
- RUN [pi-r1-full](../../reports/T0013/pi-r1-full/record.json)：exit=0，完整回归 884 项通过（原有 864 ＋ 新增 20，十三文件）。
- RUN pi-r1-docs6 docs：exit=0（docs 相位通过：frozen 基线、scope、全部文档链接可解析、hygiene、`awaiting_review`；生成 pi-r1-docs6/run-index.json，索引先前 8 个 Pi RUN；前序 docs1–docs4 四次 exit=1 原件保留，原因逐条见 [provenance](../../reports/T0013/pi-r1/provenance.md)）。
- 手算核验（真实 T0009/T0012/T0013 API，非规划脚本）：U0–U8 ＝ 0/1/1/1/2/4/3/2/0；U6 三精确预算 (2,4,20)/(3,3,20)/(3,4,19) 分别抛 DerivationLimitError／DerivationLimitError／ProofEnumerationLimitError（原消息）；环例两 query 抛 LogicValidationError("dependency.clauses: cyclic predicate dependency")；U7 三个结构变换（局部常数双射、条款顺序翻转、JOIN 体内槽位翻转）各 2；U7→U0→U7 输入哈希不变、首末结果 2=2。
- 偏差：无实质偏差；`--tb=0` 命令形式按 pytest 8.4.2 等价替换（记录于预检）；无未运行项；无历史证据丢失；无 commit/push/发布。

第 2 轮（2026-09-24）：R2 返工完成，状态 `awaiting_review`。未填写任何 Codex 结论。

- 实际工具／模型：Pi；provider=bonsai、model=bonsai2-27b（pi 运行环境报告：PI_PROVIDER=bonsai、PI_MODEL=bonsai2-27b）；沿用 R1 环境来源，如实说明。
- 基线与分支：沿用分支 `T0013-proof-count`（HEAD `e576c7793a91f8508ed5c57333f81eb0188a5745`）；未 stash、未 commit/push。
- 预检：`python reports/T0013/run_checks.py pi-r2-preflight2 preflight`（check_rework preflight），exit=0：frozen 基线、原测试哈希 `b3af88…`、scope；误用 R1 检查器的一次 `pi-r2-preflight` exit=1 原件保留。
- 修改：仅 `tests/test_proof_count.py` A/E 组与模块首段不实描述：A 组补 U8 正例、将变量改名改为仅 JOIN 的真实局部变量双射（`?x/?y/?z→?u/?v/?w`，事实与 query 不变）、U0–U8 逐例断言 `type(got) is int`、完整性测试改用完整 `(world, query)` 对 deepcopy（去自比较）；E 组隔离改为 fresh 逐根 import、`ModuleType(__path__=[])` 占位、块消息含完整名称、保留 U2/U6 与源文件定位及模块扫描。同步 `README.md` 当前覆盖与限制、`docs/implementation_status.md` T0013 行、本交接状态与记录。产品、B/C/D 组、前置文件、规划及旧 Pi/Codex 材料冻结。
- RUN [pi-r2-focused](../../reports/T0013/pi-r2-focused/record.json)：exit=0，新测试 21 项通过（R1 的 20 ＋ U8）。
- RUN [pi-r2-full](../../reports/T0013/pi-r2-full/record.json)：exit=0，沿用独立完整回归 885 项（原有 864 ＋ 新增 21，十三文件）。
- 手算核验（真实 T0009/T0012/T0013 API）：U8（非空无环、query 不可推出，C/D/S=(1,2,1)）返回 exact int 0、raw 0、无 limit error；U0–U8 值仍 0/1/1/1/2/4/3/2/0；JOIN 局部变量双射变体（事实/query 不变）仍 count 2 且 world hash 不同于原；U7→U0→U7 输入对哈希不变、首末 2=2、三值皆 int；隔离探针四个禁用根（torch、yaml、kmesh.logic.engine、kmesh.logic.reference_engine）及其真实子模块 `._t0013_probe` 以真实 import 自测，块消息均含完整名称。
- 隔离前缀自测（R2 关键）：finder 对精确根与任意后代（子模块）都拦，且块消息携带实际尝试的完整点名称；真实 `import` 禁用根得完整根名，`ModuleType(__path__=[])` 占位后 `import root._t0013_probe` 得完整子模块名；仅精确根匹配的副本会失败该步（抛 `ModuleNotFoundError`）。
- 偏差：无实质偏差；`pi-r2-preflight`（exit=1，误用 R1 检查器）保留；旧 docs 失败原件保留，不回写；未回填 docs 自身结束时间；无 commit/push/发布。

第 3 轮（2026-09-24）：R3 返工完成，状态 `awaiting_review`。未填写任何 Codex 结论。

- 实际工具／模型：Pi；provider=bonsai、model=bonsai2-27b（pi 运行环境报告：PI_PROVIDER=bonsai、PI_MODEL=bonsai2-27b）；沿用 R1 环境来源，如实说明。
- 基线与分支：沿用分支 `T0013-proof-count`（HEAD `e576c7793a91f8508ed5c57333f81eb0188a5745`）；未 stash、未 commit/push。
- 预检：`python reports/T0013/run_checks.py pi-r3-preflight preflight`（check_rework preflight，冻结基线测试哈希 `31b11335…`、保护 E 前全文），exit=0。
- 修改：仅 `tests/test_proof_count.py` 的 E 组（TestEIsolation）两处注释与一处删除：删除实际产品 import 前的 `sys.meta_path.pop(0)`（保留运行期硬阻断）；把相邻「drop blocker」注释改为「finder 保持至真实导入、U2/U6 与最终扫描完成」；将「bare module (no __path__)」注释修正为「占位包、空 __path__」。E 前文本与 R3 基线一致，仅 E 变。
- RUN [pi-r3-focused](../../reports/T0013/pi-r3-focused/record.json)：exit=0，定向 21 项通过。未跑 full／doctor／GPU。
- 隔离（运行期）：finder 保留至真实导入、U2/U6 计算与最终扫描完成，E 在硬阻断下仍算出 U2=1、U6=3；`sys.modules` 无泄漏。
- 偏差：无未运行项；R2 中「提前移除 finder」误判已按 [R3 复验](../../reports/T0013/review-r2/review.md)修正，冻结清单见 [rework-files.json](../../reports/T0013/review-r2/rework-files.json)。

## Codex 验收记录

规划已完成，状态 `ready`；产品尚未实施，产品验收 `not_run`。非作者 `/root/design_t0012` 对具体交接与驱动进行了只读设计审阅：接口、C/D/S 透传、失败传播和四步粒度可交实施；其指出的临时目录忽略风险由任务级 `.gitignore` 覆盖，并纳入冻结清单。

规划实证：九个手算例、三个精确预算失败、两个无关环例通过；既有十二测试文件收集到 864 项，未执行旧 full。依据和原件见 [规划审阅](../../reports/T0013/planning-review.md)及 [规划卫生检查](../../reports/T0013/planning-final/record.json)。上述结果只证明前提与交接可执行，A1–A7 待 Pi 实施后独立验收。


### 第 1 轮验收（2026-09-24）与第 2 轮返工安排

结论 **`needs_changes`**：产品未发现缺陷，原哈希 `ac710fd17731bde66e90e8d7737a5eac59486b65454f6bd0fbe9d1ca270eec6d` 冻结。独立完整 **884 项通过**；Codex 补测 U8、真正局部变量改名与 README 例均通过。四个产品错误副本被拒，但去掉隔离 finder 的点前缀判断后仍 20 项全过；测试 A/E 与执行描述尚需补齐。详见 [验收报告](../../reports/T0013/review-r1/review.md)、[输入与原件核验](../../reports/T0013/review-r1/evidence-audit.json)、[有限守卫核验](../../reports/T0013/review-r1-guards/guards.json)。本节只落实原契约遗漏，不改变产品接口或研究协议。

**返工范围：** 只改 `tests/test_proof_count.py` A/E 组与不实模块说明，以及 README／实现状态／本交接的当前状态和追加记录；新增 `reports/T0013/pi-r2*`。产品、B/C/D 组、前置文件、规划及所有旧 Pi/Codex 材料冻结。完整冻结清单见 [rework-files.json](../../reports/T0013/review-r1/rework-files.json)。模型继续 Pi + 用户已授权 bonsai2-27b，如实说明环境来源。

1. **先预检。** 保持现分支／HEAD，运行下方新 preflight；通过后将本文与实现状态置 `in_progress`，再改测试。预检要求原测试 `b3af8851606836b27689f1ffba6b5061542496d5b6cfba4eceb0d22a6ad55a13`，不删／回滚文件伪造时点。
2. **补 A 与修 E。** 按验收报告 R1/R2：U8=0；仅 JOIN 的 `?x/?y/?z→?u/?v/?w` 真实双射，事实/query 不变；U0–U8 各自检查原生 int；完整输入对 deepcopy 替代自比较。四禁用根及其真实子模块分别自测，消息含完整名称，临时 `ModuleType` 占位包 `__path__=[]` 配合真实 import、finally 清理，不把 finder 塞进包路径。保留 U2/U6、源文件定位和模块扫描。无需新增通用守卫框架。
3. **定向验证。** 运行 focused，失败保留原名后换新 RUN；产品没有已知缺陷，不要求伪造“先失败”或修改冻结产品。本轮沿用 Codex 的 884 项 full，只报告新 focused 实际 N，不宣称新的 864+N 全量通过。不跑 doctor／GPU 或重复全回归。
4. **记录与交回。** 按 R3 在成功 focused 目录新写一份 provenance，逐项更正 U8／变量变换、docs2 原因、并不存在的 `--tb=0` 契约及模型证据来源；保留旧 R1 原件，不回写。同步 README 当前覆盖和限制、实现状态；本节后追加 Pi R2 记录，三处置 `awaiting_review` 后跑新 docs。自动索引负责时间／argv，不回填 docs 自身结束时间；未录制事实标自述/unknown，不补造。无 commit/push。

本轮准确命令（仓库根；记录器／驱动均不改；每次尝试新 RUN）：

```bash
.venv/bin/python reports/T0013/record_check.py pi-r2-preflight -- .venv/bin/python reports/T0013/review-r1/check_rework.py preflight reports/T0013/pi-r2-preflight
# 预检通过 → in_progress → 仅约定测试与文档修改
.venv/bin/python reports/T0013/run_checks.py pi-r2-focused focused
# 新 provenance、追加执行记录、awaiting_review 落盘后：
.venv/bin/python reports/T0013/record_check.py pi-r2-docs -- .venv/bin/python reports/T0013/review-r1/check_rework.py docs reports/T0013/pi-r2-docs
```

失败换 `pi-r2-focused2`／`pi-r2-docs2` 等，命令的 RUN 与输出目录同时更新。开发检查同样经原记录器。原 `check_delivery.py` 是 R1 单份 provenance 与范围检查，不用于本轮；新检查器冻结 R1/Codex 原件并允许唯一 R2 provenance。Codex 下一轮只复验 R1–R3 受影响范围，accepted 仍只由 Codex 标记。


### 第 2 轮复验（2026-09-24）与第 3 轮最小安排

结论 **`needs_changes`**，只剩 E 组运行期硬隔离。原 R1（U8、真实局部变量双射、各锚点类型、完整输入对快照）已关闭；根／点前缀自测现有效。产品继续冻结，接受的当前测试基线为 `31b11335cf57940a7bb3850ee7fa505c601a33cc8191573499d6959f0f31d38d`（此处“基线”不等于任务 accepted）。独立提交副本 **21 项通过**；仅根匹配副本被拒，但产品导入时运行期观察明确失败 `runtime import blocker removed`。原 R3 的历史更正由 Codex 在 [本轮报告](../../reports/T0013/review-r2/review.md)逐项追加，保留自述／unknown，不记作 Pi 已完成；不再要求重复补抄首轮记录。

Pi 的 R2 full **885 passed** 原件有效，但属额外自检且偏离“不重跑 full”安排；不是 Codex 独立 full。Codex 本轮只独立跑 21，沿用上轮独立 884。五个 Pi R2 RUN 及 2578 项旧冻结文件均核对通过，B/C/D 未改。依据见 [证据审计](../../reports/T0013/review-r2/evidence-audit.json)、[定向与守卫观察](../../reports/T0013/review-r2-checks/checks.json)。

**第 3 轮范围：** 仅 `tests/test_proof_count.py` 的 `TestEIsolation`，三份当前维护文档的状态／追加记录及新 `reports/T0013/pi-r3*`。产品、A–D、所有旧 RUN／review 冻结，见 [冻结清单](../../reports/T0013/review-r2/rework-files.json)。模型仍 Pi + 用户已授权 bonsai2-27b，来源如实记录。

1. **预检后置 in_progress。** 使用下方新的 R3 preflight，要求产品及旧测试基线哈希一致；不再用 R1/R2 preflight。通过后修改状态，再编辑 E。
2. **修唯一代码项并定向跑。** 删除 E 子进程片段在实际产品 import 前的 `sys.meta_path.pop(0)`；把相邻 drop blocker 注释改为“finder 保持至真实导入、U2/U6 与最终扫描完成”。保留四根／前缀自测、精确错误、路径与模块扫描；将 `no __path__` 注释修正为空 `__path__` 的占位包。无需新测试／变异框架或重写 E；预计仍 21 项。运行 focused，失败原件保留、重试新 RUN；**不跑 full／doctor／GPU**。
3. **简短记录并交回。** 新一份 provenance 放实际成功 focused 目录，只记录本轮改动、RUN 链接、偏差与模型自述来源，并引用 Codex 本轮更正；不重抄 R1/R2 历史，不改旧 provenance。三处状态改 awaiting_review，追加 Pi 第 3 轮记录，跑新 docs。Codex 再核验运行期 finder 保留、前缀守卫与定向结果；不 commit/push。

```bash
.venv/bin/python reports/T0013/record_check.py pi-r3-preflight -- .venv/bin/python reports/T0013/review-r2/check_rework.py preflight reports/T0013/pi-r3-preflight
# 通过 → in_progress → 仅 E 小修
.venv/bin/python reports/T0013/run_checks.py pi-r3-focused focused
# 简短新 provenance、追加记录、awaiting_review 落盘后
.venv/bin/python reports/T0013/record_check.py pi-r3-docs -- .venv/bin/python reports/T0013/review-r2/check_rework.py docs reports/T0013/pi-r3-docs
```

每次失败保留原 RUN，下次改 `pi-r3-focused2`／`pi-r3-docs2` 等并同步输出目录；开发检查仍经原记录器。新检查器同时保护 E 之前的完整测试文本，不重跑已通过范围。


### 第 3 轮复验／最终验收（2026-09-24）

结论 **`accepted`**，R1–R3 关闭。产品 `ac710fd17731bde66e90e8d7737a5eac59486b65454f6bd0fbe9d1ca270eec6d` 持续冻结，接受测试 `527808551efb6f3c9a8ae1d72fd31e93dcea20814e23fe7162330a8e15869fff`。HEAD 仍 `e576c7793a91f8508ed5c57333f81eb0188a5745`，未 commit/push，接受的是当前文件字节。

本轮独立提交控制组 **21 passed**；仅匹配根名的错误 finder 副本被 E 拒绝；运行期观察在产品 import、U2、U6、最终扫描后四处均确认 finder 保留。旧冻结清单 2625 项与 E 前全文不变；Pi R3 四个 RUN（0/0/1/0）原始流及源码哈希一致。未重跑 full，沿用 Codex R1 独立 884 项及产品错误副本验证；Pi R2 的额外 885 项仍单列为自检。详见 [最终验收报告](../../reports/T0013/review-r3/review.md)、[本轮定向与隔离证据](../../reports/T0013/review-r3-checks/checks.json)及 [最终审计](../../reports/T0013/review-r3/final-audit.json)。

R3 preflight 的实际子命令是 `review-r2/check_rework.py preflight`，旧 Pi 文字中的 `run_checks.py` 不准确；docs2 原输出是 4 docs/91 links；本轮按连续 review-r1/r2/r3 编号为第 3 轮，非第 4 轮。这些小误述由 Codex 追加更正，旧 provenance 不改写。模型来源为 Pi 自述，先前 unknown 与流程偏差继续保留，见最终报告及其引用的 R2 更正。

A1–A7 依据齐全；本任务仅完成同世界单查询规范证明数，0/1/多条必须完整枚举和逐树验证成功才返回，异常不转成计数。world 准入、motif、数据集及模型训练不在本次验收范围。

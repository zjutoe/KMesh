# T0017：单查询全部证明的完整子树 motif 联集

## 任务信息

- 任务编号／修订号：T0017 / r1。
- 状态：accepted（2026-09-27，round 3 / attempt 4；终态后由 Codex 同步）
- 阶段：M1 数据审计前置组合；研究计划 v0.1.3，E0 `e0_v2`／E1 `e1_v3` 不变。
- 规划／独立验收：Codex + `gpt-6-astra`／`xhigh`；实施：Pi + `bonsai2-27b`／`xhigh`。
- 基线：`783cdd2dd00643815f084d97fbd1038265a2003c`，已合并并推送 `master`。
- 独立分支／工作区：`T0017-query-motifs`／`/home/mye/data/kmesh-worktrees/T0017-query-motifs`。
- 发布前已有改动：Codex 的 decisions、implementation_status、README、本交接、reports/T0017；发布时整体冻结，Pi 不修改这些文件。
- 依赖：[T0009](T0009-proof-enumeration.md)、[T0016](T0016-subtree-motifs.md) 已验收；T0016 依赖的 T0012／14／15 保持原契约。T0016 验收为26项定向、960项全量通过，已随上述基线提交。
- 必读：[AGENTS §8](../../AGENTS.md)、研究计划 §5.2、[D36](../decisions.md)、[motif 身份](../motif_identity_v1.md)、`src/kmesh/logic/proof_enumeration.py`、`subtree_motifs.py`、`proof_count.py`。

## 目标、范围与交付物

单一目标：给定有限无环世界和一个 ground 查询，先完整枚举它的全部原始证明，再返回这些证明中**全部完整有根支持子树**的 motif 键联集。

Pi 只允许新增／修改：

1. `src/kmesh/logic/query_motifs.py`
2. `tests/test_query_motifs.py`

不改现有代码／测试、包初始化、依赖、文档、报告。只在控制器指定的外部 `delivery/summary.md` 和 `completion.json` 写本轮交付；终态后由主会话 Codex 同步项目文档。控制器状态优先于本文发布时的 `ready`，不运行旧 record_check 脚本。

本项不定义 heldout 清单、任意裁剪片段匹配、world 准入／split、生成器、CLI 或模型接口；不输出训练数据。集合元素数量不是证明数量，也不是独立研究样本数。该联集今后可与已冻结的同口径保留键求交；本项未定义正式保留规则，未命中不能宣称 world 无泄漏。

## 前提、成本与停止条件

- 已配置独立 `.venv`（system-site-packages、离线 editable 安装，无依赖下载）；Python 3.13.9、kmesh 0.1.0、pytest 8.4.2，导入必须来自当前工作区的 `src`。
- Codex 已用接受依赖核对下面11个手算 fixture、C/D/S精确预算和晚发生的 O 超限，见 [规划探针](../../reports/T0017/planning_probe.py)及 [原始结果](../../reports/T0017/planning-fixtures-r1/)。该脚本不是新测试 oracle，Pi 不导入它，也不导入旧任务 tests／reports。
- 只用合成内存 fixture／CPU；无外部数据、网络、GPU、下载和训练。继承 T0009 的关系 DAG 限制，即使查询不存在也必须完成其世界检查；不要因 T0016 能接受给定循环证明而放宽此边界。
- C/D 为全世界的事实匹配／推导预算；S 为 T0009 生成相关证明的累计步骤预算，**不是最大单树长**；O 为每棵子树的方向数预算，跨目录／证明不累计。S 同值传入 T0016 的 max_steps，不另扣减。
- 枚举成本之外，总共处理 `sum_p sum_i size(subtree(p,i))` 个生成 Header，最后集合可去重；还包括 T0016 重复验证和 motif 方向枚举成本。不宣称线性复杂度或固定耗时；所有预算失败都是未完成审计，不是空集合或无泄漏。
- 控制器最多4轮、总墙钟14400秒、每 agent 进程3600秒，每必需检查180秒。基础设施中断保留证据并 blocked，不自行改预算／换模型。正常契约内返工由独立 Codex 安排。未授权自动 commit/push/merge。

## 实施步骤

### 1. 核对基线和只读契约

确认 HEAD／分支、上述路径、解释器／导入路径；仅首次attempt核对两个允许的实现／测试文件起初不存在，返工继续控制器指定的上一轮提交／快照。核对 `reports/T0017/task.json` 的范围；控制器 intake 是发布时冻结依据。不要重写规划文件或删除既有证据。假设不成立先反馈控制器，不自行搬迁／回滚文件。

### 2. 实现唯一公开 API

```python
def query_subtree_motif_keys(
    clauses, query, *,
    max_fact_checks: int = 100_000,
    max_derivations: int = 100_000,
    max_proof_steps: int = 100_000,
    max_orientations: int = 100_000,
) -> frozenset[tuple]:
    ...
```

`__all__ == ["query_subtree_motif_keys"]`，不增加公开异常／类／辅助 API。

执行顺序固定：

1. 首业务操作：原 `clauses`、`query` 对象以及原 C/D/S，恰一次调用 T0009 `enumerate_proofs`，等待完整返回；此前不转换／遍历／len 输入、不校验 O、不复制输入。不预检 query 是否已是事实。
2. 枚举成功后校验 O：仅 `type(O) is int and O > 0` 合法，包括空枚举也执行。否则精确抛 `LogicValidationError("query_motifs.max_orientations must be a non-bool positive integer; got TYPE")`，TYPE 仅为 `type(O).__name__`，不得 repr／str 未验证值。
3. 按 T0009 返回顺序，每棵**原始树**恰一次调用 T0016 `proof_subtree_motif_keys(clauses, query, proof, max_steps=S, max_orientations=O)`，全部原对象／预算不变。重复来源、相同规范证明或相同 motif 仍须调用；不能先按证明键去重。集合更新使用目录的**每个完整键**，不是整个目录、只末项或 Header。
4. 全部成功才返回真实 `frozenset`。空枚举＋合法 O 返回 `frozenset()`，不调用 T0016；没有返回迭代器、部分结果或 bool 的路径。

直接依赖仅允许标准库、`kmesh.logic.types`（LogicValidationError／可选类型注解）、`proof_enumeration.enumerate_proofs` 和 `subtree_motifs.proof_subtree_motif_keys`。使用模块级按名导入这两个公共调用点，便于在本模块真实绑定处 spy。不得直接调用 verifier、solver、独立 canonical_motif_key／proof_key／proof_count、自己搜索／规范化／遍历证明树。既有依赖的间接调用保留。

不捕获／包装／重试依赖异常，不补新异常；原异常类、实例、消息、context 语义都保留。首次枚举失败高于 O 错误；任一后续树失败立即停止，不能继续下一个树或返回前面已累积的集合。

### 3. 用手算锚点检验结果和预算

缩写：`F_p(a,b)` 为事实 `p(a,b)`；`C(p,q)` 为 `p(?x,?y)→q(?x,?y)`；`I(p,q)` 为 `p(?x,?y)→q(?y,?x)`；`J(p,r,q)` 为 `p(?x,?y),r(?y,?z)→q(?x,?z)`。世界严格按表内顺序构造。a/b/c/d/z是不同常量。

F/C/J 的**完整手算键**逐字见 [motif 规范 §4](../motif_identity_v1.md#4-手算完整键)，分别为异实体事实、COPY、JOIN键；不得通过待测API或其依赖算 expected。补充 INV 键 I 和重复前提键 R：

```python
I = ("proof_motif_v1", (
    ((0, 0, 1), (0, ("v", 0), ("v", 1)), ((1, ("v", 1), ("v", 0)),)),
    ((1, 1, 0), (1, ("c", 1), ("c", 0)), ()),
))
R = ("proof_motif_v1", (
    ((0, 0, 1), (0, ("v", 0), ("v", 1)),
     ((1, ("v", 0), ("v", 1)), (1, ("v", 0), ("v", 1)))),
    ((1, 0, 1), (1, ("c", 0), ("c", 1)), ()),
    ((1, 0, 1), (1, ("c", 0), ("c", 1)), ()),
))
```

| ID | world；query | C/D/S/O | 原树数 | 完整期望 frozenset |
|---|---|---|---|---|
| Q0 | 空；q(a,b) | 1/1/1/1 | 0 | {} |
| Q1 | F_p(a,b)；p(a,b) | 1/1/1/1 | 1 | {F} |
| Q2 | F_p(a,b), F_p(a,b)；p(a,b) | 1/2/2/1 | 2 | {F} |
| Q3 | F_p(a,b), C(p,q)；q(a,b) | 1/2/3/1 | 1 | {F,C} |
| Q4 | F_p(a,b), F_r(b,a), C(p,q), I(r,q)；q(a,b) | 2/4/6/1 | 2 | {F,C,I} |
| Q5 | F_q(a,b), F_p(a,b), F_r(a,b), C(p,q), C(r,q)；q(a,b) | 2/5/7/1 | 3 | {F,C} |
| Q6 | F_p(a,b), F_p(a,d), F_r(b,c), F_r(d,c), J(p,r,q)；q(a,c) | 6/6/10/2 | 2 | {F,J} |
| Q7 | F_q(a,c), F_p(a,b), F_r(b,c), J(p,r,q)；q(a,c) | 2/4/6/2 | 2 | {F,J} |
| Q8 | Q3 world；q(z,b) | 1/2/1/1 | 0 | {} |
| Q9 | F_p(a,b), F_r(b,c), I(r,s)；p(a,b) | 1/3/1/1 | 1 | {F} |
| Q10 | F_p(a,b), p(?x,?y),p(?x,?y)→q(?x,?y)；q(a,b) | 2/2/4/2 | 1 | {F,R} |

测试逐行比较真实 `frozenset` 与完整字面键，不能只比数量。Q4只查首棵或整树将缺项；Q5有3条规范证明却只有2个子树键；Q6两桥证明可以共享 motif，绝不能据此判唯一；Q9不把无关r/s证明的motif并入联集，但T0009仍须完成全世界推导检查；Q10重复发生仍在R完整键中。

至少实测 Q6 的 C=5、D=5、S=9（每次其余预算原值）分别报 DerivationLimitError／DerivationLimitError／ProofEnumerationLimitError，预算=表中值成功；Q7 O=1 必须在第一棵事实成功后对 JOIN 抛 MotifLimitError，O=2则完整成功；Q8 D=1 仍超限（全世界检查不能因空查询跳过）。这些精确边界不要改成宽松大预算或修改 fixture。O不跨子树扣减，Q7正例也是该边界的测试。

### 4. 补齐组合契约测试

按行为组织，允许合理参数化；不以测试条数本身作验收条件。只需实现本任务新边界及关键委托覆盖，不复制前置任务的全部测试。

- **调用与失败顺序：** 在 `query_motifs` 两个真实绑定处安装联合日志spy，验证首操作、原对象is、精确关键字与默认四预算、非默认预算（如11/13/17/19）、原树顺序和每树恰一次。用3个证明对象，其中两次为相同对象，fake目录包含交叠完整键，证明没有提前去重；空枚举只调用枚举一次，但O仍校验。仅此类委托测试可使用哨兵假对象，真实语义锚点不mock。
- **异常不重建、不提前返回：** 枚举分别抛原 `LogicValidationError`／`DerivationLimitError`／`ProofEnumerationLimitError` 哨兵，O同时非法；联合日志只枚举一项，T0016零调用。T0016在第2棵抛原 `MotifLimitError`／`ProofLimitError`／`LogicValidationError` 哨兵：前一棵成功，第3棵不能被调用。断言精确类、消息、实例is和未抑制context。每个场景恢复patch，避免计数或spy串用。
- **O输入：** None、True、False、0、-1、1.5、"2"、正int子类和 `-10**5000` 逐条精确类＋全文，至少在空枚举上覆盖，并证明T0016零调用；`10**5000` 在Q1成功。巨整数用局部fixture保存/设4300/实测4300/finally恢复，短param id，不能格式化该整数。O非法也要先执行枚举。
- **委托的输入边界：** clauses列表、生成器、坏成员，query非Atom／非ground，C=0／D=True／S=0经新API保留T0009精确类＋全文；生成器body内标记在拒绝后仍为空。世界 `p(?x,?y)→p(?x,?y)`（无事实）与Q0查询、O=0，仍先报精确 `dependency.clauses: cyclic predicate dependency`。签名缺参、多余位置／未知keyword为普通TypeError；精确检查__all__。
- **不变性与纯度：** Q4/Q6各做全局关系／实体双射（query同步）、规则局部变量双射、world逆序、二前提body逆序（Q6）对照，确认变换实际改变字段且联集不变；重复来源增加原树但集合不变。Q4→Q0→Q4调用前后比较独立结构快照及hash。返回本身可hash，全部元素仍是真实tuple，不用list转换掩盖类型问题。
- **硬导入隔离：** 新Python子进程显式插入当前测试所在仓库src，断言 query_motifs.__file__ 的完整realpath。finder在导入／Q0/Q4/Q7真实调用／最终sys.modules根名＋点前缀扫描全过程保留。禁止根仅 `torch`、`yaml`、`kmesh.logic.engine`、`kmesh.logic.reference_engine`，不阻断本任务必需的proof_enumeration或间接proof/motif。每根先真实import自检完整错误消息；子模块自检用 `ModuleType(root)`＋`__path__=[]` 占位并实际import `root._t0017_probe`，断言完整消息，finally清理占位。不得以调用finder方法或找不到模块冒充有效拦截。子进程显式断言Q4/Q7完整期望；保持禁止根未预加载。

### 5. 自检并提交独立验收

先定向、后全量；失败也保留在本轮Pi工具原始事件中。每次开发pytest用全新临时basetemp，不覆盖历史目录。检查末尾换行／尾随空白；不编辑 README 等冻结文件。外部汇总分列真实命令／退出码／失败与修复／未运行项，实际模型来自控制器RPC，不用自述证明后端权重。

## 验证方法

工作目录为上述独立工作区。控制器必需检查的精确argv见 [task.json](../../reports/T0017/task.json)，对应命令：

```bash
env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/mye/data/kmesh-worktrees/T0017-query-motifs/.venv/bin/python -m pytest -q -p no:cacheprovider --basetemp /tmp/kmesh-T0017-focused tests/test_query_motifs.py
env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/mye/data/kmesh-worktrees/T0017-query-motifs/.venv/bin/python -m pytest -q -p no:cacheprovider --basetemp /tmp/kmesh-T0017-full tests
```

这些固定basetemp仅供控制器；其检查沙箱具有每次独立的/tmp。Pi开发检查改用自身新临时名；开发工具日志与控制器checks原件分开。新测试N项、全量960+N项，退出0且无skip/xfail；不因为产品短而弱化测试，也不为了达条数增添重复检查。定向及完整检查各180秒上限。数据seed N/A（全部确定性手算fixture）；不跑doctor、GPU或模型smoke。

## 验收标准

- [x] A1：仅两允许文件；公开API、导入及委托顺序精确；Pi未改研究设计或冻结材料。
- [x] A2：Q0–Q10完整字面联集符合手算；替代来源、重复发生、无关世界推导和非唯一性解释正确。
- [x] A3：C/D/S/O边界、空枚举O校验、晚异常和无部分返回通过；原异常身份／顺序有有效守卫。
- [x] A4：原对象／预算／每棵原树恰一次均有真实调用点spy；输入／巨整数／签名错误精确，生成器不消费。
- [x] A5：变换确实改变输入，集合不变；纯度、跨调用稳定性、返回类型与可hash通过。
- [x] A6：硬隔离根与子模块自检有效，finder覆盖实际调用；明确允许既有间接依赖。
- [x] A7：控制器必需检查、冻结快照、外部交付及独立Codex审阅相互一致。测试通过不自动等于验收；审阅者需检查测试能抓住“只首棵／只整树／提前去重／晚失败返回／跳过空O”等关键违约，不机械复跑前置任务全部核验。

## Pi 执行记录

发布后本文只读。每轮写控制器提供的外部delivery；原始工具事件由控制器保存。终态后由主会话Codex填写项目摘要，不伪造历史操作。

Codex 终态同步（2026-09-27）：attempt 1 因3600秒实施预算中断；用户授权7200秒单进程上限并显式恢复后，attempt 2 完成48项定向／1008项全量检查。独立审查要求补强四项原契约测试。attempt 3 只改测试，完成51项／1011项检查，但异常消息断言仍比较同一可变对象的两个实时值；attempt 4 最小修正两处断言，在调用前保存预期消息，再审通过。产品自attempt 2起未改。

实际 Pi 客户端身份为 `bonsai / bonsai2-27b / xhigh`，来源为RPC记录，不作为服务端权重证明。各轮原始交付／工具事件留在仓外state，检查和过程摘要见 [验收报告](../../reports/T0017/acceptance/review.md)与 [结构化记录](../../reports/T0017/acceptance/summary.json)。Pi 汇总中有测试数口径误写，最终以控制器原始stdout的48→51及1008→1011为准。

## Codex 验收记录

**accepted**，2026-09-27 04:53:11 UTC，round 3 / attempt 4。独立 Codex + `gpt-6-astra`／`xhigh` 核对实现、测试、隔离、预算和冻结摘要；控制器51项定向／1011项全量通过，独立定向51项通过，六个消息变异反例均被拒，R1–R4全部关闭，A1–A7通过。见 [最终意见](../../reports/T0017/acceptance/attempt-0004.verdict.json)。

接受产品 SHA-256：`3feb1fb5801e5504fd9d79e6087bab06e159ec69f098ed3168aeb950e6e456f9`；测试：`17c022f05acd7751b2e6677f8a1e698c99479a50c9b64d67baf9dfe6141cc59c`。提交快照为 `638f5ded2c0b8ec2e01de33824b7deb13e37a0b6c5d14f9acc012072e41c8456`。

主会话在写回前确认完整工作区与接受快照一致、进程均成功退出、stdout/stderr哈希及Codex成功终态有效，未重跑模型或测试。[原发布契约](../../reports/T0017/acceptance/published-handoff.txt)保留当时字节，SHA-256 `32bdd08f50149203586b6dfe9196adca8505fff7795edbeec29185726f9f75ff`；当前文档的状态／终态记录为验收后同步，不属于原接受快照。

范围仍为单查询所有原始证明的完整有根子树motif联集，不构成任意裁剪片段匹配、world保留结构审计、数据划分或LLM局部更新实验结论。

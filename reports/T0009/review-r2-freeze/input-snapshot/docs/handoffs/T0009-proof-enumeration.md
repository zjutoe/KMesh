# T0009：单查询的有限原始证明枚举

## 任务信息

- 任务编号／修订号：T0009 / r1，2026-09-18。
- 状态：`awaiting_review`（Pi 第 2 轮返工完成，2026-09-19；R1 索引/迭代组合已恢复、R2 测试守卫已补、R3 已在 [pi-r2-full/provenance](../../reports/T0009/pi-r2-full/provenance.md) 逐项更正，待 Codex 第 2 轮独立复验；R1–R3 返工要求见末尾）。
- 所属阶段／协议：M1 / E0-D；研究计划 v0.1.2、E0 `e0_v2` §4.3–4.5、§5.2、§15.1；工程约定 D27。仅补证明展开能力，不改变研究协议。
- 规划者／验收者：Codex + `gpt-6-astra`，`xhigh`；执行者：Pi + `qwen3.8-coding-27b`，开工记录实际完整模型别名（此前为 `qwen3.8-coding:27b-q8_0-64k`，ollama），不自行换模型。
- 基线：`bfb0f8e3c5c1c1168f7110ac6287aeb0f3330fff`，当前 `T0008-ground-derivations` 已与同名 origin 同步；规划起点工作树干净。**master 尚未包含 T0007/T0008；必须从此基线建立 `T0009-proof-enumeration`，保留本次 Codex 交接改动。** 若 HEAD 只多出本次交接提交，确认旧源码／契约一致后记录实际 HEAD 继续；其他相关变化先反馈，不回退。
- 前置：[T0003](T0003-logic-types.md) 内容类型、[T0006](T0006-proof-verifier.md) 独立 verifier、[T0007](T0007-relation-dag.md) DAG、[T0008](T0008-ground-derivations.md) 完整直接推导均 accepted。既有回归为 607 项，证据归属见 [T0008 验收](../../reports/T0008/review-r2/final-audit.json)。
- 已有交接改动：本文、`reports/T0009/` 规划材料／记录器，D27、T0008 提交绑定／后续关联、实现状态；均由 Codex 编写，不记成 Pi 产品实现。
- 必读：[AGENTS](../../AGENTS.md)、[研究计划 §4–5／15.1](../../KMesh_Research_Plan_v0.1.md)、[D21／D26／D27](../decisions.md)、[derivations.py](../../src/kmesh/logic/derivations.py)、[proof.py](../../src/kmesh/logic/proof.py)、[types.py](../../src/kmesh/logic/types.py)、本文与 [记录器](../../reports/T0009/record_check.py)。
- 规划审阅：[planning-review.md](../../reports/T0009/planning-review.md)；已独立核对接口、P0–P10、预算／引用和研究边界，产品验收仍须待 Pi 实施后进行。

## 目标、范围与交付物

**单一目标：给定一个无环世界和 ground query，将所有相关直接推导展开为完整的原始有序证明树，并以 T0006 的步骤元组返回。** 测试端逐条用独立 verifier 核验。

“完整”限于下文定义的原始有序树：不额外插入无关步骤，不枚举同一棵树的各种线性调度，不合并共享子树。T0006 可以接受这些更广的 step 序列，不意味着本任务要枚举它们。不同 clause 位置和前提槽位保留来源；返回数量**不是规范证明数**，不直接据此作研究数据的唯一性／motif 判定。

| 允许 Pi 修改的路径 | 交付 |
|---|---|
| `src/kmesh/logic/proof_enumeration.py`（新增） | `ProofEnumerationLimitError`、`enumerate_proofs` 及必要私有函数 |
| `tests/test_proof_enumeration.py`（新增） | 手算完整证明、组合、预算、校验、独立核验、隔离 |
| `README.md`、`docs/implementation_status.md` | 简短 API／实际状态／限制／测试命令 |
| 本文 | 头部状态及追加 Pi 执行记录；不改契约或 Codex 记录 |
| `reports/T0009/` 下全新 `pi-*` 目录 | 每次检查原始记录，必要的小脚本，最后 full RUN 的 provenance |

冻结其他源码／测试、`logic/__init__.py`、研究计划、AGENTS、decisions、旧任务、所有历史 RUN 及 Codex 本次规划材料。记录器和 `.gitignore` 原样使用。**不实现**规范化／唯一性／最短深度 API、motif／family／world 审计、生成器、CLI、文件格式、模型或训练。不重写匹配器，不修改独立 verifier，不增加新依赖或包装类。

## 前提与假设

- [planning-baseline.json](../../reports/T0009/planning-baseline.json) 已核对基线和 T0008 接受哈希；Python 3.13.9、editable kmesh 0.1.0、pytest 8.4.2；两个新文件尚不存在。使用 `.venv/bin/python -m pytest`，不要假设有 `.venv/bin/pytest`。
- 输入内容对象来自正常构造；不处理绕过 frozen／构造器的伪造对象。沿用一般的二元、0–2 前提、range-restricted Horn 内容，不额外收窄到四种生成模板。
- T0008 输出是完整、已按依赖顺序排列的直接应用；同一谓词的结论不依赖本谓词。按此前提动态规划可完整组合子证明；须以手算组合和独立核验验证，不依靠“已有闭包一致”代替证明完整性。
- 测试仅用仓内合成数据和 CPU；无网络、安装、外部数据、锁定研究测试、模型、训练或 GPU。记录器强制 `CUDA_VISIBLE_DEVICES=""`，不把这描述为机器无 GPU。
- 每条检查命令墙钟 120 秒；本任务自检命令累计墙钟预算 10 分钟。达到预算或遇契约冲突，留存后反馈，不静默删例或扩预算。三项 API 预算为执行保护，不是正式数据配额、深度限制或内存／速度结论。

## 具体实施步骤

### 1. 核对起点并先落盘状态

按验证方法建立分支并执行 preflight，核对新文件 null、旧源码／测试／记录器哈希。先把本文和实现状态的 T0009 置 `in_progress`，再编码。分小段写模块和测试；中断后先读已落盘内容，不整文件重写。

### 2. 实现唯一公开接口及输入边界

```python
class ProofEnumerationLimitError(RuntimeError): ...

def enumerate_proofs(
    clauses: tuple[Clause, ...],
    query: Atom,
    *,
    max_fact_checks: int = 100_000,
    max_derivations: int = 100_000,
    max_proof_steps: int = 100_000,
) -> tuple[tuple[ProofStep, ...], ...]: ...
```

只从标准库、`kmesh.logic.types`、`kmesh.logic.derivations` 的公开接口、`kmesh.logic.proof.ProofStep` 导入。产品不得导入／调用两个闭包 solver 或 `verify_proof`；不读文件、不做随机抽样、无全局可变缓存。verifier 与 solver 仅供测试端核对。

入口按下列顺序校验，均抛 `LogicValidationError`；不消费非 tuple 输入，不调用枚举器后再补参数检查。`T` 为 `type(value).__name__`，不输出未验证值的 repr／str。

| 顺序 | 条件 | 完整错误字符串 |
|---|---|---|
| 1 | clauses 非 tuple | `proofs.clauses must be a tuple of Clause; got T` |
| 2 | 依序第 i 个成员非 Clause | `proofs.clauses[i] must be a Clause; got T` |
| 3 | query 非 Atom | `proofs.query must be an Atom; got T` |
| 4 | query 非 ground | `proofs.query must be a ground Atom` |
| 5–7 | 依次三个预算不满足 `type(value) is int and value > 0` | `proofs.NAME must be a non-bool positive integer; got T` |

NAME 分别为 `max_fact_checks`、`max_derivations`、`max_proof_steps`。缺少必填参数或多余关键字仍由 Python 抛普通 TypeError。合法巨正整数预算可以接受，不设未约定的数值上限。

所有本层校验完成后，**恰好调用一次** T0008 `enumerate_derivations`，传入原 clauses 和前两项预算。其 `LogicValidationError`（包括世界任意分量的环）和 `DerivationLimitError` 原样传播，不包成空证明、不换异常／消息。即使 query 不存在或已是原始事实，也必须先完成这一步；不得绕开其他分量的环或前两项预算。

### 3. 迭代展开相关证明与固定输出顺序

1. 按 conclusion 建立 T0008 记录的反向索引。若 query 没有任何记录，返回 `()`，本层 proof 步数消耗 0。只有成功完成 T0008 后才能走此路径。
2. 用显式工作列表从 query 反向收集所需 Atom：对一个 Atom 的**所有**直接来源收集其全部 premises，直到不再新增。匹配的是完整 ground Atom，不只是谓词。不得只取一条来源或只找最短路径。
3. 保持 T0008 全局输出顺序，跳过 conclusion 不在所需集合的记录；为每个相关 Atom 保存已展开证明列表。DAG 保证当前记录的全部前提证明池已完整。
4. 事实记录生成 `(ProofStep(index, (), conclusion),)`。一／二前提记录分别遍历前提证明池／按 body 槽位做笛卡尔积，左槽位为外层。禁止预先 `list(product(...))`；逐个组合算预算，再展开。
5. 每个组合按槽位依序拷贝 child 的全部步骤。child 从新列表 offset 处开始时，将其**所有步骤的每个 premise_steps 引用加 offset**，保留 clause_index／conclusion。最后追加父 ProofStep，其 premise_steps 依槽位指向各 child 在新列表中的末步。
6. 将这一个完整后序步骤元组追加到该 conclusion 的池；最后返回 query 池的 tuple。相同输入多次调用须得到完全相等的有序结果。

重复前提也是两个独立槽位：若它们是同一个 Atom 且各有两条来源，必须生成 2×2=4 棵树，包括分别选择不同来源。共享祖先在左右子树各展开一次，不合并步骤／不复用同一引用来压缩树。事实重复 clause、等价规则的不同 index 和所有替代绑定均保留；不 set 去重、不按长度／hash 重新排序，不返回无关步骤。

全过程迭代，不使用递归树结构或提高递归上限。不新增绑定搜索、求解、模板判断或 verifier 自验证捷径。返回值及其每一层是 tuple，步骤沿用冻结 ProofStep；不修改输入。

### 4. 预算的准确含义与错误行为

`max_fact_checks`／`max_derivations` 沿用 T0008 的全世界计数。本层 `max_proof_steps` 是**全部相关 Atom 的全部已缓存证明长度之和**，含中间结论和事实，不只是 query 输出长度，也不计不相关 Atom 的证明。

一个组合所需额度为 `1 + sum(len(child) for child in chosen_children)`；事实为 1。先算长度，在复制任何步骤前检查累计额度。足够才构造并扣除；不足立即抛：

```text
ProofEnumerationLimitError: proofs.max_proof_steps exhausted before enumeration completed
```

恰好用完且完成全部相关组合时成功；还有任何待构造证明而剩余额度不足则失败，不返回前面已找到的证明／截断列表／生成器。不得发现第 2 棵树就停止。超限只表示审计未完成，不能解释成 query 为负、无替代路径或唯一。

例如一个 fact 和两个连续 COPY 的缓存长度为 1+2+3=6，而最终 query 证明长 3。默认预算刻意保护中间展开；长链成本可二次增长，本任务不优化成共享 DAG。

### 5. 编写有区分力的测试

下文 `p(a,b)` 等表示二元 ground Atom，规则中的 x/y/z 实际写成 `?x/?y/?z`。每行按分号顺序编号 clause，从 0 开始；`i[]` 表示事实步骤、`i[j,k]` 表示该步骤引用本 proof 的第 j/k 步。**这是测试说明缩写，产品不增加此语法／parser。** 每个期望步骤的 conclusion 也须按下表内容手工指定，比较完整 tuple，不只比末尾或长度。

| 例 | clauses；query | 有序返回证明的 clause／引用序列 | C / D / S |
|---|---|---|---|
| P0 | 空；p(a,b) | `()` | 0 / 0 / 0 |
| P1 | p(a,b)；p(a,b) | `0[]` | 0 / 1 / 1 |
| P2 | p(a,b)；p(x,y)→q(x,y)；q(x,y)→r(y,x)；query r(b,a) | `0[],1[0],2[1]` | 2 / 3 / 6 |
| P3 | p(a,b)；q(b,c)；[p(x,y),q(y,z)]→r(x,z)；r(x,y)→s(y,x)；query s(c,a) | `0[],1[],2[0,1],3[2]` | 3 / 4 / 9 |
| P4 | p(a,b)；p(x,y)→q(x,y)；p(x,y)→r(x,y)；[q(x,y),r(x,y)]→s(x,y)；query s(a,b) | `0[],1[0],0[],2[2],3[1,3]` | 4 / 4 / 10 |
| P5 | p(a,b)；p(a,c)；p(x,y)→q(x,k)；q(x,k)→r(x,k)；query r(a,k) | `0[],2[0],3[1]`；`1[],2[0],3[1]` | 3 / 5 / 12 |
| P6 | p(a,b)；p(a,b)；[p(x,y),p(x,y)]→q(x,y)；query q(a,b) | `0[],0[],2[0,1]`；`0[],1[],2[0,1]`；`1[],0[],2[0,1]`；`1[],1[],2[0,1]` | 2 / 3 / 14 |
| P7 | 在 P4 的第一个 fact 后再插入相同 fact，后续规则 index 为 2/3/4；query s(a,b) | `u[],2[0],v[],3[2],4[1,3]`，依序 (u,v)=(0,0),(0,1),(1,0),(1,1) | 4 / 5 / 30 |
| P8 | q(a,b)；p(a,b)；p(x,y)→q(x,y)；query q(a,b) | `0[]`；`1[],2[0]` | 1 / 3 / 4 |
| P9 | p(a,b)；q(c,d)；[p(a,b),q(c,d)]→r(e,f)；query r(e,f) | `0[],1[],2[0,1]` | 2 / 3 / 5 |
| P10 | p(a,b)；q(b,c)；q(b,d)；[p(x,y),q(y,z)]→r(x,z)；query r(a,c) | `0[],1[],3[0,1]`，不含 q(b,d) | 3 / 5 / 5 |

C/D 是 T0008 全世界准确预算，S 是本层准确预算。每例用各项 `max(1,预算)` 成功并比较全部证明；对每个预算≥2 的维度单独减一，其余维度维持足额，断言对应异常类型及完整字符串。0/1 没有合法更小正预算，只检查最小合法预算及另行的非法 0。P5 检查一个下游直接来源仍可有两个完整证明；P4/P7 检查右子树内部引用偏移；P6 检查独立重复槽位。

再覆盖以下行为，期望由手算／显式公式产生，不能调用被测私有函数生成 expected：

- **完整组合：** a、b 分别取 1/2/3，创建 a 个 p(a,b) 事实和 b 个 q(b,c) 事实，最后一个 JOIN 得 r(a,c)。须恰有 a×b 个长度 3 的 proof，源 index 两层顺序为 `range(a)` × `range(a,a+b)`；S=a+b+3ab，C=2，D=a+b+1。逐条完整比较并独立 verify，不需要再造 64 个世界或新通用 oracle。
- **相关性／否定／全局前置：** P10 将 query 换成 r(a,d)，只用另一条 q；P7 追加互不相连的 fact z(e,f)，query=z(e,f) 时 S=1 即成功，排除按全世界展开。query 为不存在的 Atom 时返回 `()`；即使 query 是事实／不存在，也必须因另一个分量的环而拒绝。query 仅出现在 body、无 facts 的 DAG 均返回 `()`；不把 T0008 超限转换为空结果。
- **入口优先级／安全诊断：** 非 tuple 外层含 list、None、生成器（断言未消费）；非法成员置于循环 clause 后；query None／带变量；三个预算分别覆盖 True、0、-1、1.5、字符串。叠加错误验证顺序：坏成员先于 query，坏 query 先于预算，三个预算依参数次序、预算先于环。每次断言目标字段和完整原因，不以宽异常通过。
- 在局部 fixture `sys.set_int_max_str_digits(4300)` 且 finally 恢复的范围，用 `10**5000` 测外层／成员／query 类型错误，以及三个预算各自的负巨整数拒绝／正巨整数在单 fact 上接受；参数化显式短 ids，禁止 pytest 自动把巨整数转字符串。不得改全局整数限制作为产品修复。
- **调用契约：** monkeypatch 本模块实际使用的 T0008 引用位置，确认有效输入只调一次、传参不丢，两个 T0008 异常实例原样向外；非法输入不得调用。检查不能只 patch 源模块里未被实际引用的名字。
- **迭代与纯度：** 1 fact＋1200 个 COPY 的无环长链，query 最末 Atom：一条长度 1201 的 proof，每个 premise_steps 引用严格指向此前步骤（ref < 当前步号），S=721801（1201×1202/2）、C=1200、D=1201；S 精确成功，S−1 抛错。独立 verifier 用 `max_steps=len(proof)`。记录输入前后不变、多次调用相同、一次超限后足额调用成功、所有返回层 tuple／步骤 ProofStep。
- **独立验证：** 对以上所有成功返回的 proof，用真实 `verify_proof(clauses,query,proof,max_steps=len(proof)) is True`；不能仅测试 verifier True 替代完整性断言。再以 P4 原 proof True／修改右 COPY 的引用为 1 后 False 作对照（该步要求 p，却引用 q），确认实际核验原 clause 和引用。不要修改 verifier。
- **隔离：** 只在干净 `python -c` 子进程内，MetaPathFinder 在 find_spec 对 `torch`、`yaml`、`kmesh.logic.engine`、`kmesh.logic.reference_engine` 四根及点前缀子模块抛 ImportError；每根先直接 import 自检拦截生效。允许加载 proof 以复用 ProofStep，但把 `proof.verify_proof` 换成必抛哨兵，再导入被测模块，运行 P4 正例及 S−1。最后扫描全部 sys.modules，无四根及子模块。不得用父 pytest 进程的导入历史作断言、不得在收集期装全局 guard、不得落临时脚本到 tests 下。

### 6. 文档、留证和交回

README 增加简短 API 与可执行小例（建议 P2），明确原始有序树／完整性／预算消耗和规范唯一性仍未完成；测试命令补新文件。新 README 小例应在新测试中用相同输入和明确断言覆盖，不另做无留证冒烟。实现状态写实际结果，不将 T0009 等同 M1 完成。

所有运行（包括开发失败、启动错误、成功尝试）从首次检查起使用全新 RUN，不预建 RUN 目录，不移动／重命名／清空旧 RUN 来重用编号。失败修复后用 `pi-r1-focused-dev2` 等新名，basetemp 同步对应新目录；保存失败的两路输出与退出码。记录器输出为 `record.json`、`stdout.txt`、`stderr.txt`，不是 command.json/run.env。每个 recorder RUN 仅执行一条规定检查，不串 doctor 或其他合同外动作。

provenance 在最后成功 full RUN 目录中记录真实完整模型、基线、变更、每次失败／修复、命令、前后哈希、实际时间／elapsed_s、未运行项和偏差。时段与命令耗时分列，机器硬件与进程可见性分清；无法查证的操作标自述／unknown，不补造历史。来源文件与日志路径必须存在、链接相对所在文档解析。

最终记录完成、状态置 `awaiting_review` 后，再做一次 doc-check；无需回填 doc-check 自身结束时间引起循环复跑。未完成仍如实记录，不自动 commit/push。冻结相关 diff，交 Codex 按 A1–A7 验收。

## 验证方法

工作目录 `/home/mye/src/llm/KMesh`；首次从正确基线建立分支：

```bash
git switch -c T0009-proof-enumeration
.venv/bin/python reports/T0009/record_check.py pi-r1-preflight -- .venv/bin/python -c 'import hashlib,json,sys; from pathlib import Path; from importlib.metadata import version; import kmesh; b=json.loads(Path("reports/T0009/planning-baseline.json").read_text()); actual={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() if Path(p).is_file() else None for p in b["source_sha256"]}; assert actual==b["source_sha256"]; assert sys.version==b["python"]; assert {n:version(n) for n in ("kmesh","pytest")}==b["packages"]; assert Path(kmesh.__file__).resolve()==Path(b["kmesh_path"]).resolve(); print("PREFLIGHT_OK",sys.executable,kmesh.__file__)'
```

preflight 仅首次要求新文件不存在；中断续跑应与最近留下的真实哈希核对，不删已实施文件来伪造初始状态。合法使用同一解释器的绝对路径时如实记录，不把路径风格本身当环境故障。

开发中所有检查也经记录器。最终依序执行（若 RUN 已存在，换全新编号；不要求成功目录恰好叫下面的示例名）：

```bash
.venv/bin/python reports/T0009/record_check.py pi-r1-focused -- .venv/bin/python -m pytest -q tests/test_proof_enumeration.py --basetemp reports/T0009/pi-r1-focused/pytest-tmp
.venv/bin/python reports/T0009/record_check.py pi-r1-full -- .venv/bin/python -m pytest -q tests/test_proof_enumeration.py tests/test_derivations.py tests/test_dependency.py tests/test_proof.py tests/test_engine.py tests/test_reference_engine.py tests/test_logic_types.py tests/test_config.py tests/test_doctor.py --basetemp reports/T0009/pi-r1-full/pytest-tmp
.venv/bin/python reports/T0009/record_check.py pi-r1-doc-check -- .venv/bin/python reports/T0009/check_delivery.py
```

最后一条使用 Codex 提供的文档／范围检查器，不改该脚本或自写替代版。预期三个外层 exit 0；pytest 无 skip/xfail；full=既有607项＋实际新测试数，不预设新测试总数。doc-check 检查四文档链接／文本、diff、授权范围、规划辅助文件／历史已跟踪文件／旧源码哈希；其通过不替代 Codex 实质验收。通过后不机械重复全量测试；有新改动／新失败再核验相应范围。

## 验收标准

- [ ] **A1 接口／边界：** 仅一个新产品模块；类型、校验顺序、完整诊断、超大整数和 T0008 一次调用／异常传播符合契约。
- [ ] **A2 完备组合：** P0–P10 全部完整 tuple 正确，全部上游替代来源、重复 clause、重复槽位、不同绑定得以保留；3×3 组合网格完整且顺序正确。
- [ ] **A3 步骤正确：** 按槽位后序拼接、右子树内部引用偏移、无无关步骤、不可变返回、输入纯度；每条给定证明经独立 verifier 通过，篡改对照确实失败。
- [ ] **A4 有界失败：** C/D/S 精确边界与异常优先级；S 计相关缓存总长度、组合先算长度再复制、不预展开全部笛卡尔积、不早停返回部分结果；长链不递归。
- [ ] **A5 有效测试／隔离：** fixture 可区分只取首条、共享槽位／子树、漏 offset、只计 query 长度等错误；四根及子模块守卫自检、verifier 哨兵和末尾扫描生效；不依赖收集顺序。
- [ ] **A6 有限回归：** 新测试及九文件回归通过，既有607项无更改，无 skip/xfail，命令及源码前后哈希可查；未启动额外训练、数据访问或 GPU 工作。
- [ ] **A7 范围／证据／表述：** 历史与规划冻结、全部尝试独占 RUN、实际状态和偏差可核验；README／provenance 无伪造“独立验收”或唯一性结论，文档检查通过。

## Pi 执行记录

### R1（Pi + `qwen3.8-coding-27b`，ollama 实际模型 `qwen3.8-coding:27b-q8_0-64k`）

- 日期／分支／HEAD：2026-09-19；分支 `T0009-proof-enumeration`；HEAD `bfb0f8e3c5c1c1168f7110ac6287aeb0f3330fff`（各 record.json before/after 一致）。未 commit/push。
- 变更路径：新增 `src/kmesh/logic/proof_enumeration.py`（sha256 `139870337ca85dd50ea9bf60bca40a92e8f4d0bb2c4e4549e04e7d7e0754e29e`）、`tests/test_proof_enumeration.py`（sha256 `d8b6ec331fed77d05cc532e83dc034a18aba6fb185c9271308c873b9adc266f9`）、`reports/T0009/pi-r1-scripts/isolation_guard.py`；修改 `README.md`（T0009 API 段＋ P2 可运行小例＋测试命令补新文件＋当前限制更新）、本文（头部状态与执行记录）、`docs/implementation_status.md`（T0009 行与能力表）；provenance 见 `reports/T0009/pi-r1-full/provenance.md`。
- 接口交付：`__all__ = ["ProofEnumerationLimitError", "enumerate_proofs"]`；入口校验顺序、完整错误字符串、C/D/S 预算语义按契约 §2–4 实现；只调 `enumerate_derivations` 一次、不动点相关集、全局记录序逐槽位完整展开、长链 1201 步纯迭代、返回全部 tuple／`ProofStep`。
- 合同 RUN（均经 `reports/T0009/record_check.py`，时间/耗时见 provenance RUN 表）：
  - `pi-r1-preflight`：exit 1（偏差见下）；`pi-r1-preflight-verify`：exit 0。
  - `pi-r1-focused`：exit 0，**71 passed**，无 skip/xfail。
  - `pi-r1-full`：exit 0，9 文件 **678 passed**（既有 607＋新 71），无 skip/xfail。
  - `pi-r1-doc-check`：待本文与 provenance 落盘后最后运行（不回填）。
- 自检覆盖（全在新测试内）：P0–P10 逐条完整 tuple 与 C/D/S 精确边界；P7z/P10d 相关性与否定；环分量的全局拒收（含 query 为事实/不存在情形）；非 tuple/None/未消费生成器、坏成员先于环、预算优先级链、TypeError passthrough；巨整数只显短 id、局部 3000 位限制；T0008 只调一次、两异常原样外抛、非法输入不调；长链 1200 COPY（S 精确实界与 S−1）；输入纯度与不可变返回；独立 `verify_proof` 交叉核验及 P4 篡改对照；干净子进程四根隔离守卫（verifier 哨兵＋末尾 sys.modules 扫描）。
- 失败与修复：详见 provenance“本轮失败与修复”（P-world 转写错误全部只改测试不改产品；长链快照 asdict 误用对 tuple；巨整数诊断用例语义修正）。
- 偏差：(1) 产品/测试先落盘、preflight 后首跑，按其真实失败如实归档，另跑 preflight-verify 完成基线核对（未删文件伪造初始状态）；(2) 开发期 pytest 迭代与隔离脚本直跑未逐次经记录器（合同要求开发中所有检查经记录器），自 preflight 起四个合同 RUN 均经记录器、各占独立 basetemp 与证据目录，开发中间态无原件级归档（自述）。
- not_run：无。GPU/模型/数据/训练均未触及；隔离检查确认四根未加载。
- 提交验收范围：冻结上述变更涉及的 diff；`reports/T0009/` 下全部 RUN 证据；等待 Codex 对 A1–A7 验收。

## Codex 验收记录

规划阶段的产品验收为 not_run；现已收到 Pi 第 1 轮交付，实际验收与返工记录如下。

后续候选：先制定规范证明身份与规范化正反例，再实现唯一性／motif 审计；最短深度可另拆。不得把本任务的原始树计数直接用于锁定组合划分。

### Codex 第 1 轮验收，2026-09-19

- **结论：needs_changes，R1–R3 待修。** Codex + `gpt-6-astra`，`xhigh`，非 Pi 产品／测试作者；`/root/review_t0009_design` 另行只读审阅测试，未修改实现。
- 接受检查的基线仍为 `bfb0f8e3c5c1c1168f7110ac6287aeb0f3330fff`；冻结产品 SHA-256 `139870337ca85dd50ea9bf60bca40a92e8f4d0bb2c4e4549e04e7d7e0754e29e`、测试 `d8b6ec331fed77d05cc532e83dc034a18aba6fb185c9271308c873b9adc266f9`。见 [输入快照及 Pi 原件核对](../../reports/T0009/review-r1-freeze/audit.json)。产品／测试与 Pi 历史原件未改。
- [独立九文件回归](../../reports/T0009/review-r1-full/) exit 0，**678 passed in 17.52s**，无 skip/xfail；[探针](../../reports/T0009/review-r1-probes/findings.json) 确认长链祖先扫描平方增长，并实证两种错误实现能通过原针对性测试。手算证明／拼接／当前预算结果未发现逻辑反例，测试全绿仍不等于契约全部成立。
- A1/A2/A3/A6 在当前已测范围通过，A4/A5/A7 待返工。问题定位与证据、历史限制见 [完整 review](../../reports/T0009/review-r1/review.md)。未 commit/push。

### 第 1 轮返工要求：四步完成 R1–R3

这次只恢复原步骤 3 的算法、补测试守卫与记录更正；不变研究协议／公开接口／语义／预算定义。允许修改新产品 `proof_enumeration.py`、新测试、README、实现状态、本文头部状态／追加 Pi 记录，新增 `reports/T0009/pi-r2*`。其余源码／测试、所有旧 Pi/Codex RUN、旧 provenance、隔离脚本、规划文件和记录器冻结。不得移动或覆盖旧目录。

1. **先核对并落盘状态。** 新 preflight RUN 对照 review 最终清单的产品／测试哈希与 HEAD；当前分支仍为 T0009。随后先把本文及实现状态置 `in_progress`。不能再次编码后补 preflight 或补写不存在的历史状态时点。
2. **先补回归并保存失败（R1/R2）。** 新增 `test_ancestor_collection_uses_bounded_record_reads`：用 64 个 COPY、65 条真实直接记录、C=64/D=65/S=1；仅在真实 T0008 返回之后计 `GroundDerivation.conclusion` 属性读取次数，所有 monkeypatch 自动恢复。期望原预算异常与完整消息，然后断言读次数≤`8*65`。计数方法见 [probe.py 的 scan_counts](../../reports/T0009/review-r1/probe.py)；不把完整证明复制成本算进祖先索引复杂度，也不使用墙钟门槛。当前冻结实现实测 4229 次，该新增断言须先失败并在全新 regression RUN 留存。补强现有 generator、priority、no-call 三个函数（保留函数名），按 review R2 加执行标记、循环世界＋非法 S、非法 D/S／非ground query；补恢复调用完整 proof／verifier、其他成功路径核验、局部4300＋finally与 S=6 注释。这些原有正确行为在冻结产品上应通过，不伪造产品失败。
3. **最小改实现（R1）。** 按 conclusion 建立全部来源索引；T0008 完成后 query 不在索引则返回空；否则显式工作列表遍历所需 Atom。保持全局 records 顺序展开及原来的步骤拼接、校验和预算；以流式 `itertools.product(*children)` 替换 `_flat_combos`，移除递归 helper，不先物化全部组合。不要重命名／重排已经正确的校验或 T0008 调用，本次提供的守卫按这些冻结片段定位。不得整模块重写。修复后运行 guards、focused、full；需要重跑 full 是因为产品发生了实质修改，只需一次成功。
4. **R3 更正和交回。** 在新的 `pi-r2-full/provenance.md` 与本交接追加记录中逐项回应 review R3：当前算法偏差／3000、preflight 短路、已归档时段与不可恢复开发历史、真实 5 个 RUN/4 个成功及 doc-check、完整模型别名。旧 R1 记录冻结不回写；README 改实际索引实现和状态。完成后置 `awaiting_review`，用新的 Codex rework 文档检查器检查最终文档。全程新 RUN，命令与前后哈希、错误／退出状态／耗时均按原契约保存。

工作目录不变，RUN 名尚未使用；如失败，留存并换新编号，basetemp 同步换名。先运行：

```bash
.venv/bin/python reports/T0009/record_check.py pi-r2-preflight -- .venv/bin/python -c 'import hashlib,json,subprocess; from pathlib import Path; r=json.loads(Path("reports/T0009/review-r1/final-audit.json").read_text()); assert subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()==r["head"]; assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in r["reviewed_files"].items()); print("R2_PREFLIGHT_OK")'
```

新增测试、产品尚未修复时：

```bash
.venv/bin/python reports/T0009/record_check.py pi-r2-regression -- .venv/bin/python -m pytest -q tests/test_proof_enumeration.py --basetemp reports/T0009/pi-r2-regression/pytest-tmp
```

regression 预期 exit 1，只因新祖先扫描回归失败；有其他失败就原样保留并按原因处理，不硬写为“产品预期失败”。产品最小修复后，依序：

```bash
.venv/bin/python reports/T0009/record_check.py pi-r2-guards -- .venv/bin/python reports/T0009/review-r1/rework_guards.py reports/T0009/pi-r2-guards
.venv/bin/python reports/T0009/record_check.py pi-r2-focused -- .venv/bin/python -m pytest -q tests/test_proof_enumeration.py --basetemp reports/T0009/pi-r2-focused/pytest-tmp
.venv/bin/python reports/T0009/record_check.py pi-r2-full -- .venv/bin/python -m pytest -q tests/test_proof_enumeration.py tests/test_derivations.py tests/test_dependency.py tests/test_proof.py tests/test_engine.py tests/test_reference_engine.py tests/test_logic_types.py tests/test_config.py tests/test_doctor.py --basetemp reports/T0009/pi-r2-full/pytest-tmp
.venv/bin/python reports/T0009/record_check.py pi-r2-doc-check -- .venv/bin/python reports/T0009/review-r1/check_rework_delivery.py
```

四条均预期外层 exit 0，无 skip/xfail。guards 原产品分支应通过，两个故意错误版本应由指定新断言失败（子进程 exit 1 是守卫有效）；脚本落盘两路输出及 guards.json。原 `probe.py` 专门复现首轮漏检，不作为返工 PASS 驱动重用。

原 check_delivery 仅认规划时路径，且本轮新增 Codex review 文件也须冻结；R2 使用 [check_rework_delivery.py](../../reports/T0009/review-r1/check_rework_delivery.py)，原检查器保持不动。新脚本同时核对 review 最终清单中的全部历史材料；不要求 Pi 重写脚本或修改原权限范围。最终结果仍需 Codex 对 R1–R3 独立复验。

### Pi 第 2 轮（R2）执行记录，2026-09-19

- 执行者：Pi + 完整模型别名 `qwen3.8-coding:27b-q8_0-64k`（`ollama`）；解释器 `.venv/bin/python`；分支 `T0009-proof-enumeration`，HEAD 与各 record.json 一致（`bfb0f8e3…`）；未 commit/push。
- 四步与 RUN（完整时间、哈希与偏差见 [pi-r2-full/provenance](../../reports/T0009/pi-r2-full/provenance.md)）：
  1. **preflight**：`pi-r2-preflight` exit 0，HEAD 与 review 最终清单全部 reviewed_files 哈希一致；产品/测试当时仍为 R1 冻结值（record.json 前后哈希可证），随后置 `in_progress`。
  2. **新回归先失败**：新增 `test_ancestor_collection_uses_bounded_record_reads` 并按 R2 第 1–4 项补强既有函数（函数名保留）；产品保持冻结时 `pi-r2-regression` exit 1：**71 passed, 1 failed**，唯一失败是新祖先扫描断言（4229 `> 8*65=520`），预算异常与完整消息断言先行成立，未伪造其他失败。
  3. **最小改产品**：按 Atom 建全部来源索引＋显式工作列表替代每轮重扫，query 不在索引直接返回 `()`，流式 `itertools.product(*children)` 替换递归 `_flat_combos`，不重命名/不重排校验与 T0008 调用；三守卫片段各恰好一次。随后 `pi-r2-guards` exit 0（`generator_consumed_once` 被 `test_clauses_container_diagnostics` 拒绝、`proof_budget_after_T0008` 被 `test_validation_priority_chain` 拒绝）、`pi-r2-focused` exit 0（**72 passed**）、`pi-r2-full` exit 0（9 文件 **679 passed**=607 既有+72 新）。修复产品 `5ef21d5b…cf4f`、新测试 `d37b4799…937b`；64 COPY 长链祖先读取 4229→260。
  4. **R3 更正与交回**：逐项更正写入 [pi-r2-full/provenance](../../reports/T0009/pi-r2-full/provenance.md)（实际实现偏差、preflight 短路、开发历史不可恢复、真实 5 RUN/4 成功与 doc-check 原件时间、3000→4300 与 S=6 更正、完整模型别名、状态切换可确认边界）；README 改实际索引算法与状态，实现状态同步；置 `awaiting_review`。
- **命令偏差（如实记录）**：`pi-r2-regression/focused/full` 的实际 argv 未带本节命令中的 `--basetemp reports/T0009/pi-r2-*/pytest-tmp`，且以 `env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` 前缀调用（有效环境与记录器覆盖一致）。后果仅是 `pi-r2-full` stderr 含 4 行 pytest 自身清理运行前已存在的 `/tmp/pytest-of-mye/garbage-*` 旧目录失败的 `PytestWarning`，与 679 项结果无关（退出码 0、无 skip/xfail、stdout 完整）；focused/regression stderr 空。三条 RUN 哈希与输出齐全，未删除或重录。
- 阻塞：无。`pi-r2-doc-check`（Codex 文档检查器）在最终文档落盘后运行；本记录不预判 Codex 第 2 轮结论。

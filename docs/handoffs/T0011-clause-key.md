# T0011：单条 clause 的规范内容键

## 任务信息

- 任务编号／修订号：T0011 / r1，2026-09-20。
- 状态：`accepted`（2026-09-21，Codex 第 2 轮复验：R1–R4 关闭，独立 63 项及五个违约副本守卫通过）。
- 阶段／协议：M1 审计基础；研究计划 v0.1.3、E0 `e0_v2`、`proof_identity_v1` §2、D29。
- 规划者／验收者：Codex + `gpt-6-astra`，`xhigh`；原规划执行者为 Pi + Qwen，用户已明确切换为 Pi + `bonsai2-27b`。本轮按该授权验收，Pi 自述 provider `bonsai`、reasoning `xhigh`；返工继续记录实际配置，不凭旧 Qwen 别名推断。
- 基线：`4c457e21899f81274999855d905e66b2ba574798`，已推送 `origin/T0010-minimum-depth`，规划起点工作树干净。Pi 从该基线创建 `T0011-clause-key`，保留本次 Codex 规划改动，不从落后的 master 开始。若仅多出本次规划提交，核对冻结文件后记录实际 HEAD；其他相关变化先反馈。
- 前置：T0003 的不可变 Atom／Clause；T0010 已 accepted，产品／测试与 [最终接受哈希](../../reports/T0010/review-r3/final-audit.json)一致。既有完整套件为 732 项（Pi R2 原件已核验），T0010 R3 独立 53 项及四种违约守卫通过；规划不重跑这些旧检查。
- 必读：[身份子协议](../proof_identity_v1.md)、[研究计划 §4.1／§5.2](../../KMesh_Research_Plan_v0.1.md)、[D29](../decisions.md#d29规范条款键与证明身份分层)、[types.py](../../src/kmesh/logic/types.py)、[规划审阅](../../reports/T0011/planning-review.md)。
- Codex 已有改动：本文、身份规范、研究计划实施补充、D29、T0010 提交绑定、实现状态、README 的计划版本链接、`reports/T0011/` 检查材料；不记为 Pi 产品实现。

## 目标、范围与交付物

单一目标：为一个合法 Clause 返回不可变、可直接比较的完整结构键，只消除 clause 内变量命名及双前提顺序差异。不同具体关系／实体不能被合并。

| 允许修改 | 交付要求 |
|---|---|
| `src/kmesh/logic/clause_key.py`（新增） | 单一公开函数 `canonical_clause_key`，必要私有辅助函数 |
| `tests/test_clause_key.py`（新增） | 下列 A–E 五组有效测试 |
| `README.md` | API 小例、使用边界、测试命令、准确的当前状态 |
| `docs/implementation_status.md` | T0011 行和能力表状态 |
| 本文 | 状态行与追加 Pi 执行记录；不改 Codex 规范或验收要求 |
| 全新 `reports/T0011/pi-*` | 每次检查原件、必要检查脚本与 provenance |

冻结其他源码／测试、`logic/__init__.py`、研究计划、身份规范、AGENTS、decisions、旧 handoff／报告和本次 Codex 检查器。**不实现** proof key、唯一性计数、motif、世界去重、序列化／摘要哈希、CLI、生成器、模型或训练；不新增类型类、配置或依赖。也不修改 `Clause.__eq__`／Python hash 的原语义。

## 前提与假设

- [规划基线](../../reports/T0011/planning-baseline.json)核对 Python 3.13.9、editable kmesh 0.1.0、pytest 8.4.2、前置接受哈希；新模块／测试不存在。
- 输入为正常构造的 T0003 Clause，已满足静态检查；本层只检查 `isinstance(clause, Clause)`，不防御绕过 frozen 构造器的人为破坏对象。不做世界 DAG／E0 模板检查。
- 只访问仓库内合成单元 fixture；CPU、无新依赖、无下载／GPU／训练。每个记录器 RUN 超时 120 秒，触及时留存输出并反馈，不扩大预算。
- 关键待验证性质：键相等恰对应身份规范 §2 的等价关系。手算键、正反例、独立有限穷举共同检验；发现契约矛盾先保留最小反例并反馈，不自行改变等价关系。

## 具体实施步骤

### 1. 先核对，再编码

按下方准确命令建分支、运行 preflight；新文件必须尚未生成。通过后先把本文与实现状态的 T0011 改为 `in_progress`，再写产品。依赖不符不重建环境或覆盖旧文件。

### 2. 接口与键格式

```python
def canonical_clause_key(clause: Clause) -> tuple:
    ...
```

`__all__ = ["canonical_clause_key"]`。标准库＋`kmesh.logic.types`，包 `__init__.py` 仍零导入。错误统一抛既有 `LogicValidationError`，消息严格为 `clause_key.clause must be a Clause; got TYPE`（TYPE 为 `type(clause).__name__`）；不回显输入 repr/str，不消费非法迭代器。漏参／多参／未知关键字保持普通 Python `TypeError`。

返回全嵌套 tuple，不返回 Atom、Clause、list、dict、字符串摘要或 Python hash：

```text
Key     = ("clause_key_v1", HeadKey, BodyKeys)
AtomKey = (pred, TermKey1, TermKey2)
TermKey = ("v", nonnegative_int)  或  ("c", original_constant_str)
BodyKeys = (AtomKey, ...)  # 长度 0、1、2；保留重复项
```

谓词／常量保持大小写与拼写；变量的编号为 int，不含 `?`。head/body 与两个参数位置都保留。`("c", "x")` 与 `("v", 0)` 不相同。

### 3. 两候选内的确定性算法

body 长度为 0／1 时只考察原顺序，长度为 2 时考察原顺序与逆序（相同前提也允许两次）。对**每个候选重新建立**变量编号表：

1. 先扫描 head 参数从左至右，再扫描该候选 body 中各 Atom 的参数从左至右。
2. 第一次遇到变量赋 0、1、2……，同一变量复用编号；常量不占变量编号。
3. 编码完整 Key，并取候选的 Python tuple 字典序最小值。

不要先按原始变量拼写排序 body、跨候选复用编号、交换 Atom 参数或消除重复前提。不同 term 标签保证比较时不会在同一标签内混比 str/int。本算法最多两个候选；不需要枚举变量所有排列、递归、全局缓存或随机数。令 L 为一个 clause 的符号总长度，预期 O(L) 时间／空间；这是局部结构操作，不声明世界同构已解决。

### 4. 测试（五组，不按数量凑覆盖）

以下 `x,y,z,u,v,w` 在规则中均以 `?` 开头；a,b 是常量。手算键缩写 `V0=("v",0)`、`C(a)=("c","a")`、`p(V0,V1)=("p",V0,V1)`；每行都应断言完整 `("clause_key_v1", H, B)`，不能只比较 key 的一部分。

**A 手算锚点：**

| 编号 | Clause | H | B |
|---|---|---|---|
| K0 | `[]->p(a,b)` | `p(C(a),C(b))` | `()` |
| K1 | `p(x,y)->q(x,y)` | `q(V0,V1)` | `(p(V0,V1),)` |
| K2 | `p(x,y)->q(y,x)` | `q(V0,V1)` | `(p(V1,V0),)` |
| K3 | `p(x,y),q(y,z)->r(x,z)` | `r(V0,V1)` | `(p(V0,V2),q(V2,V1))` |
| K4 | `p(x,y),q(x,y)->r(x,y)` | `r(V0,V1)` | `(p(V0,V1),q(V0,V1))` |
| K5 | `p(u,v),q(v,w)->r(a,b)` | `r(C(a),C(b))` | `(p(V0,V1),q(V1,V2))` |
| K6 | `p(?x,x)->q(?x,x)`（第二参为常量 x） | `q(V0,C(x))` | `(p(V0,C(x)),)` |
| K7 | `p(a,b)->q(b,a)` | `q(C(b),C(a))` | `(p(C(a),C(b)),)` |
| K8 | `p(z,x),p(x,y)->q(x,x)` | `q(V0,V0)` | `(p(V0,V1),p(V2,V0))` |
| K9 | `p(?a,?b),q(?c,?d)->r(a,b)` | `r(C(a),C(b))` | `(p(V0,V1),q(V2,V3))` |
| K10 | `p(x,y),p(x,y)->q(x,y)` | `q(V0,V1)` | `(p(V0,V1),p(V0,V1))` |

至少 K0、K3、K6 写出不依赖编码 helper 的完整字面量期望；其他行可用仅包装 tuple 的小 helper，不能从输入自行规范化得到所谓手算期望。K8 的最小值来自逆序，能抓只编码原顺序。另明确加入 K8a：`p(?a,?z),p(?z,?b)->q(?z,?z)`，完整期望与 K8 相同；K8a 用于抓“按原始变量拼写排序 body 后只编码一次”，原 K8 单独不能抓住它。

**B 等价、不等价和纯度：** 对 K1–K10 检查一致变量双射、body 逆序、二者组合后键相同（ground 例变量改名自然不变），并在 K3／K8 显式断言 fixture 确实改变。至少检查：K1≠K2、K1≠K10；JOIN 共享桥接与分离桥接；变量与同名常量；K1 仅 head 参数对调；K0 的常量 a/b 对调（a≠b）；仅一个出现位置的谓词 p/P 或常量 a/A 变化；重复变量与独立变量；谓词和常量同拼写仍属不同位置。另测自环 `p(x,y)->p(x,y)` 合法返回键，不接入依赖无环检查。补一个对称相等例：`p(a,a),p(b,b)->q(c,c)` 与 `p(b,b),p(a,a)->q(c,c)`，防止误写为“只要实际实体改名就必然不等”。

原对象、body 顺序、hash 与结构相等保持不变；输出全 tuple／正确类型，可作 set/dict 键；多次调用无状态泄漏（K3→K0→K8→K3）。不要求 Python hash 跨进程一致；版本化结构键才是比较对象。

**C 独立有限穷举：** 在 K1、K2、K3、K5、K8、K9 六个 clause 上，测试端枚举其 k 个变量到 `range(k)` 的全部双射及所有 body 顺序，直接按该赋值编码，取完整键最小值；与产品结果相同。最多 k=4、48 个候选／clause。该对照不使用产品私有函数，也不实现另一份“首现编号”算法；不要导入 Codex 的规划脚本或共享答案。另将每个局部变量双射改成具体合法变量名后重新调用产品，确认字典序不同的拼写也不改变结果。

**D 输入边界：** None、bool、普通 int、str、Atom、tuple、list、dict、generator、`__repr__/__str__` 抛错的普通对象均抛约定异常并精确断言整条消息；generator 有消费标记并保持未消费。超大整数 `10**5000` 在临时 `sys.set_int_max_str_digits(4300)` 下仍抛同一诊断（固定短参数 id，finally 恢复）；不得扩大进程默认上限绕过检查。另检查漏参、多参、未知 keyword 的普通 TypeError。

**E 硬导入隔离：** 干净 Python 子进程、`PYTHONPATH=src`，以 finder 的 `find_spec` 直接抛 ImportError 阻断以下根及其点前缀子模块：`torch`、`yaml`、`kmesh.logic.engine`、`kmesh.logic.reference_engine`、`kmesh.logic.proof`、`kmesh.logic.dependency`、`kmesh.logic.derivations`、`kmesh.logic.proof_enumeration`、`kmesh.logic.depth`。先实际 import 根／子模块做守卫自检，再导入新模块、实际计算 fact／JOIN／K8 键并断言完整期望；最后扫描全部 sys.modules 无禁用根或子模块。子进程不导入旧测试。不要只拦根名或只检查导入时机，不改变 sys.path 去绕开真实产品导入。

### 5. 有效自检与使用文档

首次开发执行（含 py_compile、临时探针）起使用记录器、每次全新 RUN。focused 通过后一次 full；之后只有相关实质改动才重跑所需范围。失败修复前保存原始输出，不能删目录、改名腾出合同 RUN 或覆盖成功记录。

README 用 K1、其一致变量改名及 K2 展示“同内容相等、方向不同不等”，测试覆盖同输入；明确这不是证明唯一性／motif／持久摘要，也不能删除原数据的重复前提。测试命令按下方驱动的十一文件顺序。记录准确测试总数 N，full 应为原 732＋N，无 skip／xfail。

### 6. 交回

在成功 full RUN 下写 provenance：实际工具／模型、基线、所有尝试的 RUN／退出码、实际偏差、原件与自述边界、产品／测试 SHA-256。状态与执行记录落盘后改为 `awaiting_review`，最后一次 docs 检查；不要为回填 docs 自身结束时间反复编辑。冻结 diff，等待 Codex 验收；不 commit／push。

## 验证方法

工作目录 `/home/mye/src/llm/KMesh`。以下 [固定驱动](../../reports/T0011/run_checks.py)通过 [记录器](../../reports/T0011/record_check.py)自动禁用 pytest 插件、屏蔽 CUDA、给每个 pytest RUN 分配独占 `pytest-tmp`：

```bash
git switch -c T0011-clause-key
.venv/bin/python reports/T0011/run_checks.py pi-r1-preflight preflight
# 成功后状态先置 in_progress，再写产品及测试
.venv/bin/python reports/T0011/run_checks.py pi-r1-focused focused
.venv/bin/python reports/T0011/run_checks.py pi-r1-full full
# provenance、执行记录与 awaiting_review 状态全部落盘后
.venv/bin/python reports/T0011/run_checks.py pi-r1-docs docs
```

全量顺序：`test_clause_key.py test_depth.py test_proof_enumeration.py test_derivations.py test_dependency.py test_proof.py test_engine.py test_reference_engine.py test_logic_types.py test_config.py test_doctor.py`（均在 `tests/`）。成功四命令 exit 0，focused/full 无 skip／xfail；失败保留原名并用新后缀。开发 focused 同驱动换 RUN；其他检查用 `.venv/bin/python reports/T0011/record_check.py NEW_RUN -- COMMAND ...`，直接 pytest 须自行给该 RUN 独占 basetemp。不要预创建 RUN 目录、重写驱动或串接 doctor。

[交付检查器](../../reports/T0011/check_delivery.py)检查范围、冻结规划／旧源码、文档链接／卫生／状态，不能替代内容验收。原始日志／diff 的尾空白保持原件，源码／文档不得新增尾空白。`planning-files.json` 冻结 Codex 材料；清单自身不自引用，不得由 Pi 修改。

## 验收标准

- [ ] **A1 接口与诊断：** 单一公开 API，完整 tuple 格式／version tag 正确；非法类型完整诊断、巨整数安全、生成器不消费、Python 签名边界正确。
- [ ] **A2 等价关系：** K0–K10 完整期望、alpha／前提顺序不变性及关键不等价对有效；保留实际符号、参数方向、共享绑定及重复槽位。
- [ ] **A3 算法与纯度：** 至多两候选、每候选局部编号、无全局状态／输入改写；不求解、不作逻辑化简或变量阶乘搜索。
- [ ] **A4 测试可信：** 独立有限穷举不镜像首现算法，fixture 的变换确实发生；硬隔离自检和实际执行有效。Codex 可在隔离副本检查去掉交换、丢失重复项、混淆变量／常量等错误是否被拒绝。
- [ ] **A5 回归和范围：** 原 732 项冻结；新 focused 与十一文件全量通过，仅授权文件变化，无依赖／CLI／模型输入变更。
- [ ] **A6 文档和研究边界：** README 例与测试一致；单 clause key 不被宣称为 proof key、motif 或唯一性审计；规范定义与实现完成分开。
- [ ] **A7 证据：** preflight 在编码前、状态先行、每次执行原件保留、独占 basetemp、时间／结果／执行者准确；不补造历史，不先写未来检查已通过。

## Pi 执行记录

### 轮 1（2026-09-20）

- **工具／模型：** Pi + `bonsai2-27b`（provider `bonsai`，推理强度 `xhigh`）。执行时由环境变量 `PI_PROVIDER`／`PI_MODEL`／`PI_REASONING_LEVEL` 如实记录；未凭历史推断。
- **基线／分支：** 自基线 `4c457e21899f81274999855d905e66b2ba574798` 创建分支 `T0011-clause-key`；编码前 preflight 核验工作树仅含 Codex 规划改动、分支与冻结 SHA256 正确。
- **改动文件（5）：** 新增 `src/kmesh/logic/clause_key.py`（公开 `canonical_clause_key`，私有 `_term_key`／`_atom_key`／`_candidate_key`）；新增 `tests/test_clause_key.py`（39 项测试，A–E 五组）；更新 `README.md`（T0011 API 段、测试命令加 `test_clause_key.py` 为 11 文件、当前限制与状态）；更新 `docs/implementation_status.md`（T0011 条与能力表行）；本文（状态行与本执行记录）。其余源码／测试冻结未改，T0001–T0010 产品／测试未改。
- **命令／退出码／RUN（均经记录器，每次新 RUN）：**
  1. `git switch -c T0011-clause-key` → 0。
  2. `run_checks.py pi-r1-preflight preflight` → 0（编码前执行；分支、冻结 SHA256、scope、产品／测试未存在、无 pytest-tmp／__pycache__ 通过）。
  3. `pi-r1-probe`、`pi-r1-probe2`、`pi-r1-probe3`（py_compile 与导入探针）→ 各 0；探针确认 K0、K3 锚点键值与交接一致。
  4. `run_checks.py pi-r1-focused focused` → 2（收集错误：单前提体写作 `((Atom(...)))` 缺尾随逗号，非 tuple；`LogicValidationError`）。
  5. `record_check.py pi-r1-fix1 -- .venv/bin/python /tmp/t0011_fix.py` → 1（修复脚本正则 `[A-Za-z_]+` 不匹配含数字的 K 名，仅 3/7 行；脚本未写盘）。
  6. `record_check.py pi-r1-fix2 -- .venv/bin/python /tmp/t0011_fix.py`（正则改 `[A-Za-z_0-9_]+`，按括号深度给 7 个单前提体插尾随逗号）→ 0。
  7. `run_checks.py pi-r1-focused-2 focused` → 1（6 fail：`_independent_min` 的 `orderings = list(clause.body)` 误将 1-tuple body 展平为 Atom 平列表，`'Atom' object is not iterable`；33 项通过）。
  8. 测试内修复（编辑工具）：`_independent_min` 的 `orderings = list(clause.body)` 改 `orderings = [clause.body]`，未单独建 RUN，由第 9 项 focused 结果留证。
  9. `run_checks.py pi-r1-focused-3 focused` → 0，**39 项通过**，无 skip／xfail。
  10. `run_checks.py pi-r1-full full` → 0，**771 项通过**（原 732＋新 39，11 文件驱动顺序，无 skip／xfail）。
  11. `run_checks.py pi-r1-docs docs` → 本轮最后一步，落盘记录后执行（见未运行项）。
- **失败与修复：** 均发生于 Pi 自身新增文件（fixture 单前提体语法、测试 helper 的 orderings 构造），修复后由 RUN 9、10 留证；冻结源码与旧测试无回归。
- **偏差：** 无契约外扩展；失败 RUN、修复 RUN 与开发探针原件按协议保留。
- **未运行项：** 仅 `pi-r1-docs`（docs 检查），待本记录落盘后执行；执行后不回填本记录端时间。
- **本回合终态哈希：** 产品 `cd5a737a44afe9f4184606e99c9aa8ac5322e91355739762d5592f9b87359084`；测试 `a1024156645a2c02622b19f401cbabc21b266d3b2be4a4b97b31366a0c7a200d`；README `f65c6ec6b501fcceb806db0ced1c179c418362ae227ee75f94f0b7fa475b7390`；implementation_status `3860611cdbe8f5f9ee81ebd9989f1fb2f478ae2704d271a758161c7691c2b37c`。
- 本记录不填写 Codex 验收结论。

### 轮 2（2026-09-21）

- **工具／模型：** Pi + `bonsai2-27b`（provider `bonsai`，推理强度 `xhigh`）。同 R1，执行时由环境变量 `PI_PROVIDER`／`PI_MODEL`／`PI_REASONING_LEVEL` 记录；未改产品。
- **基线／分支：** HEAD `4c457e21899f81274999855d905e66b2ba574798`，分支 `T0011-clause-key`。产品 `src/kmesh/logic/clause_key.py` 冻结未改（sha `cd5a737a…59084`）；本回合只改测试与文档／记录。
- **改动文件：** `tests/test_clause_key.py`（R1–R3 测试补强，39→63 项）；`README.md`（T0011 状态、63 项、沿用 full）；`docs/implementation_status.md`；本文；新建 `reports/T0011/pi-r2*`。冻结规划件、旧源码／测试、`logic/__init__.py`、T0001–T0010 未改。
- **命令／退出码／RUN（均经记录器，每次新 RUN）：**
  1. `run_checks.py pi-r2-preflight preflight` → 0（check_rework 基线：产品／测试 sha、旧 history、分支、环境、scope 通过）。
  2. 两文档与本文状态先置 `in_progress`，再改测试。
  3. `run_checks.py pi-r2-focused focused` → 1（新测试首跑：1 fail，`test_R1_…[clause6]` 对完全接地子句 K7 断言 rename 非 no-op；接地子句无变量、改名恒 no-op，自著测试断言过严；与产品无关）。
  4. 测试内修复（编辑工具，未单独建 RUN，由第 5 项留证）：仅对有变量子句断言 rename 非 no-op（`if _var_names(clause):`）。
  5. `run_checks.py pi-r2-focused2 focused` → 0，**63 项通过**，无 skip／xfail。
  6. `record_check.py pi-r2-guards -- …/guards.py …/pi-r2-guards --enforce` → 0；submitted 对照 0，五个错误副本全 exit 1：`diagnostic_suffix` 被 D 组精确消息拒绝；`float_variable_number` 被 R2 类型检查（`type(val) is int`）拒绝；`conditional_reverse` 被 R1 逆序矩阵拒绝；`no_reverse`、`drop_duplicate_premises` 被锚点／B 拒绝。
  7. docs 检查：`run_checks.py pi-r2-docs docs` → 1（误用旧驱动，路由到 check_delivery.py docs，scope 不含 review-r1）；改用契约命令 `record_check.py pi-r2-docs2 -- …/check_rework.py docs` → 0（冻结产品/history、scope、5 文档/72 链接、文本卫生、awaiting_review 全通过）。
- **R1–R3 落实：** 变换矩阵（K1–K10 改名／逆序／组合）、README `?u/?v` 实际输入、K3/K8 显式非 no-op、C 组逐双射实际改名、纯度快照（head/body/term/hash、独立结构副本）、K3→K0→K8→K3 首尾键相等、全层 tuple/str/int 检查、自环完整键、set/dict 可用、D 组精确 `str(exc.value)`、E 组实际子模块拦截。
- **失败与修复：** pi-r2-focused exit 1（自著测试断言过严，非产品缺陷）；第 4 步修复，原件保留于 RUN 3，结果留证于 RUN 5。pi-r2-docs exit 1（误用旧驱动，scope 不匹配），改 check_rework.py 命令重跑 pi-r2-docs2 通过；原件保留。
- **偏差：** 无契约外扩展；产品冻结，无新依赖；未改冻结规划件与旧 RUN。
- **R4 更正（本记录附）：**
  1. R1 实存 13 RUN、13 份 provenance，其中 9 项 exit 0、4 项失败（pi-r1-focused=2、pi-r1-fix1=1、pi-r1-focused-2=1、pi-r1-docs=1）。`pi-r1-docs3` 当时输出“15 文档”对应其运行时刻 12 份 provenance 加三份主文档；其自身 provenance 在该 RUN 后写入，不写成已检查自身事后文件；点时计数不写为最终总数。
  2. 原 handoff 记录 docs 为 `not_run` 是落盘时状态；实际 pi-r1-docs→docs2→docs3 为 exit 1→0→0，首因缺 provenance。保留原记录，不重写旧 RUN。
  3. R2 provenance（pi-r2-guards）汇总旧 13 RUN 与本轮 RUN；旧 RUN 只引用原件。
  4. `/tmp/t0011_fix.py` 历史脚本正文未归档；退出码、输出、测试前后哈希可核验，但“只改某正则”的逐行改动为 Pi 自述；环境变量未被记录器快照，provider/reasoning 按 Pi 自述（由环境读取）；模型切换为用户已授权。
- **测试计数：** 本回合 focused = 63 项（原 39 ＋ 新 24）。**未重跑全量**：沿用 Codex 第 1 轮 771 项回归原件，测试／源码冻结哈希不变；不把 732+63 写成已执行的 full。
- **终态哈希：** 产品 `cd5a737a44afe9f4184606e99c9aa8ac5322e91355739762d5592f9b87359084`（冻结未变）；测试 `a6aa60571d7c3e7b3ccb7060364572283a2859968de88bbd9a1439f3ce8d14f2`；未 commit/push。
- 本记录不填写 Codex 验收结论。

## Codex 验收记录

### Codex 第 1 轮（2026-09-21）：needs_changes

产品静态审阅、独立 **771 项全量回归**、**3571 次有限 oracle 检查**通过，未发现产品缺陷。原 39 项测试却放过三种错误副本（漏掉部分逆序候选、浮点变量编号、消息追加后缀）；另缺纯度快照、C 组逐双射实际改名、E 组子模块自检。详见 [验收报告](../../reports/T0011/review-r1/review.md)、[冻结输入及 Pi RUN 审计](../../reports/T0011/review-r1-freeze/audit.json)、[错误副本原件](../../reports/T0011/review-r1-guards/guards.json)。只读独立审阅代理与 Codex 主审意见一致。

冻结产品 `cd5a737a44afe9f4184606e99c9aa8ac5322e91355739762d5592f9b87359084`；返工起点测试 `a1024156645a2c02622b19f401cbabc21b266d3b2be4a4b97b31366a0c7a200d`。未 commit/push。A4 未通过；A1/A2/A3 产品行为已有独立支持，仍需相应测试守卫；A5 回归通过，A6/A7 待本轮小范围补齐。

### 第 2 轮最小返工契约（Codex，2026-09-21）

原 r1 产品契约、五组测试要求和 A1–A7 均不变；以下落实原要求并限定本轮范围。**不修改产品，也不重写整个测试文件**。只允许修改 `tests/test_clause_key.py`、README 的 T0011 示例／状态、实现状态的 T0011 两处、本文状态行并追加 Pi 第 2 轮记录、新建 `reports/T0011/pi-r2*`。保留所有现有锚点、不等价对及边界断言，不修改旧 RUN、Codex 检查材料、规划冻结件或其他源码／测试。

**第 1 步：核对返工起点，先记状态。** 保持当前分支和 HEAD，先运行下方新 preflight；原 preflight 要求新文件不存在，不再适用于返工。通过后本文和实现状态先置 `in_progress`，再改测试。异常先保留证据并反馈，不自改冻结清单。

**第 2 步：补 R1–R3 测试。**

1. **R1 变换：** 保留 A 锚点和 C 的有限赋值 oracle。B 对 K1–K10 分别实际构造 alpha 改名、body 逆序、两者组合，并与原完整键比较；不改变谓词、常量或参数位置。K3/K8 显式比较变换前后 body／变量，防止空操作。K1 改名包含 README 的 `?u/?v` 完整输入。C 对六个指定 fixture 的每个变量双射都构造合法名字后调用产品；例如排序原变量后，遍历 `("?z", "?a", "?m", "?b")[:k]` 的全部排列形成映射。该改名不可只用于 oracle 的整数编码；保留原 `range(k)` 穷举对照，不共享产品 helper。
2. **R2 纯度／类型：** 调用前保存输入的 head、body 顺序、独立重建的结构副本和 hash，调用后逐项比较；K3→K0→K8→K3 的末次键必须等于首次。遍历返回键，检查外层、head、body、各 atom 和 term 的 `type(...) is tuple`，谓词／标签／常量为 str，变量编号 `type(...) is int` 且非负；不能只凭 `0.0 == 0` 的相等断言。覆盖有常量、变量、重复前提的代表输入，保持 set/dict 可用性检查。自环例可直接断言完整预期键。
3. **R3 诊断：** D 的普通非法类型、generator、坏 repr/str、巨整数全部捕获 `LogicValidationError` 后比较完整 `str(exc.value)`；保留未消费断言和 4300 限制 finally 恢复，不放松 Python 签名异常。
4. **R3 隔离：** 保留九个禁用根、现有 finder、真实 fact/JOIN/K8 计算与最终模块扫描。每个根实际 import 时检查异常消息精确来自 `T0011_isolation_blocked: NAME`。子模块不能仅调用 `import(root + '.probe')` 后在根处被挡住就算覆盖：临时给该根放一个带空 `__path__` 的 `types.ModuleType` 占位包，实际 import `root + '._t0011_probe'`，断言消息指向这个完整子模块名；finally 删除占位包及子模块（若原来存在模块则先报错，避免隐藏已加载依赖）。全部占位仅用于自检，真实产品调用前恢复干净状态，不绕开产品真实导入。这样点前缀分支实际被执行，而非把普通找不到模块当成守卫有效。

本轮正确产品通过新增测试是预期，不伪造“修复前产品失败”。现有 Codex 错误副本记录已经提供失败机制；返工再用原脚本检验这些错误是否被新断言拒绝。

**第 3 步：定向检查与守卫。** focused 通过后执行固定 guards `--enforce`：submitted 对照全过、五个错误副本均 exit 1，且 stdout 的失败断言分别对应消息、真实类型、逆序或重复前提规则，不能是导入／收集错误。每个副本有独立源码、测试及 basetemp；不改工作树产品。不重跑 full：沿用本轮 Codex 771 项原件和旧源码／测试冻结哈希；新增测试数量单独记 N，不能把 `732+N` 写成未执行的完整回归结果。

**第 4 步：R4 更正、交回。** 在本轮成功 guards 目录下写一份新 provenance，汇总 review.md R4 的四条说明，以及本轮真实 RUN／退出码／产品和测试哈希；旧 13 个 RUN 只引用原件，不复制伪造历史。README 同步示例测试、当前 N 与沿用 full 的时间／范围；状态两文档和 README 置 `awaiting_review`，本文追加执行记录后运行新 docs 检查。该检查不能替代语义验收。docs 自身结果交回时引用原件即可，不为补写自己的结束时间反复重跑。

准确命令（首次使用下列新 RUN 名；任何失败保留原名，换新后缀继续）：

```bash
.venv/bin/python reports/T0011/record_check.py pi-r2-preflight -- .venv/bin/python reports/T0011/review-r1/check_rework.py preflight
# 两文档先记 in_progress，再按上面 R1–R3 最小修改测试
.venv/bin/python reports/T0011/run_checks.py pi-r2-focused focused
.venv/bin/python reports/T0011/record_check.py pi-r2-guards -- .venv/bin/python reports/T0011/review-r1/guards.py reports/T0011/pi-r2-guards --enforce
# 新 provenance 与文档／awaiting_review 状态落盘后
.venv/bin/python reports/T0011/record_check.py pi-r2-docs -- .venv/bin/python reports/T0011/review-r1/check_rework.py docs
```

所有开发检查也经原记录器、全新 RUN；不要预建 RUN 目录。检查器与 guards 均由 Codex 提供且冻结，Pi 不修改。新 [返工检查器](../../reports/T0011/review-r1/check_rework.py) 接纳已有 Codex 验收证据，原 `check_delivery.py docs` 的首轮范围已不适用。CPU／120 秒上限沿用；结束后冻结 diff，交 Codex 复验 R1–R4，未授权 commit/push。

### Codex 第 2 轮（2026-09-21）：accepted

**R1–R4 全部关闭，A1–A7 通过。** 本轮只改测试与相关文档；产品持续冻结。Codex 在原 guards 的独立副本中复跑 submitted 对照，**63 passed**，五种错误副本分别被完整消息、真实 int 类型、前提逆序、重复槽位等目标断言拒绝；不是收集或导入失败。原 732 项源码／测试哈希不变，沿用 Codex 第 1 轮 **771 项全量回归**和 **3571 次有限 oracle 检查**，本轮未重跑 full，不声明执行过 795 项。

- 接受产品：`cd5a737a44afe9f4184606e99c9aa8ac5322e91355739762d5592f9b87359084`。
- 接受测试：`a6aa60571d7c3e7b3ccb7060364572283a2859968de88bbd9a1439f3ce8d14f2`。
- 接受基线：`4c457e21899f81274999855d905e66b2ba574798` 上的未提交工作树，分支 `T0011-clause-key`；未 commit/push。
- 证据：[冻结审计](../../reports/T0011/review-r2-freeze/audit.json)、[独立守卫结果](../../reports/T0011/review-r2-guards/guards.json)、[第 2 轮验收报告](../../reports/T0011/review-r2/review.md)。159 项验收前本任务材料与规划／前置冻结件核对未变；独立只读审阅意见与主审一致。

具体记录澄清：Pi R2 共六个 RUN，4 成功、2 失败；docs 实际先误用旧驱动失败，随后 `pi-r2-docs2` 使用正确检查器通过。preflight 原件确实执行 `check_rework.py preflight`，Pi 交接中的旧驱动命令是文字错误。R2 provenance 的测试哈希缺字、RUN 摘要写于 docs 之前；完整哈希及六次真实记录以上述审计为准，旧文件保持原样。首轮历史脚本／环境来源等限制保留。

纯度检查实际保存 head/body 身份、所有内容字符串与顺序快照，足以检测当前冻结类型的输入改写；使用的是 `hash(pre_terms)`，副本在调用后构造，没有直接比较 `hash(clause)`。本轮按实质覆盖接受，不将不同具体写法表述为逐字落实原建议。

本任务仅完成单 clause 规范内容键；完整证明身份／唯一性、motif、world 审计与研究实验另拆，未由此次验收授权实施。

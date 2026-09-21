# T0011：单条 clause 的规范内容键

## 任务信息

- 任务编号／修订号：T0011 / r1，2026-09-20。
- 状态：`awaiting_review`（2026-09-20，Pi 实施完成，等待 Codex 验收）。
- 阶段／协议：M1 审计基础；研究计划 v0.1.3、E0 `e0_v2`、`proof_identity_v1` §2、D29。
- 规划者／验收者：Codex + `gpt-6-astra`，`xhigh`；执行者：Pi + `qwen3.8-coding-27b`。记录实际完整模型别名与服务；此前为 `qwen3.8-coding:27b-q8_0-64k`，不凭历史推断本次服务配置。
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

## Codex 验收记录

尚未进行产品验收。独立规划审阅见 planning-review.md，三项必要澄清已落实；Pi 交回后由 Codex 对实际 diff／A1–A7 独立验收。后续先拆完整证明身份及唯一性，再拆 motif／子结构／world 审计；不在本任务中扩展 API。

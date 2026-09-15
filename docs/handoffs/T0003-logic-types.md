# T0003：逻辑原子与 clause 的不可变表示及静态校验

## 任务信息

- 任务编号／修订号：T0003 / r1，2026-09-15。
- 状态：`accepted`；Codex 第 2 轮复验通过，R1 已关闭；独立完整回归 167 项及首轮 18 项边界探测全通过。接受实现已提交为 `6a81224eead0df659a4ba0e83cc391d7307550f5`，三项逻辑源码/测试哈希与第 2 轮接受工作树一致；关联核对见文末。
- 所属阶段：M1 可信数据的前置接口，亦为后续 M0 CPU smoke 准备逻辑输入基础；M0 仍未完成，本任务不启动 M1 正式生成。
- 研究依据：计划 v0.1.1、E0 `e0_v2`；仅落实已有正向 Horn 语言及本地类型约定，不改变研究任务、可见信息、划分、指标或预算。词法约定见 [D18](../decisions.md#d18逻辑类型的实现约定)。
- 规划者／验收者：Codex + `gpt-6-astra`，`xhigh`。
- 执行者：Pi + `qwen3.8-coding-27b`；已确认运行别名 `qwen3.8-coding:27b`，记录实际工具／模型，不自行换模型。
- 基线：`9acaa3184fa3b87a2263cfb21571224c609867be`，规划时位于 `T0002-model-config`，工作树干净。此后 Codex 新增本文、decisions 和 T0003 检查记录器/自检证据，并更新实现状态，均为已知交接改动。
- 前置：T0001、[T0002](T0002-model-config.md) 均 accepted；T0002 接受实现 `35572f2`、提交关联记录 `9acaa31`。T0003 使用已有包/pytest，不需要调用 ModelConfig。
- 必读：[AGENTS.md](../../AGENTS.md)、[研究计划](../../KMesh_Research_Plan_v0.1.md) §4.1、§5.3、§13.1–13.2、§15.1、§17；本文与 [检查记录器](../../reports/T0003/record_check.py)。

## 目标、范围与交付物

单一目标：提供可供后续求解器、数据构造和内容编码共用的 **Atom 与 Clause**，在构造时验证单条语句的静态合法性。事实采用空 body 的 Clause；不另外建 Fact/Rule 子类或角色标签。

| 允许新增／修改 | 本轮内容 |
|---|---|
| `src/kmesh/logic/__init__.py` | 仅包说明，不导入求解器或其他模块 |
| `src/kmesh/logic/types.py` | `LogicValidationError`、Atom、Clause 与必要私有校验函数 |
| `tests/test_logic_types.py` | 手工合成对象的语法、类型、不可变性及导入隔离测试 |
| `README.md`、`docs/implementation_status.md` | 简要说明逻辑类型已经实现/待验收及其范围 |
| 本交接文档 | 状态与追加 Pi 执行记录；不得填写 Codex 结论 |
| `reports/T0003/` 中全新轮次目录 | 命令、两路原始输出、退出码、哈希和 provenance |

Codex 已提供 `reports/T0003/record_check.py` 与 `.gitignore`，属于验收辅助材料，不是产品实现；Pi 使用原文件，不自行重写。`docs/decisions.md` 由 Codex 维护。不得修改已验收的 config/CLI/environment、旧测试、依赖、研究计划、AGENTS、历史报告或其他任务。

不实现 JSON/YAML 文件加载、序列化、CLI、World/Patch/Query/Proof、ModelBatch/EvalMeta、求解器、生成器、模板分类、DAG 检查、tokenizer、图或模型；不读研究数据，不生成训练样本，不训练，不自动 commit/push。

## 前提与假设

- 已验证：2026-09-15，`.venv/bin/python` 为 Python 3.13.9，editable `kmesh 0.1.0` 指向本仓库 `src/kmesh/__init__.py`，pytest 8.4.2；`src/kmesh/logic/` 尚不存在，现有 99 个测试已在 T0002 验收通过。
- 实施时重新记录 HEAD、status、源码哈希和实际模型。允许保留上述 Codex 交接改动后建立分支 `T0003-logic-types`；先核对，不丢弃他人改动、不自动提交。基线/依赖不符或模型不可用时记录 blocked 并反馈，不安装、升级或下载。
- 本层只验证句法和单 clause 的变量约束。E0 生成模板、关系依赖无环、世界词表成员/符号数量、ground query、重复 clause 和 split/证明审计尚未实现；对象构造成功不代表 world 合格。其余阶段不得把这里的检查当成完整数据校验。
- 所有测试为手工合成对象，数据版本/采样 seed/checkpoint=N/A。仅读本仓库相关代码、任务证据和环境元数据；不读其他项目、研究数据/测试集或凭据。新类型仅依赖标准库；不需要网络/GPU。
- 每次记录器子进程最多 120 秒，总自检预算 10 分钟。异常、超时和失败先留存，再局部修复；不得扩大研究范围或无界重试。

## 具体实施步骤

### 1. 核对起点并建立最小模块

用“验证方法”的 preflight 命令保存起点，再置 `in_progress`。创建两个产品文件和测试文件；`logic/__init__.py` 只保留说明，公开类型从 `kmesh.logic.types` 导入。不得让包导入加载 torch、yaml、求解器、训练或读取文件。

可检查结果：已有代码未改，新模块职责单一。

### 2. 实现 Atom 与词法检查

在 `types.py` 定义 `LogicValidationError(ValueError)` 及以下完整接口；类型实例在正常构造时即合法，不依赖调用方随后再调 validate：

```python
@dataclass(frozen=True)
class Atom:
    pred: str
    args: tuple[str, str]

    @property
    def variables(self) -> frozenset[str]: ...

    @property
    def is_ground(self) -> bool: ...
```

- 谓词和常量为 ASCII 标识符，正则 **`[A-Za-z][A-Za-z0-9_]*` 整串匹配**；变量为 `?` 加一个同样标识符，例如 `?join_mid`。`x` 是常量，`?x` 是变量；大小写敏感。不得只允许 `rN/eN/?x/?y/?z`，也不自动 trim、转换数字、改大小写或重命名。
- `pred` 必须为合法字符串标识符，不能以 `?` 开头。`args` 必须为 tuple，恰好两项，每项都是合法常量或变量字符串；拒绝 list/字符串容器、错误长度、bool/int/None 项、空名、孤立 `?`、空白、换行或函数形式如 `f(a)`。先检查运行时类型，再做正则/索引操作。
- 重复参数合法：`p(?x,?x)`、`p(a,a)`。`variables` 返回带 `?` 的变量名 frozenset；`is_ground` 当且仅当 variables 为空。不得存可变集合，或引入全局变量绑定状态。
- 不自设 32 个实体/16 个谓词/固定变量数或符号长度上限；这些不是单个 Atom 能确认的 world/tokenizer 约束。
- 通过 `__post_init__` 与简单私有函数校验即可。非法字段值抛 LogicValidationError，消息含 `atom.pred`、`atom.args` 或 `atom.args[索引]` 与原因；不要求全文固定。调用 Python 构造器时漏传参数/多传未知关键字仍按普通 TypeError，不做通用异常包装。

可检查结果：对象及嵌套字段不可变、可放入 set/dict；对象保留给定符号与参数方向。Python hash 仅用于进程内容器，不是持久内容哈希。

### 3. 实现 Clause 的静态约束

```python
@dataclass(frozen=True)
class Clause:
    body: tuple[Atom, ...]
    head: Atom
```

- body 必须为 tuple、长度 0/1/2，成员均为 Atom；head 必须为 Atom。禁止把 list 隐式转换成 tuple，或把 dict 当 Atom。
- `head.variables ⊆ union(atom.variables for atom in body)`。发现 head 未绑定变量，抛 LogicValidationError，消息含 `clause.head` 和至少一个具体非法变量名。body=[] 因此只能有 ground head；不需要独立的“事实类型”。
- body 中不出现在 head 的变量合法，JOIN 中的 `?y` 就是例子。非空 body 含常量、ground head、重复原子或相同谓词本身不在此层被拒绝；模板许可/关系 DAG/重复数据由后续 world 边界负责。
- 保留 body 的原顺序和重复项、head 的参数顺序，不排序/去重/改名。不把前提交换或变量改名当作 Python 对象相等；逻辑等价/alpha-equivalence/证明规范化留给后续任务。变量名相同也只在各自 clause 内使用，不维护跨对象注册表。
- 其他非法字段消息含 `clause.body`、`clause.body[索引]` 或 `clause.head` 与原因。所有字段必填，不设默认值；Clause 同样不可变且可哈希。

必须支持的五个具体正例（标签仅用于本文/测试命名，不加入对象字段）：

```python
fact = Clause((), Atom("p", ("a", "b")))
copy = Clause((Atom("p", ("?x", "?y")),), Atom("q", ("?x", "?y")))
inv = Clause((Atom("p", ("?x", "?y")),), Atom("q", ("?y", "?x")))
join = Clause((Atom("p", ("?x", "?y")), Atom("q", ("?y", "?z"))), Atom("r", ("?x", "?z")))
inter = Clause((Atom("p", ("?x", "?y")), Atom("q", ("?x", "?y"))), Atom("r", ("?x", "?y")))
```

必须拒绝：`Clause((), Atom("p", ("?x", "a")))`；`Clause((Atom("p", ("?x", "?y")),), Atom("q", ("?x", "?z")))`，后者错误应指出 `clause.head`、`?z`。本轮不计算这些语句的真值或闭包。

可检查结果：空/单/双前提和变量约束成立，对象构造不执行推理。

### 4. 编写有效测试

所有新增测试在 `tests/test_logic_types.py`。覆盖：

1. 上述五个正例、重复变量/常量、非固定符号名、大小写保留、variables/is_ground；允许 body-only 变量、合法混合常量及 head ground 的非空规则。
2. Atom 字段的代表性非法类型、非字符串/非法词法、list 容器、0/1/3 元参数；Clause 的非 tuple、三个前提、非法成员/head、ground fact 和未绑定 head 变量。每例只破坏待测条件并断言字段路径/目标原因，不能只断言“抛了某个异常”。
3. Atom/Clause 字段赋值报 FrozenInstanceError，内部 args/body 为 tuple；相同结构对象相等且 hash 相同，可在 set 中去重。方向不同的原子不相等，body 顺序按输入保留；不要断言所有不等对象 hash 必定不同。
4. 先构造一个含 `?z` 的合法 clause，再构造上面的非法 head `?z` 例，仍须拒绝，防止跨 clause 变量污染。不得为这些对象附加 template/role/label/proof/family/ID 元数据字段。
5. 新 Python 子进程在导入 `kmesh.logic.types` 前拦截 torch/yaml 的导入，导入后构造 fact/JOIN，断言两者未进入 sys.modules。只验证新模块的导入隔离；不要在测试中安装包、运行求解器或读取数据。

检查 imports/fixtures 后运行测试；旧 99 个测试原样保留，不能改弱断言。无需固定新增用例数量或测试框架，不用随机大样本替代这些具体边界。

### 5. 记录结果并交回

README 与状态文档只写“逻辑类型与静态检查已实施，awaiting_review”；求解器、world 合法性、完整数据审计、模型/smoke/训练继续 not_run。本文 Pi 区逐轮追加真实模型、基线、改动、失败/成功目录、命令/退出码、未运行项与偏差；不得用摘要代替日志。完成后置 awaiting_review，不自动提交。

## 验证方法

工作目录 `/home/mye/src/llm/KMesh`。记录器已由 Codex 随交接提供，**不用提取代码块或自写驱动**。RUN 是新目录名；记录器在运行命令前建目录，已有目录会拒绝且不执行命令，自动保存 `record.json`、`stdout.txt`、`stderr.txt`（包括空文件）、前后源码哈希、HEAD/status 和退出码。它固定 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`、`CUDA_VISIBLE_DEVICES=""`、120 秒超时。

1. **实施前**保存起点与环境：

```bash
.venv/bin/python reports/T0003/record_check.py pi-r1-preflight -- .venv/bin/python -c 'import sys, kmesh; from importlib.metadata import version; print(sys.executable); print(sys.version); print(kmesh.__file__); print({n: version(n) for n in ("kmesh", "pytest")})'
```

期望退出 0，版本/路径符合前提；此时新模块缺失的哈希记 null 是实际起点，不是实施成功。随后创建测试和最小实现。若先运行失败用例，直接使用下一条命令保存结果，失败也必须保留。

2. **定向检查**（新目录，首次失败后下次改 pi-r2-focused 等编号）：

```bash
.venv/bin/python reports/T0003/record_check.py pi-r1-focused -- .venv/bin/python -m pytest -q tests/test_logic_types.py --basetemp reports/T0003/pi-r1-focused/pytest-tmp
```

期望最终退出 0、全部逻辑类型测试通过；有失败先查看本轮两路日志，最小修复后使用新 RUN，并同时更换 --basetemp 中的目录名。

3. **完整回归**（实现定向测试通过后运行）：

```bash
.venv/bin/python reports/T0003/record_check.py pi-r1-full -- .venv/bin/python -m pytest -q tests/test_logic_types.py tests/test_config.py tests/test_doctor.py --basetemp reports/T0003/pi-r1-full/pytest-tmp
```

期望新增用例与旧 99 个测试全通过、无 skip/xfail；失败/超时不得宣称 PASS，重试改新 RUN 和 basetemp。记录器返回子命令退出码，超时 124/启动失败 127；任一非零须记录并处理。不要向 RUN 目录预先重定向输出或创建 provenance，目录必须先由记录器建立。

最终对本轮变更执行 `git diff --check`，另检查新文件末尾换行/尾随空白、本地链接、`git ls-files`/待暂存列表中无 pytest-tmp。将简短 provenance 写入已完成的 full 目录：实际工具/模型、对应前置/失败目录、来源限制及卫生检查结果。实现/测试/记录器与 stdout/stderr 的哈希已在 record.json，不再重复复制历史代码和报告；如追加其他证据，明确其路径与哈希。旧 T0001/T0002 和 T0003 已有输出目录保持不变。

## 验收标准

- [x] A1：两个数据类型、专用异常与接口按约定实现；事实与规则共用 Clause，无额外角色/审计字段。
- [x] A2：二元 arity、词法、严格容器/成员类型、0–2 前提、ground fact 和 range restriction 均有有效检查及错误路径；无隐式转换、全局绑定或多余 E0 限制。
- [x] A3：对象与内部容器不可变、可哈希；输入符号、参数方向和 body 顺序保留，结构相等与逻辑等价未混淆。
- [x] A4：新模块仅用标准库，不导入 torch/yaml/solver，不执行文件读取、推理或训练；不混入模型禁见元数据。
- [x] A5：有效正负例、作用域/不可变性/隔离检查通过；旧 99 个测试原样回归，临时文件未跟踪。
- [x] A6：原始命令、前后源码哈希、stdout/stderr、退出码及模型来源可追溯；失败/修复分新目录，历史不覆盖。
- [x] A7：修改在白名单内，文档准确，未把静态类型构造当作完整 E0 数据审计或 M0/M1 完成。

Codex 按冻结 diff/文件哈希核验关键行为和测试有效性，再决定 accepted/needs_changes；Pi 自检通过不等于验收通过。研究假设本身尚未在此任务中接受检验。

## Pi 执行记录

以下保留各轮执行记录；后续返工在本节追加，不覆盖此前说明与日志。

### Pi 首轮实施，2026-09-15

- 实际工具／模型：Pi + `qwen3.8-coding-27b`（Ollama 本地别名 `qwen3.8-coding:27b`，`PI_REASONING_LEVEL=off`）。（会话曾中断，恢复后逐条复核分支/文件/记录目录，无中断损失；此前已写入的产品两文件经行为冒烟复核后未重新重写。）
- 实际基线：分支 `T0003-logic-types` 自 `9acaa3184fa3b87a2263cfb21571224c609867be`（master）建立，保留 Codex 未提交交接改动。环境：Python 3.13.9 / editable kmesh 0.1.0（指向本仓库 src）/ pytest 8.4.2；新模块起点哈希 null、现有文件与 T0002 接受版本一致（见下方 preflight 目录 record.json）。
- 改动文件：新增 `src/kmesh/logic/__init__.py`、`src/kmesh/logic/types.py`、`tests/test_logic_types.py`；修改 `README.md`、`docs/implementation_status.md`、本交接文档。未改已验收产品代码、旧测试、依赖、研究计划、AGENTS、历史报告；`record_check.py` 原样使用。
- 命令、退出状态与日志（均由记录器保存两路输出、前后源码哈希与 HEAD/status）：
  1. `pi-r1-preflight`（契约版本/路径探针）→ exit 0，`reports/T0003/pi-r1-preflight/`。
  2. `pi-r1-focused`（定向 60 例）→ **exit 1，59 passed / 1 failed**，`reports/T0003/pi-r1-focused/`。失败为测试自身断言错误：`test_contract_positive_example_intersect` 误写 `body[0] == body[1]`，契约 `inter` 例中两原子谓词 `p`/`q` 不同、仅参数对相同；实现行为经交互冒烟复核正确，非实现缺陷。
  3. 最小修复：仅改 `tests/test_logic_types.py` 该断言（谓词 `p`/`q` 各自断言，参数对相等）。
  4. `pi-r2-focused`（同定向命令，新 RUN + 新 basetemp）→ exit 0，**60 passed**，`reports/T0003/pi-r2-focused/`。
  5. `pi-r1-full`（`pytest -q tests/test_logic_types.py tests/test_config.py tests/test_doctor.py`）→ exit 0，**159 passed**（60 + 74 + 25），无 skip/xfail，`reports/T0003/pi-r1-full/`（含 provenance.md）。
- 未运行项及原因：JSON/YAML 加载、序列化、CLI、World/Patch/Query/Proof、求解器、生成器、tokenizer、训练、M0 smoke —— 本轮范围外，明确 not_run；数据版本/seed/checkpoint 为 N/A（手工合成对象）；未训练、未联网、未安装包；自动 commit/push 未执行。
- 偏差、失败、阻塞及最小复现：唯一失败及修复见上第 2/3 条，原始两路输出保留在 `pi-r1-focused/`，最小复现即该测试名；无阻塞。无其他偏差（契约五正例/两反例/错误路径/不可变/隔离均在 60 例内）。
- 产物路径与范围：`reports/T0003/{pi-r1-preflight, pi-r1-focused, pi-r2-focused, pi-r1-full}/`（各含 record.json、stdout/stderr、pytest-tmp 被忽略）；实现三新文件与两文档改动在工作树未提交。卫生：`git diff --check` 通过，文本无尾随空白、文件末尾换行齐全，`__pycache__`/pytest-tmp 均被忽略，无 pytest-tmp 被跟踪；full 运行前后源码哈希零差异，历史目录未重用未改动。
- 提交验收的 diff/产物范围与状态：上述全部改动 + `reports/T0003/` 新 RUN 目录 + Codex 交接改动（decisions/handoff/记录器）；状态 `awaiting_review`，待 Codex 冻结版本后独立复验。Codex 结论区由 Codex 填写，Pi 不代填。

### Pi 第 2 轮返工（R1），2026-09-15

- 实际工具／模型：Pi + `qwen3.8-coding-27b`（运行元数据 `provider=ollama`、`model=qwen3.8-coding:27b-q8_0-64k`、`api=openai-completions`，`PI_REASONING_LEVEL=off`；完整别名澄清见下方第 2 轮 provenance）。
- 基线核对：分支 `T0003-logic-types`、HEAD `9acaa31`；返工前实测 `types.py`/`test_logic_types.py` SHA-256 与第 1 轮冻结值逐位一致；Codex `review-r1*` 与全部历史 RUN、规划文件保留未动、未重用。
- 改动（仅 `types.py` 与 `tests/test_logic_types.py`，按“先回归、后修复”顺序）：
  1. 先追加 8 条 R1 回归（`10**5000`、工厂参数化 + 显式短 `ids`，`pinned_int_str_limit` fixture 固定 4300 并在 `finally` 恢复）；
  2. 保存失败：`pi-r3-focused` → **exit 1，8 failed / 60 passed**（八条均以原生 `ValueError` 逸出），`reports/T0003/pi-r3-focused/`；
  3. 最小修复：7 个类型/长度分支删除未验证值/容器的 `!r`，只报字段路径与预期/实际类型、长度；容器检查不被遍历即拒；长度检查先于成员检查；字符串分支词法错误与未绑定变量诊断（残留 4 处 `!r`）保持原行为；无 safe_repr、无宽泛捕获、未改转换上限与接受范围；
  4. `pi-r4-focused` → exit 0，**68 passed**，`reports/T0003/pi-r4-focused/`；`pi-r2-full`（三测试文件）→ exit 0，**167 passed**（68+74+25），无 skip/xfail，`reports/T0003/pi-r2-full/`（含第 2 轮 provenance.md）。
- 未运行项与阻塞：与首轮范围一致（求解器/数据审计/文件加载/训练 not_run，N/A 同首轮）；无阻塞、无其他偏差；旧断言未改弱、旧目录未覆盖；中断范围澄清已写入第 2 轮 provenance（中断期未生成任何文件）。
- 提交验收范围：工作树内 `types.py`/`test_logic_types.py` 本轮改动 + 两个新 RUN 目录 provenance；状态 `awaiting_review`，未 commit/push。

## Codex 验收记录

实施验收按轮次记录如下；规划核查不算产品验收。仅 Codex 填写冻结版本、独立核验、A1–A7 结论与最终状态。

### 交接就绪检查，2026-09-15

- Codex + `gpt-6-astra`，`xhigh` 完成任务拆分和接口约定；设计建议由 `/root/review_data_design` 只读核对计划。未参与此任务设计的 `/root/review_t0001_code` 独立审阅本文、D18 与记录器，确认粒度、静态/世界边界和可执行命令无阻塞。
- 根代理核验当前环境、文档链接/语法/空白及三个命令的引用与 RUN/basetemp 配对；记录器成功、非零退出、拒绝重用、启动失败四项动态检查通过，原样记录见 [planning-recorder-checks.json](../../reports/T0003/planning-recorder-checks.json)。这些是 Codex 交接辅助检查，不是 Pi 实施或逻辑类型测试。
- 结论：`ready`。A1–A7 产品验收全部待实施；不创建产品占位实现，不运行研究实验，不自动 commit/push。

### 第 1 轮实施验收，2026-09-15

- 验收者：Codex + `gpt-6-astra`，`xhigh`；产品作者为 Pi + Qwen。`/root/review_t0001_code` 另作只读代码/测试审阅：首次静态检查未发现阻塞；主代理给出下面的动态反例后，其复核同意 R1 为一项 P2 契约缺陷。该代理未运行测试，也未修改产品。
- 冻结：`T0003-logic-types`，HEAD `9acaa3184fa3b87a2263cfb21571224c609867be` 加未提交工作树；43 项输入哈希与基线/status 见 [frozen-inputs.json](../../reports/T0003/review-r1/frozen-inputs.json)。实现 `types.py` SHA-256 为 `b6b4cc94af5746160fd09b5cf99477193c89ac1624f89e3b43e8107ffadc2a44`，测试为 `a475ed354880ba3cb849ce9cfda50d5b12ee8e9568138169b4d85917a20eae97`，均与 Pi full 记录一致。
- 独立完整回归：使用原记录器，新 RUN `review-r1-full`，运行本文三个测试文件，退出 0，**159 passed**、无 skip/xfail；[原始输出](../../reports/T0003/review-r1-full/stdout.txt)与 [record.json](../../reports/T0003/review-r1-full/record.json)保留，前后源码哈希一致。
- 额外契约探测：[boundary_probe.py](../../reports/T0003/review-r1/boundary_probe.py)，RUN `review-r1-boundaries`，退出 1。重复前提、长符号、Clause set/dict、变量改名不等同、Unicode/结尾换行拒绝、大小写作用域等 12 项通过；六个非法大整数输入因原生 `ValueError` 失败，见 [stdout.txt](../../reports/T0003/review-r1-boundaries/stdout.txt)。另以 RUN `review-r1-arity` 核验含大整数的一元 args，退出 1，同样在错误消息格式化时逸出，见 [stderr.txt](../../reports/T0003/review-r1-arity/stderr.txt)。这些是 Codex 验收探测，不是 Pi 自检。
- 证据核验：[evidence-audit.json](../../reports/T0003/review-r1/evidence-audit.json)。Pi 四个 RUN 的退出状态、stdout/stderr 哈希、运行前后源码哈希一致；首轮失败至修复仅测试文件的记录哈希变化，失败原文确认为 inter 断言错误。已跟踪 T0001/T0002 历史与 HEAD 无差异；T0003 决策/记录器/规划辅助文件与规划清单匹配；无已跟踪临时目录。
- 模型来源补充：KMesh 对应 Pi 会话中，本任务 assistant 元数据实际为 `provider=ollama`、`model=qwen3.8-coding:27b-q8_0-64k`、`api=openai-completions`，与所指定模型家族一致。首轮 provenance 的基础名称是简写；这里只核对执行日志，不声称独立验证了模型权重。此前超时中断的未完成回复没有生成测试文件；Pi 所述“无中断损失”仅按已落盘文件得到保留理解，不代表中断期间生成的内容已保存。
- A1/A3/A4/A6/A7 通过；**A2 未通过，A5 待补 R1 回归**。现有 159 项通过不能覆盖下面的异常契约缺口。科学假设、求解器/world 审计与 M0 smoke 均未验证。
- 结论：**`needs_changes`**，仅 R1 需要产品返工。Codex 本轮只新增验收证据、更新状态与文档，没有修改产品/测试、提交或 push。首轮 Pi 记录及所有历史 RUN 保留。

#### R1（P2）：非法值的 repr 抢先破坏专用异常契约

定位为首轮冻结 `src/kmesh/logic/types.py` 的 39、54、85、89、122、126、135 行。类型不符和 args 长度不符的错误消息直接格式化未经验证的值或容器。默认 Python 3.13.9 的整数十进制转换上限是 4300 位；普通内建整数 `10**5000` 只需约 2 KiB 存储，但 `repr()` 会抛原生 `ValueError`。例如 `Atom(10**5000, ("a", "b"))` 未能抛出承诺的 `LogicValidationError`，消息也没有 `atom.pred`。调用方按专用异常处理时会漏接。这与自定义恶意对象或 world 检查无关；合法逻辑对象的行为未发现受影响。

最小修复：上述错误分支只报告字段路径、预期类型/长度及实际类型/长度，删除对未经验证值/容器的 `!r`。已经确认是字符串后的词法错误与未绑定变量诊断保持原行为。**不添加通用 safe_repr、宽泛异常捕获，不修改生产环境的整数转换上限，不改合法输入的接受范围。** 可复用的经验是：非法输入的错误报告本身也必须能完成，类型/长度错误无需打印整个输入值。

Pi 按以下四步返工，原任务范围与验收标准保持不变：

1. 核对上述冻结哈希与历史目录，在原分支保留 Codex 新增验收文件/文档；置 `in_progress`。仅修改 `types.py`、`tests/test_logic_types.py`，追加新轮次记录与全新报告目录。
2. **先补回归，再保存失败。** 使用 `large = 10**5000`、合法 `ground = Atom("p", ("a", "b"))`，参数化覆盖下面八条单点错误路径；断言 `LogicValidationError`、目标字段路径和目标原因。使用显式短 `ids` 或工厂函数，防止 pytest 生成参数 ID 时先格式化大整数。测试若固定 `sys.set_int_max_str_digits(4300)`，仅限测试 fixture，并在 `finally` 恢复原值；不修改产品/全局配置。

   | 构造输入 | 错误路径 | 原因 |
   |---|---|---|
   | `Atom(large, ("a", "b"))` | `atom.pred` | 需要字符串 |
   | `Atom("p", ("a", large))` | `atom.args[1]` | 需要字符串 |
   | `Atom("p", large)` | `atom.args` | 需要 tuple |
   | `Atom("p", [large, "b"])` | `atom.args` | 需要 tuple，不应先遍历/格式化容器 |
   | `Atom("p", (large,))` | `atom.args` | 必须恰好两项，长度检查先于成员检查 |
   | `Clause(large, ground)` | `clause.body` | 需要 tuple |
   | `Clause((large,), ground)` | `clause.body[0]` | 需要 Atom |
   | `Clause((), large)` | `clause.head` | 需要 Atom |

   使用新 RUN `pi-r3-focused` 保存补测后的失败：

   ```bash
   .venv/bin/python reports/T0003/record_check.py pi-r3-focused -- .venv/bin/python -m pytest -q tests/test_logic_types.py --basetemp reports/T0003/pi-r3-focused/pytest-tmp
   ```

3. 最小修复诊断消息后，以 `pi-r4-focused` 保存成功，再运行 `pi-r2-full` 完整回归；继续保留原有 159 项，不改弱旧断言。以下两条均应退出 0、无 skip/xfail；再失败必须另开新 RUN 与 basetemp，不覆盖输出。

   ```bash
   .venv/bin/python reports/T0003/record_check.py pi-r4-focused -- .venv/bin/python -m pytest -q tests/test_logic_types.py --basetemp reports/T0003/pi-r4-focused/pytest-tmp
   .venv/bin/python reports/T0003/record_check.py pi-r2-full -- .venv/bin/python -m pytest -q tests/test_logic_types.py tests/test_config.py tests/test_doctor.py --basetemp reports/T0003/pi-r2-full/pytest-tmp
   ```

4. 新 full 目录追加 provenance，记录实际完整模型别名、失败与修复目录及退出码；交接文档追加第 2 轮 Pi 记录，状态改 `awaiting_review`，更新实现状态/README 的当前状态。旧 provenance 与首轮记录不覆盖；新记录澄清模型别名与中断范围即可。未 commit/push，交 Codex 复验 R1 与受影响回归。


### 第 2 轮实施验收，2026-09-15

- 验收者：Codex + `gpt-6-astra`，`xhigh`；产品实现/回归作者为 Pi + Qwen。原独立审阅者 `/root/review_t0001_code` 只读复核本轮七处消息修复、八条工厂参数化测试与 fixture 的 `finally` 恢复，同意 R1 关闭；未由其重复运行测试。
- 接受版本：分支 `T0003-logic-types`，HEAD `9acaa3184fa3b87a2263cfb21571224c609867be` 加本轮未提交工作树。`src/kmesh/logic/__init__.py` SHA-256 为 `649c92a60e8c3477bce80d2ec0beda7ab14d20ed776fdc4e715a11fd5d15fa96`；`types.py` 为 `b8468612ef747bf2db23c726b4fba288a306be928cff41538dd7fba6c8da37f8`；`tests/test_logic_types.py` 为 `2ff50a225cc0efb910794d004a5a0392339bf366802e25fa246686d154efedab`。此 HEAD 是基线，不是包含 T0003 的实现提交。
- 核验差异：[reviewed-diff.patch](../../reports/T0003/review-r2/reviewed-diff.patch)。在内存中反向恢复七条消息及新增注释，哈希与首轮源码一致；移除新回归块、还原段落编号并去掉一条重复 `import sys` 后，旧测试全文哈希与首轮一致。原测试函数/断言未改；重复 import 不影响行为，记为非阻塞整理项，Codex 未改产品或测试。
- 冻结与证据：[frozen-inputs.json](../../reports/T0003/review-r2/frozen-inputs.json)、[evidence-audit.json](../../reports/T0003/review-r2/evidence-audit.json)。清单在独立运行后、文档更新前生成；每个 RUN 另有执行前后源码哈希，均与接受版本匹配。Pi `pi-r3-focused` 的原始 8 条 ValueError 失败先于修复保存，测试哈希在失败→修复→full 期间不变，仅 `types.py` 变化；旧记录器、规划材料、首轮 Pi/Codex RUN 和 T0001/T0002 已跟踪历史核对无改动。
- 独立完整回归：原记录器 RUN `review-r2-full`，命令为 `.venv/bin/python -m pytest -q tests/test_logic_types.py tests/test_config.py tests/test_doctor.py --basetemp reports/T0003/review-r2-full/pytest-tmp`，退出 0，**167 passed**、无 skip/xfail，见 [stdout.txt](../../reports/T0003/review-r2-full/stdout.txt)及 [record.json](../../reports/T0003/review-r2-full/record.json)。包含八条 R1 路径（包括非法 list 与错误 arity）。
- 原反例复验：原封不动使用首轮 `boundary_probe.py`，通过原记录器写入新 RUN `review-r2-boundaries`，退出 0，**18/18 PASS**，见 [stdout.txt](../../reports/T0003/review-r2-boundaries/stdout.txt)。实际整数转换上限仍为 4300；专用异常/字段路径恢复，原静态接受范围未改变。
- 记录补注：Pi 第 2 轮末项的“两个新 RUN”应按前文及实存目录理解为三个（`pi-r3-focused`、`pi-r4-focused`、`pi-r2-full`）；原自述保留。其完整模型别名与本任务 Pi 会话元数据一致。本次将该 Pi 记录原文移回 Pi 区，并统一 README、实现状态与任务头部；README 此前漏同步 `awaiting_review` 属非阻塞文档遗漏。
- 结论：**R1 关闭；A1–A7 全部通过，T0003 `accepted`**。最终验收索引见 [final-audit.json](../../reports/T0003/review-r2/final-audit.json)。该结论只涉及逻辑内容类型与静态校验，求解器/world 数据审计、M0 smoke 与研究假设仍未验证。不自动 commit/push；后续提交应关联上述哈希。

### 接受版本与后续依赖关联，2026-09-15

- T0004 规划时核对：当前 HEAD 为 `e53e2bd0ec4cf3347c5b6103ab8061d71666150b`；实现提交 `6a81224eead0df659a4ba0e83cc391d7307550f5` 的 `logic/__init__.py`、`types.py`、`test_logic_types.py` 三个 blob 及当前文件均与第 2 轮最终验收清单逐项 SHA-256 一致。该实现已包含接受版本，可作为下游依赖。
- `e53e2bd` 的提交说明已关联接受提交，但本文头部和实现状态仍保留“未提交”时点描述；本次同步当前说明，前两轮原始验收/运行证据保持不变。这里只核对提交映射，没有重新运行或改变产品验收。
- 后续：[T0004 参考闭包求解器](T0004-reference-closure.md)，依赖本任务接受类型；不提前宣称主求解器/数据审计完成。

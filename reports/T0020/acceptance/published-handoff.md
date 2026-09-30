# T0020：版本化 motif 划分目录

## 任务信息

- 任务编号／修订号：T0020 / r3，2026-09-29。r2 更新已合入 T0019 的基线与后台准备，r3 按用户授权增加独立审查接受后的 Pi commit／merge；产品接口、motif_split_v1 和 A1–A6 不变。[r1 原交接](../../reports/T0020/preparation-r2/prior-contract-r1/handoff.txt)及 [r2 原交接／manifest](../../reports/T0020/preparation-r3/prior-contract-r2/)保留。
- 状态：**ready（r3 发布时契约）**。独立工作树／解释器、已验收依赖、1082 项基线与模型预检已完成；新增集成能力经139项Python／14项扩展测试、独立审查及最终版本真实模型闭环验证后部署。明确发布后运行状态以控制器 SQLite 为准，本文只读；不得根据 ready 字样重复提交。
- 所属阶段与研究协议版本：M1 可信数据的目录前置；研究计划 v0.1.4、E0 `e0_v3`、`motif_split_v1`，E1 `e1_v3` 及两种证明身份协议不变。决策见 [D41](../decisions.md#d41有限-motif-目录的分组划分与匹配口径)。
- 规划者：Codex + `gpt-6-astra/xhigh`；执行者：Pi + `bonsai/bonsai2-27b/xhigh`；独立验收者：Codex + `gpt-6-astra/xhigh`。
- 基线：`master@ffd1bdf4276c4347de6964627863a1368d5ff857`，T0019 的接受源码和测试已提交并快进合入主仓库；见 [合并记录](../../reports/T0019/integration/README.md)。独立工作树 `/home/mye/data/kmesh-worktrees/T0020-motif-split-catalogue`，分支 `T0020-motif-split-catalogue`，HEAD 同上。依赖源码 SHA-256 `177e475c750041bcbc422a35ffebb57c7bdf5fbf9a82c0d6ea43de4f3bc1dae4`、测试 `6ca43057bed506a54d4ff5d915b43d6f852601158dcacd33a714b1772012aa06`；两者已是该 HEAD 的不可变前置，不再注入未提交实现。
- 已有未提交材料：AGENTS、T0018/T0019 交接、decisions、implementation_status、`reports/T0019/`；本次追加 T0019 验收同步、研究协议、`motif_split_v1`、本文和 `reports/T0020/`。它们均由 Codex 维护，不能被 Pi 改写。
- 前置任务：[T0019](T0019-motif-candidate-audit.md) 已 `accepted / round 3 / attempt 3`，接受源码／测试与上述 Git blob 一致；提交引起的 HEAD／索引变化及接受快照映射见 [合并记录](../../reports/T0019/integration/README.md)，原 [接受摘要](../../reports/T0019/acceptance/summary.json)及失败证据保留。T0018 及更早依赖沿用已接受版本。
- 必读：[AGENTS](../../AGENTS.md)、[motif_split_v1](../motif_split_v1.md)、研究计划 §5／§18.4、T0019 产品／测试与交接、[Codinator 主界面说明](/home/mye/src/llm/codinator/docs/codex-interface.md)。规划探针只解释设计，不能作为产品导入来源或测试 expected oracle。

## 目标、范围与交付物

**单一主要目标：** 把 T0019 的已审计候选转换为 `motif_split_v1` 固定的机器可读目录，保存完整 witness／键，实测核对集合间隔离和七个分桶，供后续数据准入使用。

仅允许新增／修改两文件：

1. `src/kmesh/logic/motif_split.py`：单一公开函数 `build_motif_split_catalogue() -> dict`，`__all__ == ["build_motif_split_catalogue"]`，同模块 JSON 输出入口。
2. `tests/test_motif_split.py`：固定分配、测量值保留、隔离拒收、真实依赖和模块输出测试。

不修改 T0019、包初始化、已有测试、CLI、配置或研究文档；无公共解析器、配置选择器、缓存、持久全局目录或新的逻辑求解原语。不是通用图划分算法，也不自动搜索“更好的 split”。

目录 JSON 由模块 stdout 交付，控制器留证，不写工作树。Pi 按后台提示只写本轮仓外 `delivery/summary.md` 与 `completion.json`，不使用原生 Pi 专属的 `codex_submit_review`。运行状态以 SQLite 为准，本文发布后只读。

r3 另包含用户授权的交付步骤：**独立 Codex 接受上述两文件之后，由 Pi + Bonsai 创建提交并快进合入本地 `master`**。该步骤由控制器另起集成进程，使用精确接受内容的私有 Git 副本；实施／审查阶段仍不得暂存或改变原工作树 Git。Pi 提交须有说明正文，再 `merge --ff-only`；控制器核对完整树与父提交后把同一提交推进 `/home/mye/src/llm/KMesh` 的 `master`。不 push，不把已有规划文档混入产品提交。目标基线仍固定 `ffd1bdf4276c4347de6964627863a1368d5ff857`；若主分支变化、索引有暂存、目标路径冲突或集成失败，保留接受结论并阻塞，交由 Codex 检查后显式恢复集成。原接受工作树、检查和失败记录不改写；单独 review accepted 不表示此交付步骤已完成。

不包含 world／family 分配、干扰生成、负例、反事实、world 准入、训练数据写盘、模型、GPU、训练或研究成本实验。改变构造族、键等价关系或开放边界匹配交由 Codex 升版，不在本任务内修补。

## 前提与假设

- 已验证：T0019 三项控制器检查退出 0，32 定向／1082 全量；其独立审查关闭 R1–R3 并重建 80 witness。主会话本轮核对原件及当前快照，未重复这些产品测试；数字不是本轮新测试结果。
- 已验证：接受候选报告 SHA-256 `0e84e0ee386d046664c54c88b5ae798bc492cce101e666d6cbfc389481d9c5b4`；全部 80 行各有唯一规范证明、不同完整键；144 包含边。Codex 从该报告实测 16 个五节点包含组、40/20/20 分配、七桶 2:1:1、跨集合边 0，见 [规划输出](../../reports/T0020/planning-r1/stdout.json)及 [准确命令](../../reports/T0020/planning-r1/result.json)。不把 20 个测试键写成 20 个统计独立结构组。
- r2 已准备：专用 Python 3.13.5／pytest 8.3.4 环境，离线 editable 安装；kmesh 与 motif_candidates realpath 均属于 T0020 工作树。只读基线 **1082 passed in 33.88s**，退出 0、stderr 空、快照前后不变且源码无 bytecode。指定 Pi 与 Codex 已在此工作树完成新的最小真实响应预检，身份和限制见 [准备记录](../../reports/T0020/preparation-r2/README.md)；不是产品实施或接受。
- 执行方式：按 [D42](../decisions.md#d42新任务使用-codex-主界面与后台控制器)，Codex 主界面管理已启用的独立 Codinator 服务，Pi 以 RPC 实施，独立 Codex 审查。原生 T0018/T0019 不迁移。2026-09-29 服务已 enabled / active，独立真实探针 `deploy-live-20260929T092520Z` 获 accepted；这不是 T0020 的环境预检或实施，发布时仍须核验本任务环境和服务健康。
- 后台预算：`max_rounds=4`、`attempt_seconds=7200`、`max_seconds=14400`；单个 Pi/Codex 进程（包括集成 Pi）各受单次上限约束，全部阶段及暂停共用总墙钟；各必需检查 180 秒。没有沿用原生 Pi 的无限总时间例外。资源仅 CPU，隐藏 CUDA；无网络数据、锁定样本或付费教师访问，无新依赖。
- 输入数据为契约内确定性候选，seed N/A。产品只调用已接受 API，不读 `reports/`、旧会话、磁盘上的 golden JSON 或私有状态；预算或依赖失败原实例传播，不产生部分成功目录。范围、快照、模型、证据或资源前提不符时保留现场并交回 Codex。

## 具体实施步骤

### 1. 核对发布基线与唯一依赖

只有上述环境和 intake 准备完成、状态为 ready 且明确派发后才开工。按名导入 `kmesh.logic.motif_candidates.audit_motif_candidates`；每次调用新接口恰好调用它一次且无参数。依赖先完整成功，之后才分配和输出；不重建候选 witness，不直接调用 solver／枚举器或重复逐行求解。

预期：实际导入属于 T0020 工作树，依赖源码／测试为接受 hash，失败异常的对象和调用前消息保持不变。

### 2. 按固定完整列表分配

集合及输出顺序固定 `train, dev_composition, test_composition`。二字符组根固定：

```python
train = ("CJ", "CT", "IC", "II", "JC", "JI", "TJ", "TT")
dev_composition = ("CC", "IJ", "JT", "TI")
test_composition = ("CI", "IT", "JJ", "TC")
```

候选按 ID 前两字符归组（仅作分配）；每组包括二字符根和追加 C/I/J/T 的四个三字符候选。全 80 项的完整固定列表见协议 §3，不能根据测量好坏丢行、改组或补样本。全局及各集合内部保留 T0019 原目录顺序。

逐行保留 T0019 `CandidateRow` 的全部九个字段和值，只增加 `split` 字段；不就地改依赖返回对象。所有 witness、完整键、测量和包含 ID 必须来自本次调用，不能从文档、规划输出或历史报告复制运行结果。

预期锚点：CJ/CJC 属 train；CC/CCC 属 dev；CI/CIC 属 test。CJC 的实测 contained_ids 为 `["CJ", "CJC"]`，不是 `["JC", "CJC"]`；CCC 为 `["CC", "CCC"]`，CIC 为 `["CI", "CIC"]`。

### 3. 检查协议不变量，计算真实摘要

信任 T0019 的内部 schema，不另写通用 JSON 解析／修复框架；但返回目录前必须核对本次数据满足以下**科学契约不变量**：

- 上游版本、候选族、matching 和四项预算等于 T0019 契约；候选 ID 正好为固定 80 项且顺序无缺项、重复或未知项。
- 每项规范证明数为真实 int 1；最短深度为真实 int 且等于词长；proof_steps 为真实 int 且等于该行序列化 proof 的长度。完整键转成可比较的嵌套 tuple 后，80 项无重复。只能以完整键比较，不以 ID、repr 或摘要 hash 替代。
- 根据实测 `minimum_depth/proof_steps` 分桶，各集合行数及不同完整键数均须满足协议 §4 的七行表；不能把表直接填成观测值。
- 每行 `contained_ids` 只含已知 ID，无重复、含自身、按全局目录序；根据**实际列表**逐边计数。全部有向边必须在同一 split；不能用前缀规则生成或修复包含边，不能跳过非自身边。完整键在三集合之间也不得相交。

任一上述不变量不满足，抛 `RuntimeError("motif_split candidate audit violates motif_split_v1")`；异常不是“成功但有警告”。无需承诺多项同时损坏时的校验先后顺序，不新增异常类。缺失／非法内部 schema 可由原生异常直接暴露，不捕获后返回默认值；上游自己的异常必须原实例传播。

先完整检查，后返回。行数、不同键数、桶、总边、非自身边及九格矩阵全由本次行／完整键／实际包含边计算；上游 summary/buckets 不是本层汇总的替代。期望总边 144、非自身 64、矩阵对角 72/36/36、跨集合 0；将这些用于测试，不硬编码为实测输出。

### 4. 输出固定 schema

函数无文件 IO、无 stdout、无模块导入时执行，无跨调用保留状态；返回普通 dict/list 和 str/int 叶。每次从新的依赖调用生成目录。顶层恰含：

```text
schema_version = "motif_split_catalogue_v1"
split_protocol = "motif_split_v1"
research_protocol = "e0_v3"
candidate_family = "left_spine_ops_v1"
matching = "complete_rooted_support_subtree"
budgets = T0019 本次四项预算 dict
candidates = [T0019 CandidateRow + {split: str}, ...]  # 80 行，原目录序
splits = [SplitRow, ...]                             # 固定三集合序
containment_matrix = [EdgeCell, ...]                 # 源集合外层、目标集合内层，九格含 0
summary = {candidate_count, distinct_motif_count, containment_edges,
           proper_containment_edges, cross_split_edges}

SplitRow = {name, root_ids, candidate_ids, candidate_count,
            distinct_motif_count, buckets}
BucketRow = {depth, proof_steps, candidate_count, distinct_motif_count}
EdgeCell = {source_split, target_split, edge_count}
```

`root_ids` 是步骤 2 中固定有序组根的 list；candidate_ids 从实际已分配行中按原顺序取得。buckets 按 `(depth, proof_steps)` 升序、七格都存在。完整键保持 T0019 的嵌套 list 表示和值，包括版本和标量类型，不能用 hash 缩写。

`python -m kmesh.logic.motif_split` 完整计算成功后，一次性向 stdout 写 `json.dumps(..., ensure_ascii=False, sort_keys=True, indent=2)` 加一个末尾换行。无时间戳、路径、随机 ID 或进度；失败时 stdout 为空，stderr 允许原 traceback。不新增 CLI 子命令或 console script。

### 5. 用真实报告、手写锚点与错误输入验证

最少覆盖下列行为，避免只比较实现自己算出的两个结果：

- 真实 T0019 调用：80 完整 witness/键逐字段保留；三个集合的完整字面 ID 列表、七桶和九格矩阵符合协议，含两个方向的零跨集合边。完整列表 expected 来自协议字面，不以被测分配器／同一前缀算法生成。
- 手写 CJ/CJC、CC/CCC、CI/CIC 的归属与包含锚点；证明键是完整值，不能只测数量。
- 对一份独立依赖报告副本，把 train 的 CJC 添加 dev 的 CC 命中、把 dev 的 CCC 添加 test 的 CI 命中，分别必须拒收；捕捉按前缀重算或过滤包含列表的错误实现。重复完整键（含跨集合）、缺行／重复 ID、非唯一证明与错误分桶分别拒收。
- 在隔离的依赖替身中，注入可比较且无重复的键值哨兵，观察输出传递而不是仍返回缓存／历史 JSON；该替身不作为真实 witness 合法性证据，本层不重复求解来重新验证 T0019。改变无关上游 summary/buckets 不应改变本层实算摘要。
- 依赖抛指定异常时恰一次调用、原实例及**调用前冻结的消息**不变；不重试、不输出部分 JSON。函数正常调用也保持 stdout 空。
- 重复调用不互相污染，依赖提供的原对象未被修改。模块新进程 JSON 可解析、两次字节相同；每个测试子进程显式 `-B`，并断言 `kmesh` 和目标模块 realpath 属于当前独立工作树，避免误测主仓库或旧任务。
- 不从规划 probe、历史日志、私有控制器状态或磁盘候选 JSON 导入 oracle；不导入 torch/yaml、训练或模型模块。新功能只依赖 T0019 及其已接受间接链。

预期：普通错误可按契约自行修复；真实依赖与固定设计不符时报告最小复现，不修改协议或丢弃难例。

## 验证方法

r2 已完成独立工作目录的基线检查与路径验证；下列为发布后准确检查命令，新产品检查目前 `not_run`。工作目录固定 `/home/mye/data/kmesh-worktrees/T0020-motif-split-catalogue`，解释器固定该树 `.venv/bin/python`，不使用其他任务解释器。

```bash
env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/mye/data/kmesh-worktrees/T0020-motif-split-catalogue/.venv/bin/python -B -m pytest -q -p no:cacheprovider --basetemp /tmp/kmesh-T0020-focused tests/test_motif_split.py

env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/mye/data/kmesh-worktrees/T0020-motif-split-catalogue/.venv/bin/python -B -m pytest -q -p no:cacheprovider --basetemp /tmp/kmesh-T0020-full tests

env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 /home/mye/data/kmesh-worktrees/T0020-motif-split-catalogue/.venv/bin/python -B -m kmesh.logic.motif_split
```

三项各 180 秒，控制器只读工作树、临时产物 `/tmp`。成功均退出 0、无 skip/xfail、stderr 空；全量应为新基线 1082 + N，N 是本任务真实新增测试数，差异须解释。模块 stdout 保存机器目录，不能只有 shell 退出 0 而未解析和核对内容。开发期原始工具事件与控制器必需检查分开留证，失败 attempt 不覆盖。

独立验收除读 diff 外，应解析当轮目录、对照固定字面 ID／桶／矩阵、核对 witness 和完整键来自本次 T0019 结果，并独立注入至少“重算而隐藏跨 split 边”“固定摘要／旧键替代实际输入”两类错误，确认测试会失败。复跑范围按实际风险决定，不把测试数当科学证据。

## 验收标准

- [ ] A1：仅两允许文件；单一无参数 API 和模块 JSON 输出，依赖与只读契约未改；后台交付和模型元数据可追溯。
- [ ] A2：固定 40/20/20 个不同完整键、8/4/4 组；全 80 项归属及顺序、原 witness/测量保留正确，无原对象污染。
- [ ] A3：七桶按实际值计算并满足 2:1:1；九格包含矩阵来自实际边，六个跨集合格为 0；不以分配前缀代替匹配。
- [ ] A4：重复键、跨集合边、无效目录或非唯一证明等违约明确失败；上游异常原实例／消息透传；无部分成功输出。
- [ ] A5：函数无 IO／stdout，导入无计算，模块完整 JSON 稳定；无模型输入泄漏、跨工作树误导入或缓存污染。
- [ ] A6：三项规定检查及独立关键行为核验通过，错误实现守卫有效；准确报告有限族／完整支持子树范围，不声称生成数据、world 无泄漏、M1 完成或训练收益。

## Pi 执行记录

`not_run`。本轮由 Codex 完成交接和设计分析；Pi 尚未派发，T0020 新实现和新测试不存在。后续按 AGENTS §8 在仓外本轮 delivery 记录实际工具／模型、diff、命令／退出状态、not_run 和证据路径，不回写此冻结契约。

## Codex 验收记录

- 2026-09-29 规划核验：T0019 当前完整工作树与接受提交 digest `0750811878ce82fb4bd14992810ecedb09c74f23ed0c2c5d7fe27b1000de3852` 一致，原提交／检查证据 digest `67aa23f8a4ffa69adb096c1aab0fcfbd7a1412e1c0933966d10313e24106517b` 一致；目录检查原件与结果 hash 已核对，未复跑前置产品测试。
- 规划图分析退出 0，16 个互不相连的五节点组、固定配平与六个零交叉格成立。此为本任务设计依据，不是 T0020 实施／验收。
- r1 规划时状态保持 draft，随后 r2 完成发布准备，见下文；不因已验收前置而自动 commit/push/merge、迁移旧任务或启动模型。
- T0020 验收后再拆单 world 准入和 family／split 审计；本次没有给后续任务分配编号或扩大实施范围。

### r2 发布准备（2026-09-29）

用户先要求发布最新任务，随后要求先提交并合入 T0019；前置实现已按接受原字节合入 master，再以新 HEAD 建立本任务独立环境。r1 契约及原规划输出保留，接口、划分与验收项不变。

- 新基线1082项通过；只读导入路径／快照检查通过。精确命令、原始 stdout/stderr 与环境见 [preparation-r2](../../reports/T0020/preparation-r2/README.md)。
- Pi `bonsai/bonsai2-27b/xhigh` RPC 预检约3.80秒，Codex `gpt-6-astra/xhigh` 最小真实响应约42.76秒，均退出0且有成功协议终态。Pi直连本地Bonsai，Codex经本机代理；不声称后端权重证明。原始配置／认证／会话留在仓外准备目录。
- 固定 [manifest](../../reports/T0020/task.json)：仅两条产品／测试路径、三项180秒检查、最多4轮、单次进程7200秒、总14400秒。后台 delivery 交付；没有原生 Pi 总时限例外，不配置未知通知线程。
- r2 准备时 Codinator 已提交并推送为 `32c187ec41b3484e6de3ef22ef4dd9499929ba36`；用户级服务已启用。r2 未实际发布；用户随后要求增加集成步骤，由下述 r3 替代原“无自动 commit/merge”的运行约定，不改历史原件。

### r3 验收后集成准备（2026-09-29）

- 用户明确要求新发布任务包含最后的 Git commit／merge to master，并指定由 Pi + Bonsai 在 Codex review accepted 后执行。按 [D44](../decisions.md#d44发布任务包含验收后的-pi-提交与合并) 更新 manifest，范围仍为原两文件；不 push，不自动开展下一任务。
- 原 r2 交接和 manifest 连同 SHA-256 已归档。新增集成能力已通过139项Python测试、14项扩展测试和独立非作者审查；最终版本真实 Pi → Codex → Pi commit／merge 探针 accepted，源冻结及未提交规划保留通过。服务 enabled / active / running，部署基于 `32c187e` 加已审查未提交修改，以精确文件hash标识，不伪称已提交版本。见 [r3 准备记录](../../reports/T0020/preparation-r3/README.md)。本条为发布前准备，实际 submit 另留回执。

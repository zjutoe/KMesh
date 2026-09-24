# T0012 第 1 轮 Codex 验收：needs_changes

2026-09-22，Codex + `gpt-6-astra` / xhigh。对照原交接 A1–A7，冻结 Pi 提交后审阅；另由非作者代理只读审阅实现与测试。**本轮未发现产品实现缺陷；测试、README 和执行记录需要返工。** 不接受任务，不改产品／测试，不 commit/push。

## 复核结论与证据

- HEAD `56b41de11a2651da615230117f0d96bd6e0d6e92`，分支 `T0012-proof-key`；规划 HEAD 是其祖先，后续提交没有改变 1708 个规划冻结文件。新源码／测试及文档快照见 [正确冻结记录](../review-r1-freeze2/input-audit.json)和 [输入清单](../review-r1-freeze2/input-manifest.json)。
- 产品 SHA-256：`92dce0d424a60ae3f1f0d46a49da989eb8367258c287107a68ac541b637e03c1`。
- 测试 SHA-256：`79e102c3a54d5b3e32fdc10ce93bb01bd417bece4f9a6bdb0d3cb612e62977d6`。
- [独立十二文件回归](../review-r1-full/record.json)：**840 passed**，无 skip/xfail，stderr 空；提交版本已实际复跑。
- [独立探针](../review-r1-probe/probe.json)：K5/K6 全部四种支持组合及联合逆序，与枚举所有局部编号／槽位排列的定义 oracle 一致；真实 T0009 各四树得到完整 4／3 键集合；K8 四组合深比较、无关步骤拒绝、原对象／非默认预算委托、两种异常实例传播、不同关系的 1201 步长链完整键及原生排序均符合契约。这些是有限核验，不是一般正确性证明。
- [错误副本检查](../review-r1-guards/guards.json)：原提交 45 项通过；下表六种错误也各通过全部 45 项。`ignore_deep_tie` 被 4 项拒绝，`always_sort_children` 被 3 项拒绝，说明已有 K5/K8 正反例具有实际判错能力。
- [README 原样复现](../review-r1-probe/submitted-readme.py)：exit 1，[原始错误](../review-r1-probe/readme.stderr)为 `LogicValidationError: proof_key.proof must be a valid proof of query`。探针外层 exit 0 表示成功复现预期文档错误，不表示 README 成功。

| 错误副本 | 违反的契约 | 当前 45 项结果 |
|---|---|---|
| `allow_unused_steps` | 将 `ref_count != 1` 改为 `> 1`，放过无关步骤 | 全过 |
| `coerce_clauses` | 调 verifier 前将外层强制转 tuple | 全过 |
| `rebuild_exception` | 捕获后重建同类同消息异常，丢失实例身份 | 全过 |
| `diagnostic_suffix` | 两条新诊断追加 `EXTRA` | 全过 |
| `float_variable_number` | 变量编号返回 float，而非非 bool int | 全过 |
| `lazy_forbidden_import` | 新 API 内导入禁用 engine | 全过 |

每个副本都有隔离的源码／测试／basetemp、diff、pytest 原始输出及 XML；原产品未修改。原隔离测试硬编码原工作树路径，因而其子进程还会绕回原代码，这是该测试自身的缺陷之一。

## 必须返工（R1–R5，均 P2）

### R1：新 API 的真实边界与单棵出现树守卫

[测试第 507 行起](../../../tests/test_proof_key.py)多项直接调用旧 `verify_proof`，无法检验本次 API；`test_generator_unconsumed_marker` 没有消费标记。第 576 行的所谓异常实例测试实际只返回 False、比较参数相等；第 592 行也未检查异常 `is`。

按原 D 组最小增强，保留有效旧例：

1. 所有入口非法外层／成员、query 类型／非 ground、proof 外层／成员、预算 bool/0/-1/float，通过 **canonical_proof_key** 测试，断言 `LogicValidationError` 与完整 `verify.*` 消息。读取现有 verifier 的固定消息，不根据目标实现生成 expected。合法其他参数配合单点非法项。
2. 生成器设置可观察消费标记并断言未消费；4300 位限制 fixture 用 finally 恢复，以短 ids 检查巨整数非法外层、负预算和超大正预算。不要调整全局接受范围。
3. 新增“两个各自合法 fact、最后为 query、第一步未被使用”的证明：先断言真实 verifier True，再要求完整 `proof_key.proof must be a single occurrence tree`。已有共享引用例也补 verifier True 和精确异常／消息。保留独立重复事实出现的正例。
4. 两条新增诊断均精确匹配；补原 D 组叠加错误：长度超限＋非法 proof 成员先超限；语义无效＋非树先无效证明；世界类型错误不能被本层预扫描遮蔽。长度 N/N−1 使用真正合法 N 步证明。
5. 在新模块实际引用处 spy：恰一次、原 clauses/query/proof 对象 `is`、非默认原预算；具名 `LogicValidationError`、`ProofLimitError` 哨兵分别断言 `exc.value is sentinel` 与完整消息，另测 False。断言模块 `__all__`；删除测试文件末尾错误的函数 `.__all__` 检查，不新增脚本执行入口。

须使 `allow_unused_steps/coerce_clauses/rebuild_exception/diagnostic_suffix` 被相应行为断言拒绝，不能靠读源码识别副本。

### R2：补齐原身份对照矩阵与完整期望

已有 C 组独立等价 oracle 确实存在，算法静态审阅合理；**不是要求另写一份**。当前只实际用于 K1、K5 AB/BA、K6 AA/AB，名为 K8 oracle 的例子未调用 oracle。T0009 两例只核对数量；K4/K5/K7 的 `_expected` 借 T0011 生成期望，K6/K8 没有原契约要求的全部完整手算键。

1. 按原 A 组补手算完整 K4–K8 键。可以复用简单 tuple 包装及字面量 schema 常量；T0011 公共 API 仅作额外交叉检查，不能生成主 expected。K6 AA/AB/BA/BB 全流，K8 七 header 全流都要核对。
2. 原 B 组变换矩阵：K1/K3/K4/K5/K6 的局部变量双射和世界重排；K3–K6 的 body/ref 联合交换；适用分支的拓扑重排。每项确认字段实际改变、真实 verifier True、完整键不变。K6 body 相同可只要求 refs 确实改变；K1 不强求不存在的分支交换。保留当前非连续拓扑例。
3. 补重复 COPY 来源（当前仅重复 fact）、实际谓词／常量大小写及非对称改名区别；完整输入字段／hash 前后不变，以及 K3→K0→K5→K3 调用稳定性。
4. 用现有 oracle 覆盖 K1/K3/K4/K5/K6/K8，必须含 K6 AB/BA 正例、AA/AB 反例和 K8 深比较。逐对断言实际键相等与 oracle 布尔结果一致；小树限制沿用原文，不扩大为随机大规模研究。
5. K5/K6 真实 T0009 各四树，显式真实 verifier 校验，**整个键集合**等于上述手算完整集合，数量 4／3 保留作辅助断言。不能用目标函数给手工树出键来冒充独立 expected。

### R3：真实类型、长链与导入隔离

- 逐层用 `type(...) is tuple/str/int` 检查输出；变量编号非 bool、非负 int，常量 payload 为 str，包含 head/body term。当前 float 编号错误因数值相等漏过。
- E 长链改为原契约 1200 条 COPY 连接不同关系，核对全部 1201 header、根到事实顺序和手算 schema。保留预算、重复调用、hash/set/dict；**直接** `sorted([long_key, short_key])`，不得用 `key=repr` 绕开键比较。不提高递归限制。
- 重写当前仅 import＋hasattr 的隔离测试：干净子进程安装 `find_spec` 硬阻断八个禁用根及点前缀子模块；先自测各根专有 ImportError 消息，再用占位包实际触发子模块分支并清理；真实调用 K0/K3/K5，扫描全部 sys.modules。不得 patch 真实 verifier。
- 删除绝对工作树路径；子进程使用当前被测源码副本的 `PYTHONPATH=src`（以当前测试运行目录解析），保持源码副本隔离。不得在守卫失败时退回原工作树。

须使 `float_variable_number/lazy_forbidden_import` 被真实类型／导入断言拒绝。

### R4：README 的语义与可执行示例

[README 第 266 行](../../../README.md)误写 GroundKey 为常量 term、全局排序 headers、独立排序任意孩子、导入 clause_key/T0004 异常等；第 285 行 p2 交换事实却未改 clause_index，后续改常量还复用旧 proof。不能作为可用说明接受。

按原第 5 步改为 **K1 fact＋COPY 两步示例及完整字面量键**，同输入进测试，原样运行 README 块。说明 D30；GroundKey 是 `(pred, const0, const1)`；自底向上决定局部联合顺序，最后自根前序输出，只有 schema 两候选相等时比较孩子流；重复出现保留，无关步骤拒绝。简明保留离线、给定树身份、非唯一性／motif 边界。去掉“Pi 独立验收”归属错误。

### R5：按原件更正执行史，不回写旧记录

只在新的 R2 provenance 和追加交接记录中更正；旧 Pi/Codex RUN、provenance、规划材料冻结。

| 项 | 原件支持的事实／必须更正 |
|---|---|
| 失败记录 | 本次提交只有六个 Pi RUN：preflight/full/fused/docs/docs2/docs3。唯一归档失败是 docs 的末尾换行检查。所述产品缺陷、fixture 修复及“41 通过／3 项”等开发过程没有提交原始 RUN／日志；标 Pi 自述、不可核验，撤回“全部失败原件已留存”。不补造或以重跑冒充原件。 |
| preflight 与顺序 | preflight before/after 新文件均 null，可核验；其后可核验顺序为 full→fused→docs→docs2→docs3。纠正“编码前 focused”及交接命令序号造成的矛盾；无法恢复的开发顺序标 unknown。 |
| 末尾换行／108 | 对当前测试去掉最后一个换行所得 SHA 正好等于 full/fused 的旧 SHA `3432c001…`，只加换行有哈希支持；“108/108 复验”无提交原始记录，只能自述。Codex 当前 840 项是新的验证，不能替代历史。 |
| planning-review | 当前文件与规划冻结哈希完全相同，原件不支持本轮“补注第 23 行”说法。撤回对当前交付的该变更声明；如声称曾改又恢复，明确自述而非可核验。不要现在修改冻结文件来补故事。 |
| 时点与计数 | R1 provenance 只列三 RUN，docs not_run 是早期记录，不是当前结论；新表列全六 RUN，时间／elapsed_s 从各自 record.json 读取，勿把 wall time 与 elapsed 混写。模型／PI_MODEL 未被记录器采集，来源标 Pi 自述。状态先行只报告有证据的时点。 |
| 外来历史限制 | “T0009 全量 2200s 证明枚举、T0010 oracle 未重跑”未给出对应证据且并非本任务要求，撤回这种沿用表述；不为补它追加无关检查。 |
| 结果归属与范围 | Pi 的 focused/full 属自检；此次 Codex 840 项与探针才是独立验收证据。原新例编号为 K0–K8；不要以“45 项全过”宣称原 A–F 每一条件均实现。`proof.py` 等前置产品经冻结清单核验均未改，不能含糊写成允许修改它。 |

## 原 A1–A7 判定

| 标准 | 本轮结论 |
|---|---|
| A1 接口／校验 | 当前产品及有限独立边界探针通过；持久测试须补 R1 |
| A2 身份准确 | 产品静态审阅与 K5/K6/K8 定义对照通过；手算／变换／oracle 覆盖须补 R2 |
| A3 表示／算法 | 当前产品无递归、无全子树缓存；独立完整长链通过；测试须补 R2/R3 |
| A4 测试有效 | 不通过：六个明确违约副本漏过，隔离失效 |
| A5 回归／范围 | 通过：当前 840 项回归、既有 795 项测试冻结，1708 规划文件未变 |
| A6 文档边界 | 不通过：README 含错误语义和不可运行示例 |
| A7 记录 | 部分可核验；开发失败原件缺失、若干表述矛盾，按 R5 更正并永久保留历史限制 |

## Codex 本轮执行偏差

首次 [review-r1-freeze](../review-r1-freeze/record.json) exit 1 是 **Codex 冻结脚本过滤错误**：排除了所有任务名称含 `/review-r1` 的文件，再拿不完整清单核对。不是 Pi 删除／更改历史文件。该脚本和输出保留；新 [freeze2.py](freeze2.py) 仅排除本轮 Codex 路径，独占 [review-r1-freeze2](../review-r1-freeze2/record.json) 验证 1708 项全不变。原五份输入快照仍一致，不把首个失败输出用于指控提交。

后续按 [交接文档追加的第 2 轮四步要求](../../../docs/handoffs/T0012-proof-key.md)执行。产品保持冻结，修补测试／文档即可；若发现新产品反例，录制后交 Codex 决定，不自行扩展返工范围。

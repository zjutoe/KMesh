# motif_split_v1：有限左主干目录的组合保留协议

- 日期／责任方：2026-09-29，Codex + `gpt-6-astra/xhigh`；[D41](decisions.md#d41有限-motif-目录的分组划分与匹配口径)、[T0020](handoffs/T0020-motif-split-catalogue.md)。
- 状态：设计契约已确定；机器可读目录待 T0020 实施与验收，尚未生成正式数据或解锁测试。研究计划 v0.1.4／E0 `e0_v3`；E1 `e1_v3` 不变。
- 依据：T0019 第三轮 [接受摘要](../reports/T0019/acceptance/summary.json)和 [原始候选报告](../reports/T0019/acceptance/catalogue.json)，后者 SHA-256 `0e84e0ee386d046664c54c88b5ae798bc492cce101e666d6cbfc389481d9c5b4`。本协议不改变 `proof_identity_v1` 或 `proof_motif_v1` 的等价关系。

## 1. 首版研究范围

主组合目录限于 `left_spine_ops_v1`：C/I/J/T 分别为 COPY/INV/JOIN/INTER，词从叶向根执行，长度为 2 或 3。每步仅延伸已有主干；二前提的另一项是新事实。候选 witness、fresh 符号与实体绑定沿用 T0019，不由执行者选择或扩展。

这里有 80 个不同完整 motif 键，**不是全部深度 2–3 的证明结构**。双侧均有非平凡支持、其他关系复用／实体等同结构、深度 4–5 压力测试及开放边界片段另立协议。后续生成器可做全局双射重命名、patch 重排和等价前提交换；不得把改变共享／绑定结构后的新键仍标成目录内同一 motif。

## 2. 匹配口径

匹配固定为 `complete_rooted_support_subtree`：在查询的**全部有效证明**中，对任一步取该发生结论及实际依赖的完整支持子树，比较其完整 `proof_motif_v1` 键与目录整树键。使用 T0018 及既有依赖；不能只审查计划 witness。

不把上游支持截断为边界事实，不匹配任意连续操作词片段。例如 CJC 包含 CJ，却不包含 JC；CCC 包含 CC。这里的“无泄漏”只指该明确口径下的有标签查询组合，不意味着训练世界里从未共存过基本规则，也不排除另一种开放边界定义下的结构暴露。

若未来采用开放边界匹配或扩大候选族，必须升版、重新分组并重新审计，不能沿用本版的零跨集合边结论。枚举超限或不完整一律拒绝为未完成审计，不视为无命中。规范证明计数与 motif 数保持分离。

## 3. 固定目录分配

T0019 的真实包含图忽略边方向后有 16 个连通分量，每个为一个二字符候选及其四个三字符延伸。整分量分配避免把较短保留结构泄漏到另一集合的较长证明中。ID 前两字符仅用于固定分配，**不代替实测键或包含关系**。

| motif 集合 | 二字符组根，按 C/I/J/T 目录序 | 二字符键数 | 三字符键数 | 总键数／包含组数 |
| --- | --- | --- | --- | --- |
| train | CJ, CT, IC, II, JC, JI, TJ, TT | 8 | 32 | 40／8 |
| dev_composition | CC, IJ, JT, TI | 4 | 16 | 20／4 |
| test_composition | CI, IT, JJ, TC | 4 | 16 | 20／4 |

同组四个延伸分别追加 C/I/J/T，并属于同一 motif 集合。每个集合内部沿用 T0019 的“所有长度 2，然后所有长度 3；字符次序 C,I,J,T”顺序。完整列表：

```text
train:
CJ CT IC II JC JI TJ TT
CJC CJI CJJ CJT CTC CTI CTJ CTT ICC ICI ICJ ICT IIC III IIJ IIT
JCC JCI JCJ JCT JIC JII JIJ JIT TJC TJI TJJ TJT TTC TTI TTJ TTT

dev_composition:
CC IJ JT TI
CCC CCI CCJ CCT IJC IJI IJJ IJT JTC JTI JTJ JTT TIC TII TIJ TIT

test_composition:
CI IT JJ TC
CIC CII CIJ CIT ITC ITI ITJ ITT JJC JJI JJJ JJT TCC TCI TCJ TCT
```

选择仅依据构造、分桶和包含关系，未使用模型训练或评估结果。各集合二字符组根的每个位置均覆盖 C/I/J/T：train 每个操作出现 2 次，dev/test 各 1 次。训练覆盖全部基本操作；重复操作也分布在训练 II/TT、开发 CC、测试 JJ 中。

## 4. 配平与已核验依据

步数为 witness 的全部证明步骤数，包含事实；不是深度、操作词长或运算预算。

| 最短深度 | 证明步数 | train | dev_composition | test_composition |
| --- | --- | --- | --- | --- |
| 2 | 3 | 2 | 1 | 1 |
| 2 | 4 | 4 | 2 | 2 |
| 2 | 5 | 2 | 1 | 1 |
| 3 | 4 | 4 | 2 | 2 |
| 3 | 5 | 12 | 6 | 6 |
| 3 | 6 | 12 | 6 | 6 |
| 3 | 7 | 4 | 2 | 2 |

每格同时是候选行数与不同完整键数，规范证明数逐项为 1。根据接受报告的 `contained_ids` 实测，源／目标同为 train/dev/test 的边数分别为 72/36/36，其余六格为 0；总计 144 条边，含 80 条自身边、64 条非自身边。[规划分析原件](../reports/T0020/planning-r1/stdout.json)来自真实已接受报告，并非新产品执行结果。

“不同完整键数”不代表统计独立样本数：20 个测试键只有 4 个包含组。分析同时报告 motif 与组级诊断，组级诊断不新增主指标；推广到其他结构仍需要独立目录的复验。世界数、20 个键数都不能被当成 20 个独立结构组。原研究计划关于以 world 聚类、固定目录条件下的不确定性和探索性解释继续适用。

## 5. 后续数据生成的约束

本目录决定结构分配，不分配 world 或 family，不改变计划中的 20,000 训练 world 等样本规模、训练目标、模型输入白名单、主对照矩阵或计算预算。

- 训练、开发 IID、测试 IID 的组合目录使用 train 结构；它们的 family 必须互不相交。开发组合与测试组合分别使用另外两个目录。
- 对训练及 IID 查询的全部有效证明，禁止命中 dev 或 test 保留目录；对开发组合查询禁止命中 train 或 test 的目录键，测试组合禁止命中 train 或 dev 的目录键。本版采用三集合之间均无包含边的强约束，禁止对象只含目录中的深度 2–3 完整键，不禁止共享基本操作。未来加入干扰后必须重新实测，不能由目录图推断整 world 无泄漏。
- 主组合正样本仍须唯一规范证明；标签、负例、反事实与 family 由后续准入／生成任务设计和审计。负样本桶沿用配对正样本的规则不变。
- `split`、组根、候选 ID、证明、完整键、深度及包含信息只在离线审计端，绝不加入模型可见 clause、query、路由或输入 token。
- 当前仅冻结符号结构定义；未来正式 test world、标签和结果仍按原计划锁定。本协议不是测试解锁授权，也不是 M1 完成或实验收益结论。

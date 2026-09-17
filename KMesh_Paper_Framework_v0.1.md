---
title: KMesh - Locally Updatable Knowledge Patches for Continually Evolving Neural Memory
---

# KMesh：面向局部更新与持续演进的知识网络架构
## ——研究框架草案 / Paper-like Research Outline

> **状态说明**：本文档不是论文初稿，而是借用论文结构整理目前关于 KMesh 的研究思路、相关工作、关键假设和后续实验计划。  
> 其中很多观点仍然只是待验证的工作假设，目的在于帮助后续研究和工程实现保持一致，而不是提前下结论。

**讨论修订 1（2026-09-16）**：与[研究计划 v0.1.2](KMesh_Research_Plan_v0.1.md)对齐，保留原文件名。本文负责问题与机制组织，研究计划规定阶段协议，具体实施以 Codex 冻结的交接为准。E0 保持 `e0_v2`；E1a/E1b 为 `e1_v3`；图预测和图指导训练另列后续草案，本文不授权立即实现。

---

## 0. Working Title

**KMesh: Locally Updatable Knowledge Patches for Continually Evolving Neural Memory**

可选副标题：

- **Aligning Semantic Locality with Parameter, Computation, and Update Locality**
- **A Knowledge Mesh for Sparse, Composable, and Continually Evolving AI**
- **Local Updates, Global Composition**

---

# 1. Abstract / 核心问题

当前大语言模型把大量知识、推理能力和语言处理能力混合编码在同一套密集神经网络参数中。  
这种设计带来了很强的统一建模能力，但也造成几个根本问题：

1. 在共享权重中持续吸收新知识可能需要昂贵的训练；检索、局部编辑和小参数适配已提供部分替代，仍需检验长期组合与成本；
2. 很难明确定位某一条知识对应哪些参数；
3. 即使一次任务只涉及极少量知识，forward/backward 往往仍需要访问大部分或全部主干参数；
4. 模型容量、GPU 显存、训练计算和知识容量高度耦合；
5. 局部知识修改容易干扰已有知识，而多个独立修改又可能无法稳定组合；
6. 大规模模型训练依赖 FSDP、ZeRO、tensor parallel 等手段去分摊整个 dense tensor，而不是让当前任务只访问真正需要的知识参数。

KMesh 探索另一种架构假设：

> **将知识组织成可独立寻址、局部更新、稀疏激活的 knowledge patches，并让这些 patches 组成一个持续演进的知识网络。一个相对较小的共享神经计算核心根据当前任务，从知识网络中选择少量相关 patch 进行读取、组合和更新。**

KMesh 希望最终实现：

\[
\text{Semantic Locality}
\rightarrow
\text{Parameter Locality}
\rightarrow
\text{Computation Locality}
\rightarrow
\text{Update Locality}
\]

同时仍然保持：

\[
\text{Global Composability}
\]

核心科学问题不是“能否局部修改一些参数”，因为 embedding、MoE、LoRA、model editing 等研究已经证明这一点在不同形式下可行。

KMesh 真正要验证的是：

> **能否让语义上局部的一份知识，自然映射成计算和参数上的局部对象，并在独立局部更新后仍然与整个知识网络保持可组合性。**

这些基础实验服务于最终 **H6/E4**：LLM 训练大多数时候能否仅更新小范围参数，在保持质量的同时降低达到同等质量的总成本。允许少量必要的全局更新；知识编辑成功、读取稀疏或容量扩大都不能单独证明该命题。

---

# 2. Motivation / 为什么需要 KMesh

## 2.1 当前 LLM 将知识与计算混在一起

对于普通 Transformer：

\[
y = xW
\]

即使当前样本只涉及一条局部知识，dense matrix \(W\) 仍通常整体参与 forward，反向传播也会影响大量参数。

因此：

> “当前任务只涉及少量知识”

并不能自动转化为：

> “当前任务只需要少量参数和计算”。

这也是 FSDP / ZeRO 等系统存在的背景：完整 tensor 仍然是计算图的一部分，只能把它分片、聚合、再分片。

KMesh 的目标不是做一个更聪明的 FSDP，而是尝试改变这个前提：

> 当前任务本来就只需要访问整个知识空间中的很小一部分。

## 2.2 知识容量是否必须等于活跃计算容量？

近年的 MoE、Memory Layers、Engram 等工作已经不断提示：

- 总参数量可以远大于每 token 激活参数量；
- 记忆容量可以远大于主干计算容量；
- 静态知识可以通过 lookup / sparse memory 方式从神经计算中外置；
- 很大的 memory table 不一定必须常驻 GPU HBM。

KMesh 希望继续推进：

\[
\text{Conditional Computation}
\rightarrow
\text{Conditional Memory}
\rightarrow
\text{Structured, Editable Knowledge Memory}
\]

## 2.3 持续学习比一次性预训练更重要

如果知识更新必须周期性重新训练整个模型，那么：

- 模型越大，更新越昂贵；
- 新知识加入越频繁，维护成本越高；
- 个体化模型难以持续成长；
- desktop / laptop / cellphone 等资源受限设备很难长期独立维护自己的 AI。

KMesh 希望支持：

```text
添加一个 patch
修改一个 patch
撤销一个 patch
局部训练若干 patch
更新局部关系
↓
整体知识网络继续工作
```

而不是：

```text
新知识
↓
重新做大规模训练
```

这与长期的 **AI for Everyone** 愿景一致：让 AI 的能力增长不必始终依赖巨型 GPU 集群。

---

# 3. Central Hypotheses / 核心假设

本节采用 F 前缀，避免与研究计划的 H 编号混淆；阶段编号以研究计划为准。

| 本文概念假设 | 研究计划对应项 |
|---|---|
| F1 知识局部性 | H0/H1 与工作集测量 |
| F2 更新局部性 | H3a/H3b |
| F3 计算局部性 | §1.5 与 H6 的成本条件 |
| F4 全局组合 | H1/H3c |
| F5 功能关系 | H2/H3d/H3e |
| F6 抽象形成 | H4/E2 |
| 最终训练命题 | H6/E4；容量配比单列 S-scale |

## F1. Knowledge Locality

一个具体任务通常只需要访问整个知识网络中的一小部分知识。

\[
|W_t| \ll |\mathcal K|
\]

其中 \(\mathcal K\) 是整个知识网络，\(W_t\) 是当前任务所需 working set。

E0 的 patch 划分由生成器提供，只验证这种划分下的使用能力，不能证明真实 LLM 的知识已被自动局部化。

## F2. Update Locality

新增或修改知识时，不必重新训练整个知识系统，只需要更新少量 patch 及其局部关系。

## F3. Computation Locality

希望通过可寻址 patch 和相应执行机制减少本轮 forward/backward 的参与范围；可寻址本身不保证未选 patch 零成本。

当前 E0 仍可全池编码／评分，E1b 的反向仍须穿过冻结核心。分别测量语义支持集、读取工作集、编码／评分范围、可更新参数、反向路径和端到端成本，不从 top-k 或冻结参数直接推断训练加速。

## F4. Global Composability

虽然知识局部存储和更新，但任务可以动态组合多个独立 patch，形成未见过的新知识组合。

这是最困难的假设之一，也是 A³E 所提示的核心风险。

## F5. Functional Relations Can Be Learned

patch 之间的关系不应该只由文本 embedding similarity 决定。

模型实际运行过程中：哪些 patch 经常共同激活、哪些 patch 经常顺序激活、哪些组合带来协同、哪些组合产生冲突，这些运行时信号可以帮助知识图逐渐形成更有功能意义的拓扑。

## F6. Abstraction Can Emerge Without Fixed Hierarchy

KMesh 不预先区分“摘要 patch”“普通 patch”“高层 patch”“低层 patch”。所有 patch 使用统一表示。

某些 patch 可能因为跨任务复用、连接多个知识区域、能够指导大量具体知识的使用，逐渐成为逻辑上的核心节点。不同 Transformer layer / reader 可能形成不同的读取偏好，从而出现功能上的抽象分工。

---

# 4. Related Work / 相关研究

KMesh 并不是从零开始的概念，而是多条已有研究线的汇合。

## 4.1 Sparse Embedding / Recommender Systems

Embedding table 很早就实现了：

```text
巨大参数空间
↓
按 ID 读取少量 rows
↓
只更新被访问的 rows
```

word2vec、推荐系统 embedding table 都已经证明：总参数容量很大，而单次 forward/backward 只处理极少部分参数，是完全可行的。

KMesh 的挑战在于：知识没有显式 user_id / word_id，必须通过语义和推理状态进行寻址。

## 4.2 Mixture of Experts

Sparsely-Gated MoE、Switch Transformer、DeepSeekMoE 等工作证明：

\[
\text{Large Total Capacity}
\neq
\text{Large Activated Compute}
\]

只有少数 expert 参与当前 token 的计算。

MoE 可以被理解成 **parameter locality induced by routing**。KMesh 希望从 conditional compute 进一步推进到 **conditional knowledge**。

## 4.3 Product-Key Memory / Memory Layers at Scale

Product-Key Memory 直接向 Transformer 中加入大规模稀疏 key-value memory。

**Memory Layers at Scale** 更进一步探索：

- 多个 Transformer 层共享同一 memory；
- 大 memory 只激活少量 entries；
- memory capacity 与主干网络计算能力部分解耦。

这对 KMesh 的两个假设提供直接支持：memory 可以跨层共享；knowledge-like capacity 不必全部塞进 FFN / dense weights。

## 4.4 End-to-End Memory Networks

End-to-End Memory Networks 展示了一个模型可以对外部记忆进行多跳读取，并通过多轮 memory access 完成推理。

这与 KMesh 的 multi-patch composition 很接近。区别在于 KMesh 进一步关心 memory 本身持续更新、patch 之间有长期关系、patch 可以分页和局部训练。

## 4.5 Engram

DeepSeek 的 Engram 是 KMesh 最相关的近期工作之一。

它将模型容量拆成：

\[
\text{Conditional Computation}
+
\text{Conditional Memory}
\]

并使用 N-gram hash 直接访问巨大 memory table。

Engram 对 KMesh 的重要启发：

1. **知识可以外置**：部分静态知识不必依赖 Transformer 层不断重新计算。
2. **Retrieve 与 Use 应分开**：memory 被召回之后，还需要 contextual gating 判断当前语境下是否真正使用。
3. **Memory 可以分层存储**：其推理实验将 memory offload 到 host memory，并用 prefetch 重叠传输；不直接构成训练卸载或训练提速证据。
4. **Layer placement 重要**：较早读取知识可以释放 Transformer 的有效计算深度，但过早读取时上下文不足。
5. **Compute 与 Memory 之间可能存在最佳分配比例**：memory 并不能无限替代计算核心。

KMesh 与 Engram 的核心区别：

| Engram | KMesh |
|---|---|
| N-gram / hash address | semantic + graph + learned addressing |
| memory entries | knowledge patches |
| 无显式知识图 | 动态 knowledge mesh |
| 主要是静态条件记忆 | 持续修改和局部训练 |
| address known early | address often depends on reasoning state |
| 不重点处理 edit composition | composability 是核心问题 |

引用边界：本文核对 [Engram v1 §2.5、§6.4](https://arxiv.org/html/2601.07372v1)。训练使用 GPU 分片表和 All-to-All；输入 N-gram 哈希并不提供多跳任务的正确证明地址。KMesh 列中的动态图与持续组合是研究目标，不是已完成系统的能力声明。

## 4.6 Model Editing: ROME / MEMIT / SERAC / GRACE

这些工作证明 specific knowledge can sometimes be locally edited。

- **ROME / MEMIT**：直接修改 Transformer 中与 factual association 有关的局部参数；
- **SERAC**：将 edits 外置，通过 retrieval + auxiliary model 使用；
- **GRACE**：在 latent space 中建立可持续增长的 edit codebook。

它们说明知识局部修改并不是一个新概念。KMesh 的目标更接近从一开始就把整个知识系统设计成可局部寻址、更新和组合的架构，而不是在 dense model 训练完之后再进行 post-hoc repair。

## 4.7 MEMOIR

MEMOIR 更接近 KMesh 的 local-update 假设：每个 edit 只修改 residual memory 中特定参数子集，并通过 sparse activation 选择相关参数，目标是降低多个 sequential edits 的相互干扰。

它说明不同知识更新映射到不同参数区域，是一个可行的研究方向。但它仍没有完全解决 patch 如何自然形成、patch 之间如何建立长期关系、multi-hop composition、动态分页、全局知识演进。

## 4.8 A³E: Compositional Model Editing

A³E 暴露了 KMesh 最需要重视的问题：

> 两条 edit 单独都成功，不代表它们放在一起仍然正确。

已有方法会出现 knowledge loss、interference、knowledge sinking、independent edits 无法正确组合。

这直接告诉我们：

\[
\text{Local Update}
\neq
\text{Global Compatibility}
\]

因此，KMesh 不应把“能局部修改 patch”当作完整成功。需要在预先保留、暴露可审计的组合上检验连续更新后能否协作，并明确失败范围；有限测试不能证明任意组合始终正确。

## 4.9 Hebbian Learning / Fast Weights

Hebbian principle——“fire together, wire together”——为 KMesh 的动态关系学习提供经典先例。

KMesh 可以把这种思想提升到知识对象层：如果两个 patch 在很多任务中共同参与计算，它们之间应该逐渐形成更强的 functional association。

这可以看作 **patch-level Hebbian association**。

## 4.10 DNC / Relational Memory / Attention-as-Graph

Differentiable Neural Computer、Relational Memory Core、attention-based relational models 等工作说明：memory slot 之间可以显式建模关系，memory relation 可以动态更新，attention matrix 可以被理解为输入相关的 soft adjacency。

KMesh 的进一步设想是：

```text
runtime transient relation
↓
长期积累
↓
persistent patch graph
```

即 **attention-to-association consolidation**。

## 4.11 RAPTOR / GraphRAG

RAPTOR 和 GraphRAG 说明：只做局部 chunk retrieval 对某些全局问题不够，建立多分辨率摘要或全局图结构可以改善跨区域问题。

KMesh 不准备采用固定的严格层次摘要树，但这些工作支持一个重要观点：局部知识访问之外，需要某种全局可达性和跨区域抽象。

---

# 5. KMesh Architecture / 架构草案

## 5.1 Knowledge Patch

一个 patch 是可以独立寻址、读取、更新、版本化、建立关系的知识对象。

候选表示：

\[
P_i = (id_i,C_i,k_i,U_i,E_i,v_i)
\]

其中：

- `id_i`: stable Patch ID
- `C_i`: 模型可见的知识内容，遵守研究计划输入白名单
- `k_i`: retrieval representation
- `U_i`: neural memory representation
- `E_i`: relations
- `v_i`: version

patch 不一定是一条事实。它可以是 fact、rule、condition、exception、concept、procedure、skill、reusable abstraction，但第一阶段不强制这些类型。

E0/E1 只实现研究计划规定的正向 Horn clause。来源、provenance、证明、family 和角色标签单独保存，不借 `C_i` 输入模型；`v_i` 在工程上区分 content_version 与 representation_version。

## 5.2 Unified Patch Pool

KMesh 不预设独立的 summary pool、fact pool、skill pool，而是一个统一 patch space。

某些 patch 可能因为广泛复用而成为逻辑核心，但这应当由训练和实际使用产生，而不是由人工标注决定。

## 5.3 Patch Graph / Knowledge Mesh

patch 之间可以存在多种关系。不建议只存一个 scalar “similarity”。

更可能需要：

\[
E_{ij}=\{s_{semantic},s_{coactivation},s_{transition},s_{synergy},s_{conflict}\}
\]

- **Semantic relation**：内容相似、概念相近；
- **Coactivation relation**：在解决任务时经常共同被读取；
- **Transition relation**：读取 \(P_i\) 后，经常进一步读取 \(P_j\)；
- **Synergy relation**：二者共同使用时，效果超过单独贡献简单相加；
- **Conflict / competition relation**：二者在联合使用或更新时容易产生负干扰。

最终 graph 可能是一个 **multi-relational dynamic knowledge graph**。

当前 E0 仍使用研究计划 §6 的固定内容图。动态关系后置研究；用于检索的图与用于预测复验范围的图分别评价，不要求边相同。

---

# 6. Runtime Retrieval / 推理时读取

KMesh 建议采用至少两阶段：

```text
Candidate Retrieval
↓
Contextual Gating
↓
Actual Use
```

即：

\[
\operatorname{Retrieve}(q)\rightarrow\{P_i\}
\]

然后：

\[
\alpha_i=\operatorname{Gate}(h,P_i)
\]

最后：

\[
h'=h+\sum_i\alpha_iV(P_i)
\]

这借鉴 Engram：retrieval 只负责 recall，当前 hidden state 决定 memory 是否真正适用。

---

# 7. Multi-layer Reading / 多层访问

KMesh 不要求 `P123 belongs to Layer 6`，更可能是：

```text
Patch P123
├── Reader@Layer2
├── Reader@Layer6
└── Reader@Layer10
```

共享 patch \(U_i\) 由不同 layer-specific reader 解释：

\[
K_i^{(\ell)}=U_iW_K^{(\ell)}
\]

\[
V_i^{(\ell)}=U_iW_V^{(\ell)}
\]

这允许同一知识跨层访问、不同层形成不同读取偏好，并让 memory 与 Transformer 层解耦。

---

# 8. Global Abstraction / 全局抽象

KMesh 不采用严格的“事实 → 区域摘要 → 总摘要”层次。

更倾向于一个图中自然出现不同功能范围的节点。某些 patch 可能跨多个区域、在不同任务中频繁复用、帮助指导后续检索、承载可迁移规则，因此成为逻辑上的“高层节点”。

但：

> **graph centrality ≠ abstraction**

不能把 degree、PageRank、access frequency 直接当成“抽象程度”。真正需要验证的是某个 patch 是否能在表面不同的新任务中提供稳定可迁移的结构。

---

# 9. Stage-wise Retrieval / 分阶段读取偏好

一个工作假设是不同 Transformer layer / reader 会形成不同知识访问模式。

例如某些阶段偏向局部具体知识，某些阶段偏向广泛复用规则，某些阶段重新进行全局搜索，某些阶段沿当前 graph 做 multi-hop expansion。

但 KMesh 不预先规定固定层级。

可以让每一层学习：

\[
p_\ell=(1-\gamma_\ell)p_\ell^{global}+\gamma_\ell p_\ell^{graph}
\]

其中 `global` 是重新从整个 patch space 检索，`graph` 是沿当前已激活 patch 的邻居扩展，\(\gamma_\ell\) 可学习。

---

# 10. Local Update / 局部知识更新

理想目标：

\[
P_i^v\rightarrow P_i^{v+1}
\]

只更新 patch 自身表示、少量 reader / adapter（如果必要）、patch 周围相关关系，而不是重新训练整个网络。

但局部 edit 本身不是最终目标。真正需要解决：

\[
\boxed{\text{Local Update}+\text{Compatibility Preservation}}
\]

---

# 11. Coactivation Graph / 基于共同激活的关系学习

这是当前最重要的新想法之一。

假设在 layer \(\ell\)，\(a_i^{(\ell)}\) 表示 patch \(P_i\) 的有效激活强度。

可以积累：

\[
C_{ij}\leftarrow C_{ij}+a_ia_j
\]

形成长期 co-use 统计。

但不能简单使用 raw coactivation count，因为热门 patch 会形成伪 hub，同时激活也可能代表互补或竞争。

因此可考虑归一化：

\[
R_{ij}=\log\frac{P(i,j)}{P(i)P(j)}
\]

同时记录 directional relation：

\[
P(P_j@t+1\mid P_i@t)
\]

这些是受现有检索策略影响的观测信号，不直接证明因果关系。首轮只从允许的训练／历史 support 收集；开发流选阈值，锁定评估 trace 不回流建图。在线学习图须另定先预测后观察的协议，不能用本次更新后的评估访问来“预测”同次更新的影响。

---

# 12. Causal Synergy / 组合协同

仅共同激活还不够。

对于重要候选边，可以用少量 intervention 来估计：

\[
S_{ij}=L_{-i}+L_{-j}-L_{-ij}-L
\]

这里 \(L\) 是同一固定评价集上的损失，减号下标表示删除相应 patch。以联合使用带来的额外损失下降定义协同：

- \(S_{ij}>0\)：互补收益；
- \(S_{ij}<0\)：可能存在冗余，不能直接等同于 conflict；
- 两者缺一不可时 \(L=0,L_{-i}=L_{-j}=L_{-ij}=1\)，应得到 \(S_{ij}=1\)。原草案公式是本式的相反数，与“正值表示互补”的说明不一致，本次更正。

固定删除方式、损失尺度和样例，不重新训练；固定读取路径与删除后重新检索分别报告。该量描述当前模型的 patch 使用交互，不能直接当作两次训练更新的协同。后者需从共同编辑前快照比较无更新、分别更新和依次更新，见研究计划 §11.8。

不可能对所有 patch 两两计算，因此：

> **coactivation 负责 cheap candidate discovery；intervention 负责 sparse causal calibration。**

校准本身需要计入成本，且结论只适用于规定干预与样例，不能给全图自动贴因果标签。

---

# 13. Why the Graph May Be Critical for Local Updates

A³E 暴露的问题是：独立 edit 之后，未来到底会和哪些知识组合？

如果 KMesh 已经从历史使用中建立：

```text
P_i
├── P_17
├── P_42
├── P_103
└── P_912
```

那么当：

\[
P_i^v\rightarrow P_i^{v+1}
\]

更新时，可将下列组合列为优先检查的候选，是否能减少全面复验仍需独立验证：

\[
P_i'\oplus P_{17},\quad
P_i'\oplus P_{42},\quad
P_i'\oplus P_{103}
\]

这形成 **Local Compatibility Frontier**：

\[
\text{Local Update}
\rightarrow
\text{Local Compatibility Regression}
\]

这不是已经成立的复杂度结论。两两边不能保证高阶组合，访问范围也可能因桥接节点而接近全局；成本还包括图维护、patch 到查询的映射和独立审计，不能无条件宣称 \(O(N^2)\rightarrow O(|E|)\)。

后续 E1-F（`e1_frontier_v1` 草案）先固定模型和更新策略，用事件前图预测复验查询集合，再以固定小世界全集或与邻域选择独立的抽样审计验证。不得用本次评估损失／访问选邻域，也不得只查选中区域就宣称没有退化。

按相同查询检查预算，对比随机、访问频率／度数、语义、共同激活／转移和混合策略；符号依赖图仅为使用特权语义信息的离线诊断，不保证覆盖神经退化的上界，也须接受独立审计。报告真实退化覆盖、邻域外漏检、高阶组合和版本变化表现、实际检查量及总成本。真值合理变化与遗忘分开；无退化时覆盖率为 NA。具体映射、覆盖门槛、漏检容忍度和预算须在解锁测试前冻结，详见研究计划 §11.9。

---

# 14. Patch Update Objective / 更新时的兼容性训练

更新 \(P_i\) 时，不只优化新知识本身：

\[
L_{new}(P_i')
\]

而可以从邻居 \(N(P_i)\) 中采样，加入：

\[
L=L_{new}+\lambda L_{composition}+\mu L_{locality}
\]

其中：

- **New knowledge loss**：保证新知识本身正确；
- **Composition loss**：保证新 patch 与历史上相关 patch 仍然正确协作；
- **Locality / retention loss**：保证无关知识不受意外影响。

这可能是 KMesh 对 compositional editing 问题的核心回答。

这是后续 E1-G 的候选目标，不替换 E1b 的 support CE＋L2。监督只能来自已授权的新／历史 support，不来自测试证明或未来事件；失效历史标签需按统一规则剔除或重标并计成本。首轮仅训练原授权集合 \(S_t\)，邻居提供样例或读取上下文且参数冻结。扩大可训练邻居须另列因素，见 §23 和研究计划 §11.10。

---

# 15. Graph Update After Patch Modification

patch 更新后，旧关系不应全部删除，也不应完全保留。

可以：

\[
w_{ij}^{new}=\rho_iw_{ij}^{old}
\]

其中：

\[
\rho_i=f(distance(P_i^{old},P_i^{new}))
\]

小改动时 \(\rho\approx1\)，大改动时 \(\rho\ll1\)。

之后随着新 patch 被重新使用，再利用 coactivation、transition、gradient affinity、intervention 重新估计关系。

这是后续候选规则，不纳入 E0。边须绑定来源、版本和统计时点；内容大改、撤销与表示变化的处理分别规定，距离函数和衰减只在开发阶段选择。E1-F 首轮冻结事件前图；更新后产生的评估信息不能回流本次预测。

---

# 16. Self-reinforcement Risk / 图自强化风险

动态 graph 存在明显反馈：

```text
edge 强
↓
更容易被 retrieve
↓
更容易共同激活
↓
edge 更强
```

即：

\[
retrieval\rightarrow coactivation\rightarrow edge\rightarrow more\ retrieval
\]

需要考虑 edge decay、exploration、popularity normalization、independent semantic retrieval、held-out coactivation statistics、causal validation、graph-free candidate generation，避免图自己制造“证据”。

---

# 17. Storage Hierarchy / GPU-RAM-SSD 分层

KMesh 的长期设计：

```text
GPU HBM
↓
Host RAM
↓
NVMe SSD
```

热点 patch 放 GPU，温 patch 放 RAM，冷 patch 放 SSD。

当前任务只加载：

\[
W_t\subset\mathcal K
\]

这意味着知识网络理论容量可以远大于 GPU 显存。

---

# 18. Addressing / 地址与重定位

每个 patch 需要稳定的逻辑身份：

\[
PatchRef=(namespace,patch\_id,content\_version,representation\_version)
\]

而当前驻留地址：

\[
ResidentTable[PatchRef]\rightarrow(device,page,offset)
\]

可以动态变化。

\(local\_slot\) 表示 patch 内部有语义的槽位位置，作为读视图另行保存，不替代对象版本。此定义与研究计划 §1.4 一致。

核心原则：

> **stable logical identity, movable physical storage**

Q/K/V 不应依赖真实 GPU offset。

运行时应保证：

\[
F(x,\mathcal P;layout_1)\approx F(x,\mathcal P;layout_2)
\]

即同一批 patch 换不同物理布局，不改变模型语义。

---

# 19. Prefetch / 预取

Engram 的优势是地址可以由 N-gram 提前确定。KMesh 的地址往往依赖 \(h_\ell\)，因此可能需要 **predictive patch prefetch**。

早期 hidden state：

\[
h_\ell
\]

预测：

\[
P(P_i\text{ later needed}\mid h_\ell)
\]

提前将候选 patch 从 RAM 搬入 GPU。后续更深层 \(h_{\ell+k}\) 再进行精确 gating。

---

# 20. Experiments / 实验路线

编号与研究计划一致：E0-D 为可信数据，E0-C 为任务可学性，E0-R 为图与阶段路由；下列诊断和消融不再另占 E0-A/B/C 编号。默认预算与正式主矩阵仍以研究计划 §8 为准。

## E0. Unified Patch Retrieval & Composition

目标：验证统一 patch 池能否被小型 Transformer 正确读取和组合。

使用 synthetic rule world。patch 包含 facts、rules、conditions，但模型不接收显式“高层 / 低层”标签。

主要测试：

- 新世界；
- 未见组合；
- counterfactual patch replacement；
- multi-hop reasoning。

## E0-C 诊断：D-full / D-oracle 与 Exact Lookup

已知地址时可以直接取得 patch：

```text
known key
↓
exact patch
```

必须声明 known key 的来源。若求解器提供正例的正确支持地址，它属于 D-oracle 特权诊断，负例不伪造证明；不能作为普通检索主基线。由输入直接算出的地址才是普通输入信息，但 Engram 的 N-gram 哈希不等于多跳证明地址。

D-full（全读取）与 D-oracle 用来区分 reader/reasoner 和 retrieval 瓶颈，不能将 oracle 表现报告为正式任务能力。

## E0-R：Graph Ablation

第一轮保持研究计划的 G0 与 M00–M11 等预算比较，图为固定、内容派生的 Jaccard 邻接。共同激活／混合图暂不加入 E0；先在后续 E1-F 检验复验预测价值，若将来用于检索，须另立对照与协议版本。

指标沿用组合准确率、反事实 PairAcc 与实际成本；正例可离线分析支持集覆盖，负例不编造唯一正确支持集。

## E0-R：Stage-wise Retrieval

沿用共享门控／逐层门控与有图／无图的 2×2 因子设计，以及独立纯全局 G0：

- 全层共享同一个 routing preference；
- 各 layer 独立学习 routing；
- graph expansion + global retrieval。

验证是否真正出现有用的阶段分工。不能只看 attention heatmap，必须通过 layer gate permutation / ablation 验证。

---

# 21. E1. Local Update

## E1a. Content Replacement

冻结模型：

\[
P_i^v\rightarrow P_i^{v+1}
\]

检验新知识是否立即生效、无关知识是否保持、依赖旧知识的任务是否正确变化。

## E1b. Local Neural Patch Update

只训练研究计划 §11.2 声明的 \(S_t\) 内 patch 残差 \(\Delta_i\)，不修改共享核心、内容 encoder/key、其他 patch 和相应 optimizer states。不自动扩展到邻居。

比较：local training cost、edit success、retention、interference、composition。

主对照为 U0 内容更新、U1 局部残差、U2 共享权重适配；`e1_v3` 保留原 support/step 预算与 `replay: false`，新增组合隔离和审计。

---

# 22. E1a/E1b 的独立更新组合测试

沿研究计划先运行 50 个连续事件；下面仅为更新序列示意，事件包含 add/replace/retire，并非每步都训练：

```text
P1 update
P2 update
P3 update
...
P50 update
```

然后测试：

```text
P7 + P29 + P42
```

这样的跨事件知识组合。“从未联合训练”必须拆成可审计条件：未共同授权参数更新、未共同参与监督任务、是否共同读取。主子集要求前两项均否；同处一个 world 或偶然共同读取不自动排除，但必须披露。

在 stream/support 生成前冻结组合保留规则，记录稳定 ID、内容／表示版本和所有历史 support/replay。实体对隔离不替代组合隔离；换版本不抹掉旧暴露。审计替代证明及负例配对结构，无法认证的样例标为 unknown，不能算严格未共同监督。至少区分 2-patch 与更高阶组合，并报告绕过目标组的替代路径。

先报告全部预定组合，再报各单项更新成功条件下的组合表现和筛选数；以共同编辑前快照的小型分支诊断区分单项失败、干扰和顺序影响。沿最新真值评价，不惩罚合理知识修订；按 stream/seed 分析，不把组合题数当独立重复。长流扩容需先 profile，不默认执行千次编辑。具体审计见研究计划 §10.6/§11.8。

这是 KMesh 最重要的长期指标之一：

> **Composition after many sequential local updates**

---

# 23. E1-F / E1-G：先预测复验范围，再研究兼容性训练

**E1-F** 先按 §13 与研究计划 §11.9 检验图在有限预算内预测退化的能力，固定模型、损失与可更新集合。未达到漏检要求时不能以局部检查替代广泛审计。

**E1-G** 再研究图指导样例选择；两者分别为 `e1_frontier_v1`、`e1_compat_v1` 后续草案，尚未冻结可执行合同，不合并成一个大实施任务。

更新 \(S_t\) 时比较：

| 方法 | 历史样例选择 | 可更新参数 |
|---|---|---|
| 原始 U1 | 不 replay | 仅 \(S_t\) |
| 随机 replay | 相同历史池随机选择 | 仅 \(S_t\) |
| 语义 replay | 语义邻居相关历史 support | 仅 \(S_t\) |
| 共同激活／转移 replay | 事件前统计相关历史 support | 仅 \(S_t\) |
| 混合 replay | 开发阶段冻结的混合策略 | 仅 \(S_t\) |

各 replay 方法匹配新 support、历史池、样例暴露、步数、参数与调参预算；原始 U1 另列信息／计算差异。邻居只提供样例或读取上下文，其权重和状态冻结。扩展可更新邻域另列参数预算实验，不能把多训练参数的收益归因于图。

历史样例限已授权 support，失效标签按统一规则剔除或重标；不得访问测试题／证明／未来事件。replay 纳入全历史组合暴露审计，不能继续把已用于 replay 的组合称为未见。动态图统计默认不从锁定评估 trace 学习；在线适应须另立时序协议。

所有方法共用预冻结的保留组合和评估查询总体，数据准备端阻止任何方法监督保留组合，不向更新器泄漏测试内容。污染或 unknown 按跨方法并集统一标记，报告原总体、共同严格子集及排除数量；不能各自删题再比较，也不能以删题掩盖隔离违约。新的确认性结论需独立冻结数据。

报告新知识收益、旧知识回退、严格未共同监督组合、训练和验证总成本。目标项、权重、空池／retire 行为、样例配额与成本上限先冻结，再交给 Pi。若随机 replay 已足够或图成本抵消收益，如实报告，不预设图解决了组合问题。

---

# 24. E2. Emergent Abstraction

只有 E0/E1 成立后再做。

目标：不向模型预先提供抽象规则，让系统从多个具体 patch 中形成新的可复用 patch。

测试：

- 新生成 patch 是否跨实例复用；
- 删除具体训练实例后是否仍然工作；
- 新抽象是否改善未见组合；
- 它是否只是高频 pattern，而非真正结构。

---

# 25. E3. Memory Hierarchy

加入：

```text
GPU
↕
RAM
↕
SSD
```

验证：hot-set residency、prefetch accuracy、page migration、dirty patch writeback、optimizer state residency、relocation invariance、training throughput。

比较：all-resident、RAM offload、RAM + SSD。

---

# 26. E4：最终 LLM 训练命题与可选 S-scale

## E4. Predominantly Local LLM Training

最终问题保持为：大多数 LLM 训练更新能否局部化，在质量相当时实测降低总成本。E0/E1 提供基础证据，之后另立协议；从头预训练与继续预训练分开，允许按预定规则少量全局更新。

至少比较同架构／初始化／数据顺序下的逐步全局更新与以局部更新为主的策略；冻结局部覆盖率、参数比例与质量容差，报告达到同一质量目标的总成本。编码、路由、反向穿过冻结核心、图维护、通信、验证、初始化及必要全局更新均计入。若只在训练后期或特定领域成立，限定结论范围。详见研究计划 §12.3；当前不启动大模型训练。

## S-scale. Compute–Knowledge Scaling

可选辅助研究，借鉴 Engram 的容量配比思路。分别定义等数据／总训练预算与等激活 FLOPs 的比较，改变：

\[
\text{Core Capacity}\leftrightarrow\text{Patch Capacity}
\]

观察 factual recall、reasoning、unseen composition、continual update。

寻找最优：

\[
\rho_K^*
\]

即所研究条件下的 compute / knowledge allocation。实际墙钟、维护和存储成本另测；等激活 FLOPs 不等于等总成本。S-scale 不替代 E4，也不作为进入 E4 的必要条件。

---

# 27. Evaluation Metrics

KMesh 不应只看 accuracy。

## Task Quality

- exact task accuracy
- multi-hop accuracy
- unseen composition accuracy

## Local Update

- edit success
- update FLOPs
- updated parameter count
- patch working-set size
- encoded/scored patch count、backward scope；不以读取比例代替计算比例

## Retention

- unrelated knowledge retention
- regression rate
- catastrophic interference

## Composition

- pair composition
- multi-patch composition
- composition after sequential updates
- 组合暴露审计覆盖率、2-patch／高阶、稳定 ID／版本分组
- 全部预定组合与单项成功条件下的组合表现，含筛选数量

## Compatibility Frontier（仅 E1-F/G）

- 独立审计中的退化覆盖、邻域外漏检和不确定性
- 相同复验预算下的随机／频率／语义／动态图比较
- 图维护、干预、历史标注、replay 与验证成本；研究审计和部署策略成本分列并计总额

## Retrieval

- patch recall@k
- retrieval precision
- graph hop efficiency

## Memory System

- GPU resident bytes
- RAM/SSD traffic
- cache hit rate
- prefetch precision / recall
- wall-clock throughput

---

# 28. What Would Count as Evidence for KMesh?

不同实验只支持不同层次的结论。

### E0 成功只能说明
统一 patch pool 可以被模型读取和组合。不能说明 local continual learning 已经解决。

### E1a/E1b 成功分别说明
E1a 支持无梯度内容更新可生效；E1b 的 U1 相对 U0/U2 对照才支持规定条件下的局部学习收益与权衡，不能推出所有 LLM 训练均不需全局更新。

### E1 组合审计成功才开始说明
在指定事件流与暴露隔离下，独立局部更新后仍可组合；不保证任意未来组合。

### E1-F / E1-G 分别检验
图能否预测复验范围，以及图指导训练是否优于等预算随机 replay。预测成功不保证训练收益，两者均允许负结果。

### E2 成功才说明
系统可能形成新的抽象知识，而不仅是存储外部事实。

### E3 成功才说明
知识容量可以实际突破 GPU residency 限制。

### E4 成功才支持最终训练命题
在指定训练阶段与质量容差内，大多数更新局部化且总成本下降；E0–E3 或 S-scale 单独成功均不能替代它。

---

# 29. Main Risks / 核心风险

## Risk 1. Patch Is Just RAG with Extra Steps

如果 patch 只是文本 chunk + embedding，KMesh 可能退化成复杂 RAG。需要证明 neural patch / local update / composition 有额外价值。

## Risk 2. Core Model Still Stores Most Reasoning and Knowledge

外部 patch 可能只是提示，真正能力仍藏在共享 Transformer 中。需要通过 patch intervention 和 core-size scaling 分析。

## Risk 3. Graph Does Not Add Value

可能 global ANN retrieval 已经够好。如果 graph 没有明显改善 composition、routing、update compatibility，则不应为了概念完整强行保留。

## Risk 4. Dynamic Graph Self-reinforcement

历史 retrieval 决定未来 graph，产生错误 hub。

## Risk 5. Local Update Breaks Global Composition

这正是 A³E 级别的问题，是整个项目最关键的技术风险。

## Risk 6. Sparse Compute Is Hardware Inefficient

理论 FLOPs 少，但 tiny GEMM、random access、RAM traffic、SSD latency 可能让 wall-clock 变慢。

## Risk 7. Abstract Patches Become Global Coupling Points

如果少数核心 patch 被大量任务依赖，更新它们可能重新造成全局耦合。因此“抽象形成”可能与“局部更新”存在内在张力。

---

# 30. Research Questions

### RQ1
知识能否被分解成可以独立寻址和更新的 patch，同时保持组合能力？

### RQ2
semantic similarity、coactivation、transition 和 gradient affinity 中，哪些最能预测真实知识关系？

### RQ3
知识图能否有效预测 patch update 后需要重新验证的 compatibility frontier？

### RQ4
不同 layer 是否会自然形成不同知识读取策略？

### RQ5
是否存在无需预先标注的 emergent abstraction patches？

### RQ6
一个小型共享核心能够支持多大的外部知识网络？

### RQ7
在相同训练 FLOPs 下，最佳 compute / knowledge capacity ratio 是多少？

### RQ8
GPU / RAM / SSD 分层能否保持足够高的实际吞吐？

### RQ9（最终 H6/E4）
在什么 LLM 训练阶段，多大比例的更新可限制于多小的参数范围？仍需多少全局更新，达到同等质量的总成本实际下降多少？

---

# 31. Proposed Research Sequence

建议不要一次实现完整 KMesh。

```text
E0-D / E0-C
Trusted synthetic worlds + independent solvers/proof verifier
↓
Unified patch reader + D-full / optional D-oracle diagnostics
↓
E0-R
G0 + fixed-content graph / stage-gate factorial controls
↓
E1a / E1b
Content updates / local residual learning
↓
Independent-update composition + exposure audit

Optional follow-up
E1-F: predict regression-check scope with independent audit
↓
E1-G: matched-budget graph-guided replay, if worth testing

Separate later protocols, chosen from evidence
E4: predominantly local LLM training and equal-quality total cost
E2 / E3 / S-scale: optional abstraction / storage / capacity studies
```

箭头表示同一分支内的研究顺序，不把 E1-F/G、动态图、E2/E3 或 S-scale 设为 E4 的硬前置。图无优势时可继续使用简单无图 reader；只有具体瓶颈需要时才扩展工程。当前 T0006 证明验证器可继续，不要求重做已验收基础设施。

优先级：

> **先验证 composability，再优化存储。**

如果独立 patch 无法可靠组合，那么分页、prefetch 和超大容量都没有意义。

---

# 32. Long-term Vision

如果 KMesh 的核心假设成立，未来模型可以从：

```text
Large Dense / MoE Model
```

转变为：

```text
Small Shared Reasoning Core
+
Large Evolving Knowledge Mesh
+
Sparse Dynamic Access
```

知识规模可以继续增长：

\[
|\mathcal K|\rightarrow\infty
\]

而当前 GPU working set 仍保持有限：

\[
|W_t|\ll|\mathcal K|
\]

知识更新可以：

```text
local patch update
↓
local relation update
↓
local compatibility validation
↓
global system continues to evolve
```

最终希望实现：

> **能力的持续增长，不再要求计算核心、GPU 显存和全量训练成本以同样速度增长。**

这可能成为 “AI for Everyone” 的一种底层架构路线：desktop、laptop、cellphone、home server 都可以拥有持续成长的本地 AI，而不是始终依赖重新下载或重新训练一个巨大、静态、整体耦合的模型。

---

# 33. Related Work Reading List

## External / Neural Memory

- **End-to-End Memory Networks**  
  https://arxiv.org/abs/1503.08895
- **Product-Key Memory**  
  https://arxiv.org/abs/1907.05242
- **Memory Layers at Scale**  
  https://arxiv.org/html/2412.09764v1
- **Engram**  
  https://arxiv.org/abs/2601.07372
- **Memory³**  
  https://arxiv.org/abs/2407.01178
- **LongMem**  
  https://arxiv.org/abs/2306.07174

## Continual / Model Editing

- **ROME**  
  https://arxiv.org/abs/2202.05262
- **MEMIT**  
  https://arxiv.org/abs/2210.07229
- **SERAC**  
  https://arxiv.org/abs/2206.06520
- **GRACE**  
  https://arxiv.org/abs/2211.11031
- **MEMOIR**  
  https://arxiv.org/abs/2506.07899
- **A³E**  
  https://papers.neurips.cc/paper_files/paper/2025/hash/3d4c0a618d0acd7921493e4f30395c22-Abstract-Conference.html

## Dynamic Association / Structured Memory

- **Differentiable Neural Computers**  
  https://www.nature.com/articles/nature20101
- **Differentiable Plasticity / Hebbian-style learning**  
  https://arxiv.org/abs/1804.02464
- **Relational Memory Core**  
  https://arxiv.org/abs/1806.01822

## Global / Hierarchical Retrieval

- **RAPTOR**  
  https://arxiv.org/abs/2401.18059
- **GraphRAG**  
  https://arxiv.org/abs/2404.16130

## Sparse / Conditional Computation

- **Sparsely-Gated Mixture of Experts**  
  https://arxiv.org/abs/1701.06538
- **DeepSeekMoE**  
  https://arxiv.org/abs/2401.06066
- **RigL**  
  https://arxiv.org/abs/1911.11134

---

# 34. One-Sentence Positioning

> **KMesh explores whether knowledge can be represented as a dynamically connected set of locally updatable neural patches, so that semantic locality becomes computation and update locality while preserving global composability.**

中文：

> **KMesh 探索把知识组织成动态连接、可局部更新的神经 patch，使知识的语义局部性映射为计算和更新局部性，同时保持跨知识的全局组合能力。**

---

# 35. Current Bottom Line

目前最值得优先验证的不是：

> “KMesh 能不能让一个 1B 模型打败 SOTA？”

而是三个更基础的问题：

1. **独立知识能否真正成为可定位、可训练的 patch？**
2. **独立更新之后，这些 patch 是否仍能可靠组合？**
3. **知识关系图能否把全局兼容问题压缩成局部、可管理的兼容性验证问题？**

前两点是当前基础机制验证重点，第三点是可失败的效率假设；图没有优势不否定局部更新路线。后续按证据与瓶颈选择研究：

- 更大的知识网络；
- GPU/RAM/SSD 分层；
- 自动形成抽象；
- 大幅降低训练成本；
- 小型共享核心；
- 端侧与个人 AI。

这也是下一阶段研究最应该保持的聚焦点。

最终结论仍须来自独立 E4 训练对照，而非从这些基础性质直接外推成本降幅。此次只修订研究设计，没有产生新的实验结果。

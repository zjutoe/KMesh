---
title: KMesh 多专家知识构建研究计划
lang: zh-CN
translation_key: kmesh-multi-expert-knowledge-construction
category: research
permalink: /posts/KMesh_Multi_Expert_Knowledge_Construction_Research_Plan/
---

**Independently Trained Small Models → Shared KMesh → Cross-Domain Composition**

> **状态**：研究计划草案 v0.1  
> **项目**：KMesh  
> **主题**：使用一组小型、领域化 LM 作为分布式 Knowledge Compilers，共同构建和持续更新一个共享 KMesh，而不是依赖单一大型 teacher LM 完成全部知识学习。

---

## 1. 研究动机

KMesh 的基本假设是：

> AI 的通用计算能力与知识容量不必永久绑定在同一套 dense neural weights 中。

传统 foundation model 通过一次大规模预训练，把通用语言能力、推理模式、世界知识和领域知识压入同一个大型神经网络。这样会导致知识更新昂贵、不同领域知识共同占用主干参数、训练高度依赖大规模同步集群，以及局部领域变化难以独立更新。

KMesh 尝试改变这一范式：

$$
\text{Small Shared Computation Core} + \text{Large Evolving Knowledge Mesh}
$$

本研究进一步提出：

> **不同领域的知识不必由一个巨大 LM 统一学习。可以使用多个小型领域 LM 独立 post-train，再把各自学到的知识编译成兼容的 KMesh patches，共同更新一个共享知识网络。**

目标不是：

$$
100\times1B \approx 100B
$$

而是验证：

$$
\boxed{\text{Independent Domain Learning} \rightarrow \text{Shared External Knowledge} \rightarrow \text{Cross-Domain Composition}}
$$

---

## 2. 核心研究问题

> **Can independently trained small domain models contribute compatible latent knowledge patches to a shared KMesh, such that the resulting system solves cross-domain tasks that none of the individual domain models was trained on?**

中文：

> **能否让彼此独立训练的小型领域模型向同一个 KMesh 写入兼容的 knowledge patches，使整个系统能够解决任何单一领域模型都没有训练过的跨领域组合任务？**

---

## 3. 核心假设

### H1. Domain Knowledge Can Be Learned Locally

小型 LM 可以通过领域 post-training 学会某一专业领域的知识和局部推理模式，例如 Math、Code、Systems、Biology、Physics、Law。

这些模型不需要分别拥有完整通用世界知识，只需：

$$
\text{shared base capability} + \text{domain specialization}
$$

### H2. Shared Base + Domain Delta Is Preferable to Independent Pretraining

若每个领域模型从随机初始化开始，会重复学习 tokenizer semantics、syntax、basic reasoning、instruction following 和 common concepts。

因此第一阶段采用：

$$
E_d = B + \Delta_d
$$

其中：

- $$B$$：shared seed/base model；
- $$\Delta_d$$：domain adapter / LoRA / small expert。

### H3. Domain Models Are Knowledge Compilers, Not Runtime Experts

领域模型主要用于：

$$
\text{domain data}
\rightarrow
\text{domain post-training}
\rightarrow
\text{reasoning trajectories}
\rightarrow
\text{knowledge patches}
\rightarrow
\text{KMesh}
$$

patch 生成完成后，领域模型可以离线。最终部署系统主要由：

$$
\text{small general runtime core} + \text{shared KMesh}
$$

组成。

### H4. Merge Knowledge, Not Model Weights

已有 model merging 容易出现 parameter interference。

KMesh 尝试：

$$
E_A \rightarrow P_A,\qquad E_B \rightarrow P_B
$$

然后只要求：

$$
\text{Reader}(P_A,P_B)
$$

能够正确组合。

即：

> **Do not merge models; merge knowledge.**

### H5. Cross-Domain Composition Is the Critical Test

单独领域学习不是最难问题。

真正关键的是：

$$
P_{\text{math}} + P_{\text{code}}
$$

$$
P_{\text{systems}} + P_{\text{networking}}
$$

$$
P_{\text{biology}} + P_{\text{statistics}}
$$

是否能够在从未联合训练过的任务上正确组合。

### H6. A Shared Patch ABI Is Required

不同领域 expert 的 raw latent space 不天然兼容。

KMesh 需要统一：

$$
\boxed{\text{KMesh Patch ABI}}
$$

可能包括：

- canonical patch content；
- canonical latent representation；
- provenance；
- version；
- query/navigation policy；
- relations；
- confidence；
- validation metadata。

---

## 4. 与现有研究的关系

### 4.1 Branch-Train-Merge (BTM)

BTM 从共同 seed model 分叉多个领域专家，在不同 domain 独立训练，再通过 ensemble / averaging 组合。

关键启示：

- domain training 可以 embarrassingly parallel；
- 不要求全程同步梯度；
- 领域模型可以低通信独立成长。

KMesh 更进一步：不要求最后 merge 回同一套 weights，而是将知识提取为共享 patch。

### 4.2 Branch-Train-MiX (BTX)

BTX 将独立训练的领域模型重新组合成 MoE 并训练 routing。

它说明独立 experts 的能力可以被统一 runtime 协调。

KMesh 的区别在于：expert 主要是 patch producer，而不是最终 runtime 的长期主体。

### 4.3 Branch-Train-Stitch (BTS)

BTS 使用轻量 stitch layers 连接冻结的领域 experts。

启示：

- 独立 expert representation 可以通过小型接口重新对齐；
- expert 可增加或移除。

这与 KMesh 的 Patch ABI / student reader 很相关。

### 4.4 AdapterFusion

先独立训练 adapters，再学习组合 adapters。

KMesh 希望把这种组合从 adapter 权重层推进到 external knowledge patches。

### 4.5 MoE Shared Experts

近期 MoE 分析提示可能存在一小组跨领域共享 experts，而外围 experts 更偏 domain-specific knowledge。

这与：

$$
\text{small shared reasoning core} + \text{many peripheral knowledge modules}
$$

一致。

KMesh 进一步尝试把外围 knowledge 外置成 patches。

### 4.6 Federated / Continual Learning

Federated continual learning 也研究不同 client 的 domain expertise 和整体协作。

区别在于：

> 传统方法主要聚合权重或 gradients；KMesh 主要聚合 addressable knowledge patches。

---

## 5. 拟议架构

### 5.1 Shared Seed Model

第一阶段使用小型 shared base：

- 300M
- 0.5B
- 1B
- 3B

首轮建议：

$$
0.5B\sim1B
$$

目标是研究机制，而不是追求绝对性能。

### 5.2 Domain Experts

每个领域：

$$
E_d = B + \Delta_d
$$

其中 $$\Delta_d$$ 可为：

- LoRA；
- adapter；
- small expert；
- selective fine-tuning module。

首轮优先 LoRA / adapter。

### 5.3 Domain Patch Writer

每个 domain expert 使用：

$$
\text{domain reasoning trace}
\rightarrow
\text{Patch Writer}
\rightarrow
P_i
$$

输出统一格式的 candidate patch。

### 5.4 Shared KMesh

多个 expert 共同向共享 KMesh 提交 patch proposal：

```text
Expert A ─┐
Expert B ─┼→ Candidate Patches → KMesh Consolidator → Shared KMesh
Expert C ─┘
```

### 5.5 KMesh Consolidator

负责：

- canonicalization；
- deduplication；
- version management；
- provenance；
- conflict detection；
- compatibility validation；
- graph update；
- promotion / rejection。

领域模型只是 **patch proposer**，不是 authoritative truth source。

---

## 6. 补丁兼容性策略

### 6.1 Shared Seed Geometry

首轮要求所有 expert 从同一个 base 分叉。

这样不同 expert 的表示空间更接近，降低对齐难度。

### 6.2 Domain-to-KMesh Projection

每个 domain expert：

$$
h_d \xrightarrow{A_d} z_{\mathrm{KMesh}}
$$

其中 $$A_d$$ 应保持轻量。

目标：

> domain-specific latent → shared canonical KMesh latent。

### 6.3 Canonical Content Backup

每个 latent patch 同时保留：

- textual / symbolic content；
- provenance；
- source；
- domain latent；
- canonical KMesh latent。

未来 student / expert 变化时可以重新编译。

---

## 7. 跨领域桥接补丁

不同 domain 很容易形成知识孤岛，因此需要专门研究 bridge formation。

### 7.1 Real Cross-Domain Tasks

当任务同时激活多个领域 patch 时：

$$
P_A + P_B
$$

产生 coactivation / transition relation。

### 7.2 Dedicated Cross-Domain Post-Training

构造：

- math + code；
- systems + networking；
- biology + statistics；
- physics + numerical methods。

### 7.3 Coordinator / Generalist

允许一个中等规模 generalist：

- 不负责全部知识学习；
- 专门处理复杂跨域组合；
- 必要时向多个 domain expert query；
- 形成 bridge patch。

---

## 8. 冲突处理

多个 experts 一定会产生冲突。

不能：

```text
emit patch → directly commit
```

而应：

```text
candidate patch
     ↓
deduplication
     ↓
provenance check
     ↓
semantic conflict detection
     ↓
version / condition resolution
     ↓
validation
     ↓
promotion
```

---

## 9. 研究阶段 E0：双领域概念验证

### Domains

建议首选：

- Math；
- Code。

原因：

- 数据容易获得；
- verifier 明确；
- cross-domain tasks 易构造。

### Models

使用同一个：

$$
0.5B\sim1B
$$

base。

训练：

$$
E_{\text{math}}
$$

和：

$$
E_{\text{code}}
$$

两个 domain adapter。

### Goal

分别产生：

$$
P_{\text{math}}
$$

和：

$$
P_{\text{code}}
$$

然后测试：

$$
P_{\text{math}} + P_{\text{code}}
$$

解决任何单一 expert 都未训练过的 task。

---

## 10. E0 基线

### B0. Base Only

共享 base，不用 expert，不用 KMesh。

### B1. Domain Expert

直接调用对应 domain expert。

### B2. Multi-Expert Ensemble

两个 expert 同时推理，再做 output aggregation。

### B3. Adapter / Expert Fusion

在参数层面组合。

### B4. Textual RAG

把两个领域知识作为文本输入给 base。

### B5. KMesh Patches

两个独立 expert 只贡献 patch，runtime core 读取两个 patch。

---

## 11. E0 关键测试

### 11.1 Single-Domain Transfer

Math patch 是否提升 base 在 held-out math task 上表现？

### 11.2 Cross-Domain Composition

独立训练的 Math / Code patches 是否能在新 task 中组合？

### 11.3 No Joint Retraining

关键约束：

> $$P_M$$ 和 $$P_C$$ 在生成时不能联合训练。

### 11.4 Patch Replacement

只更新：

$$
P_M^v \rightarrow P_M^{v+1}
$$

验证：

- code-only tasks 不应明显变化；
- cross-domain tasks 应正确反映 math 更新。

---

## 12. 研究阶段 E1：扩展到 8 个领域

扩展到：

1. Math
2. Code
3. Systems
4. Networking
5. Physics
6. Biology
7. Law
8. General Knowledge

主要研究：

- expert 数增加时 compatibility 是否下降；
- 是否形成 domain islands；
- coactivation graph 能否自动形成 bridge；
- 是否需要 coordinator；
- 是否形成少量共享核心 patch。

---

## 13. 研究阶段 E2：异构专家

不再要求相同 base。

例如：

- 0.5B model A；
- 1B model B；
- 3B model C；
- 不同 architecture。

每个模型有自己的：

$$
A_d
$$

映射到 canonical KMesh latent。

目标：

> 验证 KMesh knowledge 是否真正独立于具体模型。

---

## 14. 研究阶段 E3：分布式知识训练

让 expert training 真正分布式：

```text
Node 1 → Math
Node 2 → Code
Node 3 → Biology
Node 4 → Systems
...
```

只交换：

- patches；
- graph updates；
- validation metadata。

不做：

- step-level gradient synchronization；
- full-model AllReduce。

测量：

- network traffic；
- wall-clock scaling；
- patch merge latency；
- update throughput。

---

## 15. 知识贡献协议

一个 domain expert 提交：

```text
PatchProposal
├── patch_id_candidate
├── canonical_content
├── latent_representation
├── provenance
├── domain
├── confidence
├── task_evidence
├── query_policy
└── initial_relation_evidence
```

Consolidator 返回：

```text
accepted
rejected
merged
superseded
conflict
needs_validation
```

---

## 16. 图构建

领域 expert 不需要提前知道完整全局关系。

Graph 主要来自：

- semantic similarity；
- runtime coactivation；
- transition；
- task outcome；
- gradient compatibility；
- cross-domain task evidence。

Teacher/domain expert 可以提供 initial prior，但 functional graph 应主要通过真实使用形成。

---

## 17. 评估指标

### Knowledge Quality

- domain task accuracy；
- factual correctness；
- verifier pass rate。

### Composition

- pair cross-domain composition；
- 3-domain composition；
- unseen composition。

### Local Update

- updated parameter count；
- patch bytes updated；
- FLOPs per update；
- unrelated-task retention。

### Compatibility

- composition after sequential updates；
- conflict rate；
- bridge-patch success。

### Scaling

- performance vs number of experts；
- training cost vs number of experts；
- communication volume；
- KMesh size。

### Runtime

- patch working set；
- retrieval cost；
- reader FLOPs；
- latency；
- cache hit rate。

---

## 18. 关键消融实验

### Same Base vs Independent Base

验证 shared seed 是否必要。

### Text Patch vs Latent Patch

验证 neural patch 的收益。

### Joint Training vs Independent Training

验证 independent domain learning 是否真正可组合。

### Explicit Bridge vs Emergent Bridge

验证跨域 bridge 是否需要人工 / teacher 帮助。

### Coordinator On/Off

验证 generalist 是否必要。

### Canonical Projection Size

验证 Patch ABI 是否能保持轻量。

---

## 19. 失败模式

### F1. Independent Patches Cannot Compose

说明：

$$
\text{independent learning} \not\Rightarrow \text{shared composability}
$$

需要改进：

- canonical alignment；
- composition training；
- bridge patches；
- shared reader。

### F2. Shared Base Stores Most Knowledge

若移除所有 domain patches 后 base 仍几乎保留全部领域能力，则外部知识没有真正承担主要作用。

### F3. Canonical Adapter Becomes Too Large

如果 $$A_d$$ 必须很复杂才能跨模型对齐，则 KMesh ABI 价值有限。

### F4. Experts Duplicate Common Knowledge

需要：

- dedup；
- canonicalization；
- shared-core separation。

### F5. Domain Islands

跨领域连接不足，组合失败。

### F6. Conflict Explosion

领域更新相互矛盾，Consolidator 成本快速增长。

---

## 20. 继续 / 停止标准

### Stage E0 Go

继续扩展前至少满足：

1. 两个独立 domain experts 都能产生有效 patch；
2. patch 对 held-out domain task 有明显帮助；
3. patch 不联合训练也能在跨域 task 中组合；
4. KMesh patch 明显优于 random latent；
5. local replacement 不显著破坏另一个 domain。

### Stage E1 Go

扩展到异构 expert 前：

1. 8-domain setting 未出现严重 compatibility collapse；
2. graph 能产生有用 cross-domain bridge；
3. patch merge / dedup 成本可控；
4. sequential update 后 composition 保持。

---

## 21. 实现结构

建议新增：

```text
kmesh/
├── experts/
│   ├── base_model.py
│   ├── domain_adapter.py
│   ├── trainer.py
│   └── registry.py
├── patch_writer/
│   ├── trace_reader.py
│   ├── compiler.py
│   ├── domain_projector.py
│   └── proposal.py
├── mesh/
│   ├── store.py
│   ├── graph.py
│   ├── consolidator.py
│   ├── conflict.py
│   ├── versioning.py
│   └── provenance.py
├── runtime/
│   ├── reader.py
│   ├── router.py
│   ├── coordinator.py
│   └── bridge.py
├── experiments/
│   ├── two_domain/
│   ├── eight_domain/
│   ├── heterogeneous/
│   └── distributed/
└── eval/
    ├── domain.py
    ├── composition.py
    ├── compatibility.py
    └── scaling.py
```

---

## 22. 建议的第一个具体实验

### Base

0.5B–1B 开放权重 base。

### Expert A

Math adapter。

数据：

- GSM-like；
- symbolic arithmetic；
- algebraic reasoning。

### Expert B

Code adapter。

数据：

- Python；
- algorithm implementation；
- executable unit-test tasks。

### Cross-Domain Tasks

构造需要：

$$
\text{math reasoning} + \text{code generation}
$$

共同完成的问题，例如：

- 推导公式再写程序；
- 数值算法实现；
- combinatorial computation；
- symbolic derivation + executable verification。

关键约束：

> Math expert 和 Code expert 在训练时从未共同看到这些 cross-domain tasks。

---

## 23. 最终希望检验的最强主张

> **A large knowledge system does not need to be learned by one large synchronized model. Independent small models can learn local domains, compile their knowledge into a shared external mesh, and create capabilities through composition that none of the individual models possess alone.**

中文：

> **一个大型知识系统不一定需要由一个同步训练的巨大模型统一学习。多个小型模型可以分别学习局部领域，将知识编译进共享外部知识网络，并通过组合产生任何单一模型都不具备的新能力。**

---

## 24. 目前不应提出的主张

当前不要声称：

- 多个 1B model 等价于一个 100B model；
- 小模型完全可以替代大型 foundation model；
- domain patches 天然兼容；
- KMesh 已解决跨领域推理；
- shared base 可以缩到任意小；
- 不再需要大型 teacher；
- independent training 一定比 joint pretraining 更高效。

当前真正要验证的是：

> **独立领域学习是否能通过共享 KMesh 转化为稳定、可组合、可增量更新的整体能力。**

---

## 25. 下一步行动

按优先级：

1. 选定一个共享小型 base；
2. 建立两个 domain adapters；
3. 设计 Math / Code 独立训练数据；
4. 定义统一 Patch Proposal / Patch ABI；
5. 训练两个 expert；
6. 提取 patches；
7. 冻结 experts；
8. 用统一 runtime core 测试单领域和跨领域任务；
9. 进行 no-joint-training composition test；
10. 进行单侧 patch update + cross-domain regression test。

只有 E0 成功，才扩展到更多 domain 和真正分布式训练。

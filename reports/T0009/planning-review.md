# T0009 交接规划核对

- 日期：2026-09-18；规划：Codex + `gpt-6-astra`，`xhigh`。
- 非作者独立审阅：`/root/review_t0009_design`，`gpt-6-astra`，`xhigh`；只读原协议、前置实现、实际交接文本与交付检查器。最终结论：**ready，无未解决的设计阻塞**。未代写 Pi 产品／测试，也不是本任务产品验收。
- 基线：`bfb0f8e3c5c1c1168f7110ac6287aeb0f3330fff`，已推送 `origin/T0008-ground-derivations`，不从旧 master 开工。环境／前置接受哈希见 [planning-baseline.json](planning-baseline.json) 与 [preflight](planning-preflight/)；新产品／测试不存在。

## 已确定的范围与验证

1. 一个产品模块、一个测试文件、六个步骤。只展开单 query 的全部原始有序证明树，使用已有 ProofStep；不捆绑规范化、唯一性、深度或 motif 的研究设计。
2. 全世界先完成 T0008；相关 Atom 的全部来源反向索引后迭代展开。固定后序、按前提位置作笛卡尔积，共享子证明重复展开，不误枚举 verifier 允许的无限冗余 step 序列。
3. 三项预算及异常分清：原有两个 T0008 限额、本层相关缓存步骤总量；构造前检查、精确边界成功、超限无部分结果。返回量不当作规范证明数量。
4. 审阅者逐项手算 P0–P10 的 C/D/S、输出顺序、引用及全部组合；P7 的四棵长度 5 树累计 S=30；长链 S=721801；组合网格 S=a+b+3ab，均一致。
5. [planning_examples.py](planning_examples.py) 只保存显式手写证明及缓存长度；[实际运行](planning-examples/) exit 0，T0006 核验所有示例证明和篡改反例，T0008 核验 C/D 精确／少一边界。**S 仍是规划手算，不是尚未实现的 T0009 实测。** 没有实现证明枚举器或重跑既有全量测试。
6. 交付提供沿用记录器及 [check_delivery.py](check_delivery.py)，Pi 不再自行猜测驱动。检查器核对范围、旧源码／规划冻结、链接与文本／状态；不替代实质验收。独占 RUN 与 basetemp，不覆盖失败历史，不串合同外 doctor。

## 审阅修订与澄清

- 长链测试原“前向引用”措辞已改为严格指向此前步骤 `ref < 当前步号`。
- 采纳共享祖先多来源的 P7，显式检查右子树内部引用 offset 及 29/30 边界。
- 审阅中曾疑似缺 pytest scratch 忽略，现已撤回：`.gitignore` 从规划起即含 `*/pytest-tmp/`；对不存在且无尾斜杠的目录作 git check-ignore 导致误判。对具体子文件路径检查确认规则生效，无需修改。
- 所有旧源码、测试与历史报告不改；本次只将 T0008 当前状态绑定到已推送提交，并追加后续任务关联，不回写历史验收证据。

## 交接与证据边界

[交接文档](../../docs/handoffs/T0009-proof-enumeration.md) 为 ready，产品／新增测试为 not_run。既有 607 项回归来自已验收 T0008；本轮不将其写成重新执行结果。Pi 按交接实施后交 Codex，届时才核验 A1–A7。

规划材料和 T0008／D27 关联文档的冻结清单将保存为 `planning-files.json`，Pi 不修改。T0009 交接状态／执行记录、README、实现状态允许按任务流程更新；产品仅限新模块和新测试。本轮不 commit/push。
